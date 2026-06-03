"""v1.5.8 — fetch PLANNED enrollment from CT.gov v2 version-zero records.

Background: v1.5.7 ablation showed CT.gov's current `enrollmentInfo.count`
is ACTUAL enrollment (verified on a 30-trial sample: 30/30 ACTUAL), and a
trial terminated early for futility has low *actual* enrollment AS A
CONSEQUENCE of failing — so "low enrollment → failure" is post-hoc label
leakage, not prediction. See methodology/15 for the full diagnosis.

v1.5.8 fix: fetch each trial's REGISTRATION-TIME (version 0) enrollment
from the CT.gov internal version-history endpoint, which returns ESTIMATED
type or (for older trials registered before the schema added `type`) a
plain `count` field which is *by construction* the planned number because
it appears in the trial's first-ever registration submission.

Endpoint shape:
  GET https://clinicaltrials.gov/api/int/studies/{NCT}/history/0
  → JSON with protocolSection.designModule.enrollmentInfo containing
    {"count": N, "type": "ESTIMATED"} (newer) or just {"count": N} (older).

This is an undocumented internal endpoint (the one that powers the
"History of Changes" tab on CT.gov). It's stable, JSON-shaped, and the
only mechanism CT.gov exposes for per-version records. A recon probe of
45 stratified HINT trials returned 100% history-fetch success and 87%
effective enrollment coverage (39/45 had a parseable v0 count).

What this writes:
  Updates the existing JSONL caches in-place (HINT + CTO) by adding a
  `planned_enrollment_count` field to each record. The existing fields
  (eligibility_criteria, conditions, intervention_types/_names, mesh_terms,
  enrollment_count [the leaky ACTUAL one — left intact for audit],
  num_arms, allocation, masking) are unchanged.

Run with:
    cd api && python -m data_pipeline.fetch_planned_enrollment hint
    cd api && python -m data_pipeline.fetch_planned_enrollment cto
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

from .cto_fetch_metadata import (
    REQUEST_INTERVAL_SECONDS,
    _curl_fetch,
)

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
HINT_CACHE = API_DIR / "data" / "hint" / "metadata_cache.jsonl"
CTO_CACHE = API_DIR / "data" / "cto" / "metadata_cache.jsonl"

# The CT.gov internal version-history endpoint. NOT formally documented —
# this is what the public history viewer fetches client-side.
HISTORY_V0_TEMPLATE = "https://clinicaltrials.gov/api/int/studies/{nct}/history/0"

# Older-schema v0 records lack `type` but include `count`. Newer ones
# include both. We accept both forms; the type is recorded if present.
_ENROLL_BLOCK_RE = re.compile(r'"enrollmentInfo"\s*:\s*\{[^}]*\}')
_COUNT_RE = re.compile(r'"count"\s*:\s*(\d+)')
_TYPE_RE = re.compile(r'"type"\s*:\s*"([A-Z_]+)"')


def parse_planned_enrollment(body: str) -> tuple[int | None, str | None]:
    """Extract (count, type) from a v0 history payload.

    Returns (None, None) if no parseable enrollmentInfo block. `type` may
    be None when present in older-schema records (this is fine — v0 is the
    registration version by construction, so the count is planned).
    """
    m = _ENROLL_BLOCK_RE.search(body)
    if not m:
        return (None, None)
    block = m.group(0)
    cm = _COUNT_RE.search(block)
    if not cm:
        return (None, None)
    count = int(cm.group(1))
    tm = _TYPE_RE.search(block)
    type_val = tm.group(1) if tm else None
    return (count, type_val)


def fetch_planned_enrollment(nct_id: str) -> tuple[int | None, str | None]:
    """Fetch one trial's version-0 enrollmentInfo. Returns (count, type)
    with either side being None on any failure path. Logs failures.
    """
    nct_clean = nct_id.strip().upper()
    if not nct_clean.startswith("NCT"):
        return (None, None)
    url = HISTORY_V0_TEMPLATE.format(nct=nct_clean)
    status, body = _curl_fetch(url)
    if status != 200 or not body:
        log.info("history/0 returned %d for %s", status, nct_clean)
        return (None, None)
    return parse_planned_enrollment(body)


def _atomic_write(records: list[dict], cache_path: Path) -> None:
    """Write all records to a .tmp file then rename onto the target. If
    interrupted partway through the tmp write, the original cache stays
    intact; if interrupted between rename and program exit, the new cache
    is already in place. Standard POSIX rename-is-atomic pattern."""
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")
    tmp.replace(cache_path)


def _augment_cache(
    cache_path: Path,
    *,
    throttle: float,
    log_every: int = 100,
    checkpoint_every: int = 250,
) -> dict:
    """Read a metadata cache JSONL, add a `planned_enrollment_count` field
    to each record (when fetched successfully), checkpoint to disk every
    `checkpoint_every` records, rewrite atomically at the end.

    Resumable: skips records that already have the field populated (or were
    previously attempted unsuccessfully — the `_planned_fetch_attempted`
    sentinel). A run interrupted by laptop sleep or signal loses at most
    `checkpoint_every` records of progress.
    """
    if not cache_path.exists():
        raise FileNotFoundError(f"cache not found: {cache_path}")

    records: list[dict] = []
    with cache_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                log.warning("skip corrupt line in %s", cache_path)
    log.info("loaded %d records from %s", len(records), cache_path)

    todo = [
        r for r in records
        if r.get("planned_enrollment_count") is None
        and not r.get("_planned_fetch_attempted")
    ]
    log.info("to fetch (no planned_enrollment yet): %d", len(todo))

    n_ok, n_skip, n_typed, n_untyped = 0, 0, 0, 0
    started = time.time()

    for i, rec in enumerate(todo, start=1):
        nct = rec.get("nct_id")
        if not isinstance(nct, str):
            n_skip += 1
            continue
        count, type_val = fetch_planned_enrollment(nct)
        rec["_planned_fetch_attempted"] = True
        if count is not None:
            rec["planned_enrollment_count"] = count
            rec["planned_enrollment_type"] = type_val  # may be None for older schema
            n_ok += 1
            if type_val == "ESTIMATED":
                n_typed += 1
            else:
                n_untyped += 1
        else:
            n_skip += 1

        if i % log_every == 0:
            elapsed = time.time() - started
            rate = i / elapsed if elapsed else 0
            eta_min = (len(todo) - i) / rate / 60 if rate > 0 else 0
            log.info(
                "%d / %d (ok=%d skip=%d) — %.1f req/s, eta %.1f min",
                i, len(todo), n_ok, n_skip, rate, eta_min,
            )
        # Incremental checkpoint so an interrupted run doesn't lose more
        # than ~checkpoint_every records of progress.
        if i % checkpoint_every == 0:
            _atomic_write(records, cache_path)
            log.info("checkpoint written at %d/%d", i, len(todo))
        if i < len(todo):
            time.sleep(throttle)

    # Final write (catches the last <checkpoint_every records)
    _atomic_write(records, cache_path)

    elapsed = time.time() - started
    stats = {
        "cache_path": str(cache_path),
        "total_records": len(records),
        "to_fetch": len(todo),
        "n_succeeded": n_ok,
        "n_typed_estimated": n_typed,
        "n_typed_absent_old_schema": n_untyped,
        "n_failed": n_skip,
        "elapsed_seconds": round(elapsed, 1),
    }
    log.info("done: %s", stats)
    return stats


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "corpus", choices=["hint", "cto"],
        help="Which metadata cache to augment.",
    )
    parser.add_argument(
        "--throttle", type=float, default=REQUEST_INTERVAL_SECONDS,
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cache = HINT_CACHE if args.corpus == "hint" else CTO_CACHE
    stats = _augment_cache(cache, throttle=args.throttle)
    print("\n=== Planned-enrollment augmentation stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
