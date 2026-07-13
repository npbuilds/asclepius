"""Access-gate tests for the agent routes.

The three agents (/api/agents/<id>/run) are the only money-spending routes. The
gate (ASCLEPIUS_ACCESS_PASSPHRASE) is FAIL-OPEN — inert when the env var is
unset, active when set.

R3 change: the gate applies ONLY to the LIVE (money-spending) path. A request
whose result is served from a pre-computed cache spends nothing, so it returns
WITHOUT the passphrase. So:
  - a CACHED asset (adagrasib memo) → served ungated even with the gate active;
  - an UNCACHED asset → gated (403 without a valid header when the gate is set).

These tests pin both, so a future change can't silently open the live path or
break the cached-asset-is-visible behavior.

We assert `!= 403` (not a specific success code) for pass-through cases because,
with no ANTHROPIC_API_KEY in the test env, an uncached live call returns 503 —
that's fine; what we test is whether the request CLEARS THE GATE.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import reset_registry_for_tests

# adagrasib is pre-cached for the agents (see each agent's cache/adagrasib.json),
# so it exercises the FREE path.
CACHED_RECORD = {
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

# A name that is NOT in any agent's cached_assets → exercises the LIVE (gated) path.
UNCACHED_RECORD = {
    "asset": {
        "asset_name": "totally_uncached_test_asset",
        "phase": "phase_2",
        "therapeutic_area": "oncology",
        "modality": "small_molecule",
        "capital_position": "adequate",
    }
}


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _client() -> TestClient:
    return TestClient(create_app())


# ---- fail-open (gate unset) ----


def test_gate_inert_when_passphrase_unset(monkeypatch) -> None:
    """No ASCLEPIUS_ACCESS_PASSPHRASE → even the live path is public."""
    monkeypatch.delenv("ASCLEPIUS_ACCESS_PASSPHRASE", raising=False)
    r = _client().post("/api/agents/memo_writer/run", json=UNCACHED_RECORD)
    assert r.status_code != 403


# ---- gate active: the LIVE (uncached) path is protected ----


def test_gate_blocks_uncached_without_header(monkeypatch) -> None:
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post("/api/agents/memo_writer/run", json=UNCACHED_RECORD)
    assert r.status_code == 403


def test_gate_blocks_uncached_wrong_header(monkeypatch) -> None:
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post(
        "/api/agents/memo_writer/run",
        json=UNCACHED_RECORD,
        headers={"X-Asclepius-Access": "wrong"},
    )
    assert r.status_code == 403


def test_gate_allows_uncached_with_correct_header(monkeypatch) -> None:
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post(
        "/api/agents/memo_writer/run",
        json=UNCACHED_RECORD,
        headers={"X-Asclepius-Access": "swordfish"},
    )
    assert r.status_code != 403  # clears the gate (then 503: no key in test env)


# ---- gate active: the CACHED (free) path is NOT gated ----


def test_cached_asset_served_without_gate(monkeypatch) -> None:
    """A pre-cached asset spends nothing, so it's served even with the gate
    active and NO header — this is what keeps the AI features visible to a cold
    visitor on the staged assets."""
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post("/api/agents/memo_writer/run", json=CACHED_RECORD)
    assert r.status_code == 200
    assert r.json().get("from_cache") is True


# ---- the gate never touches the public deterministic module routes ----


def test_gate_does_not_touch_public_module_routes(monkeypatch) -> None:
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().post("/api/modules/pos", json={"asset": UNCACHED_RECORD["asset"]})
    assert r.status_code != 403
