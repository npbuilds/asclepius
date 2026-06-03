"""v1.5.6 — Build a CTO training parquet from the 2,429-trial benchmark set.

The v1.5.5 benchmark established AUC 0.600 on these trials as the honest
external validation. v1.5.6 now *trains* on them (the benchmark milestone
is permanently recorded in methodology/13; training on labelled data is
the natural next step, per standard ML practice).

Outputs:
  api/data/training/cto_training_dataset.parquet   (same schema as
                                                    training_dataset.parquet)

Split strategy: stratified 65/15/20 train/val/test within each
(phase × label) stratum. This preserves the conformal calibration
split discipline: val rows → Mondrian radii; test rows → honest
held-out evaluation distinct from both HINT test and the old
benchmark framing.

Run with:
  cd api && python -m data_pipeline.build_cto_training_dataset
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.ml_pos_prior.features import encode  # noqa: E402
from data_pipeline.cto_acquire import load_uncontaminated_test_set  # noqa: E402
from data_pipeline.cto_derive_features import derive_from_cto_row  # noqa: E402
from data_pipeline.cto_fetch_metadata import CtGovMetadata  # noqa: E402

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
CTO_DIR = API_DIR / "data" / "cto"
TRAINING_DIR = API_DIR / "data" / "training"
METADATA_CACHE = CTO_DIR / "metadata_cache.jsonl"
EMBEDDINGS_NPY = CTO_DIR / "cto_embeddings.npy"
EMBEDDINGS_NCTIDS = CTO_DIR / "cto_embeddings_nctid.txt"
OUT_PARQUET = TRAINING_DIR / "cto_training_dataset.parquet"

# 65 / 15 / 20 split — generous val (conformal calibration) + test (per-phase eval)
TRAIN_FRAC = 0.65
VAL_FRAC = 0.15
# TEST_FRAC = 1 - TRAIN_FRAC - VAL_FRAC = 0.20

RANDOM_SEED = 42


def _load_metadata_cache(path: Path) -> dict[str, CtGovMetadata]:
    """Rehydrate the Stage 3 JSONL cache (same as cto_benchmark.py)."""
    if not path.exists():
        raise FileNotFoundError(
            f"Metadata cache not found at {path}. "
            "Run: python -m data_pipeline.cto_fetch_batch"
        )
    out: dict[str, CtGovMetadata] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out[r["nct_id"].upper()] = CtGovMetadata(
                nct_id=r["nct_id"],
                eligibility_criteria=r.get("eligibility_criteria"),
                conditions=r.get("conditions", []),
                intervention_types=r.get("intervention_types", []),
                intervention_names=r.get("intervention_names", []),
                mesh_terms=r.get("mesh_terms", []),
                enrollment_count=r.get("enrollment_count"),
                raw={},
            )
    log.info("loaded %d metadata records", len(out))
    return out


def _stratified_split(
    rows: list[dict],
    *,
    seed: int = RANDOM_SEED,
) -> list[dict]:
    """Assign 'split' key (train/valid/test) to each row using stratified
    sampling within each (phase × label) cell.

    Rows with insufficient cell size (<5) fall into 'train' to avoid
    empty val/test strata breaking conformal coverage.
    """
    rng = np.random.default_rng(seed)
    # Group by stratum
    strata: dict[tuple, list[int]] = {}
    for i, row in enumerate(rows):
        key = (row["phase"], int(row["label"]))
        strata.setdefault(key, []).append(i)

    # Assign splits within each stratum
    splits = ["train"] * len(rows)
    for key, indices in strata.items():
        arr = np.array(indices)
        arr = rng.permutation(arr)
        n = len(arr)
        if n < 5:
            # Too small to split — put all in train
            continue
        n_val = max(1, int(round(n * VAL_FRAC)))
        n_test = max(1, int(round(n * (1 - TRAIN_FRAC - VAL_FRAC))))
        n_test = min(n_test, n - n_val - 1)  # ensure at least 1 train
        for idx in arr[:n_val]:
            splits[idx] = "valid"
        for idx in arr[n_val : n_val + n_test]:
            splits[idx] = "test"
        # remainder → "train"
    return splits


def build() -> dict:
    """Main builder. Returns stats dict."""
    log.info("loading CTO uncontaminated test set (the 2,429-trial benchmark set)…")
    acquired = load_uncontaminated_test_set()
    test_df = acquired.uncontaminated.copy()
    test_df["nct_id"] = test_df["nct_id"].str.upper()

    log.info("loading Stage 3 metadata cache…")
    metadata = _load_metadata_cache(METADATA_CACHE)

    log.info("loading Stage 4 CTO embeddings…")
    emb_arr = np.load(EMBEDDINGS_NPY)
    emb_nctids = EMBEDDINGS_NCTIDS.read_text().strip().split("\n")
    emb_dict: dict[str, np.ndarray] = {
        nid.upper(): emb_arr[i] for i, nid in enumerate(emb_nctids)
    }
    log.info("embeddings loaded: %d trials", len(emb_dict))

    rows: list[dict] = []
    skipped: Counter = Counter()

    for _, row in test_df.iterrows():
        nct = row["nct_id"]
        meta = metadata.get(nct)
        if meta is None:
            skipped["no_metadata"] += 1
            continue
        if nct not in emb_dict:
            skipped["no_embedding"] += 1
            continue
        derivation = derive_from_cto_row(row.to_dict(), meta)
        if derivation is None:
            skipped["derivation_failed"] += 1
            continue
        try:
            fvec = encode(derivation.asset).tolist()
        except Exception as exc:
            log.warning("encode failed for %s: %s", nct, exc)
            skipped["encode_error"] += 1
            continue

        rows.append({
            "nctid": nct,
            "phase": derivation.asset.phase.value,
            "therapeutic_area": derivation.asset.therapeutic_area.value,
            "modality": derivation.asset.modality.value,
            "capital_position": derivation.asset.capital_position.value,
            "biomarker_enrichment": derivation.asset.biomarker_enrichment,
            "target_validated": derivation.asset.target_validated,
            "num_competitors": derivation.asset.num_competitors,
            "feature_vector": fvec,
            "criteria_text": derivation.criteria_text or "",
            "label": derivation.label,
            "split": "train",       # placeholder; _stratified_split fills this in
            "source_phase_file": row.get("phase_normalized", "cto_external"),
            "source_domain": "cto",  # v1.5.6: tracks provenance
        })

    log.info("derived %d rows, skipped %s", len(rows), dict(skipped))

    # Assign stratified splits
    splits = _stratified_split(rows)
    for i, row in enumerate(rows):
        row["split"] = splits[i]

    log.info("split counts: %s", Counter(splits))

    # Write parquet (deferred import — consistent with HINT builder)
    import pandas as pd  # noqa: PLC0415

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_parquet(OUT_PARQUET, index=False)
    log.info("wrote CTO training parquet → %s (%.2f MB)", OUT_PARQUET,
             OUT_PARQUET.stat().st_size / 1e6)

    stats = {
        "n_total": len(rows),
        "skipped": dict(skipped),
        "splits": Counter(splits),
        "phase_counts": df["phase"].value_counts().to_dict(),
        "label_rate_overall": round(df["label"].mean(), 3),
        "label_rate_by_phase": df.groupby("phase")["label"].mean().round(3).to_dict(),
        "output_path": str(OUT_PARQUET),
    }
    return stats


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = build()
    print("\nCTO TRAINING DATASET BUILD COMPLETE")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
