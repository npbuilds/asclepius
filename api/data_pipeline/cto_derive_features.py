"""CT Open benchmark — derive an AssetInput from a CTO row + CT.gov metadata.

CTO ships rich CTI.gov metadata in the human_labels CSV (phase, source_class,
overall_status, completion_year, enrollment, etc.) but NOT our 36-dim
structured feature vector. We derive what we can from the available data:

  - phase: direct from CTO's `phase` column (normalized to phase_1/2/3)
  - therapeutic_area: keyword-matched from CT.gov MeSH terms + conditions
  - modality: pattern-matched from CT.gov intervention types + drug names
  - capital_position: heuristic from CTO source_class (proxy — see notes)
  - biomarker_enrichment: regex over CT.gov eligibility criteria text
  - target_validated: default False (would need separate literature lookup)
  - num_competitors: default 0 (would need separate CT.gov cohort query)
  - regulatory_designations: default empty (CT.gov v2 sometimes carries
    them but inconsistently across older trials)

These are coarse proxies — same philosophy as derive_features.py for HINT.
PubMedBERT embedding of the eligibility-criteria text carries the bulk of
the predictive signal; structured features are augmentation. The honesty
caveat: for CTO trials, the structured-feature contribution is weaker
than for HINT trials, where ICD codes + SMILES drove cleaner TA + modality
derivation. The methodology writeup names this.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.domain import (
    AssetInput,
    CapitalPosition,
    Modality,
    Phase,
    TherapeuticArea,
)

from .cto_fetch_metadata import CtGovMetadata

log = logging.getLogger(__name__)


@dataclass
class CtoRowDerivation:
    """Result of deriving an AssetInput from one CTO row."""

    asset: AssetInput
    label: int  # 0 = failure, 1 = success — the supervised target
    criteria_text: str
    nctid: str
    debug: dict[str, str]


# ---------------------------------------------------------------------------
# Phase mapping (CTO is uppercase + simpler than HINT)
# ---------------------------------------------------------------------------

_CTO_PHASE_MAP = {
    "PHASE1": Phase.PHASE_1,
    "PHASE2": Phase.PHASE_2,
    "PHASE3": Phase.PHASE_3,
}


# ---------------------------------------------------------------------------
# Therapeutic area — keyword match against MeSH + conditions
# ---------------------------------------------------------------------------

# Each TA's keyword list. Lowercased; substring match. Order matters:
# oncology + cns are most-specific markers; the catchall "other" is the
# fallback. Phrases like "cancer" or "tumor" are HIGH-precision oncology
# markers because they almost never appear in cns / metabolic etc.
_TA_KEYWORDS: list[tuple[TherapeuticArea, list[str]]] = [
    (TherapeuticArea.ONCOLOGY, [
        "neoplasm", "carcinoma", "cancer", "tumor", "tumour", "leukemia",
        "lymphoma", "melanoma", "sarcoma", "myeloma", "oncolog", "metastatic",
    ]),
    (TherapeuticArea.CNS, [
        "alzheimer", "parkinson", "epilepsy", "schizophren", "depression",
        "anxiety", "bipolar", "multiple sclerosis", "stroke", "ALS",
        "amyotrophic lateral sclerosis", "neurodegenerative", "huntington",
    ]),
    (TherapeuticArea.METABOLIC, [
        "diabetes", "obesity", "metabolic", "insulin", "glucose", "lipid",
        "cholesterol", "hyperlipidemia",
    ]),
    (TherapeuticArea.INFECTIOUS, [
        "infection", "virus", "viral", "bacterial", "antimicrobial", "antibiotic",
        "antiviral", "antifungal", "sepsis", "covid", "hiv", "hepatitis",
        "tuberculosis", "malaria",
    ]),
    (TherapeuticArea.CARDIOVASCULAR, [
        "cardiovascular", "heart failure", "myocardial", "hypertension",
        "atherosclerosis", "thrombosis", "stroke", "atrial fibrillation",
        "coronary artery",
    ]),
    (TherapeuticArea.AUTOIMMUNE, [
        "autoimmune", "rheumatoid", "lupus", "psoriasis", "crohn", "colitis",
        "inflammatory bowel", "ulcerative", "vasculitis",
    ]),
    (TherapeuticArea.OPHTHALMOLOGY, [
        "macular", "glaucoma", "retinopathy", "uveitis", "dry eye",
        "diabetic retinopathy", "ophthalm",
    ]),
    (TherapeuticArea.HEMATOLOGY, [
        "hematolog", "anemia", "thalassemia", "sickle cell", "hemophilia",
    ]),
    (TherapeuticArea.RESPIRATORY, [
        "asthma", "copd", "chronic obstructive pulmonary", "cystic fibrosis",
        "respiratory", "pulmonary",
    ]),
    (TherapeuticArea.RARE_ORPHAN, [
        "rare disease", "orphan", "ultra-rare",
    ]),
]


def _derive_therapeutic_area(meta: CtGovMetadata | None) -> tuple[TherapeuticArea, str]:
    """Keyword-match against MeSH terms + conditions to pick a TA.
    Returns (TA, debug_string). Defaults to OTHER when no keyword fires."""
    if meta is None:
        return (TherapeuticArea.OTHER, "no_ctgov_metadata")
    haystack = " ".join(
        [t.lower() for t in (meta.mesh_terms or [])]
        + [c.lower() for c in (meta.conditions or [])]
    )
    if not haystack.strip():
        return (TherapeuticArea.OTHER, "empty_conditions")
    for ta, keywords in _TA_KEYWORDS:
        for kw in keywords:
            if kw in haystack:
                return (ta, f"match:{kw}")
    return (TherapeuticArea.OTHER, "no_keyword_match")


# ---------------------------------------------------------------------------
# Modality — derive from CT.gov intervention type + drug-name patterns
# ---------------------------------------------------------------------------

# Suffix patterns from WHO INN naming for biologics. Aligned with HINT
# derive_features.py.
_MODALITY_SUFFIXES: list[tuple[str, Modality]] = [
    ("mab", Modality.MAB),       # monoclonal antibody
    ("nib", Modality.SMALL_MOLECULE),  # kinase inhibitor
    ("tinib", Modality.SMALL_MOLECULE),
    ("cept", Modality.PROTEIN),  # fusion protein (etanercept)
    ("ase", Modality.PROTEIN),   # enzyme
    ("mer", Modality.OLIGONUCLEOTIDE),  # antisense oligo
    ("sense", Modality.OLIGONUCLEOTIDE),
    ("siran", Modality.OLIGONUCLEOTIDE),  # siRNA
]

# CT.gov intervention type → modality default (when name doesn't match a suffix)
_INTERVENTION_TYPE_DEFAULT: dict[str, Modality] = {
    "DRUG": Modality.SMALL_MOLECULE,
    "BIOLOGICAL": Modality.PROTEIN,
    "GENETIC": Modality.GENE_THERAPY,
}


def _derive_modality(meta: CtGovMetadata | None) -> tuple[Modality, str]:
    """Combine intervention types + drug-name pattern matches."""
    if meta is None or not meta.intervention_names:
        return (Modality.OTHER, "no_intervention_data")

    # Try suffix-match on drug names first (more specific)
    for name in meta.intervention_names:
        name_l = name.lower().strip()
        for suffix, modality in _MODALITY_SUFFIXES:
            if name_l.endswith(suffix):
                return (modality, f"suffix:{suffix} on {name_l}")

    # Fall back to first intervention type's default mapping
    for itype in meta.intervention_types:
        if itype in _INTERVENTION_TYPE_DEFAULT:
            return (_INTERVENTION_TYPE_DEFAULT[itype], f"type:{itype}")

    return (Modality.OTHER, "no_pattern_match")


# ---------------------------------------------------------------------------
# Capital position — coarse proxy from CTO source_class
# ---------------------------------------------------------------------------

_SOURCE_CLASS_TO_CAPITAL: dict[str, CapitalPosition] = {
    "INDUSTRY": CapitalPosition.ADEQUATE,
    # NIH-funded or other gov programs typically have stable multi-year
    # funding lines — treat as adequate. Not a perfect proxy for the
    # reflexivity-thesis notion of trial-quality-via-capital-credibility,
    # but acceptable for benchmark feature derivation.
    "NIH": CapitalPosition.ADEQUATE,
    "OTHER_GOV": CapitalPosition.ADEQUATE,
    "FED": CapitalPosition.ADEQUATE,
    "NETWORK": CapitalPosition.ADEQUATE,
    "OTHER": CapitalPosition.ADEQUATE,
    "INDIV": CapitalPosition.CONSTRAINED,
    "UNKNOWN": CapitalPosition.ADEQUATE,
}


def _derive_capital_position(source_class: str | None) -> CapitalPosition:
    if not source_class:
        return CapitalPosition.ADEQUATE
    return _SOURCE_CLASS_TO_CAPITAL.get(
        source_class.strip(), CapitalPosition.ADEQUATE,
    )


# ---------------------------------------------------------------------------
# Biomarker enrichment — regex over eligibility criteria text
# ---------------------------------------------------------------------------

_BIOMARKER_PATTERNS = [
    r"\bbiomarker\b",
    r"\bmutation\b",
    r"\boverexpress",
    r"\bexpressing\b",
    r"\bpositive for\b",
    r"\b(EGFR|KRAS|BRAF|ALK|ROS1|HER2|PD-L1|MSI-H|TMB-H)\b",
    r"\b(BRCA1|BRCA2|TP53|PIK3CA)\b",
    r"\bgenetic test\b",
    r"\bcompanion diagnostic\b",
]

_BIOMARKER_RE = re.compile("|".join(_BIOMARKER_PATTERNS), re.IGNORECASE)


def _derive_biomarker_enrichment(criteria: str | None) -> bool:
    if not criteria:
        return False
    return bool(_BIOMARKER_RE.search(criteria))


# ---------------------------------------------------------------------------
# Top-level derivation
# ---------------------------------------------------------------------------


def derive_from_cto_row(
    row: dict,
    meta: CtGovMetadata | None,
) -> CtoRowDerivation | None:
    """Combine a CTO human_labels row + CT.gov metadata into an AssetInput.
    Returns None when the trial can't be processed (missing phase, no
    eligibility criteria, etc.)."""
    nct_id = str(row.get("nct_id", "")).strip().upper()
    if not nct_id.startswith("NCT"):
        return None

    label_raw = row.get("labels")
    if label_raw is None or (isinstance(label_raw, float) and label_raw != label_raw):
        return None  # NaN check via != self
    label = int(label_raw)

    phase_str = row.get("phase")
    if phase_str not in _CTO_PHASE_MAP:
        return None
    phase = _CTO_PHASE_MAP[phase_str]

    # CT.gov criteria is mandatory for the PubMedBERT embedding input
    if meta is None or not meta.eligibility_criteria:
        return None
    criteria_text = meta.eligibility_criteria

    ta, ta_debug = _derive_therapeutic_area(meta)
    modality, mod_debug = _derive_modality(meta)
    capital = _derive_capital_position(row.get("source_class"))
    biomarker = _derive_biomarker_enrichment(criteria_text)

    asset = AssetInput(
        asset_name=nct_id,  # use NCT ID as the asset_name for benchmark trials
        sponsor=row.get("source"),
        phase=phase,
        therapeutic_area=ta,
        modality=modality,
        capital_position=capital,
        regulatory_designations=[],  # default; CT.gov v2 designation data inconsistent
        num_competitors=0,  # default — would need separate cohort query
        target_validated=False,  # default — would need literature lookup
        biomarker_enrichment=biomarker,
    )

    debug = {
        "ta_match": ta_debug,
        "modality_match": mod_debug,
        "biomarker_match": "regex_hit" if biomarker else "no_regex_hit",
        "source_class": str(row.get("source_class", "")),
        "completion_year": str(row.get("completion_year", "")),
    }

    return CtoRowDerivation(
        asset=asset,
        label=label,
        criteria_text=criteria_text,
        nctid=nct_id,
        debug=debug,
    )
