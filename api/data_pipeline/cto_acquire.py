"""CT Open (CTO) benchmark — data acquisition + uncontamination filter.

Loads the CTO gold-tier human-annotated labels (Gao et al. 2024 / Nature
Health 2026 — https://chufangao.github.io/CTOD/), filters to phase_1/2/3
trials, identifies the uncontaminated subset (CTO trials NOT in HINT
training data), and returns clean dataframes for downstream embedding
and retrain.

Why uncontamination matters: HINT (Fu et al. 2022) labeled ~11.5K
clinical trials. Our v1.5.x model trains on HINT. CTO is built on
top of CTI.gov data and overlaps with HINT — the `hint_train` columns
in the CTO phase prediction CSVs flag which trials were also in HINT's
training set. For an honest external benchmark, we exclude those trials
from the held-out test set.

Uncontamination strategy:
  - Filter by completion_year ≥ 2023 (HINT was published 2022, so
    later-completing trials are essentially guaranteed to be unseen)
  - Cross-reference NCT IDs against the CTO phase prediction CSVs'
    `hint_train` columns to drop any remaining overlap

Expected output (as of the 2026-06 download): ~2,400 uncontaminated
phase_1/2/3 trials with manually-annotated outcome labels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
CTO_DIR = API_DIR / "data" / "cto"

HUMAN_LABELS_CSV = CTO_DIR / "human_labels_2020_2024.csv"
PHASE_PRED_CSVS = {
    "phase_1": CTO_DIR / "phase1_CTO_rf.csv",
    "phase_2": CTO_DIR / "phase2_CTO_rf.csv",
    "phase_3": CTO_DIR / "phase3_CTO_rf.csv",
}

# CTO uses uppercase phase strings; map to our lowercase enum values.
PHASE_NORMALIZATION = {
    "PHASE1": "phase_1",
    "PHASE2": "phase_2",
    "PHASE3": "phase_3",
}

# Trials we keep for downstream processing. Combined-phase classifications
# (PHASE1/PHASE2, PHASE2/PHASE3) are excluded because their phase semantics
# don't cleanly match our PoS-by-phase model. PHASE4 (post-approval) is
# also excluded because our model is fit on pre-approval transitions.
KEEP_PHASES = ("PHASE1", "PHASE2", "PHASE3")

# Trials completed before this year are at risk of HINT contamination.
# HINT (Fu et al. 2022) was finalized in early 2022; setting the cutoff at
# 2023 gives a conservative safety margin.
COMPLETION_YEAR_CUTOFF = 2023


@dataclass
class CtoUncontaminated:
    """Result of the acquire+filter pipeline."""

    # All CTO trials passing phase + completion-year filter.
    raw: pd.DataFrame
    # After cross-referencing with HINT-flagged trials.
    uncontaminated: pd.DataFrame
    # NCT IDs identified as HINT-overlapping (excluded from `uncontaminated`).
    hint_overlap_nct_ids: set[str]
    # Diagnostic counts for logging / methodology writeup.
    stats: dict[str, int]


def _load_hint_nct_ids() -> set[str]:
    """Identify NCT IDs that appear in HINT training data, by reading the
    `hint_train*` columns of the CTO phase prediction CSVs. A trial is
    flagged HINT-overlapping if any of `hint_train`, `hint_train2`, or
    `hint_train3` is non-missing (CTO uses -1 as the missing sentinel)."""
    overlap: set[str] = set()
    for phase, path in PHASE_PRED_CSVS.items():
        if not path.exists():
            log.warning("CTO phase prediction CSV missing: %s", path)
            continue
        df = pd.read_csv(
            path,
            usecols=["nct_id", "hint_train", "hint_train2", "hint_train3"],
            low_memory=False,
        )
        in_hint = (
            (df["hint_train"] != -1)
            | (df["hint_train2"] != -1)
            | (df["hint_train3"] != -1)
        )
        overlap.update(df.loc[in_hint, "nct_id"].tolist())
        log.info(
            "%s: %d trials, %d HINT-flagged",
            phase, len(df), int(in_hint.sum()),
        )
    log.info("Total unique HINT-flagged NCT IDs across phases: %d", len(overlap))
    return overlap


def load_uncontaminated_test_set(
    *,
    completion_year_cutoff: int = COMPLETION_YEAR_CUTOFF,
) -> CtoUncontaminated:
    """Top-level entry point. Loads, filters, returns the uncontaminated
    phase_1/2/3 CTO test set."""
    if not HUMAN_LABELS_CSV.exists():
        raise FileNotFoundError(
            f"CTO gold-tier human labels not found at {HUMAN_LABELS_CSV}. "
            f"Download from "
            f"https://huggingface.co/datasets/chufangao/CTO/resolve/main/"
            f"human_labels_2020_2024/human_labels_2020_2024.csv"
        )

    human = pd.read_csv(HUMAN_LABELS_CSV, low_memory=False)
    n_total = len(human)
    log.info("Loaded %d rows from CTO human_labels", n_total)

    # Phase filter — keep only single-phase 1/2/3
    phase_mask = human["phase"].isin(KEEP_PHASES)
    phase_filtered = human[phase_mask].copy()
    log.info("After phase filter (PHASE1/2/3 only): %d", len(phase_filtered))

    # Completion-year filter
    phase_filtered["completion_year"] = pd.to_numeric(
        phase_filtered["completion_year"], errors="coerce",
    )
    year_mask = phase_filtered["completion_year"] >= completion_year_cutoff
    year_filtered = phase_filtered[year_mask].copy()
    log.info(
        "After completion_year ≥ %d filter: %d",
        completion_year_cutoff, len(year_filtered),
    )

    # Label-resolved filter — drop rows with missing label
    label_mask = year_filtered["labels"].notna()
    labeled = year_filtered[label_mask].copy()
    log.info("After labels-not-null filter: %d", len(labeled))

    # HINT-overlap filter
    hint_overlap = _load_hint_nct_ids()
    uncontaminated_mask = ~labeled["nct_id"].isin(hint_overlap)
    uncontaminated = labeled[uncontaminated_mask].copy()
    log.info(
        "After HINT-overlap filter: %d uncontaminated (dropped %d)",
        len(uncontaminated), (~uncontaminated_mask).sum(),
    )

    # Normalize the phase column to our lowercase enum values for downstream
    uncontaminated["phase_normalized"] = uncontaminated["phase"].map(
        PHASE_NORMALIZATION
    )
    labeled["phase_normalized"] = labeled["phase"].map(PHASE_NORMALIZATION)

    stats = {
        "n_total_human_labels": int(n_total),
        "n_after_phase_filter": int(len(phase_filtered)),
        "n_after_completion_year_filter": int(len(year_filtered)),
        "n_after_label_filter": int(len(labeled)),
        "n_hint_overlap_flagged": int(uncontaminated_mask.sum() * -1 + len(labeled)),
        "n_uncontaminated_final": int(len(uncontaminated)),
        "completion_year_cutoff": completion_year_cutoff,
    }

    return CtoUncontaminated(
        raw=labeled,
        uncontaminated=uncontaminated,
        hint_overlap_nct_ids=hint_overlap,
        stats=stats,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = load_uncontaminated_test_set()
    print(f"\nUncontaminated test set: {len(result.uncontaminated)} trials")
    print("\nPhase distribution:")
    print(result.uncontaminated["phase_normalized"].value_counts().to_string())
    print("\nLabel distribution:")
    print(result.uncontaminated["labels"].value_counts().to_string())
    print(f"\nBase rate (success): {result.uncontaminated['labels'].mean():.3f}")
