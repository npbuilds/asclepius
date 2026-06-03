"""v1.5.7 — Bulk CT.gov metadata fetch for HINT trials (resumable).

Mirrors cto_fetch_batch.py but targets the HINT corpus. HINT ships only
nctid/status/label/phase/diseases/icdcodes/drugs/smiless/criteria — it
does NOT carry the trial-design fields (enrollment, arms, allocation,
masking) that Doane et al. 2025 use to reach AUC 0.74. v1.5.7 fetches
those from CT.gov v2 to close the within-phase discrimination gap that
v1.5.6 ([methodology/14]) diagnosed as informational, not architectural.

Coverage probe (60-trial stratified sample, 2026-06): fetch 100%,
enrollment 98%, num_arms 85%, allocation 97%, masking 97%. Strong enough
to make these real features rather than domain-leak proxies.

Output: api/data/hint/metadata_cache.jsonl (append-only, resumable).
Each line carries the v1.5.7 design fields:
  {"nct_id","eligibility_criteria","conditions","intervention_types",
   "intervention_names","mesh_terms","enrollment_count","num_arms",
   "allocation","masking"}

Run with:
  cd api && python -m data_pipeline.hint_fetch_metadata
"""

from __future__ import annotations

import dataclasses
import json
import logging
import time
from pathlib import Path

import pandas as pd

from .cto_fetch_metadata import REQUEST_INTERVAL_SECONDS, fetch_ctgov_metadata

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
HINT_PARQUET = API_DIR / "data" / "training" / "training_dataset.parquet"
CACHE_PATH = API_DIR / "data" / "hint" / "metadata_cache.jsonl"


def _already_cached(cache_path: Path) -> set[str]:
    if not cache_path.exists():
        return set()
    cached: set[str] = set()
    with cache_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            nct = rec.get("nct_id")
            if isinstance(nct, str):
                cached.add(nct.upper())
    return cached


def _serialize(meta) -> dict:
    out = dataclasses.asdict(meta)
    out.pop("raw", None)
    return out


def run_batch(
    *,
    cache_path: Path = CACHE_PATH,
    throttle_seconds: float = REQUEST_INTERVAL_SECONDS,
    log_every: int = 100,
) -> dict:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    already = _already_cached(cache_path)

    df = pd.read_parquet(HINT_PARQUET)
    all_ncts = [n.upper() for n in df["nctid"].tolist()]
    targets = [n for n in all_ncts if n not in already]
    log.info(
        "HINT corpus: %d trials. Already cached: %d. To fetch: %d.",
        len(all_ncts), len(already), len(targets),
    )

    n_ok = 0
    n_skip = 0
    started = time.time()

    with cache_path.open("a", encoding="utf-8") as out_f:
        for i, nct in enumerate(targets, start=1):
            meta = fetch_ctgov_metadata(nct)
            if meta is None:
                n_skip += 1
            else:
                # Unlike the CTO fetch, we DON'T require eligibility_criteria —
                # HINT already ships criteria text in the parquet; here we only
                # need the design fields. A trial with design data but no
                # criteria in CT.gov is still useful.
                out_f.write(json.dumps(_serialize(meta)) + "\n")
                out_f.flush()
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
        "n_hint": len(all_ncts),
        "n_already_cached": len(already),
        "n_attempted": len(targets),
        "n_succeeded": n_ok,
        "n_skipped": n_skip,
        "n_total_cached_after": len(already) + n_ok,
        "elapsed_seconds": round(elapsed, 1),
    }
    log.info("HINT metadata batch complete: %s", final)
    return final


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stats = run_batch()
    print("\n=== HINT metadata fetch stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
