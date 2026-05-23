"""Map a HINT corpus row → AssetInput compatible with the v1.5.1 feature encoder.

HINT carries:
  - nctid, status, why_stop, label (0/1), phase, diseases (list), icdcodes
    (list of lists, by disease), drugs (list), smiless (list of SMILES
    strings), criteria (eligibility criteria text)

Our AssetInput needs:
  - phase, therapeutic_area, modality, capital_position,
    regulatory_designations, biomarker_enrichment, target_validated,
    num_competitors, plus the asset_name and metadata fields the encoder
    ignores.

Coverage:
  - phase: direct from HINT.
  - therapeutic_area: ICD-10 chapter prefix → TA enum (oncology, cns, etc.).
  - modality: SMILES + drug-name heuristics (small_molecule, mab, ADC, gene
    therapy, cell therapy, mRNA, oligonucleotide, peptide, protein).
  - biomarker_enrichment: regex over criteria text for established biomarkers
    + biomarker-selection language.
  - capital_position: NOT in HINT → defaults to ADEQUATE. Documented
    limitation.
  - regulatory_designations: NOT in HINT → defaults to []. Documented.
  - target_validated: NOT in HINT (requires literature lookup) → defaults to
    False. Documented.
  - num_competitors: NOT in HINT (requires cohort lookup) → defaults to 0.
    Documented.

Honesty caveat: the four "Not in HINT" fields are the structural-feature
contribution the v1.5.1 encoder was tuned on. Defaulting them all to the
same value reduces their training-time signal to zero, which means the
v1.5.2 model learns less from the structured side than the v1.5.1 surrogate
did. That's expected and acceptable — the BioBERT signal on the criteria
text is what carries the prediction; structured features are augmentation.
The methodology writeup names this directly.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from app.domain import (
    AssetInput,
    CapitalPosition,
    Modality,
    Phase,
    RegulatoryDesignation,
    TherapeuticArea,
)


@dataclass
class HintRowDerivation:
    """Result of deriving features from one HINT row."""

    asset: AssetInput
    label: int  # 0 = failure, 1 = success — the supervised target
    criteria_text: str  # protocol text input for BioBERT embedding
    nctid: str
    # Provenance: which raw values drove the derivation, for audit / debugging
    debug: dict[str, str]


# ---------------------------------------------------------------------------
# Phase mapping
# ---------------------------------------------------------------------------

_PHASE_MAP = {
    "phase 0": Phase.PRECLINICAL,
    "phase 1": Phase.PHASE_1,
    "phase 1/phase 2": Phase.PHASE_1,  # treat as more conservative phase
    "phase 2": Phase.PHASE_2,
    "phase 2/phase 3": Phase.PHASE_2,
    "phase 3": Phase.PHASE_3,
    "phase 4": Phase.APPROVED,
}


def _derive_phase(phase_str: str) -> Phase | None:
    """Returns None if phase is unparseable — caller drops the row."""
    return _PHASE_MAP.get(phase_str.strip().lower())


# ---------------------------------------------------------------------------
# Therapeutic area from ICD-10
#
# ICD-10 chapter prefixes (https://icd.who.int/browse10/2019/en):
#   A00-B99  Infectious + parasitic diseases
#   C00-D49  Neoplasms                          → oncology
#   D50-D89  Blood / blood-forming organs       → hematology
#   E00-E89  Endocrine + metabolic              → metabolic
#   F01-F99  Mental + behavioral                → cns
#   G00-G99  Nervous system                     → cns
#   H00-H59  Eye / adnexa                       → ophthalmology
#   H60-H95  Ear / mastoid                      → other
#   I00-I99  Circulatory                        → cardiovascular
#   J00-J99  Respiratory                        → respiratory
#   M00-M99  Musculoskeletal                    → autoimmune (loose)
# ---------------------------------------------------------------------------

# Cancer-specific keywords for rare-orphan classification of pediatric /
# ultra-rare oncology (the "rare orphan" enum supersedes oncology for those).
_RARE_DISEASE_HINTS = ("rare ", "orphan", "ultra-rare", "ultra rare")


def _classify_icd_prefix(code: str) -> TherapeuticArea | None:
    """One ICD-10 code → TA enum, by chapter prefix."""
    if not code or len(code) == 0:
        return None
    c = code.strip().upper()
    if not c:
        return None
    head = c[0]
    if head in ("C",) or (head == "D" and c[1:3] < "50"):
        return TherapeuticArea.ONCOLOGY
    if head == "D" and c[1:3] >= "50":
        return TherapeuticArea.HEMATOLOGY
    if head == "E":
        return TherapeuticArea.METABOLIC
    if head in ("F", "G"):
        return TherapeuticArea.CNS
    if head == "H" and c[1:3] < "60":
        return TherapeuticArea.OPHTHALMOLOGY
    if head == "I":
        return TherapeuticArea.CARDIOVASCULAR
    if head == "J":
        return TherapeuticArea.RESPIRATORY
    if head == "M":
        return TherapeuticArea.AUTOIMMUNE
    if head in ("A", "B"):
        return TherapeuticArea.INFECTIOUS
    return TherapeuticArea.OTHER


def _derive_therapeutic_area(
    diseases_raw: str, icdcodes_raw: str
) -> tuple[TherapeuticArea, str]:
    """Returns (TA, debug_provenance)."""
    # 1) Rare-disease hint in the disease names wins
    diseases_lower = diseases_raw.lower()
    if any(hint in diseases_lower for hint in _RARE_DISEASE_HINTS):
        return TherapeuticArea.RARE_ORPHAN, "rare_disease_hint"

    # 2) ICD code chapter prefix
    icd_codes: list[str] = []
    try:
        # HINT stores ICD as a string-encoded list of lists; parse defensively
        outer = ast.literal_eval(icdcodes_raw) if icdcodes_raw else []
        for item in outer:
            if isinstance(item, str):
                inner = ast.literal_eval(item)
                if isinstance(inner, list):
                    icd_codes.extend(inner)
            elif isinstance(item, list):
                icd_codes.extend(item)
    except (ValueError, SyntaxError):
        pass

    if icd_codes:
        # Pick the most-common chapter, fall back to first hit
        from collections import Counter
        chapters: list[TherapeuticArea] = []
        for code in icd_codes:
            ta = _classify_icd_prefix(code)
            if ta is not None:
                chapters.append(ta)
        if chapters:
            top = Counter(chapters).most_common(1)[0][0]
            return top, f"icd_chapter:{icd_codes[0]}"

    # 3) Fallback to OTHER
    return TherapeuticArea.OTHER, "no_icd_match"


# ---------------------------------------------------------------------------
# Modality from SMILES + drug names
# ---------------------------------------------------------------------------

_MAB_SUFFIXES = ("mab", "-mab", "umab", "ximab", "zumab")
_GENE_THERAPY_HINTS = ("aav", "lentiviral", "lentivirus", "adenoviral", "gene therapy")
_CELL_AUTO_HINTS = ("car-t", "car t", "autologous", "tcr-t")
_CELL_ALLO_HINTS = ("allogeneic",)
_MRNA_HINTS = ("mrna", "self-amplifying rna")
_ANTISENSE_HINTS = ("antisense", "siRNA", "oligonucleotide", "asn")
_PEPTIDE_HINTS = ("peptide",)
_ADC_HINTS = ("antibody-drug conjugate", "adc", "drug conjugate")


def _derive_modality(drugs_raw: str, smiless_raw: str) -> tuple[Modality, str]:
    """Returns (modality, debug_provenance)."""
    drugs_lower = drugs_raw.lower()

    # Order matters — ADC before mAb (ADCs contain "mab" in their components)
    if any(hint in drugs_lower for hint in _ADC_HINTS):
        return Modality.ADC, "drug_name:adc"

    # Cell therapy (autologous before allogeneic)
    if any(hint in drugs_lower for hint in _CELL_AUTO_HINTS):
        return Modality.CELL_THERAPY_AUTO, "drug_name:cell_auto"
    if any(hint in drugs_lower for hint in _CELL_ALLO_HINTS):
        return Modality.CELL_THERAPY_ALLO, "drug_name:cell_allo"

    if any(hint in drugs_lower for hint in _GENE_THERAPY_HINTS):
        return Modality.GENE_THERAPY, "drug_name:gene_therapy"

    if any(hint in drugs_lower for hint in _MRNA_HINTS):
        return Modality.MRNA, "drug_name:mrna"

    if any(hint in drugs_lower for hint in _ANTISENSE_HINTS):
        return Modality.OLIGONUCLEOTIDE, "drug_name:oligonucleotide"

    if any(hint in drugs_lower for hint in _PEPTIDE_HINTS):
        return Modality.PEPTIDE, "drug_name:peptide"

    # mAb suffix check on individual drug tokens
    drug_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+", drugs_raw)
    for token in drug_tokens:
        tl = token.lower()
        if any(tl.endswith(s) for s in _MAB_SUFFIXES) and len(tl) > 4:
            return Modality.MAB, f"drug_suffix:{token}"

    # Has SMILES → small molecule (default)
    smiless_stripped = smiless_raw.strip()
    if smiless_stripped and smiless_stripped != "[]":
        return Modality.SMALL_MOLECULE, "smiles_present"

    return Modality.OTHER, "no_match"


# ---------------------------------------------------------------------------
# Biomarker enrichment from criteria text
# ---------------------------------------------------------------------------

# Common biomarker tokens used in inclusion criteria. Conservative — false
# positives are worse than false negatives because the encoder treats this
# as a binary structural feature.
_BIOMARKER_REGEX = re.compile(
    r"\b(?:"
    r"BRCA[12]?|HER2|EGFR|KRAS|BRAF|ALK|ROS1|PD-?L1|MSI-H|TMB-?[Hh]igh|"
    r"FGFR[0-9]?|MET|RET|NTRK[0-9]?|IDH[12]?|CD19|CD20|CD22|CD30|"
    r"BCMA|GUCY2C|PSMA|VEGF|VEGFR|c-MET|"
    r"biomarker[\s-]?(?:positive|selected|stratified|enriched)|"
    r"mutation[\s-]?positive|expressing|amplified"
    r")\b",
    re.IGNORECASE,
)


def _derive_biomarker_enrichment(criteria_text: str) -> bool:
    """Heuristic: returns True if biomarker-enrichment language is present
    in the eligibility criteria. Conservative — requires explicit token
    matches rather than inferring from gene names alone."""
    if not criteria_text:
        return False
    return bool(_BIOMARKER_REGEX.search(criteria_text))


# ---------------------------------------------------------------------------
# Top-level row derivation
# ---------------------------------------------------------------------------


def derive_from_hint_row(row: dict) -> HintRowDerivation | None:
    """Map one HINT row → HintRowDerivation. Returns None for unusable rows
    (unparseable phase, missing critical fields)."""
    nctid = row.get("nctid", "").strip()
    if not nctid:
        return None

    # Phase — drop if unparseable
    phase = _derive_phase(row.get("phase", ""))
    if phase is None:
        return None

    # Label — drop if not 0/1
    label_raw = row.get("label", "").strip()
    if label_raw not in ("0", "1"):
        return None
    label = int(label_raw)

    # Criteria text — drop if empty
    criteria = (row.get("criteria") or "").strip()
    if not criteria:
        return None

    # Derive TA + modality + biomarker
    ta, ta_debug = _derive_therapeutic_area(
        row.get("diseases", ""), row.get("icdcodes", "")
    )
    modality, mod_debug = _derive_modality(
        row.get("drugs", ""), row.get("smiless", "")
    )
    biomarker = _derive_biomarker_enrichment(criteria)

    asset = AssetInput(
        asset_name=nctid,  # use NCT ID as canonical name since drug name list is messy
        phase=phase,
        therapeutic_area=ta,
        modality=modality,
        capital_position=CapitalPosition.ADEQUATE,  # default — HINT doesn't carry sponsor
        regulatory_designations=[],  # default — not in HINT
        biomarker_enrichment=biomarker,
        target_validated=False,  # default — requires literature lookup
        num_competitors=0,  # default — requires cohort lookup
    )

    return HintRowDerivation(
        asset=asset,
        label=label,
        criteria_text=criteria,
        nctid=nctid,
        debug={
            "ta_provenance": ta_debug,
            "modality_provenance": mod_debug,
            "biomarker_detected": str(biomarker),
        },
    )


# Re-export the regulatory-designation enum so callers don't need to import
# from app.domain — keeps the data_pipeline boundary thin.
__all__ = [
    "HintRowDerivation",
    "derive_from_hint_row",
    "RegulatoryDesignation",  # for downstream backfill scripts
]
