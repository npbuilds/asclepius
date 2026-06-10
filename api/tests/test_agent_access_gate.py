"""Access-gate tests for the agent routes (v1.9.1).

The three agents (/api/agents/<id>/run) are gated behind a shared passphrase
read from ASCLEPIUS_ACCESS_PASSPHRASE. The gate is FAIL-OPEN: inert when the
env var is unset (public), active when set. These tests pin both behaviors so
a future change can't silently open the gate or break the public path.

We assert `!= 403` (rather than a specific success code) for the pass-through
cases because, with the staged caches archived and no ANTHROPIC_API_KEY in the
test env, the agent itself returns 503 — that's fine; what we're testing is
that the request CLEARS THE GATE, not what the agent does afterward.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import reset_registry_for_tests

# A valid DiligenceRecord body so request-body validation passes and we isolate
# the gate's behavior (403 vs not-403) from any 422.
RECORD = {
    "asset": {
        "asset_name": "adagrasib",
        "sponsor": "Mirati",
        "phase": "phase_2",
        "therapeutic_area": "oncology",
        "modality": "small_molecule",
        "capital_position": "adequate",
        "mechanism": "KRAS G12C inhibitor",
        "target": "KRAS G12C",
        "indication": "NSCLC",
        "regulatory_designations": ["breakthrough_therapy"],
        "num_competitors": 1,
        "target_validated": True,
        "biomarker_enrichment": True,
    }
}


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _client() -> TestClient:
    return TestClient(create_app())


def test_gate_inert_when_passphrase_unset(monkeypatch) -> None:
    """No ASCLEPIUS_ACCESS_PASSPHRASE → gate is public (fail-open)."""
    monkeypatch.delenv("ASCLEPIUS_ACCESS_PASSPHRASE", raising=False)
    r = _client().post("/api/agents/memo_writer/run", json=RECORD)
    assert r.status_code != 403


def test_gate_blocks_without_header(monkeypatch) -> None:
    """Passphrase set + no header → 403."""
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post("/api/agents/memo_writer/run", json=RECORD)
    assert r.status_code == 403


def test_gate_blocks_wrong_header(monkeypatch) -> None:
    """Passphrase set + wrong header → 403."""
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post(
        "/api/agents/memo_writer/run",
        json=RECORD,
        headers={"X-Asclepius-Access": "wrong"},
    )
    assert r.status_code == 403


def test_gate_allows_correct_header(monkeypatch) -> None:
    """Passphrase set + correct header → clears the gate (not 403)."""
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post(
        "/api/agents/memo_writer/run",
        json=RECORD,
        headers={"X-Asclepius-Access": "swordfish"},
    )
    assert r.status_code != 403


def test_gate_does_not_touch_public_module_routes(monkeypatch) -> None:
    """Even with the gate active, the deterministic module routes stay open."""
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post("/api/modules/pos", json={"asset": RECORD["asset"]})
    assert r.status_code != 403
