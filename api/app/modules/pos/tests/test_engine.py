"""PoS engine tests — pure-function unit tests over the asset input."""

from __future__ import annotations

from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    RegulatoryDesignation,
    TherapeuticArea,
)
from app.modules.pos.engine import compute
from app.registry import reset_registry_for_tests


def _record(**overrides) -> DiligenceRecord:
    base = dict(
        asset_name="TestAsset",
        phase=Phase.PHASE_2,
        therapeutic_area=TherapeuticArea.ONCOLOGY,
        modality=Modality.SMALL_MOLECULE,
        capital_position=CapitalPosition.ADEQUATE,
    )
    base.update(overrides)
    return DiligenceRecord(asset=AssetInput(**base))


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def test_phase_2_oncology_baseline_matches_bio_table() -> None:
    """Phase 2 oncology, adequate capital, no boosters → LOA close to BIO base."""
    record = _record()
    pos = compute(record)
    # BIO oncology: P2→P3 = 0.24, P3→NDA = 0.52, NDA→appr = 0.85 → ~0.106
    assert 0.10 <= pos.base_rate <= 0.11
    # Modality = small_molecule (1.0) and capital = adequate (1.0) → final ≈ base.
    assert abs(pos.final_loa - pos.base_rate) < 0.005


def test_reflexivity_well_capitalized_raises_loa() -> None:
    base = compute(_record(capital_position=CapitalPosition.ADEQUATE)).final_loa
    well = compute(_record(capital_position=CapitalPosition.WELL_CAPITALIZED)).final_loa
    constrained = compute(_record(capital_position=CapitalPosition.CONSTRAINED)).final_loa
    distressed = compute(_record(capital_position=CapitalPosition.DISTRESSED)).final_loa
    assert well > base > constrained > distressed
    # Reflexivity should move LOA by ~8% relative for well-capitalized
    assert well / base > 1.05


def test_biomarker_enrichment_boosts_loa() -> None:
    plain = compute(_record()).final_loa
    enriched = compute(_record(biomarker_enrichment=True)).final_loa
    assert enriched > plain
    # +20% multiplier should give a ~20% relative uplift to running PoS
    assert 1.15 < enriched / plain < 1.25


def test_btd_orphan_stack() -> None:
    base = compute(_record(therapeutic_area=TherapeuticArea.RARE_ORPHAN)).final_loa
    boosted = compute(
        _record(
            therapeutic_area=TherapeuticArea.RARE_ORPHAN,
            regulatory_designations=[
                RegulatoryDesignation.BTD,
                RegulatoryDesignation.ORPHAN,
            ],
        )
    ).final_loa
    assert boosted > base


def test_audit_trail_is_populated() -> None:
    record = _record(biomarker_enrichment=True, target_validated=True)
    pos = compute(record)
    names = [a.name for a in pos.adjustments]
    # Modality + biomarker + target validated + reflexivity
    assert any("modality" in n for n in names)
    assert any("biomarker" in n for n in names)
    assert any("target validated" in n for n in names)
    assert any("reflexivity" in n for n in names)
    # Every adjustment has a citation
    for adj in pos.adjustments:
        assert adj.source, f"adjustment {adj.name} has empty source"


def test_modality_multiplier_applied() -> None:
    sm = compute(_record(modality=Modality.SMALL_MOLECULE)).final_loa
    cell = compute(_record(modality=Modality.CELL_THERAPY_AUTO)).final_loa
    assert cell < sm  # autologous cell therapy should reduce LOA


def test_confidence_range_brackets_final_loa() -> None:
    pos = compute(_record())
    assert pos.confidence_low <= pos.final_loa <= pos.confidence_high


def test_unvalidated_no_biomarker_cap_binds_for_aducanumab() -> None:
    """v1.7.7 hard-cap: aducanumab-shaped inputs (CNS · mAb · phase 3 ·
    Fast Track · well-capitalized · target_validated=false · biomarker_enrichment=false)
    should be capped at 3× the long-run cohort base rate, not the ~54% the
    multiplier chain would otherwise produce. See
    methodology/21-aducanumab-contested-retrospective.md."""
    aducanumab = _record(
        asset_name="aducanumab",
        phase=Phase.PHASE_3,
        therapeutic_area=TherapeuticArea.CNS,
        modality=Modality.MAB,
        capital_position=CapitalPosition.WELL_CAPITALIZED,
        regulatory_designations=[RegulatoryDesignation.FAST_TRACK],
        target_validated=False,
        biomarker_enrichment=False,
    )
    pos = compute(aducanumab)
    # Pre-cap (multiplier chain only) would be base * mAb * FT * well-cap
    #   = 0.425 * 1.15 * 1.03 * 1.08 ≈ 0.544 (~54%)
    # Cohort loa-from-P1 for CNS = 0.048 * 0.20 * 0.50 * 0.85 ≈ 0.041
    # Cap = 0.041 * 1.15 (mAb) * 3 ≈ 0.141
    assert pos.final_loa < 0.20, (
        f"cap should bind: final_loa={pos.final_loa:.3f} > 0.20"
    )
    assert pos.final_loa > 0.10, (
        f"cap should not over-compress: final_loa={pos.final_loa:.3f}"
    )
    # The audit trail should expose the cap as an adjustment so the waterfall
    # reconstructs the final number.
    cap_adj = next(
        (a for a in pos.adjustments if "unvalidated target" in a.name.lower()), None
    )
    assert cap_adj is not None, "cap adjustment must appear in audit trail"
    assert "methodology/21" in cap_adj.source


def test_cap_does_not_apply_when_target_validated() -> None:
    """Same aducanumab shape but with target_validated=true → cap must NOT fire."""
    record = _record(
        phase=Phase.PHASE_3,
        therapeutic_area=TherapeuticArea.CNS,
        modality=Modality.MAB,
        capital_position=CapitalPosition.WELL_CAPITALIZED,
        regulatory_designations=[RegulatoryDesignation.FAST_TRACK],
        target_validated=True,
        biomarker_enrichment=False,
    )
    pos = compute(record)
    assert pos.final_loa > 0.40, (
        "with target_validated=true the cap must not fire and PoS should sit "
        f"in the ~50-60% range; got {pos.final_loa:.3f}"
    )
    assert not any("unvalidated target" in a.name.lower() for a in pos.adjustments)


def test_cap_does_not_apply_when_biomarker_enrichment_true() -> None:
    """Same aducanumab shape but with biomarker_enrichment=true → cap must NOT fire."""
    record = _record(
        phase=Phase.PHASE_3,
        therapeutic_area=TherapeuticArea.CNS,
        modality=Modality.MAB,
        capital_position=CapitalPosition.WELL_CAPITALIZED,
        regulatory_designations=[RegulatoryDesignation.FAST_TRACK],
        target_validated=False,
        biomarker_enrichment=True,
    )
    pos = compute(record)
    assert pos.final_loa > 0.40
    assert not any("unvalidated target" in a.name.lower() for a in pos.adjustments)
