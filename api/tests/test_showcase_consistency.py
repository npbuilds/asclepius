"""Showcase ↔ engine consistency guard.

The /showcase page (web/app/showcase/page.tsx) BAKES the Ac-225 numbers as
static constants so the page renders instantly and offline. That is only honest
if the live engines still produce those exact numbers for the Ac-225 inputs
staged in web/lib/staged-assets.ts. This test recomputes them and asserts the
match — if an engine change silently moves a number, this fails and tells us the
showcase constants are now stale (rather than a reviewer noticing the drift).

Keep the SHOWCASE_* constants below in sync with web/app/showcase/page.tsx.
"""

from __future__ import annotations

from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    RegulatoryDesignation,
    RnpvInputs,
    SupplyConstraint,
    TherapeuticArea,
)
from app.modules.comparables.engine import compute as compute_comparables
from app.modules.pos.engine import compute as compute_pos
from app.modules.rnpv.engine import compute as compute_rnpv
from app.registry import reset_registry_for_tests

# --- The numbers baked into web/app/showcase/page.tsx ----------------------
SHOWCASE_POS_BASE_PCT = 4.7
SHOWCASE_POS_FINAL_PCT = 5.5
SHOWCASE_RNPV_BASE_USD_M = 18
SHOWCASE_SUPPLY_CEILING_PCT = 0.65
SHOWCASE_SUPPLY_ADJ_PEAK_USD_M = 975
SHOWCASE_COMP_MULTIPLE = 2.0
SHOWCASE_COMP_IMPLIED_USD_M = 3000


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _ac225_record() -> DiligenceRecord:
    """Mirror of the AC225 / AC225_RNPV staged inputs in staged-assets.ts."""
    asset = AssetInput(
        asset_name="Ac-225 alpha-emitter (radioligand therapy)",
        sponsor="Illustrative frontier exemplar",
        phase=Phase.PHASE_1,
        therapeutic_area=TherapeuticArea.ONCOLOGY,
        modality=Modality.RADIOPHARMACEUTICAL,
        capital_position=CapitalPosition.CONSTRAINED,
        supply_constraint=SupplyConstraint.SEVERE,
        mechanism="Actinium-225 targeted alpha therapy",
        target_validated=True,
        biomarker_enrichment=True,
        num_competitors=2,
        regulatory_designations=[
            RegulatoryDesignation.ORPHAN,
            RegulatoryDesignation.FAST_TRACK,
        ],
    )
    rnpv_inputs = RnpvInputs(
        peak_sales_usd_m=1500.0,
        years_to_peak=5,
        years_of_exclusivity=12,
        cogs_pct=0.20,
        wacc=0.12,
        dev_cost_phase_1_usd_m=25.0,
        dev_cost_phase_2_usd_m=75.0,
        dev_cost_phase_3_usd_m=250.0,
        launch_cost_usd_m=150.0,
        years_per_phase={"phase_1": 1.5, "phase_2": 2.5, "phase_3": 3.0, "regulatory": 1.0},
    )
    record = DiligenceRecord(asset=asset, rnpv_inputs=rnpv_inputs)
    record.pos = compute_pos(record)
    record.rnpv = compute_rnpv(record)
    record.comparables = compute_comparables(record)
    return record


def test_showcase_pos_matches_engine() -> None:
    r = _ac225_record()
    assert round(r.pos.base_rate * 100, 1) == SHOWCASE_POS_BASE_PCT
    assert round(r.pos.final_loa * 100, 1) == SHOWCASE_POS_FINAL_PCT


def test_showcase_rnpv_and_supply_ceiling_match_engine() -> None:
    r = _ac225_record()
    assert round(r.rnpv.base_case_usd_m) == SHOWCASE_RNPV_BASE_USD_M
    assert r.rnpv.supply_peak_ceiling_pct == SHOWCASE_SUPPLY_CEILING_PCT
    assert round(r.rnpv.supply_adjusted_peak_usd_m) == SHOWCASE_SUPPLY_ADJ_PEAK_USD_M


def test_showcase_comparables_match_engine() -> None:
    r = _ac225_record()
    assert r.comparables.median_ev_to_peak_sales == SHOWCASE_COMP_MULTIPLE
    assert round(r.comparables.implied_value_usd_m) == SHOWCASE_COMP_IMPLIED_USD_M
    assert r.comparables.cohort_matched is True
