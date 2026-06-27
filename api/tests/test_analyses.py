"""Saved-analyses store tests — round-trip fidelity, gate, DB isolation.

The store persists a full DiligenceRecord as JSON and denormalizes a few card
fields. These tests pin: (1) a computed record survives save→reload byte-for-
intent (pos/rnpv/comparables come back), (2) the list view's denormalized
fields are correct, (3) the access gate behaves, (4) delete + 404 paths.

Every test points ASCLEPIUS_DB_DIR at a tmp dir so the suite never touches the
real api/app/data/analyses.db.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import reset_registry_for_tests

# build_record lives in the precompute script — reuse it for a realistic, fully
# computed adagrasib record (pos + rnpv + scorecard + comparables).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from precompute_agent_outputs import build_record  # noqa: E402


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _client() -> TestClient:
    return TestClient(create_app())


def _record_json() -> dict:
    """A full computed adagrasib record as a JSON-able dict (canonical shape)."""
    return build_record("adagrasib").model_dump(mode="json")


def _isolate(monkeypatch, tmp_path: Path) -> None:
    """Point the DB at a tmp dir and open the gate (no passphrase)."""
    monkeypatch.setenv("ASCLEPIUS_DB_DIR", str(tmp_path))
    monkeypatch.delenv("ASCLEPIUS_ACCESS_PASSPHRASE", raising=False)


def test_save_list_get_roundtrip(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    client = _client()

    # save
    r = client.post("/api/analyses", json={"record": _record_json(), "label": "my take"})
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    assert aid

    # list — newest first, denormalized card fields present and correct
    r = client.get("/api/analyses")
    assert r.status_code == 200
    analyses = r.json()["analyses"]
    assert len(analyses) == 1
    summary = analyses[0]
    assert summary["id"] == aid
    assert summary["label"] == "my take"
    assert summary["asset_name"] == "adagrasib"
    assert summary["phase"] == "phase_2"
    assert summary["modality"] == "small_molecule"
    # denormalized numbers match the computed record (LOA ~16.1%, rNPV ~$516M)
    assert 0.10 < summary["final_loa"] < 0.30
    assert summary["rnpv_base_usd_m"] > 100
    assert summary["recommendation"] in {"strong_buy", "buy", "hold", "cautious", "avoid"}

    # get — full record rehydrates with module outputs intact (fidelity)
    r = client.get(f"/api/analyses/{aid}")
    assert r.status_code == 200
    detail = r.json()
    assert detail["id"] == aid
    rec = detail["record"]
    assert rec["asset"]["asset_name"] == "adagrasib"
    assert rec["pos"]["final_loa"] == summary["final_loa"]
    assert rec["rnpv"]["base_case_usd_m"] == summary["rnpv_base_usd_m"]
    assert rec["comparables"]["median_ev_to_peak_sales"] is not None


def test_list_newest_first(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    client = _client()
    body = {"record": _record_json()}
    first = client.post("/api/analyses", json={**body, "label": "first"}).json()["id"]
    second = client.post("/api/analyses", json={**body, "label": "second"}).json()["id"]
    ids = [a["id"] for a in client.get("/api/analyses").json()["analyses"]]
    # newest first
    assert ids[0] == second
    assert ids[1] == first


def test_get_unknown_id_404(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    r = _client().get("/api/analyses/does-not-exist")
    assert r.status_code == 404


def test_delete_is_idempotent(monkeypatch, tmp_path) -> None:
    _isolate(monkeypatch, tmp_path)
    client = _client()
    aid = client.post("/api/analyses", json={"record": _record_json()}).json()["id"]
    assert client.delete(f"/api/analyses/{aid}").json() == {"deleted": True}
    # gone now
    assert client.get(f"/api/analyses/{aid}").status_code == 404
    # second delete is a no-op, not an error
    assert client.delete(f"/api/analyses/{aid}").json() == {"deleted": False}


def test_db_isolation_uses_env_dir(monkeypatch, tmp_path) -> None:
    """The store writes analyses.db under ASCLEPIUS_DB_DIR (the Fly volume in prod)."""
    _isolate(monkeypatch, tmp_path)
    _client().post("/api/analyses", json={"record": _record_json()})
    assert (tmp_path / "analyses.db").exists()


# ---- access gate (mirrors test_agent_access_gate.py) ----


def test_gate_blocks_without_header(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ASCLEPIUS_DB_DIR", str(tmp_path))
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().get("/api/analyses")
    assert r.status_code == 403


def test_gate_allows_correct_header(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ASCLEPIUS_DB_DIR", str(tmp_path))
    monkeypatch.setenv("ASCLEPIUS_ACCESS_PASSPHRASE", "swordfish")
    r = _client().get("/api/analyses", headers={"X-Asclepius-Access": "swordfish"})
    assert r.status_code == 200
