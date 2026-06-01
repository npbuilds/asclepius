"""CT Open benchmark — bulk CT.gov metadata fetch with resumable caching.

Stage 3 of the CT Open benchmark pipeline. Runs after the scaffolding
modules (cto_acquire + cto_fetch_metadata + cto_derive_features) but
before embedding + retrain.

Loads the uncontaminated CTO trial set (~2,429 NCT IDs), fetches each
trial's CT.gov v2 metadata, and persists successful fetches to
api/data/cto/metadata_cache.jsonl. The cache is append-only — restarting
the script skips NCT IDs already on disk, so the fetch is interruptible.

Output format (JSON Lines, one record per line):
  {
    "nct_id": "NCT04685135",
    "eligibility_criteria": "...",
    "conditions": [...],
    "intervention_types": [...],
    "intervention_names": [...],
    "mesh_terms": [...],
    "enrollment_count": 453
  }

Failed fetches (404, network error, missing fields) are NOT written to
the cache — they just get skipped with a logged warning. On a follow-up
run those trials will be re-attempted. To force a "dead trial" list,
maintain it manually or extend this script to write failures to a
sidecar file.

Run with:
  cd api && python data_pipeline/cto_fetch_batch.py
"""

from __future__ import annotations

import dataclasses
import json
import logging
import time
from pathlib import Path

from .cto_acquire import load_uncontaminated_test_set
from .cto_fetch_metadata import (
    REQUEST_INTERVAL_SECONDS,
    fetch_ctgov_metadata,
)

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
CACHE_PATH = API_DIR / "data" / "cto" / "metadata_cache.jsonl"


def _already_cached_nct_ids(cache_path: Path) -> set[str]:
    """Read the cache file (if it exists) and return the set of NCT IDs
    we've already successfully fetched. Lines that can't be parsed are
    silently ignored — we'd rather re-fetch a corrupted line than crash."""
    if not cache_path.exists():
        return set()
    cached: set[str] = set()
    with cache_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            nct = record.get("nct_id")
            if isinstance(nct, str):
                cached.add(nct.upper())
    return cached


def _serialize(metadata) -> dict:
    """Convert a CtGovMetadata dataclass to a JSON-serializable dict,
    deliberately dropping the raw payload (large + redundant with the
    structured fields)."""
    out = dataclasses.asdict(metadata)
    out.pop("raw", None)
    return out


def run_batch(
    *,
    cache_path: Path = CACHE_PATH,
    throttle_seconds: float = REQUEST_INTERVAL_SECONDS,
    log_every: int = 50,
) -> dict:
    """Top-level runner. Returns a stats dict."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    already = _already_cached_nct_ids(cache_path)
    log.info("Cache at %s currently holds %d NCT IDs", cache_path, len(already))

    result = load_uncontaminated_test_set()
    targets = [
        n for n in result.uncontaminated["nct_id"].tolist()
        if n.upper() not in already
    ]
    log.info(
        "Uncontaminated set: %d trials. Already cached: %d. To fetch: %d.",
        len(result.uncontaminated), len(already), len(targets),
    )

    n_ok = 0
    n_skip = 0
    n_already = len(already)
    started = time.time()

    with cache_path.open("a", encoding="utf-8") as out_f:
        for i, nct in enumerate(targets, start=1):
            meta = fetch_ctgov_metadata(nct)
            if meta is None or not meta.eligibility_criteria:
                # No criteria = useless for the PubMedBERT embedding step
                n_skip += 1
            else:
                out_f.write(json.dumps(_serialize(meta)) + "\n")
                out_f.flush()  # so tail -f / wc -l reflect progress live
                n_ok += 1

            if i % log_every == 0:
                elapsed = time.time() - started
                rate = i / elapsed if elapsed > 0 else 0
                eta_min = (len(targets) - i) / rate / 60 if rate > 0 else 0
                log.info(
                    "%d / %d (%d ok, %d skip) — %.1f req/s, eta %.1f min",
                    i, len(targets), n_ok, n_skip, rate, eta_min,
                )

            if i < len(targets):
                time.sleep(throttle_seconds)

    elapsed = time.time() - started
    final = {
        "n_uncontaminated": int(len(result.uncontaminated)),
        "n_already_cached": int(n_already),
        "n_attempted": int(len(targets)),
        "n_succeeded": int(n_ok),
        "n_skipped": int(n_skip),
        "n_total_cached_after": int(n_already + n_ok),
        "elapsed_seconds": round(elapsed, 1),
        "throttle_seconds": throttle_seconds,
    }
    log.info("batch complete: %s", final)
    return final


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    stats = run_batch()
    print("\n=== Batch fetch stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
