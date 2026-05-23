"""Calibration module tests — DB layer + engine + Brier math."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    TherapeuticArea,
)
from app.modules.calibration import db, engine
from app.modules.calibration.schemas import AssetCalibrationContext


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Per-test SQLite path; seed_data.json will populate it on first open."""
    return tmp_path / "calibration_test.db"


def _record(name: str = "adagrasib") -> DiligenceRecord:
    return DiligenceRecord(
        asset=AssetInput(
            asset_name=name,
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.SMALL_MOLECULE,
            capital_position=CapitalPosition.ADEQUATE,
        )
    )


def test_log_and_resolve_round_trip(temp_db: Path):
    pid = db.log_prediction(
        asset_name="vorasidenib",
        phase="phase_2",
        therapeutic_area="oncology",
        modality="small_molecule",
        capital_position="well_capitalized",
        predicted_pos=0.20,
        reflexivity_multiplier=1.08,
        db_path=temp_db,
    )
    assert pid
    ok = db.resolve_prediction(
        prediction_id=pid,
        outcome=1,
        outcome_source="test",
        db_path=temp_db,
    )
    assert ok is True
    rows = db.list_predictions(db_path=temp_db)
    by_id = {r.id: r for r in rows}
    assert by_id[pid].outcome == 1
    assert by_id[pid].outcome_source == "test"


def test_resolve_missing_prediction_returns_false(temp_db: Path):
    ok = db.resolve_prediction(
        prediction_id="does-not-exist",
        outcome=1,
        db_path=temp_db,
    )
    assert ok is False


def test_seed_data_loads_on_first_access(temp_db: Path):
    """The seed JSON should populate an empty DB on first open."""
    rows = db.list_predictions(db_path=temp_db)
    assert len(rows) >= 5  # seed_data.json carries 8 predictions
    # adagrasib must be present and resolved as a success
    adagrasib = next((r for r in rows if r.asset_name == "adagrasib"), None)
    assert adagrasib is not None
    assert adagrasib.outcome == 1
    assert adagrasib.predicted_pos == pytest.approx(0.161, abs=1e-3)


def test_seed_is_idempotent(temp_db: Path):
    """Calling _open twice should not re-seed."""
    n1 = len(db.list_predictions(db_path=temp_db))
    n2 = len(db.list_predictions(db_path=temp_db))
    assert n1 == n2


def test_brier_score_computes_correctly(temp_db: Path):
    """Seed sample (5 success + 2 failure + 1 unresolved) has a known Brier."""
    report = db.get_calibration_report(db_path=temp_db)
    assert report.n_total_predictions == 8
    assert report.n_resolved == 7
    # Survivorship-biased: predictions ~15% but observed 5/7 ≈ 71% success
    # Brier should be in [0.3, 0.7] band given the calibration gap
    assert 0.3 < report.overall.brier_score < 0.7
    # Mean predicted should be much lower than mean observed
    assert report.overall.mean_predicted < report.overall.mean_observed


def test_segment_breakdown_has_resolved_and_unresolved_counts(temp_db: Path):
    """Verify per-segment stats include the unresolved count."""
    report = db.get_calibration_report(db_path=temp_db)
    # Should have oncology bucket; almost all seeds are oncology
    oncology = next(
        (s for s in report.by_therapeutic_area if s.segment_value == "oncology"),
        None,
    )
    assert oncology is not None
    assert oncology.n_resolved + oncology.n_unresolved >= 7


def test_engine_compute_returns_context_for_segment(temp_db: Path, monkeypatch):
    """Engine pulls the asset's specific segment slice."""
    monkeypatch.setattr(db, "_DB_PATH", temp_db)
    ctx = engine.compute(_record())
    assert isinstance(ctx, AssetCalibrationContext)
    assert ctx.asset_segment_label.startswith("oncology / small_molecule")
    assert ctx.overall_n_resolved > 0


def test_unresolved_segment_returns_no_brier(temp_db: Path):
    """A segment with no resolved predictions has brier_score=None."""
    stats = db._segment_stats_from_rows([], "modality", "novel_modality")
    assert stats.brier_score is None
    assert stats.n_resolved == 0
