"""Comparables engine tests."""

from __future__ import annotations

from app.domain import (
    AssetInput,
    DiligenceRecord,
    Modality,
    Phase,
    RnpvInputs,
    TherapeuticArea,
)
from app.modules.comparables.engine import compute
from app.registry import reset_registry_for_tests


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _record(peak_sales: float = 1200.0) -> DiligenceRecord:
    return DiligenceRecord(
        asset=AssetInput(
            asset_name="adagrasib",
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.SMALL_MOLECULE,
        ),
        rnpv_inputs=RnpvInputs(peak_sales_usd_m=peak_sales),
    )


def test_default_cohort_has_three_assets() -> None:
    out = compute(_record())
    assert len(out.cohort) == 3
    names = [c.asset_name for c in out.cohort]
    assert any("encorafenib" in n for n in names)
    assert any("selpercatinib" in n for n in names)
    assert any("larotrectinib" in n for n in names)


def test_radiopharmaceutical_cohort_matches() -> None:
    """v1.1 frontier modality: an oncology radiopharmaceutical (e.g. an Ac-225
    alpha emitter) routes to the curated radiopharma cohort, NOT the kinase-TKI
    fallback. Regression guard for the dogfood-driven coverage fix."""
    record = DiligenceRecord(
        asset=AssetInput(
            asset_name="ac-225 alpha emitter",
            phase=Phase.PHASE_1,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.RADIOPHARMACEUTICAL,
        ),
        rnpv_inputs=RnpvInputs(peak_sales_usd_m=1500.0),
    )
    out = compute(record)
    assert out.cohort_matched is True
    assert "radiopharmaceutical" in out.cohort_label
    assert len(out.cohort) >= 3
    names = " ".join(c.asset_name for c in out.cohort).lower()
    assert "actinium-225" in names or "radioligand" in names


def test_autoimmune_small_molecule_cohort_matches() -> None:
    """An autoimmune small-molecule asset (e.g. KT-621-style oral immunology)
    routes to the curated autoimmune · small_molecule cohort (Arena/etrasimod,
    Receptos/ozanimod, Principia/rilzabrutinib), NOT the oncology kinase-TKI
    fallback. Regression guard for the autoimmune coverage fix."""
    record = DiligenceRecord(
        asset=AssetInput(
            asset_name="kt-621-style oral immunology asset",
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.AUTOIMMUNE,
            modality=Modality.SMALL_MOLECULE,
        ),
        rnpv_inputs=RnpvInputs(peak_sales_usd_m=1500.0),
    )
    out = compute(record)
    assert out.cohort_matched is True
    assert "Autoimmune" in out.cohort_label
    assert "small molecule" in out.cohort_label
    assert len(out.cohort) == 3
    names = " ".join(c.asset_name for c in out.cohort).lower()
    assert "etrasimod" in names
    assert "ozanimod" in names
    assert "rilzabrutinib" in names
    # And it is NOT the cancer kinase fallback.
    assert "kinase" not in out.cohort_label.lower()


def test_same_ta_approximation_fallback() -> None:
    """Smarter same-TA fallback: an autoimmune asset whose exact
    (TA, modality_family) bucket is empty (e.g. an autoimmune gene therapy,
    of which there are no deals) falls back to ANOTHER cohort in the SAME
    therapeutic area (autoimmune small_molecule) rather than to the oncology
    kinase-TKI cohort. cohort_matched stays False because it is not an exact
    modality match — the 'Same-TA approximation' label carries the nuance."""
    record = DiligenceRecord(
        asset=AssetInput(
            asset_name="hypothetical autoimmune gene therapy",
            phase=Phase.PHASE_1,
            therapeutic_area=TherapeuticArea.AUTOIMMUNE,
            modality=Modality.GENE_THERAPY,
        ),
        rnpv_inputs=RnpvInputs(peak_sales_usd_m=1500.0),
    )
    out = compute(record)
    assert out.cohort_matched is False
    assert out.cohort_label.startswith("Same-TA approximation:")
    assert "Autoimmune" in out.cohort_label
    # Autoimmune has two qualifying same-TA cohorts: biologic (3 deals) and
    # small_molecule (3 deals). They tie on size, so the deterministic
    # alphabetical tie-break picks "biologic" (b < s). Either way it is a
    # same-TA autoimmune cohort, NOT the oncology kinase-TKI fallback.
    assert "biologic" in out.cohort_label
    assert len(out.cohort) == 3
    names = " ".join(c.asset_name for c in out.cohort).lower()
    # Explicitly NOT the cancer kinase fallback.
    assert "encorafenib" not in names
    assert "selpercatinib" not in names
    assert "larotrectinib" not in names


def test_each_comparable_has_ev_peak_multiple() -> None:
    out = compute(_record())
    for c in out.cohort:
        assert c.ev_to_peak_sales is not None
        assert c.ev_to_peak_sales > 0


def test_median_multiple_in_plausible_range() -> None:
    out = compute(_record())
    # Encorafenib ~15x, selpercatinib ~6.7x, larotrectinib ~3.9x — median ~6.7x
    assert 5.0 <= out.median_ev_to_peak_sales <= 10.0


def test_implied_value_uses_target_peak_sales() -> None:
    out = compute(_record(peak_sales=1000.0))
    assert out.implied_value_usd_m is not None
    # implied = median × target peak_sales
    expected = out.median_ev_to_peak_sales * 1000.0
    assert abs(out.implied_value_usd_m - expected) < 0.1


def test_no_rnpv_inputs_means_no_implied_value() -> None:
    record = DiligenceRecord(
        asset=AssetInput(
            asset_name="Test",
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.SMALL_MOLECULE,
        ),
    )
    out = compute(record)
    assert out.implied_value_usd_m is None
    # But the cohort itself still loads
    assert len(out.cohort) > 0


def test_unknown_cohort_id_skipped_gracefully() -> None:
    out = compute(_record(), cohort_ids=["encorafenib", "does_not_exist"])
    assert len(out.cohort) == 1  # only the real one loaded
    assert out.cohort[0].asset_name.startswith("encorafenib")
