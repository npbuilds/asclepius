"""Tests for the predictions/ public-log sync script (v1.6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the scripts/ folder importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import sync_predictions_to_public_log as sync_module  # noqa: E402


def test_slugify_matches_calibration_conventions():
    assert sync_module._slugify("adagrasib") == "adagrasib"
    assert sync_module._slugify("debio 1347 (FGFR inhibitor)") == "debio_1347_fgfr_inhibitor"
    assert sync_module._slugify("") == "unnamed"


@pytest.fixture
def isolated_db(tmp_path: Path) -> Path:
    """v1.6.1 (Codex F7): give the sync a tmp DB path so tests don't depend on
    ambient calibration state. The seed_data.json still populates the tmp DB
    on first open via the existing _ensure_seeded() machinery."""
    return tmp_path / "calibration_test.db"


def test_sync_writes_one_file_per_prediction(tmp_path, monkeypatch, isolated_db):
    """Re-target the output dir at a tmp dir; verify file-per-row mapping."""
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    summary = sync_module.sync(dry_run=False, db_path=isolated_db)
    assert summary["n_total"] >= 5  # seed_data.json carries 8
    n_written = len(list(tmp_path.glob("*.json")))
    assert n_written == summary["n_total"]


def test_sync_is_idempotent(tmp_path, monkeypatch, isolated_db):
    """Second run should report 0 new / 0 updated / N unchanged."""
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    sync_module.sync(dry_run=False, db_path=isolated_db)
    second = sync_module.sync(dry_run=False, db_path=isolated_db)
    assert second["n_new"] == 0
    assert second["n_updated"] == 0
    assert second["n_unchanged"] >= 5


def test_dry_run_writes_nothing(tmp_path, monkeypatch, isolated_db):
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    summary = sync_module.sync(dry_run=True, db_path=isolated_db)
    assert summary["dry_run"] is True
    assert summary["n_new"] > 0
    assert len(list(tmp_path.glob("*.json"))) == 0


def test_output_schema_matches_contract(tmp_path, monkeypatch, isolated_db):
    """One spot-checked entry should have all the documented top-level keys."""
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    sync_module.sync(dry_run=False, db_path=isolated_db)
    adagrasib_file = next(tmp_path.glob("*adagrasib*.json"), None)
    assert adagrasib_file is not None
    payload = json.loads(adagrasib_file.read_text())
    assert set(payload.keys()) == {
        "prediction_id",
        "asset",
        "framework",
        "prediction_date",
        "resolution",
        "schema_version",
    }
    # v1.6.1 (Codex F8): assertion uses the shared constant, not a literal
    assert payload["schema_version"] == sync_module.PUBLIC_LOG_SCHEMA_VERSION
    assert payload["resolution"]["outcome"] == 1
    assert payload["asset"]["name"] == "adagrasib"


def test_filename_includes_prediction_id_to_avoid_collision(
    tmp_path, monkeypatch, isolated_db
):
    """v1.6.1 (Codex F2): two predictions on the same date for the same asset
    must NOT collide. The fix is to include prediction_id in the filename.

    We verify this by checking that all generated filenames are unique
    even when multiple seed predictions share a (date, asset) — and by
    confirming the filename pattern matches `<date>-<slug>-<pid_slug>.json`.
    """
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    sync_module.sync(dry_run=False, db_path=isolated_db)
    names = [p.name for p in tmp_path.glob("*.json")]
    assert len(names) == len(set(names)), "filename collision detected"
    # Each filename should have at least one '-' separator beyond the date,
    # marking the prediction_id segment.
    adagrasib = next((n for n in names if "adagrasib" in n), None)
    assert adagrasib is not None
    # 2022-06-01-adagrasib-seed_adagrasib_2022_06.json
    assert adagrasib.count("-") >= 4  # YYYY-MM-DD already has 2 dashes


def test_slugify_is_imported_from_shared_util():
    """v1.6.1 (Codex F9): the sync script's `_slugify` must be the canonical
    one from app.utils.text, not a duplicated re-implementation."""
    from app.utils.text import slugify_asset_name

    assert sync_module._slugify is slugify_asset_name
