"""Saved analyses — persist / list / reload a completed DiligenceRecord.

A computed DiligenceRecord otherwise lives only in the browser's React state
for the duration of a session; navigate away and the work is gone. This store
makes a finished analysis durable: "save", "list", "reload". It is the
substrate the narrated case-study showcase sits on — NOT a track record.

Design (mirrors feedback.py / calibration/db.py):
  - SQLite at $ASCLEPIUS_DB_DIR/analyses.db. Unset (local dev / CI) →
    api/app/data/. In prod ASCLEPIUS_DB_DIR=/data points at the persistent
    Fly volume so saved analyses survive redeploys (the whole reason the
    volume work mattered).
  - The full record is stored verbatim as JSON (`record_json`) — a
    DiligenceRecord is already a self-contained, schema-versioned Pydantic
    model, so persistence is json in / json out with no schema design.
  - A handful of fields are denormalized into columns (asset_name, phase,
    LOA, rNPV, recommendation) PURELY so the list view can render cards
    without parsing every blob.
  - Gated behind the shared `require_access` passphrase — the saved library
    is the analyst's work-product, and the frontend already plumbs the
    X-Asclepius-Access header. (The public showcase in step (c) will not read
    this endpoint; it gets its own featured/static path.)
"""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .agents.routes import require_access
from .domain import DiligenceRecord

router = APIRouter(
    prefix="/api/analyses",
    tags=["analyses"],
    dependencies=[Depends(require_access)],
)

# DB directory is env-configurable so prod points it at the persistent Fly
# volume; unset (local dev / CI) → api/app/data/. Resolved at CALL time (not
# import) so ASCLEPIUS_DB_DIR can be overridden per-test, and so a runtime env
# change is honored without a reload.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent / "data"

MAX_LABEL_CHARS = 200


def _db_path() -> Path:
    db_dir = (
        Path(os.environ["ASCLEPIUS_DB_DIR"])
        if os.getenv("ASCLEPIUS_DB_DIR")
        else _DEFAULT_DATA_DIR
    )
    return db_dir / "analyses.db"


def _open() -> sqlite3.Connection:
    """Open the SQLite store, creating the schema on first call."""
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")  # safe concurrent reads
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_analyses(
            id TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            label TEXT,
            asset_name TEXT NOT NULL,
            phase TEXT,
            therapeutic_area TEXT,
            modality TEXT,
            final_loa REAL,
            rnpv_base_usd_m REAL,
            recommendation TEXT,
            record_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


class SaveAnalysisIn(BaseModel):
    """What the frontend POSTs: the full computed record + an optional label.

    The record must be the canonical DiligenceRecord shape — the client strips
    its client-only fields (ml_pos, etc.) before posting, exactly as it does
    for agent calls.
    """

    model_config = ConfigDict(extra="forbid")

    record: DiligenceRecord
    label: str | None = Field(default=None, max_length=MAX_LABEL_CHARS)


class AnalysisSummary(BaseModel):
    """One row of the list view — denormalized columns only, no record blob."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: float
    label: str | None
    asset_name: str
    phase: str | None
    therapeutic_area: str | None
    modality: str | None
    final_loa: float | None
    rnpv_base_usd_m: float | None
    recommendation: str | None


class AnalysisDetail(BaseModel):
    """A full reload payload: the summary envelope + the rehydrated record."""

    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: float
    label: str | None
    record: DiligenceRecord


def _summary_fields(record: DiligenceRecord) -> dict[str, object]:
    """Pull the denormalized card fields off a computed record.

    Every field except asset identity is nullable — a record can be saved
    before every module has run (e.g. PoS computed but scorecard not yet).
    """
    a = record.asset
    return {
        "asset_name": a.asset_name,
        "phase": a.phase.value,
        "therapeutic_area": a.therapeutic_area.value,
        "modality": a.modality.value,
        "final_loa": record.pos.final_loa if record.pos else None,
        "rnpv_base_usd_m": record.rnpv.base_case_usd_m if record.rnpv else None,
        "recommendation": record.scorecard.recommendation if record.scorecard else None,
    }


@router.post("")
def save_analysis(payload: SaveAnalysisIn) -> dict[str, str]:
    """Persist a completed analysis. Returns the new id."""
    aid = str(uuid.uuid4())
    record = payload.record
    fields = _summary_fields(record)
    with _open() as conn:
        conn.execute(
            "INSERT INTO saved_analyses("
            "id, created_at, label, asset_name, phase, therapeutic_area, "
            "modality, final_loa, rnpv_base_usd_m, recommendation, record_json"
            ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                aid,
                time.time(),
                payload.label,
                fields["asset_name"],
                fields["phase"],
                fields["therapeutic_area"],
                fields["modality"],
                fields["final_loa"],
                fields["rnpv_base_usd_m"],
                fields["recommendation"],
                record.model_dump_json(),
            ),
        )
        conn.commit()
    return {"id": aid}


@router.get("")
def list_analyses(limit: int = 200) -> dict[str, list[AnalysisSummary]]:
    """List saved analyses, newest first."""
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be in [1, 1000]")
    with _open() as conn:
        cur = conn.execute(
            "SELECT id, created_at, label, asset_name, phase, therapeutic_area, "
            "modality, final_loa, rnpv_base_usd_m, recommendation "
            "FROM saved_analyses ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [
            AnalysisSummary(
                id=r[0],
                created_at=r[1],
                label=r[2],
                asset_name=r[3],
                phase=r[4],
                therapeutic_area=r[5],
                modality=r[6],
                final_loa=r[7],
                rnpv_base_usd_m=r[8],
                recommendation=r[9],
            )
            for r in cur.fetchall()
        ]
    return {"analyses": rows}


@router.get("/{analysis_id}")
def get_analysis(analysis_id: str) -> AnalysisDetail:
    """Reload one saved analysis — rehydrates the full DiligenceRecord."""
    with _open() as conn:
        cur = conn.execute(
            "SELECT id, created_at, label, record_json FROM saved_analyses WHERE id = ?",
            (analysis_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"analysis '{analysis_id}' not found")
    return AnalysisDetail(
        id=row[0],
        created_at=row[1],
        label=row[2],
        record=DiligenceRecord.model_validate_json(row[3]),
    )


@router.delete("/{analysis_id}")
def delete_analysis(analysis_id: str) -> dict[str, bool]:
    """Delete a saved analysis. Idempotent — returns deleted=False if absent."""
    with _open() as conn:
        cur = conn.execute(
            "DELETE FROM saved_analyses WHERE id = ?", (analysis_id,)
        )
        conn.commit()
        deleted = cur.rowcount > 0
    return {"deleted": deleted}
