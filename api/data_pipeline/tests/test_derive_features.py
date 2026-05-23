"""Tests for the HINT row → AssetInput derivation logic."""

from __future__ import annotations

from app.domain import (
    CapitalPosition,
    Modality,
    Phase,
    TherapeuticArea,
)
from data_pipeline.derive_features import (
    _classify_icd_prefix,
    _derive_biomarker_enrichment,
    _derive_modality,
    _derive_phase,
    _derive_therapeutic_area,
    derive_from_hint_row,
)


# ---------------------------------------------------------------------------
# Phase parsing
# ---------------------------------------------------------------------------


def test_phase_maps_standard_strings():
    assert _derive_phase("phase 1") == Phase.PHASE_1
    assert _derive_phase("phase 2") == Phase.PHASE_2
    assert _derive_phase("phase 3") == Phase.PHASE_3
    assert _derive_phase("Phase 2") == Phase.PHASE_2  # case-insensitive


def test_phase_maps_combined_strings_conservatively():
    """Combined phases get the more-conservative (earlier) phase."""
    assert _derive_phase("phase 1/phase 2") == Phase.PHASE_1
    assert _derive_phase("phase 2/phase 3") == Phase.PHASE_2


def test_phase_returns_none_for_unknown():
    assert _derive_phase("") is None
    assert _derive_phase("xxx") is None


# ---------------------------------------------------------------------------
# ICD-10 chapter classification
# ---------------------------------------------------------------------------


def test_icd_oncology_chapter():
    assert _classify_icd_prefix("C50") == TherapeuticArea.ONCOLOGY  # breast cancer
    assert _classify_icd_prefix("C79.81") == TherapeuticArea.ONCOLOGY
    assert _classify_icd_prefix("D49.3") == TherapeuticArea.ONCOLOGY  # neoplasm uncertain


def test_icd_hematology_chapter():
    """D50-D89 is hematology, not oncology."""
    assert _classify_icd_prefix("D55") == TherapeuticArea.HEMATOLOGY
    assert _classify_icd_prefix("D70") == TherapeuticArea.HEMATOLOGY


def test_icd_cns_metabolic_cardio_respiratory():
    assert _classify_icd_prefix("G30.0") == TherapeuticArea.CNS  # Alzheimer's
    assert _classify_icd_prefix("F32") == TherapeuticArea.CNS
    assert _classify_icd_prefix("E11") == TherapeuticArea.METABOLIC  # diabetes
    assert _classify_icd_prefix("I25") == TherapeuticArea.CARDIOVASCULAR
    assert _classify_icd_prefix("J45") == TherapeuticArea.RESPIRATORY  # asthma


def test_icd_unknown_returns_other():
    assert _classify_icd_prefix("Z99") == TherapeuticArea.OTHER
    assert _classify_icd_prefix("") is None


# ---------------------------------------------------------------------------
# Therapeutic area integration
# ---------------------------------------------------------------------------


def test_ta_picks_most_common_chapter():
    diseases = "['breast cancer']"
    icd = "[\"['C50.9', 'C50.1', 'D24.1']\"]"
    ta, debug = _derive_therapeutic_area(diseases, icd)
    assert ta == TherapeuticArea.ONCOLOGY
    assert debug.startswith("icd_chapter:")


def test_ta_rare_disease_hint_overrides_icd():
    """If 'rare' shows up in the disease list, that wins over ICD chapter."""
    diseases = "['rare metabolic disorder', 'orphan disease']"
    icd = "[\"['E70', 'E71']\"]"
    ta, debug = _derive_therapeutic_area(diseases, icd)
    assert ta == TherapeuticArea.RARE_ORPHAN
    assert "rare_disease_hint" in debug


def test_ta_falls_back_to_other_when_icd_unparseable():
    ta, debug = _derive_therapeutic_area("['unknown']", "")
    assert ta == TherapeuticArea.OTHER


# ---------------------------------------------------------------------------
# Modality
# ---------------------------------------------------------------------------


def test_modality_small_molecule_via_smiles():
    """SMILES present + no antibody name → small molecule."""
    drugs = "['galantamine']"
    smiless = "['[H][C@]12C[C@@H](O)C=C[C@]11CCN(C)CC3=C1C(O2)=C(OC)C=C3']"
    mod, debug = _derive_modality(drugs, smiless)
    assert mod == Modality.SMALL_MOLECULE


def test_modality_monoclonal_antibody_via_suffix():
    drugs = "['trastuzumab']"
    smiless = "[]"
    mod, debug = _derive_modality(drugs, smiless)
    assert mod == Modality.MAB
    assert "trastuzumab" in debug


def test_modality_adc_overrides_mab():
    """ADCs contain mAbs in their name string but should be classified ADC."""
    drugs = "['trastuzumab emtansine antibody-drug conjugate']"
    smiless = "[]"
    mod, debug = _derive_modality(drugs, smiless)
    assert mod == Modality.ADC


def test_modality_cell_therapy():
    drugs = "['CAR-T cell therapy targeting CD19']"
    smiless = "[]"
    mod, debug = _derive_modality(drugs, smiless)
    assert mod == Modality.CELL_THERAPY_AUTO


def test_modality_gene_therapy():
    drugs = "['AAV9 gene therapy']"
    smiless = "[]"
    mod, debug = _derive_modality(drugs, smiless)
    assert mod == Modality.GENE_THERAPY


def test_modality_other_when_no_signals():
    mod, debug = _derive_modality("['placebo']", "[]")
    assert mod == Modality.OTHER


# ---------------------------------------------------------------------------
# Biomarker enrichment
# ---------------------------------------------------------------------------


def test_biomarker_detected_for_named_gene():
    text = "Inclusion: Patients must have BRCA1/2 mutations confirmed by sequencing."
    assert _derive_biomarker_enrichment(text) is True


def test_biomarker_detected_for_her2_amplified():
    text = "Patients with HER2 amplified breast cancer eligible."
    assert _derive_biomarker_enrichment(text) is True


def test_biomarker_not_detected_for_generic_oncology():
    """Generic disease language without explicit biomarker selection."""
    text = "Patients aged 18 or older with advanced solid tumors of any type."
    assert _derive_biomarker_enrichment(text) is False


def test_biomarker_detected_for_biomarker_selected_language():
    text = "Biomarker-selected enrollment based on companion diagnostic."
    assert _derive_biomarker_enrichment(text) is True


# ---------------------------------------------------------------------------
# Top-level row derivation
# ---------------------------------------------------------------------------


def test_full_row_derivation_oncology_small_molecule():
    """Adagrasib-style trial: oncology + small molecule + biomarker."""
    row = {
        "nctid": "NCT04685135",
        "status": "completed",
        "why_stop": "",
        "label": "1",
        "phase": "phase 2",
        "diseases": "['NSCLC', 'KRAS G12C mutated']",
        "icdcodes": "[\"['C34.9']\"]",
        "drugs": "['adagrasib']",
        "smiless": "['CN1C(=O)c2nc3...']",  # truncated synthetic SMILES
        "criteria": "Inclusion Criteria: Patients must have KRAS G12C mutation confirmed.",
    }
    d = derive_from_hint_row(row)
    assert d is not None
    assert d.nctid == "NCT04685135"
    assert d.label == 1
    assert d.asset.phase == Phase.PHASE_2
    assert d.asset.therapeutic_area == TherapeuticArea.ONCOLOGY
    assert d.asset.modality == Modality.SMALL_MOLECULE
    assert d.asset.biomarker_enrichment is True
    assert d.asset.capital_position == CapitalPosition.ADEQUATE  # default
    assert d.asset.target_validated is False  # default
    assert d.asset.num_competitors == 0  # default
    assert d.criteria_text.startswith("Inclusion Criteria")


def test_row_derivation_drops_missing_nctid():
    row = {"nctid": "", "label": "1", "phase": "phase 2", "criteria": "x"}
    assert derive_from_hint_row(row) is None


def test_row_derivation_drops_invalid_label():
    row = {
        "nctid": "NCT1",
        "label": "?",
        "phase": "phase 2",
        "criteria": "x",
        "diseases": "[]",
        "icdcodes": "[]",
        "drugs": "[]",
        "smiless": "[]",
    }
    assert derive_from_hint_row(row) is None


def test_row_derivation_drops_unparseable_phase():
    row = {
        "nctid": "NCT1",
        "label": "1",
        "phase": "n/a",
        "criteria": "x",
        "diseases": "[]",
        "icdcodes": "[]",
        "drugs": "[]",
        "smiless": "[]",
    }
    assert derive_from_hint_row(row) is None


def test_row_derivation_drops_empty_criteria():
    row = {
        "nctid": "NCT1",
        "label": "1",
        "phase": "phase 2",
        "criteria": "",
        "diseases": "[]",
        "icdcodes": "[]",
        "drugs": "[]",
        "smiless": "[]",
    }
    assert derive_from_hint_row(row) is None
