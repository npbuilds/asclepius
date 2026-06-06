"""Deal comparables — EV/peak-sales multiples and implied target value.

Loads cohort comparable JSON files from app/data/comparables/, indexes
them by (therapeutic_area, modality), and routes a request asset to the
matching cohort. Returns the median EV/peak-sales multiple and the
implied value when applied to the asset's peak-sales input.

Routing (v1.6):
  - Each comparable JSON declares its `therapeutic_area` and `modality`
    (e.g. "oncology" + "small_molecule", "cns" + "small_molecule").
  - At request time, look up the (TA, modality) bucket. If the bucket
    has ≥ 3 deals, that's the matched cohort.
  - If the bucket is empty or thin, fall back to the canonical kinase-TKI
    cohort and surface the fallback in `cohort_label` + `cohort_matched`
    so the UI can render an honest disclosure.

Routing intentionally excludes the per-asset JSON when the asset's name
matches a comparable id (self-referential exclusion). The framework is
self-consistent: adagrasib's own JSON would otherwise show up in
"Oncology · small molecule" lookups for adagrasib.

The math is intentionally simple — the value of the module is the
*curated cohort* (relevance to the target asset's therapeutic class)
and the *clean provenance* on each deal (every comp ships its source
citation). Adding a new cohort is purely additive: drop a JSON in
api/app/data/comparables/ with the TA + modality keys and it auto-
indexes on next restart.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from statistics import median

from ...domain import (
    Comparable,
    ComparablesResult,
    DiligenceRecord,
    Modality,
    TherapeuticArea,
)

log = logging.getLogger(__name__)

COMPARABLES_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "comparables"
)

# Minimum deals for a cohort to be considered "matched" rather than a
# fallback. 3 is the smallest n where the median is meaningfully different
# from any single point — at n=2 the median is just the average.
MIN_MATCHED_COHORT_SIZE = 3

# The canonical fallback cohort: kinase-TKI single-asset M&A. Used when
# the asset's (TA, modality) doesn't have a curated cohort yet.
# These are the v1 comparables that shipped with the worked example.
_KINASE_TKI_FALLBACK_IDS = ("encorafenib", "selpercatinib", "larotrectinib")
_KINASE_TKI_FALLBACK_LABEL = "Fallback: kinase-TKI single-asset M&A"

# v1.6+: modality families — group modalities into valuation-equivalent
# buckets so the cohort routing isn't broken by fine-grained classification.
# Real-world valuation: acquirers price a tumor-antigen-targeting biologic
# similarly whether it's a naked mAb or an ADC variant (Trodelvy/Elahere/
# Padcev all sit in the same EV/peak-sales ballpark). Grouping by family
# keeps cohorts at usable n=3+ without inventing comps. The label keeps
# the user-readable form (e.g. "biologic") rather than the modality enum.
_MODALITY_FAMILIES: dict[str, tuple[str, ...]] = {
    "biologic": (
        "monoclonal_antibody",
        "antibody_drug_conjugate",
        "protein",
    ),
    "cell_therapy": (
        "cell_therapy_autologous",
        "cell_therapy_allogeneic",
    ),
    "gene_therapy": ("gene_therapy",),
    "small_molecule": ("small_molecule",),
    "nucleic_acid": ("mrna", "oligonucleotide"),
    "peptide": ("peptide",),
    "other": ("other",),
}


def _family_for_modality(modality_value: str) -> str:
    """Map a Modality enum value to its valuation family."""
    for family, members in _MODALITY_FAMILIES.items():
        if modality_value in members:
            return family
    return "other"

# Display overrides for therapeutic-area enum values whose default
# title-case rendering would be wrong (acronyms). Add to this dict if a
# new TA enum needs a non-Title display form.
_TA_LABELS = {
    "cns": "CNS",
    "rare_orphan": "Rare/orphan",
    "ip": "IP",
}


def _load_comparable_json(comparable_id: str) -> dict | None:
    """Load one comparable JSON by file-stem id."""
    path = COMPARABLES_DIR / f"{comparable_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        log.warning("malformed comparable JSON at %s: %s", path, exc)
        return None


def _ev_to_peak_sales(data: dict) -> float | None:
    deal = data.get("deal_value_usd_m")
    peak = data.get("peak_sales_estimate_usd_m")
    if not deal or not peak:
        return None
    return round(deal / peak, 2)


@lru_cache(maxsize=1)
def _build_cohort_index() -> dict[tuple[str, str], list[str]]:
    """Walk COMPARABLES_DIR and group comparable ids by (TA, modality_family).

    Each comparable JSON declares its fine-grained modality (e.g.
    "antibody_drug_conjugate"); the index buckets by the corresponding
    modality family (e.g. "biologic"), so mAb + ADC + protein deals end
    up in the same bucket. The display label uses the family name.

    Cached because the JSON files don't change at runtime in production
    (they ship in the Docker image). Cache invalidates on process restart
    which is the only time new files get picked up.
    """
    index: dict[tuple[str, str], list[str]] = {}
    if not COMPARABLES_DIR.is_dir():
        log.warning("comparables directory missing: %s", COMPARABLES_DIR)
        return index
    for path in sorted(COMPARABLES_DIR.glob("*.json")):
        data = _load_comparable_json(path.stem)
        if not data:
            continue
        ta = data.get("therapeutic_area")
        modality = data.get("modality")
        if not ta or not modality:
            # Comparables without TA + modality are skipped from indexing
            # (typically the per-asset "this is the target" JSONs, not
            # actual deal comps). Adagrasib's JSON is this case.
            continue
        family = _family_for_modality(str(modality))
        key = (str(ta), family)
        index.setdefault(key, []).append(path.stem)
    log.info(
        "comparables index: %d cohort buckets, %d total deals",
        len(index),
        sum(len(v) for v in index.values()),
    )
    return index


def _select_cohort(
    asset_ta: TherapeuticArea,
    asset_modality: Modality,
    exclude_id: str | None = None,
) -> tuple[list[str], str, bool]:
    """Return (cohort_ids, human_readable_label, is_matched).

    is_matched=True when the asset's (TA, modality_family) bucket has ≥
    MIN_MATCHED_COHORT_SIZE deals; False when we fall back to the
    kinase-TKI cohort. The label is what the UI displays.
    """
    index = _build_cohort_index()
    family = _family_for_modality(asset_modality.value)
    key = (asset_ta.value, family)
    bucket = list(index.get(key, []))
    if exclude_id is not None and exclude_id in bucket:
        bucket = [b for b in bucket if b != exclude_id]
    if len(bucket) >= MIN_MATCHED_COHORT_SIZE:
        # Acronym TAs render as ALL-CAPS rather than Title-Case ("CNS",
        # not "Cns"; "IBD" not "Ibd").
        ta_label = _TA_LABELS.get(asset_ta.value) or asset_ta.value.replace("_", " ").title()
        # Family label is the same string we indexed under, but rendered
        # readably (underscore → space). We DON'T expose the raw
        # underlying modality enum here because the bucket may contain
        # multiple modalities under the same family.
        label = (
            f"{ta_label} · "
            f"{family.replace('_', ' ')} ({len(bucket)} deals)"
        )
        return bucket, label, True
    # Fallback: kinase-TKI cohort, with disclosure surfaced via the label
    # and the cohort_matched=False flag.
    return list(_KINASE_TKI_FALLBACK_IDS), _KINASE_TKI_FALLBACK_LABEL, False


def compute(
    record: DiligenceRecord, cohort_ids: list[str] | None = None
) -> ComparablesResult:
    """Required entrypoint.

    When `cohort_ids` is explicitly provided, skip routing and use those
    ids verbatim — useful for tests and methodology demos. Otherwise
    route by the asset's (TA, modality).
    """
    if cohort_ids is None:
        # Exclude the asset's own JSON if it happens to share an id with
        # a comparable (e.g., adagrasib.json contains adagrasib metadata
        # but it isn't a real comp because the framework is currently
        # evaluating adagrasib itself).
        exclude_id = (record.asset.asset_name or "").lower()
        cohort_ids, cohort_label, matched = _select_cohort(
            record.asset.therapeutic_area,
            record.asset.modality,
            exclude_id=exclude_id,
        )
    else:
        cohort_label = "Custom cohort (analyst-supplied ids)"
        matched = True

    cohort: list[Comparable] = []
    multiples: list[float] = []
    for cid in cohort_ids:
        data = _load_comparable_json(cid)
        if data is None:
            continue
        ev_peak = _ev_to_peak_sales(data)
        if ev_peak is not None:
            multiples.append(ev_peak)
        cohort.append(
            Comparable(
                asset_name=data.get("asset_name", cid),
                acquirer=data.get("acquirer"),
                deal_value_usd_m=data.get("deal_value_usd_m"),
                deal_date=data.get("deal_date"),
                peak_sales_estimate_usd_m=data.get("peak_sales_estimate_usd_m"),
                ev_to_peak_sales=ev_peak,
                notes=data.get("notes"),
                source=data.get("source"),
            )
        )

    median_mult = median(multiples) if multiples else None

    implied_value: float | None = None
    if median_mult is not None and record.rnpv_inputs is not None:
        implied_value = round(median_mult * record.rnpv_inputs.peak_sales_usd_m, 1)

    return ComparablesResult(
        cohort=cohort,
        median_ev_to_peak_sales=median_mult,
        implied_value_usd_m=implied_value,
        cohort_label=cohort_label,
        cohort_matched=matched,
    )
