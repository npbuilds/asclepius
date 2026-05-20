"""Phase-gated rNPV with Monte Carlo.

The framing: phase-gated CASH FLOWS, not just terminal value. Development costs
are PoS-weighted at each gate (you abandon on failure → costs stop). Revenue is
discounted from the projected launch date and weighted by cumulative LOA from
the current phase.

  rNPV = Σ_t [revenue_t * LOA_remaining - cost_t * PoS_to_reach_t] / (1 + r)^t

The closed-form gives the base case. The Monte Carlo wraps the same engine with
parametric draws (log-normal peak sales, beta-distributed LOA, normal WACC,
triangular COGS) and produces a distribution with P25/P50/P75 for the dashboard.

Seeded by default for reproducibility — same inputs always produce the same
histogram, which matters for snapshot tests and demo reliability.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...domain import (
    AssetInput,
    DiligenceRecord,
    Phase,
    PoSResult,
    RnpvInputs,
    RnpvResult,
    TornadoBar,
)

# Monte Carlo defaults — tuned for snappy interactive use; 10k paths converge
# the percentiles to ~0.5% precision while running in <50ms on a laptop.
_DEFAULT_MC_PATHS = 10_000
_DEFAULT_MC_SEED = 42


@dataclass
class _Timeline:
    """Time offsets (years from t=0) for each gate and launch."""

    end_phase_1: float
    end_phase_2: float
    end_phase_3: float
    launch: float


def _build_timeline(inputs: RnpvInputs, current_phase: Phase) -> _Timeline:
    """Anchors timeline at t=0 = current decision point.

    Years_per_phase keys: 'phase_1', 'phase_2', 'phase_3', 'regulatory'.
    Phases already completed contribute 0.
    """
    ypp = inputs.years_per_phase

    cursor = 0.0
    end_p1 = cursor + (ypp["phase_1"] if current_phase == Phase.PHASE_1 else 0.0)
    cursor = end_p1
    end_p2 = cursor + (
        ypp["phase_2"] if current_phase in (Phase.PHASE_1, Phase.PHASE_2) else 0.0
    )
    cursor = end_p2
    end_p3 = cursor + (
        ypp["phase_3"]
        if current_phase in (Phase.PHASE_1, Phase.PHASE_2, Phase.PHASE_3)
        else 0.0
    )
    cursor = end_p3
    launch = cursor + ypp.get("regulatory", 1.0)
    return _Timeline(end_p1, end_p2, end_p3, launch)


def _phase_pos(phase: Phase, transitions: dict[str, float]) -> dict[str, float]:
    """Probability of *reaching* each gate from current phase.

    Costs at each gate are weighted by the probability of reaching that gate.
    """
    p12 = transitions.get("p1_to_p2", 0.5)
    p23 = transitions.get("p2_to_p3", 0.3)
    p3n = transitions.get("p3_to_nda", 0.6)
    pna = transitions.get("nda_to_approval", 0.9)

    if phase == Phase.PHASE_1:
        return {
            "reach_p2": p12,
            "reach_p3": p12 * p23,
            "reach_launch": p12 * p23 * p3n * pna,
        }
    if phase == Phase.PHASE_2:
        return {"reach_p2": 1.0, "reach_p3": p23, "reach_launch": p23 * p3n * pna}
    if phase == Phase.PHASE_3:
        return {"reach_p2": 1.0, "reach_p3": 1.0, "reach_launch": p3n * pna}
    if phase == Phase.NDA:
        return {"reach_p2": 1.0, "reach_p3": 1.0, "reach_launch": pna}
    return {"reach_p2": 1.0, "reach_p3": 1.0, "reach_launch": 1.0}


def _closed_form_rnpv(
    asset: AssetInput, pos: PoSResult, inputs: RnpvInputs
) -> float:
    """Single deterministic rNPV evaluation."""
    timeline = _build_timeline(inputs, asset.phase)
    pp = _phase_pos(asset.phase, pos.phase_transitions)
    r = inputs.wacc
    loa = pos.final_loa

    # ---- Cost side: discount + PoS-weight each phase cost ----
    pv_cost = 0.0

    if asset.phase == Phase.PHASE_1:
        # Phase 1 cost incurred over phase 1 timeline; weight = 1.0 (we're here)
        pv_cost += _discount_over_period(
            inputs.dev_cost_phase_1_usd_m, 0.0, timeline.end_phase_1, r
        )
    if asset.phase in (Phase.PHASE_1, Phase.PHASE_2):
        pv_cost += pp["reach_p2"] * _discount_over_period(
            inputs.dev_cost_phase_2_usd_m, timeline.end_phase_1, timeline.end_phase_2, r
        )
    if asset.phase in (Phase.PHASE_1, Phase.PHASE_2, Phase.PHASE_3):
        pv_cost += pp["reach_p3"] * _discount_over_period(
            inputs.dev_cost_phase_3_usd_m, timeline.end_phase_2, timeline.end_phase_3, r
        )
    # Launch cost incurred at approval, weighted by LOA
    pv_cost += loa * inputs.launch_cost_usd_m / ((1 + r) ** timeline.launch)

    # ---- Revenue side: linear ramp to peak, decay flat, exclusivity-bounded ----
    # Mid-year convention: each annual cash flow is discounted as if received
    # at the midpoint of its year (t_offset + 0.5). Practitioner default;
    # avoids the rNPV overstatement of beginning-of-year and the understatement
    # of strict year-end discounting.
    pv_revenue = 0.0
    for t_offset in range(0, inputs.years_of_exclusivity):
        year = timeline.launch + t_offset + 0.5
        ramp = min(1.0, (t_offset + 1) / max(inputs.years_to_peak, 1))
        annual_sales = inputs.peak_sales_usd_m * ramp
        annual_after_cogs = annual_sales * (1.0 - inputs.cogs_pct)
        pv_revenue += loa * annual_after_cogs / ((1 + r) ** year)

    return pv_revenue - pv_cost


def _discount_over_period(amount: float, t_start: float, t_end: float, r: float) -> float:
    """Discount a cost smeared evenly between t_start and t_end."""
    if t_end <= t_start:
        return amount / ((1 + r) ** t_start)
    # Approximate by discounting at the midpoint
    midpoint = (t_start + t_end) / 2
    return amount / ((1 + r) ** midpoint)


def _downside_failed_p3(
    asset: AssetInput, pos: PoSResult, inputs: RnpvInputs
) -> float:
    """Conservative terminal value if asset fails at Phase 3.

    For v1: residual = cash committed to Phase 3 is lost; IP residual = 10% of
    forgone present value of revenue (cost recovery in a fire-sale licensing
    scenario). Returns a negative number (the loss).
    """
    timeline = _build_timeline(inputs, asset.phase)
    r = inputs.wacc
    lost_p3 = inputs.dev_cost_phase_3_usd_m / (
        (1 + r) ** ((timeline.end_phase_2 + timeline.end_phase_3) / 2)
    )
    ip_residual = (
        0.10 * inputs.peak_sales_usd_m * (1 - inputs.cogs_pct) / ((1 + r) ** timeline.launch)
    )
    return -lost_p3 + ip_residual


# ---- Tornado: one-at-a-time low/high swings on the top variables ----

_TORNADO_SWINGS = [
    ("peak_sales_usd_m", 0.70, 1.30),
    ("wacc", 0.80, 1.20),
    ("cogs_pct", 0.75, 1.25),
    ("dev_cost_phase_3_usd_m", 0.80, 1.20),
]


def _tornado(
    asset: AssetInput, pos: PoSResult, inputs: RnpvInputs, base_case: float
) -> list[TornadoBar]:
    bars: list[TornadoBar] = []
    for var, low_factor, high_factor in _TORNADO_SWINGS:
        low_inputs = inputs.model_copy(update={var: getattr(inputs, var) * low_factor})
        high_inputs = inputs.model_copy(update={var: getattr(inputs, var) * high_factor})
        low_val = _closed_form_rnpv(asset, pos, low_inputs)
        high_val = _closed_form_rnpv(asset, pos, high_inputs)
        bars.append(
            TornadoBar(
                variable=var,
                low_value_usd_m=round(low_val, 1),
                high_value_usd_m=round(high_val, 1),
                swing_usd_m=round(abs(high_val - low_val), 1),
            )
        )
    # Sort by swing magnitude (descending) — biggest sensitivity first
    bars.sort(key=lambda b: b.swing_usd_m, reverse=True)
    return bars


# ---- Monte Carlo ----


def _draw_inputs(
    rng: np.random.Generator,
    inputs: RnpvInputs,
    loa: float,
    n: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Sample n draws from the parametric prior over the four key sensitivities.

      * peak_sales: log-normal, median = inputs.peak_sales_usd_m, σ_log = 0.35
        (so the user's input is the central tendency; the right-tail mean
        sits ~6% above the input to reflect blockbuster optionality)
      * loa: beta, mean = loa, concentration κ = 30 (tight around mean)
      * wacc: normal, mean = inputs.wacc, σ = 0.02 (200bps), clipped [0.04, 0.25]
      * cogs: triangular, mode = inputs.cogs_pct, range = ±10pp clipped [0,0.95]

    Distribution choices reflect the real shape of biotech inputs: peak sales
    is right-skewed (blockbuster upside, bounded downside); LOA is bounded
    [0,1] and clustered around the point estimate; WACC has moderate normal
    noise; COGS has triangular bounded uncertainty.
    """
    sigma_log = 0.35
    # μ = log(input) → numpy lognormal has median exp(μ) = input. Mean is
    # input * exp(σ²/2) (~1.063 * input for σ=0.35), giving an asymmetric
    # upside that matches practitioner intuition for "peak sales."
    mu_log = np.log(inputs.peak_sales_usd_m)
    peak_sales = rng.lognormal(mean=mu_log, sigma=sigma_log, size=n)

    # Beta with given mean and concentration κ → α=mean*κ, β=(1-mean)*κ
    kappa = 30.0
    mean = max(0.001, min(0.999, loa))
    alpha = mean * kappa
    beta_param = (1.0 - mean) * kappa
    loa_draws = rng.beta(alpha, beta_param, size=n)

    wacc = np.clip(rng.normal(inputs.wacc, 0.02, size=n), 0.04, 0.25)

    cogs_low = max(0.0, inputs.cogs_pct - 0.10)
    cogs_high = min(0.95, inputs.cogs_pct + 0.10)
    cogs = rng.triangular(cogs_low, inputs.cogs_pct, cogs_high, size=n)

    return peak_sales, loa_draws, wacc, cogs


def _vectorized_rnpv(
    asset: AssetInput,
    pos: PoSResult,
    inputs: RnpvInputs,
    peak_sales: np.ndarray,
    loa: np.ndarray,
    wacc: np.ndarray,
    cogs: np.ndarray,
) -> np.ndarray:
    """Vectorized rNPV evaluation across the Monte Carlo sample.

    Same math as `_closed_form_rnpv` but applied with numpy arrays. We hold the
    timeline and PoS-of-reaching-each-gate fixed (those are deterministic given
    phase + transition table); peak sales / LOA / WACC / COGS vary per path.
    """
    timeline = _build_timeline(inputs, asset.phase)
    pp = _phase_pos(asset.phase, pos.phase_transitions)

    # Cost side — same logic as closed-form, vectorized over wacc
    pv_cost = np.zeros_like(wacc)
    if asset.phase == Phase.PHASE_1:
        pv_cost += _discount_array(
            inputs.dev_cost_phase_1_usd_m, 0.0, timeline.end_phase_1, wacc
        )
    if asset.phase in (Phase.PHASE_1, Phase.PHASE_2):
        pv_cost += pp["reach_p2"] * _discount_array(
            inputs.dev_cost_phase_2_usd_m,
            timeline.end_phase_1,
            timeline.end_phase_2,
            wacc,
        )
    if asset.phase in (Phase.PHASE_1, Phase.PHASE_2, Phase.PHASE_3):
        pv_cost += pp["reach_p3"] * _discount_array(
            inputs.dev_cost_phase_3_usd_m,
            timeline.end_phase_2,
            timeline.end_phase_3,
            wacc,
        )
    pv_cost += loa * inputs.launch_cost_usd_m / ((1 + wacc) ** timeline.launch)

    # Revenue side — mid-year convention (see _closed_form_rnpv for rationale)
    pv_revenue = np.zeros_like(wacc)
    for t_offset in range(inputs.years_of_exclusivity):
        year = timeline.launch + t_offset + 0.5
        ramp = min(1.0, (t_offset + 1) / max(inputs.years_to_peak, 1))
        annual_sales = peak_sales * ramp
        annual_after_cogs = annual_sales * (1.0 - cogs)
        pv_revenue += loa * annual_after_cogs / ((1 + wacc) ** year)

    return pv_revenue - pv_cost


def _discount_array(amount: float, t_start: float, t_end: float, wacc: np.ndarray) -> np.ndarray:
    """numpy-friendly version of _discount_over_period."""
    if t_end <= t_start:
        return amount / ((1 + wacc) ** t_start)
    midpoint = (t_start + t_end) / 2
    return amount / ((1 + wacc) ** midpoint)


def _run_monte_carlo(
    asset: AssetInput,
    pos: PoSResult,
    inputs: RnpvInputs,
    n_paths: int = _DEFAULT_MC_PATHS,
    seed: int = _DEFAULT_MC_SEED,
) -> tuple[float, float, float, np.ndarray]:
    """Run Monte Carlo and return (p25, p50, p75, full_sample)."""
    rng = np.random.default_rng(seed)
    peak_sales, loa_draws, wacc, cogs = _draw_inputs(rng, inputs, pos.final_loa, n_paths)
    sample = _vectorized_rnpv(asset, pos, inputs, peak_sales, loa_draws, wacc, cogs)
    p25, p50, p75 = np.percentile(sample, [25, 50, 75])
    return float(p25), float(p50), float(p75), sample


# ---- Required entrypoint for the registry ----


def compute(record: DiligenceRecord) -> RnpvResult:
    if record.pos is None:
        raise ValueError("rNPV requires a computed PoS result on the record")
    if record.rnpv_inputs is None:
        raise ValueError("rNPV requires rnpv_inputs on the record")

    base = _closed_form_rnpv(record.asset, record.pos, record.rnpv_inputs)
    downside = _downside_failed_p3(record.asset, record.pos, record.rnpv_inputs)
    tornado = _tornado(record.asset, record.pos, record.rnpv_inputs, base)

    # Monte Carlo
    p25, p50, p75, _sample = _run_monte_carlo(
        record.asset, record.pos, record.rnpv_inputs
    )

    return RnpvResult(
        base_case_usd_m=round(base, 1),
        low_case_usd_m=round(p25, 1),
        high_case_usd_m=round(p75, 1),
        downside_failed_p3_usd_m=round(downside, 1),
        tornado=tornado,
        monte_carlo_paths=_DEFAULT_MC_PATHS,
        monte_carlo_p25_usd_m=round(p25, 1),
        monte_carlo_p50_usd_m=round(p50, 1),
        monte_carlo_p75_usd_m=round(p75, 1),
    )
