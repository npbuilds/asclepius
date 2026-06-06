"""rNPV engine tests — closed-form base case and tornado sanity."""

from __future__ import annotations

from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    RnpvInputs,
    TherapeuticArea,
)
from app.modules.rnpv.engine import compute
from app.modules.pos.engine import compute as compute_pos
from app.registry import reset_registry_for_tests


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _record(**rnpv_overrides) -> DiligenceRecord:
    asset = AssetInput(
        asset_name="TestAsset",
        phase=Phase.PHASE_2,
        therapeutic_area=TherapeuticArea.ONCOLOGY,
        modality=Modality.SMALL_MOLECULE,
        capital_position=CapitalPosition.ADEQUATE,
    )
    fields: dict = {"peak_sales_usd_m": 500.0, "wacc": 0.12}
    fields.update(rnpv_overrides)
    rnpv_inputs = RnpvInputs(**fields)
    record = DiligenceRecord(asset=asset, rnpv_inputs=rnpv_inputs)
    record.pos = compute_pos(record)
    return record


def test_base_case_returns_finite_number() -> None:
    record = _record()
    out = compute(record)
    assert out.base_case_usd_m == out.base_case_usd_m  # not NaN
    # For a Phase 2 oncology with $500M peak sales and adequate capital, base case
    # rNPV should be positive but small relative to peak (LOA ~11%).
    assert -200 < out.base_case_usd_m < 200


def test_higher_peak_sales_raises_rnpv() -> None:
    low = compute(_record(peak_sales_usd_m=300.0)).base_case_usd_m
    high = compute(_record(peak_sales_usd_m=1000.0)).base_case_usd_m
    assert high > low


def test_lower_wacc_raises_rnpv() -> None:
    cheap = compute(_record(wacc=0.08)).base_case_usd_m
    expensive = compute(_record(wacc=0.20)).base_case_usd_m
    assert cheap > expensive


def test_tornado_has_four_bars_sorted_by_swing() -> None:
    out = compute(_record())
    assert len(out.tornado) == 4
    swings = [b.swing_usd_m for b in out.tornado]
    assert swings == sorted(swings, reverse=True)


def test_downside_is_negative() -> None:
    out = compute(_record(peak_sales_usd_m=500.0))
    # Failed P3 should be a loss for a Phase 2 asset
    assert out.downside_failed_p3_usd_m is not None
    assert out.downside_failed_p3_usd_m < 0


def test_monte_carlo_percentiles_are_ordered_and_finite() -> None:
    out = compute(_record())
    assert out.monte_carlo_paths == 10_000
    assert out.monte_carlo_p25_usd_m is not None
    assert out.monte_carlo_p50_usd_m is not None
    assert out.monte_carlo_p75_usd_m is not None
    assert out.monte_carlo_p25_usd_m < out.monte_carlo_p50_usd_m < out.monte_carlo_p75_usd_m


def test_monte_carlo_is_deterministic_under_seed() -> None:
    """Same inputs → same percentiles (default seed makes runs reproducible)."""
    out1 = compute(_record())
    out2 = compute(_record())
    assert out1.monte_carlo_p50_usd_m == out2.monte_carlo_p50_usd_m


def test_mc_peak_sales_sampling_has_median_at_input() -> None:
    """Targeted assertion that the lognormal peak-sales sampling has
    median ≈ input. Catches regressions where someone reintroduces the
    `- 0.5 * sigma**2` mean-correction that biases the median ~6% below the
    user's input (this was a real bug — see Codex review 2026-05-18).
    """
    import numpy as np
    from app.modules.rnpv.engine import _draw_inputs

    record = _record(peak_sales_usd_m=1500.0)
    assert record.rnpv_inputs is not None and record.pos is not None
    rng = np.random.default_rng(42)
    peak_sales, _loa, _wacc, _cogs = _draw_inputs(
        rng, record.rnpv_inputs, record.pos.final_loa, n=50_000
    )
    rel = abs(float(np.median(peak_sales)) - 1500.0) / 1500.0
    assert rel < 0.02, (
        f"peak_sales median {float(np.median(peak_sales)):.1f} drifted "
        f"{rel:.1%} from input 1500.0 — lognormal sampling regressed"
    )


def test_monte_carlo_median_within_bound_of_base_case() -> None:
    """End-to-end check that MC median tracks the closed-form base within a
    documented bound. The bound is loose (25%) because the LOA beta has
    measurable right-skew for low-LOA regimes (e.g. Phase 2 oncology at ~11%
    LOA produces a beta with median ~15% below mean), and that bias
    propagates linearly into the rNPV median.

    This is expected behavior, not a bug: when LOA is far from 0.5 the
    distribution of rNPV outcomes is asymmetric and median ≠ mean. A senior
    investor reads both the closed-form base and the MC P50 understanding
    that they differ for principled reasons. The targeted
    test_mc_peak_sales_sampling_has_median_at_input above catches sampling
    regressions specifically.
    """
    out = compute(_record(peak_sales_usd_m=2000.0))
    assert out.monte_carlo_p50_usd_m is not None
    assert out.base_case_usd_m > 100  # sanity: solidly positive regime
    rel = abs(out.monte_carlo_p50_usd_m - out.base_case_usd_m) / out.base_case_usd_m
    assert rel < 0.25, (
        f"MC median diverged from closed-form base by {rel:.1%}: "
        f"p50={out.monte_carlo_p50_usd_m} vs base={out.base_case_usd_m}"
    )


def test_phase_3_higher_rnpv_than_phase_2_same_inputs() -> None:
    """Same economics, but Phase 3 has higher cumulative LOA → higher rNPV.

    Note: target_validated=True is set explicitly so the v1.7.7 unvalidated-target
    hard-cap (see methodology/21-aducanumab-contested-retrospective.md and
    api/app/modules/pos/engine.py) does NOT fire. Otherwise, the cap would
    drag the Phase-3 PoS below the Phase-2 PoS for the same asset because the
    Phase-3 multiplier chain blows through the cohort × 3 ceiling while the
    Phase-2 chain does not — flipping this invariant. The invariant being
    tested here ('more advanced phase → higher rNPV') is conditional on at
    least one of the validation levers being on; with both off, the framework
    correctly refuses to grant the phase-advancement uplift.
    """
    asset_p2 = AssetInput(
        asset_name="A",
        phase=Phase.PHASE_2,
        therapeutic_area=TherapeuticArea.ONCOLOGY,
        modality=Modality.SMALL_MOLECULE,
        target_validated=True,
    )
    asset_p3 = asset_p2.model_copy(update={"phase": Phase.PHASE_3})
    rnpv_inputs = RnpvInputs(peak_sales_usd_m=500.0, wacc=0.12)

    rec_p2 = DiligenceRecord(asset=asset_p2, rnpv_inputs=rnpv_inputs)
    rec_p2.pos = compute_pos(rec_p2)
    rec_p3 = DiligenceRecord(asset=asset_p3, rnpv_inputs=rnpv_inputs)
    rec_p3.pos = compute_pos(rec_p3)

    out_p2 = compute(rec_p2)
    out_p3 = compute(rec_p3)
    assert out_p3.base_case_usd_m > out_p2.base_case_usd_m
