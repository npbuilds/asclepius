"""v1.6 — minimal feedback channel for the closed-beta test path.

A single VC friend (or any tester) clicks "Send feedback" in the global
header, types a note, submits. The note + page context lands in a local
SQLite store so it's auditable later via `fly ssh console` or the
public `/api/feedback/recent` endpoint.

Design choices:
  - SQLite file at api/data/feedback.db (gitignored). Same pattern as
    the calibration DB. Persists across Fly redeploys when the volume
    is mounted; otherwise lost on container restart, which is fine for
    a friend-test scope (you read it within hours of the session).
  - No auth on the read endpoint. This is scoped for the friend-test
    window; productionizing would add an admin token check. The
    write endpoint is rate-limited softly via a 5000-char body cap.
  - Captures the URL the tester was on + the asset name (if on a
    /diligence/<asset> page) + an optional persona tag. Context >
    quantity for actionable feedback.
  - No identifying info collected. The tester is implicitly the one
    person you sent the link to.
"""

from __future__ import annotations

import os
import sqlite3
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

# DB directory is env-configurable so prod can point it at a persistent Fly
# volume (writes survive redeploys); unset (local dev / CI) → api/app/data/.
# _open() mkdir's the dir on first use.
_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DB_DIR = (
    Path(os.environ["ASCLEPIUS_DB_DIR"])
    if os.getenv("ASCLEPIUS_DB_DIR")
    else _DEFAULT_DATA_DIR
)
DB_PATH = _DB_DIR / "feedback.db"

# Cap the body to a sensible length — friend-test users aren't writing
# papers, and unbounded text on a public endpoint is asking for abuse.
MAX_BODY_CHARS = 5000


def _open(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the SQLite store, creating the schema on first call."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL")  # safe concurrent reads
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback(
            id TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            url TEXT,
            asset TEXT,
            persona TEXT,
            body TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


class FeedbackIn(BaseModel):
    """What the frontend POSTs. All fields except `body` are optional —
    auto-injected by the SendFeedback modal but a recruiter pasting
    via curl can still submit a bare note."""

    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=MAX_BODY_CHARS)
    url: str | None = Field(default=None, max_length=500)
    asset: str | None = Field(default=None, max_length=120)
    persona: str | None = Field(default=None, max_length=40)


class FeedbackRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    created_at: float
    url: str | None
    asset: str | None
    persona: str | None
    body: str


@router.post("")
def submit_feedback(payload: FeedbackIn) -> dict[str, str]:
    """Write a feedback note. Returns the new row's id."""
    pid = str(uuid.uuid4())
    with _open() as conn:
        conn.execute(
            "INSERT INTO feedback(id, created_at, url, asset, persona, body) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (pid, time.time(), payload.url, payload.asset, payload.persona, payload.body),
        )
        conn.commit()
    return {"id": pid}


@router.get("/recent")
def recent_feedback(limit: int = 50) -> dict[str, list[FeedbackRow]]:
    """List recent feedback rows, newest first. Public for the friend-test
    window; productionizing would add an admin token check here.
    """
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be in [1, 500]")
    with _open() as conn:
        cur = conn.execute(
            "SELECT id, created_at, url, asset, persona, body "
            "FROM feedback ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = [
            FeedbackRow(
                id=r[0],
                created_at=r[1],
                url=r[2],
                asset=r[3],
                persona=r[4],
                body=r[5],
            )
            for r in cur.fetchall()
        ]
    return {"feedback": rows}
