"""Build the v1.5.2 BioBERT training dataset.

Reads all 9 HINT CSV files (Phase I/II/III × train/valid/test), dedups by
NCT ID (last-write-wins), derives our 36-dim feature vector per row, and
writes a unified parquet at api/data/training/training_dataset.parquet
(gitignored).

Columns in the output parquet:
  nctid              - str  (primary key)
  phase              - str  (enum value)
  therapeutic_area   - str  (enum value)
  modality           - str  (enum value)
  capital_position   - str  (enum value, defaults to 'adequate')
  biomarker_enrichment - bool
  target_validated   - bool (defaults to False)
  num_competitors    - int  (defaults to 0)
  feature_vector     - list[float] (length 36, from encode())
  criteria_text      - str  (for BioBERT embedding step)
  label              - int  (0 = failure, 1 = success)
  split              - str  ('train' | 'valid' | 'test')
  source_phase_file  - str  (which HINT split the row came from)

Usage (from api/ with venv active):
    python -m data_pipeline.build_training_dataset
    python -m data_pipeline.build_training_dataset --limit 100   # quick smoke
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import Counter
from pathlib import Path

# Ensure app/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.ml_pos_prior.features import encode  # noqa: E402
from data_pipeline.derive_features import (  # noqa: E402
    HintRowDerivation,
    derive_from_hint_row,
)

log = logging.getLogger(__name__)
csv.field_size_limit(sys.maxsize)


API_DIR = Path(__file__).resolve().parent.parent
HINT_DIR = API_DIR / "data" / "hint"
OUT_DIR = API_DIR / "data" / "training"
OUT_PARQUET = OUT_DIR / "training_dataset.parquet"

HINT_FILES = [
    ("phase_I_train.csv", "train"),
    ("phase_I_valid.csv", "valid"),
    ("phase_I_test.csv", "test"),
    ("phase_II_train.csv", "train"),
    ("phase_II_valid.csv", "valid"),
    ("phase_II_test.csv", "test"),
    ("phase_III_train.csv", "train"),
    ("phase_III_valid.csv", "valid"),
    ("phase_III_test.csv", "test"),
]


def load_hint_rows(hint_root: Path, *, limit: int | None = None):
    """Iterator over (filename, split, row_dict) tuples from all 9 files."""
    data_dir = hint_root / "data"
    if not data_dir.is_dir():
        raise FileNotFoundError(
            f"HINT data directory not found at {data_dir}. "
            f"Run api/data_pipeline/download_hint.sh first."
        )
    seen = 0
    for fname, split in HINT_FILES:
        path = data_dir / fname
        if not path.is_file():
            log.warning("missing HINT file: %s — skipping", path)
            continue
        with path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield fname, split, row
                seen += 1
                if limit is not None and seen >= limit:
                    return


def build_dataset(*, limit: int | None = None) -> dict:
    """Main entrypoint. Returns a stats summary dict."""
    derivations: dict[str, tuple[HintRowDerivation, str, str]] = {}
    skipped = Counter()
    raw_seen = 0

    for fname, split, row in load_hint_rows(HINT_DIR, limit=limit):
        raw_seen += 1
        d = derive_from_hint_row(row)
        if d is None:
            skipped["unparseable"] += 1
            continue
        # Dedup: HINT splits don't usually overlap, but if they do, keep the
        # last one we see (train < valid < test priority since we iterate in
        # that order, so test split wins — preserving held-out eval set).
        derivations[d.nctid] = (d, split, fname)

    log.info(
        "raw HINT rows: %d, deduped derivations: %d, skipped: %s",
        raw_seen,
        len(derivations),
        dict(skipped),
    )

    # Encode each derivation to its 36-dim feature vector + write parquet
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # pandas + pyarrow imports are deferred so this module can be tested
    # without those heavy deps available
    import pandas as pd  # noqa: E402

    rows = []
    for nctid, (d, split, fname) in derivations.items():
        try:
            fvec = encode(d.asset).tolist()
        except Exception as exc:
            log.warning("encode failed for %s: %s — skipping", nctid, exc)
            skipped["encode_error"] += 1
            continue
        rows.append(
            {
                "nctid": nctid,
                "phase": d.asset.phase.value,
                "therapeutic_area": d.asset.therapeutic_area.value,
                "modality": d.asset.modality.value,
                "capital_position": d.asset.capital_position.value,
                "biomarker_enrichment": d.asset.biomarker_enrichment,
                "target_validated": d.asset.target_validated,
                "num_competitors": d.asset.num_competitors,
                "feature_vector": fvec,
                "criteria_text": d.criteria_text,
                "label": d.label,
                "split": split,
                "source_phase_file": fname,
            }
        )

    df = pd.DataFrame(rows)
    df.to_parquet(OUT_PARQUET, index=False)

    # Compose a stats summary for printing
    stats = {
        "raw_seen": raw_seen,
        "derived_unique": len(derivations),
        "encoded": len(df),
        "skipped": dict(skipped),
        "output_path": str(OUT_PARQUET),
        "output_size_mb": round(OUT_PARQUET.stat().st_size / 1024 / 1024, 2),
    }
    if not df.empty:
        stats["splits"] = df["split"].value_counts().to_dict()
        stats["phase_counts"] = df["phase"].value_counts().to_dict()
        stats["modality_counts"] = df["modality"].value_counts().to_dict()
        stats["therapeutic_area_counts"] = df["therapeutic_area"].value_counts().to_dict()
        stats["biomarker_rate"] = round(df["biomarker_enrichment"].mean(), 3)
        stats["label_rate_overall"] = round(df["label"].mean(), 3)
        stats["label_rate_by_phase"] = (
            df.groupby("phase")["label"].mean().round(3).to_dict()
        )
    return stats


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap rows for a quick smoke test (e.g. 100). Default: full corpus.",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    stats = build_dataset(limit=args.limit)

    print("\nBUILD COMPLETE")
    for k, v in stats.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for sk, sv in sorted(v.items()):
                print(f"    {sk}: {sv}")
        else:
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
