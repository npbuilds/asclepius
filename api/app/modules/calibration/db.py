"""SQLite layer for the Calibration Dashboard.

Self-contained — no MCP, no external service. The database lives at
api/app/data/calibration.db (gitignored). On first access we ensure the
schema exists and seed the historical predictions from `seed_data.json`
sitting next to this module — so a fresh deploy boots with the same
calibration record every recruiter sees.

Architectural mirror of Archon's log_prediction / resolve_prediction /
get_calibration_report pattern, ported to be self-contained.

Thread-safety: SQLite is used through short-lived connections per call
(uvicorn workers share the file but never the connection). check_same_thread
defaults to True; each call opens its own connection.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from .schemas import (
    AssetCalibrationContext,
    CalibrationReport,
    PredictionLogEntry,
    SegmentStats,
)

# The DB DIRECTORY is env-configurable so prod can point it at a persistent
# Fly volume (writes survive redeploys). It must live OUTSIDE api/app/data/ in
# prod: that dir is baked into the image with the static reference JSON, so a
# volume mounted over it would hide base_rates.json etc. Unset (local dev / CI)
# → api/app/data/ alongside the committed seed JSON. The .db file itself stays
# gitignored. _connect() mkdir's the dir on first use.
_MODULE_DIR = Path(__file__).resolve().parent
_DEFAULT_DATA_DIR = _MODULE_DIR.parent.parent / "data"
_DB_DIR = (
    Path(os.environ["ASCLEPIUS_DB_DIR"])
    if os.getenv("ASCLEPIUS_DB_DIR")
    else _DEFAULT_DATA_DIR
)
_DB_PATH = _DB_DIR / "calibration.db"
_SEED_PATH = _MODULE_DIR / "seed_data.json"


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS predictions (
    id TEXT PRIMARY KEY,
    asset_name TEXT NOT NULL,
    phase TEXT NOT NULL,
    therapeutic_area TEXT NOT NULL,
    modality TEXT NOT NULL,
    capital_position TEXT NOT NULL,
    predicted_pos REAL NOT NULL CHECK (predicted_pos >= 0 AND predicted_pos <= 1),
    reflexivity_multiplier REAL NOT NULL CHECK (reflexivity_multiplier > 0),
    prediction_date TEXT NOT NULL,
    outcome INTEGER CHECK (outcome IN (0, 1)),
    outcome_date TEXT,
    outcome_source TEXT
);
CREATE INDEX IF NOT EXISTS idx_predictions_segment ON predictions(
    therapeutic_area, modality, capital_position
);
"""


def _connect(db_path: Path | None = None) -> sqlite3.Connection:
    target = db_path or _DB_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def _ensure_seeded(conn: sqlite3.Connection) -> None:
    """If the predictions table is empty AND seed_data.json exists, load it.
    Idempotent — re-seeds only an empty table."""
    row = conn.execute("SELECT COUNT(*) AS n FROM predictions").fetchone()
    if row["n"] > 0:
        return
    if not _SEED_PATH.exists():
        return
    seeds = json.loads(_SEED_PATH.read_text())
    with conn:
        for s in seeds:
            conn.execute(
                """INSERT INTO predictions(id, asset_name, phase, therapeutic_area,
                                          modality, capital_position, predicted_pos,
                                          reflexivity_multiplier, prediction_date,
                                          outcome, outcome_date, outcome_source)
                   VALUES(:id, :asset_name, :phase, :therapeutic_area, :modality,
                          :capital_position, :predicted_pos, :reflexivity_multiplier,
                          :prediction_date, :outcome, :outcome_date, :outcome_source)""",
                {
                    "id": s.get("id") or str(uuid.uuid4()),
                    "asset_name": s["asset_name"],
                    "phase": s["phase"],
                    "therapeutic_area": s["therapeutic_area"],
                    "modality": s["modality"],
                    "capital_position": s["capital_position"],
                    "predicted_pos": s["predicted_pos"],
                    "reflexivity_multiplier": s["reflexivity_multiplier"],
                    "prediction_date": s["prediction_date"],
                    "outcome": s.get("outcome"),
                    "outcome_date": s.get("outcome_date"),
                    "outcome_source": s.get("outcome_source"),
                },
            )


def _open(db_path: Path | None = None) -> sqlite3.Connection:
    """Public-ish wrapper — opens a connection and ensures seed."""
    conn = _connect(db_path)
    _ensure_seeded(conn)
    return conn


# ---------------------------------------------------------------------------
# Public API — log / resolve / report / segment-lookup
# ---------------------------------------------------------------------------


def log_prediction(
    *,
    asset_name: str,
    phase: str,
    therapeutic_area: str,
    modality: str,
    capital_position: str,
    predicted_pos: float,
    reflexivity_multiplier: float,
    prediction_date: date | None = None,
    db_path: Path | None = None,
) -> str:
    """Insert a prediction. Returns the new row's id."""
    pid = str(uuid.uuid4())
    with _open(db_path) as conn:
        conn.execute(
            """INSERT INTO predictions(id, asset_name, phase, therapeutic_area,
                                      modality, capital_position, predicted_pos,
                                      reflexivity_multiplier, prediction_date)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                pid, asset_name, phase, therapeutic_area, modality,
                capital_position, predicted_pos, reflexivity_multiplier,
                (prediction_date or date.today()).isoformat(),
            ),
        )
    return pid


def resolve_prediction(
    *,
    prediction_id: str,
    outcome: int,
    outcome_date: date | None = None,
    outcome_source: str | None = None,
    db_path: Path | None = None,
) -> bool:
    """Mark an outcome on a prediction. Returns True if found and updated."""
    with _open(db_path) as conn:
        cur = conn.execute(
            """UPDATE predictions
                  SET outcome = ?, outcome_date = ?, outcome_source = ?
                WHERE id = ?""",
            (
                outcome,
                (outcome_date or date.today()).isoformat(),
                outcome_source,
                prediction_id,
            ),
        )
        return cur.rowcount > 0


def list_predictions(db_path: Path | None = None) -> list[PredictionLogEntry]:
    with _open(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM predictions ORDER BY prediction_date DESC"""
        ).fetchall()
    return [_row_to_entry(r) for r in rows]


def _row_to_entry(row: sqlite3.Row) -> PredictionLogEntry:
    return PredictionLogEntry(
        id=row["id"],
        asset_name=row["asset_name"],
        phase=row["phase"],
        therapeutic_area=row["therapeutic_area"],
        modality=row["modality"],
        capital_position=row["capital_position"],
        predicted_pos=row["predicted_pos"],
        reflexivity_multiplier=row["reflexivity_multiplier"],
        prediction_date=date.fromisoformat(row["prediction_date"]),
        outcome=row["outcome"],
        outcome_date=(
            date.fromisoformat(row["outcome_date"])
            if row["outcome_date"]
            else None
        ),
        outcome_source=row["outcome_source"],
    )


def _segment_stats_from_rows(
    rows: list[sqlite3.Row], kind: str, value: str
) -> SegmentStats:
    """Compute Brier + calibration gap for a subset of rows. Unresolved rows
    contribute to n_unresolved but not to the score."""
    resolved = [r for r in rows if r["outcome"] is not None]
    n_unresolved = len(rows) - len(resolved)
    if not resolved:
        return SegmentStats(
            segment_kind=kind,
            segment_value=value,
            n_resolved=0,
            n_unresolved=n_unresolved,
        )
    n = len(resolved)
    brier = sum((r["predicted_pos"] - r["outcome"]) ** 2 for r in resolved) / n
    mean_pred = sum(r["predicted_pos"] for r in resolved) / n
    mean_obs = sum(r["outcome"] for r in resolved) / n
    return SegmentStats(
        segment_kind=kind,
        segment_value=value,
        n_resolved=n,
        n_unresolved=n_unresolved,
        brier_score=round(brier, 4),
        mean_predicted=round(mean_pred, 4),
        mean_observed=round(mean_obs, 4),
        calibration_gap=round(mean_pred - mean_obs, 4),
    )


def get_calibration_report(db_path: Path | None = None) -> CalibrationReport:
    with _open(db_path) as conn:
        all_rows = conn.execute("SELECT * FROM predictions").fetchall()

    overall = _segment_stats_from_rows(all_rows, "overall", "all")

    def _segment(field: str) -> list[SegmentStats]:
        values = sorted({r[field] for r in all_rows})
        return [
            _segment_stats_from_rows(
                [r for r in all_rows if r[field] == v], field, v
            )
            for v in values
        ]

    return CalibrationReport(
        n_total_predictions=len(all_rows),
        n_resolved=overall.n_resolved,
        overall=overall,
        by_therapeutic_area=_segment("therapeutic_area"),
        by_modality=_segment("modality"),
        by_capital_position=_segment("capital_position"),
        last_updated=datetime.now(timezone.utc),
    )


def get_asset_context(
    *,
    therapeutic_area: str,
    modality: str,
    capital_position: str,
    db_path: Path | None = None,
) -> AssetCalibrationContext:
    """Return the segment-specific stats for the asset on the diligence page."""
    with _open(db_path) as conn:
        seg_rows = conn.execute(
            """SELECT * FROM predictions
                WHERE therapeutic_area = ? AND modality = ?
                  AND capital_position = ?""",
            (therapeutic_area, modality, capital_position),
        ).fetchall()
        all_rows = conn.execute("SELECT * FROM predictions").fetchall()

    seg = _segment_stats_from_rows(
        seg_rows,
        "therapeutic_area",  # composite — labels include all three
        f"{therapeutic_area} / {modality} / {capital_position}",
    )
    overall = _segment_stats_from_rows(all_rows, "overall", "all")

    return AssetCalibrationContext(
        asset_segment_label=f"{therapeutic_area} / {modality} / {capital_position}",
        segment_n_resolved=seg.n_resolved,
        segment_brier=seg.brier_score,
        segment_mean_predicted=seg.mean_predicted,
        segment_mean_observed=seg.mean_observed,
        overall_n_resolved=overall.n_resolved,
        overall_brier=overall.brier_score,
        sample_size_disclaimer=(
            "Brier scores below n=20 are directional only — variance is too "
            "high to attribute calibration quality to the methodology vs. "
            "noise. v1.6+ accumulates the sample through quarterly logging."
        ),
    )
