"""Tests for the predictions/ public-log sync script (v1.6)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the scripts/ folder importable
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import sync_predictions_to_public_log as sync_module  # noqa: E402


def test_slugify_matches_calibration_conventions():
    assert sync_module._slugify("adagrasib") == "adagrasib"
    assert sync_module._slugify("debio 1347 (FGFR inhibitor)") == "debio_1347_fgfr_inhibitor"
    assert sync_module._slugify("") == "unnamed"


def test_sync_writes_one_file_per_prediction(tmp_path, monkeypatch):
    """Re-target the output dir at a tmp dir; verify file-per-row mapping."""
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    summary = sync_module.sync(dry_run=False)
    assert summary["n_total"] >= 5  # seed_data.json carries 8
    n_written = len(list(tmp_path.glob("*.json")))
    assert n_written == summary["n_total"]


def test_sync_is_idempotent(tmp_path, monkeypatch):
    """Second run should report 0 new / 0 updated / N unchanged."""
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    sync_module.sync(dry_run=False)
    second = sync_module.sync(dry_run=False)
    assert second["n_new"] == 0
    assert second["n_updated"] == 0
    assert second["n_unchanged"] >= 5


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    summary = sync_module.sync(dry_run=True)
    assert summary["dry_run"] is True
    # No files written even though n_new > 0
    assert summary["n_new"] > 0
    assert len(list(tmp_path.glob("*.json"))) == 0


def test_output_schema_matches_contract(tmp_path, monkeypatch):
    """One spot-checked entry should have all the documented top-level keys."""
    monkeypatch.setattr(sync_module, "PREDICTIONS_DIR", tmp_path)
    sync_module.sync(dry_run=False)
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
    assert payload["schema_version"] == "1.0"
    assert payload["resolution"]["outcome"] == 1
    assert payload["asset"]["name"] == "adagrasib"
