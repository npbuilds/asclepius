"""Portfolio Sizing engine tests — Kelly math, barbell, multi-asset aggregation."""

from __future__ import annotations

import pytest

from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    PoSAdjustment,
    PoSResult,
    RnpvResult,
    TherapeuticArea,
)
from app.modules.portfolio_sizing import engine
from app.modules.portfolio_sizing.engine import (
    MAX_PAYOFF_MULTIPLE,
    _kelly_fraction,
    _payoff_multiple,
)
from app.modules.portfolio_sizing.schemas import (
    AssetSizingInput,
    FundParameters,
    PortfolioRequest,
)


def _pos(loa: float) -> PoSResult:
    return PoSResult(
        base_rate=loa * 0.7,
        final_loa=loa,
        confidence_low=loa * 0.7,
        confidence_high=min(loa * 1.3, 1.0),
        adjustments=[
            PoSAdjustment(name="t", multiplier=1.0, rationale="r", source="s")
        ],
    )


def _rnpv(base: float, downside: float | None = -100.0) -> RnpvResult:
    return RnpvResult(
        base_case_usd_m=base,
        downside_failed_p3_usd_m=downside,
    )


def _asset(name: str = "test_asset") -> AssetInput:
    return AssetInput(
        asset_name=name,
        phase=Phase.PHASE_2,
        therapeutic_area=TherapeuticArea.ONCOLOGY,
        modality=Modality.SMALL_MOLECULE,
        capital_position=CapitalPosition.ADEQUATE,
    )


def _sizing(
    name: str = "x",
    loa: float = 0.16,
    base: float = 500.0,
    downside: float = -100.0,
    conviction: float = 1.0,
) -> AssetSizingInput:
    return AssetSizingInput(
        asset=_asset(name),
        pos=_pos(loa),
        rnpv=_rnpv(base, downside),
        conviction=conviction,
    )


# ---------------------------------------------------------------------------
# Kelly math
# ---------------------------------------------------------------------------


def test_kelly_fraction_positive_when_edge_exists():
    """f* = (bp - q)/b. p=0.16, b=5 (10:1 odds): f* = (5*0.16 - 0.84)/5 = -0.008
    p=0.30, b=5: f* = (5*0.30 - 0.70)/5 = 0.16. Picks the asset with edge."""
    assert _kelly_fraction(0.16, 5.0) < 0  # no edge → don't bet
    assert _kelly_fraction(0.30, 5.0) > 0  # edge exists
    assert _kelly_fraction(0.30, 5.0) == pytest.approx(0.16, abs=1e-6)


def test_kelly_fraction_zero_b_returns_zero():
    """b=0 means no payoff if you win — never bet."""
    assert _kelly_fraction(0.5, 0.0) == 0.0
    assert _kelly_fraction(0.5, -1.0) == 0.0


# ---------------------------------------------------------------------------
# Payoff multiple
# ---------------------------------------------------------------------------


def test_payoff_multiple_uses_conditional_upside():
    """Biotech-VC Kelly: b = (base_case/LOA - |downside|) / |downside|.
    For base=500, LOA=0.16, downside=-100:
      conditional_upside = 500/0.16 = 3125
      b = (3125 - 100)/100 = 30.25
    """
    assert _payoff_multiple(_rnpv(500.0, -100.0), 0.16) == pytest.approx(30.25, rel=1e-3)


def test_payoff_multiple_missing_downside_uses_default():
    """No downside scenario → cost_basis = 20% of conditional_upside.
    For base=500, LOA=0.50: conditional_upside=1000, cost_basis=200, b=4.0."""
    assert _payoff_multiple(_rnpv(500.0, downside=None), 0.50) == pytest.approx(4.0)


def test_payoff_multiple_caps_at_max():
    """Near-zero downside should not blow up Kelly."""
    assert _payoff_multiple(_rnpv(500.0, -1e-9), 0.50) == MAX_PAYOFF_MULTIPLE


def test_payoff_multiple_zero_loa_returns_zero():
    """If LOA is 0, no Kelly bet — return 0 multiplier."""
    assert _payoff_multiple(_rnpv(500.0, -100.0), 0.0) == 0.0


# ---------------------------------------------------------------------------
# Single-asset sizing (registry contract)
# ---------------------------------------------------------------------------


def test_single_asset_sizing_negative_kelly_marked_correctly():
    """Negative Kelly arises when downside is close to the conditional upside
    so b is small relative to LOA's odds. LOA=0.05, base=100, downside=-1500:
    conditional_upside=2000, b=(2000-1500)/1500=0.333, Kelly < 0 because
    0.05 < 1/(0.333+1)=0.75."""
    result = engine.compute(
        DiligenceRecord(
            asset=_asset(), pos=_pos(0.05), rnpv=_rnpv(100.0, -1500.0)
        )
    )
    assert result.status == "negative_kelly"
    assert result.final_weight == 0.0
    assert result.kelly_optimal < 0
    assert "kelly negative" in result.rationale.lower()


def test_single_asset_sizing_recommended_path():
    """Reasonable assumptions → recommended position, no cap or floor hit."""
    result = engine.compute(
        DiligenceRecord(
            asset=_asset("adagrasib"), pos=_pos(0.50), rnpv=_rnpv(500.0, -100.0)
        )
    )
    assert result.status == "recommended"
    assert result.final_weight > 0.0
    assert result.kelly_optimal > 0.0
    assert result.kelly_fractional <= result.kelly_optimal


def test_single_asset_sizing_above_cap_pinned():
    """Strong asset + 1.5x conviction should hit the 20% default cap."""
    record = DiligenceRecord(
        asset=_asset(), pos=_pos(0.75), rnpv=_rnpv(1000.0, -50.0)
    )
    # default conviction 1.0 in compute() but we test sizing directly with 1.5
    sized = engine._size_single_asset(
        AssetSizingInput(
            asset=record.asset, pos=record.pos, rnpv=record.rnpv, conviction=1.5
        ),
        FundParameters(total_capital_usd_m=100.0, max_position_pct=0.20),
    )
    assert sized.status == "above_cap"
    assert sized.final_weight == pytest.approx(0.20)


def test_single_asset_sizing_below_floor_dropped():
    """Borderline-positive Kelly but small enough to fall under floor.

    LOA=0.40, b=2.0 → Kelly = (2*0.4 - 0.6)/2 = 0.10.
    Kelly × 0.25 fractional × 0.5 conviction = 0.0125, below 0.05 floor.
    """
    sized = engine._size_single_asset(
        _sizing(loa=0.40, base=200.0, downside=-100.0, conviction=0.5),
        FundParameters(
            total_capital_usd_m=100.0,
            kelly_fraction=0.25,
            min_position_pct=0.05,
        ),
    )
    assert sized.status == "below_floor"
    assert sized.final_weight == 0.0
    assert sized.kelly_optimal > 0  # confirms it's below-floor, not negative-kelly


def test_single_asset_sizing_missing_pos_or_rnpv_graceful():
    """compute() degrades gracefully when deps haven't been computed."""
    record = DiligenceRecord(asset=_asset(), pos=None, rnpv=None)
    result = engine.compute(record)
    assert result.status == "negative_kelly"
    assert result.final_weight == 0.0
    assert "dependencies" in result.rationale.lower()


# ---------------------------------------------------------------------------
# Multi-asset allocator
# ---------------------------------------------------------------------------


def test_multi_asset_aggregation():
    """Aggregates per-asset sizes into a portfolio with summary stats."""
    req = PortfolioRequest(
        assets=[
            _sizing("strong", loa=0.50, base=500, downside=-100),
            _sizing("weak", loa=0.10, base=200, downside=-150),
            _sizing("middle", loa=0.30, base=400, downside=-80),
        ],
        fund=FundParameters(total_capital_usd_m=100.0),
    )
    rec = engine.recommend_portfolio(req)
    assert len(rec.positions) == 3
    # The weak asset should be either negative_kelly or below_floor
    weak = next(p for p in rec.positions if p.asset_name == "weak")
    assert weak.status in ("negative_kelly", "below_floor")
    assert weak.final_weight == 0.0
    # Total deployed ≤ 1.0 (no over-allocation in v2.0)
    assert 0.0 <= rec.total_deployed_pct <= 1.0
    # USD amounts consistent
    assert rec.total_deployed_usd_m == pytest.approx(
        rec.total_deployed_pct * 100.0, abs=0.01
    )
    assert rec.cash_residual_usd_m == pytest.approx(
        rec.cash_residual_pct * 100.0, abs=0.01
    )


def test_gini_extremes():
    """Gini = 0 for perfectly equal weights, → 1 for all weight on one."""
    # 3 equal positions → low Gini
    assert engine._gini([0.10, 0.10, 0.10]) == pytest.approx(0.0, abs=1e-6)
    # All weight on one → high Gini
    assert engine._gini([0.30, 0.0, 0.0]) == pytest.approx(1.0, abs=1e-6)
    # Empty
    assert engine._gini([]) == 0.0


def test_portfolio_counts_categorize_correctly():
    """Each status maps to a counter; counts should sum to n_assets."""
    req = PortfolioRequest(
        assets=[
            _sizing("strong1", loa=0.60, base=1000, downside=-50),  # likely above_cap
            _sizing("ok", loa=0.30, base=400, downside=-100),  # recommended
            _sizing("weak", loa=0.05, base=100, downside=-100),  # negative_kelly
            _sizing("tiny", loa=0.22, base=200, downside=-150, conviction=0.5),  # below_floor
        ],
        fund=FundParameters(
            total_capital_usd_m=100.0,
            kelly_fraction=0.25,
            max_position_pct=0.20,
            min_position_pct=0.05,
        ),
    )
    rec = engine.recommend_portfolio(req)
    total = (
        rec.n_recommended + rec.n_below_floor + rec.n_above_cap + rec.n_negative_kelly
    )
    assert total == 4


def test_fund_parameters_reject_inverted_bounds():
    """min_position_pct must be < max_position_pct."""
    with pytest.raises(ValueError):
        FundParameters(
            total_capital_usd_m=100.0,
            min_position_pct=0.30,
            max_position_pct=0.20,
        )
