"""Sync the calibration module's SQLite log → predictions/*.json (the
publicly-auditable derivative).

Run from anywhere (the script resolves paths relative to its own location).
Idempotent — running it twice produces the same files (modulo any predictions
logged in between).

The contract:
  - SQLite is the runtime store.
  - predictions/<YYYY-MM-DD>-<asset-slug>.json files are the publicly-auditable
    derivative. They are written by this script and committed to git.
  - Any prediction the framework makes on a public asset is expected to end up
    in this folder. That's the v1.6 calibration-credibility commitment.
  - When the prediction is resolved (FDA action, M&A, discontinuation), the
    same JSON file is updated with the outcome. Git history shows when each
    resolution happened.

Schema of each public JSON:

    {
      "prediction_id": "<sqlite row id>",
      "asset": {
        "name": "...",
        "phase": "...",
        "therapeutic_area": "...",
        "modality": "...",
        "capital_position": "..."
      },
      "framework": {
        "predicted_pos": 0.161,
        "reflexivity_multiplier": 1.0
      },
      "prediction_date": "YYYY-MM-DD",
      "resolution": {
        "outcome": 1 | 0 | null,
        "date": "YYYY-MM-DD" | null,
        "source": "..." | null
      },
      "schema_version": "1.0"
    }

Usage:
    python api/scripts/sync_predictions_to_public_log.py            # full sync
    python api/scripts/sync_predictions_to_public_log.py --dry-run  # preview
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent
REPO_DIR = API_DIR.parent
PREDICTIONS_DIR = REPO_DIR / "predictions"

# Make app/ importable when running this file directly
sys.path.insert(0, str(API_DIR))

from app.modules.calibration import db  # noqa: E402
from app.modules.calibration.schemas import PredictionLogEntry  # noqa: E402
from app.utils.text import slugify_asset_name as _slugify  # noqa: E402

# v1.6.1 (Codex F8): one canonical schema version constant for the public log,
# imported by tests and methodology cross-references. Bump when the public
# JSON shape changes in a backward-incompatible way.
PUBLIC_LOG_SCHEMA_VERSION = "1.0"


def _entry_to_public_dict(entry: PredictionLogEntry) -> dict:
    return {
        "prediction_id": entry.id,
        "asset": {
            "name": entry.asset_name,
            "phase": entry.phase,
            "therapeutic_area": entry.therapeutic_area,
            "modality": entry.modality,
            "capital_position": entry.capital_position,
        },
        "framework": {
            "predicted_pos": entry.predicted_pos,
            "reflexivity_multiplier": entry.reflexivity_multiplier,
        },
        "prediction_date": entry.prediction_date.isoformat(),
        "resolution": {
            "outcome": entry.outcome,
            "date": entry.outcome_date.isoformat() if entry.outcome_date else None,
            "source": entry.outcome_source,
        },
        "schema_version": PUBLIC_LOG_SCHEMA_VERSION,
    }


def _filename_for(entry: PredictionLogEntry) -> str:
    """Public-log filename.

    v1.6.1 (Codex F2): includes prediction_id to avoid silent collisions
    when two predictions share the same date + asset. v1.6.0 used only
    (date, slug) which would overwrite one prediction with another in the
    real-world case of multiple framework runs on the same asset on the
    same day (e.g., before/after a parameter sweep).
    """
    pid_slug = _slugify(entry.id)
    return (
        f"{entry.prediction_date.isoformat()}-"
        f"{_slugify(entry.asset_name)}-{pid_slug}.json"
    )


def sync(*, dry_run: bool = False, db_path: Path | None = None) -> dict:
    """Write one JSON per prediction. Returns a summary dict.

    v1.6.1 (Codex F7): accepts an optional db_path so tests can isolate the
    input fixture. Production callers omit it and use the default DB.
    """
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    entries = db.list_predictions(db_path=db_path)

    new_files: list[str] = []
    updated_files: list[str] = []
    unchanged_files: list[str] = []

    for entry in entries:
        out_path = PREDICTIONS_DIR / _filename_for(entry)
        payload = _entry_to_public_dict(entry)
        new_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"

        if out_path.exists():
            existing = out_path.read_text()
            if existing == new_text:
                unchanged_files.append(out_path.name)
                continue
            updated_files.append(out_path.name)
        else:
            new_files.append(out_path.name)

        if not dry_run:
            out_path.write_text(new_text)

    summary = {
        "n_total": len(entries),
        "n_new": len(new_files),
        "n_updated": len(updated_files),
        "n_unchanged": len(unchanged_files),
        "predictions_dir": str(PREDICTIONS_DIR),
        "new": new_files,
        "updated": updated_files,
        "dry_run": dry_run,
    }
    return summary


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv
    summary = sync(dry_run=dry_run)
    print(f"synced {summary['n_total']} predictions → {summary['predictions_dir']}")
    print(
        f"  new: {summary['n_new']}  updated: {summary['n_updated']}  "
        f"unchanged: {summary['n_unchanged']}"
        + ("  (dry-run; no files written)" if dry_run else "")
    )
    for name in summary["new"]:
        print(f"  + {name}")
    for name in summary["updated"]:
        print(f"  ~ {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
