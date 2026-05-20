"""Deal comparables — EV/peak-sales multiples and implied target value.

Loads cohort comparable JSON files from app/data/comparables/, computes the
EV/peak-sales multiple for each, takes the median, and applies it to the
target asset's peak sales to get an implied value.

This is intentionally simple math; the value of the module is the *curated
cohort* (relevance to the target asset's therapeutic class) and the *clean
provenance* on each deal — every comp ships its source citation.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from ...domain import (
    Comparable,
    ComparablesResult,
    DiligenceRecord,
    Modality,
    TherapeuticArea,
)

COMPARABLES_DIR = (
    Path(__file__).resolve().parent.parent.parent / "data" / "comparables"
)


# Default cohort for adagrasib-style assets: oncology + small-molecule targeted.
# Excludes adagrasib itself (it's the target, not a comp).
_ONCOLOGY_KINASE_COHORT = ("encorafenib", "selpercatinib", "larotrectinib")


def _load_comparable_json(comparable_id: str) -> dict | None:
    path = COMPARABLES_DIR / f"{comparable_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        # Skip malformed JSON rather than crashing the whole endpoint
        return None


def _ev_to_peak_sales(data: dict) -> float | None:
    deal = data.get("deal_value_usd_m")
    peak = data.get("peak_sales_estimate_usd_m")
    if not deal or not peak:
        return None
    return round(deal / peak, 2)


def _select_cohort(asset_ta: TherapeuticArea, asset_modality: Modality) -> tuple[str, ...]:
    """For v1 we only have one curated cohort. Future: route by TA + modality."""
    if asset_ta == TherapeuticArea.ONCOLOGY and asset_modality == Modality.SMALL_MOLECULE:
        return _ONCOLOGY_KINASE_COHORT
    # Fallback: return the oncology-kinase cohort with a note in upstream UI.
    return _ONCOLOGY_KINASE_COHORT


def compute(
    record: DiligenceRecord, cohort_ids: list[str] | None = None
) -> ComparablesResult:
    """Required entrypoint."""
    if cohort_ids is None:
        cohort_ids = list(
            _select_cohort(record.asset.therapeutic_area, record.asset.modality)
        )

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
    )
