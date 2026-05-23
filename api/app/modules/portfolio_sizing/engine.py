"""Portfolio Sizing engine — Kelly + fractional + conviction + barbell.

Math reference: Thorp (1969), Kelly (1956). For biotech VC application,
practitioner consensus on fractional-Kelly multipliers in the 0.20-0.30
range is documented in the Archon `position-sizing` skill (the v1
audience-expansion the v2 module operationalizes).

The chain is auditable like the PoS waterfall:
  kelly_optimal → × fund.kelly_fraction → × asset.conviction → cap+floor

Each step produces a field on AssetKellyResult so the rationale string
can name which step was load-bearing.
"""

from __future__ import annotations

from ...domain import DiligenceRecord, PoSAdjustment, RnpvResult
from .schemas import (
    AssetKellyResult,
    AssetSizingInput,
    FundParameters,
    PortfolioRecommendation,
    PortfolioRequest,
)

# Practical ceiling — payoff_multiple from rNPV base / |downside| can blow up
# when downside is near zero. Cap at 100x to keep Kelly finite; the cap
# basically never binds for real biotech assets (rNPV downsides are
# materially negative because Phase 3 dev costs + IP residual is small).
MAX_PAYOFF_MULTIPLE = 100.0


def _payoff_multiple(rnpv: RnpvResult, pos_loa: float) -> float:
    """b in Kelly's f* = (bp - q)/b — the biotech-standard
    conditional-on-success payoff multiple.

    The original (incorrect) formulation: `base_case / |downside|` treats
    base_case as the success payoff, but base_case is already
    probability-weighted (it's the rNPV, not the conditional-on-success
    value). That under-states the multiplier because the probability
    factor is double-counted (Kelly already takes p as a separate input).

    The correct formulation, used here:
      conditional_upside = base_case_rnpv / LOA
      cost_basis         = |downside_failed_p3|  (capital at risk if fail)
      b                  = (conditional_upside - cost_basis) / cost_basis

    This is the standard biotech-VC Kelly formulation — the asset returns
    multiple-of-cost-basis at exit if it succeeds, and you lose cost-basis
    if it fails. Documented in methodology/11-portfolio-sizing.md.
    """
    if pos_loa <= 0:
        return 0.0
    conditional_upside = rnpv.base_case_usd_m / pos_loa
    downside = rnpv.downside_failed_p3_usd_m
    if downside is None or downside == 0:
        # No explicit downside scenario — fall back to a conservative
        # cost_basis = 20% of conditional_upside (i.e., assume you lose
        # ~20% of what you would have made if you succeed; very rough).
        cost_basis = 0.20 * conditional_upside
    elif downside > 0:
        # Pathological — "downside" is positive. Treat as small loss to
        # produce a finite multiple, capped below.
        cost_basis = 1.0
    else:
        cost_basis = abs(downside)
    if cost_basis < 1e-6:
        return MAX_PAYOFF_MULTIPLE
    raw = (conditional_upside - cost_basis) / cost_basis
    return max(0.0, min(MAX_PAYOFF_MULTIPLE, raw))


def _kelly_fraction(p: float, b: float) -> float:
    """Raw Kelly: f* = (bp - q)/b where q = 1-p. May be negative."""
    q = 1.0 - p
    if b <= 0:
        return 0.0
    return (b * p - q) / b


def _size_single_asset(
    asset_sizing: AssetSizingInput,
    fund: FundParameters,
) -> AssetKellyResult:
    """Run the full chain on one asset. The portfolio-level allocator just
    iterates this; each asset is sized in isolation (no covariance term in
    v2.0 — assets are treated as conditionally independent, documented
    limitation)."""

    p = asset_sizing.pos.final_loa
    b = _payoff_multiple(asset_sizing.rnpv, p)
    k_opt = _kelly_fraction(p, b)
    k_frac = max(0.0, k_opt * fund.kelly_fraction)
    conviction_applied = min(1.0, k_frac * asset_sizing.conviction)

    # Apply cap + floor
    rationale_parts: list[str] = []
    if k_opt < 0:
        status = "negative_kelly"
        final = 0.0
        rationale_parts.append(
            f"Kelly negative ({k_opt:.3f}) — PoS {p:.1%} too low for "
            f"payoff multiple {b:.1f}x. Skip."
        )
    elif conviction_applied < fund.min_position_pct:
        status = "below_floor"
        final = 0.0
        rationale_parts.append(
            f"Sizing {conviction_applied:.1%} below floor "
            f"{fund.min_position_pct:.1%} — too small to move the "
            f"portfolio. Skip."
        )
    elif conviction_applied > fund.max_position_pct:
        status = "above_cap"
        final = fund.max_position_pct
        rationale_parts.append(
            f"Sizing {conviction_applied:.1%} hits the {fund.max_position_pct:.0%} "
            f"max-position cap (barbell ceiling). Allocation pinned at cap."
        )
    else:
        status = "recommended"
        final = conviction_applied
        rationale_parts.append(
            f"Kelly {k_opt:.3f} × {fund.kelly_fraction:.2f} fractional × "
            f"{asset_sizing.conviction:.2f} conviction = {final:.1%} of fund."
        )

    return AssetKellyResult(
        asset_name=asset_sizing.asset.asset_name,
        pos=p,
        payoff_multiple=round(b, 2),
        kelly_optimal=round(k_opt, 4),
        kelly_fractional=round(k_frac, 4),
        conviction_applied=round(conviction_applied, 4),
        final_weight=round(final, 4),
        status=status,
        rationale=" ".join(rationale_parts),
    )


def _gini(weights: list[float]) -> float:
    """Gini coefficient of position weights. 0 = perfectly equal, 1 = all on
    one position. Used as a barbell-concentration metric."""
    nonzero = [w for w in weights if w > 0]
    n = len(nonzero)
    if n == 0:
        return 0.0
    if n == 1:
        return 1.0
    nonzero.sort()
    cumsum = 0.0
    total = sum(nonzero)
    for i, w in enumerate(nonzero, start=1):
        cumsum += i * w
    # Standard Gini formula on sorted positive weights
    return (2 * cumsum) / (n * total) - (n + 1) / n


def recommend_portfolio(request: PortfolioRequest) -> PortfolioRecommendation:
    """Multi-asset allocator. The custom POST /portfolio route calls this."""
    positions = [_size_single_asset(a, request.fund) for a in request.assets]

    total_pct = sum(p.final_weight for p in positions)
    total_usd = total_pct * request.fund.total_capital_usd_m

    # Expected-value rNPV: probability-weighted sum across positions
    ev = 0.0
    for asset_input, sized in zip(request.assets, positions):
        if sized.final_weight <= 0:
            continue
        # The position's expected $ payoff: pos × upside + (1-pos) × downside.
        # Scale by position's fraction of fund — the EV in $M assumes the
        # weight is how much of the fund is exposed to that asset's payoff.
        upside = asset_input.rnpv.base_case_usd_m
        downside = asset_input.rnpv.downside_failed_p3_usd_m or 0.0
        expected_position = sized.pos * upside + (1 - sized.pos) * downside
        ev += sized.final_weight * expected_position

    counts = {
        "recommended": sum(1 for p in positions if p.status == "recommended"),
        "below_floor": sum(1 for p in positions if p.status == "below_floor"),
        "above_cap": sum(1 for p in positions if p.status == "above_cap"),
        "negative_kelly": sum(1 for p in positions if p.status == "negative_kelly"),
    }

    return PortfolioRecommendation(
        positions=positions,
        total_deployed_pct=round(total_pct, 4),
        total_deployed_usd_m=round(total_usd, 2),
        cash_residual_pct=round(1.0 - total_pct, 4),
        cash_residual_usd_m=round(
            (1.0 - total_pct) * request.fund.total_capital_usd_m, 2
        ),
        gini_coefficient=round(_gini([p.final_weight for p in positions]), 4),
        expected_value_rnpv_usd_m=round(ev, 2),
        n_recommended=counts["recommended"],
        n_below_floor=counts["below_floor"],
        n_above_cap=counts["above_cap"],
        n_negative_kelly=counts["negative_kelly"],
    )


# ---------------------------------------------------------------------------
# Standard module entry point — single-asset Kelly only (registry contract)
# ---------------------------------------------------------------------------


def compute(record: DiligenceRecord) -> AssetKellyResult:
    """Required by the module registry. Returns single-asset Kelly with
    default fund parameters and conviction 1.0. Useful for 'what would
    sizing recommend if this were the only asset?' framing.

    Multi-asset portfolio sizing goes through the custom POST /portfolio
    route in routes.py — the registry's standard `compute(record)` does
    not naturally accept a list of records.
    """
    if record.pos is None or record.rnpv is None:
        # Defensive: degrade gracefully if PoS / rNPV haven't been computed
        return AssetKellyResult(
            asset_name=record.asset.asset_name,
            pos=0.0,
            payoff_multiple=0.0,
            kelly_optimal=0.0,
            kelly_fractional=0.0,
            conviction_applied=0.0,
            final_weight=0.0,
            status="negative_kelly",
            rationale=(
                "Cannot size — PoS and rNPV must be computed before "
                "portfolio sizing. The module's dependencies (pos, rnpv) "
                "are unmet."
            ),
        )
    return _size_single_asset(
        AssetSizingInput(
            asset=record.asset,
            pos=record.pos,
            rnpv=record.rnpv,
            conviction=1.0,
        ),
        FundParameters(total_capital_usd_m=100.0),
    )


# Make a no-op PoSAdjustment reference live in the engine module's namespace
# so any future "the module's adjustments end up on the record" wiring has a
# class to construct. Currently unused — placeholder for v2.1.
_ = PoSAdjustment
