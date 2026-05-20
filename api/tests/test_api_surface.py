"""Smoke tests against the FastAPI surface — modules endpoint + a real PoS call."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.registry import reset_registry_for_tests


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def _client() -> TestClient:
    return TestClient(create_app())


def test_health() -> None:
    r = _client().get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_modules_lists_all_four() -> None:
    r = _client().get("/api/modules")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()["modules"]}
    assert {"pos", "rnpv", "scorecard", "comparables"}.issubset(ids)


def test_api_data_sources_lists_all_five() -> None:
    r = _client().get("/api/data_sources")
    assert r.status_code == 200
    ids = {d["id"] for d in r.json()["data_sources"]}
    assert {
        "bio_base_rates",
        "modality_multipliers",
        "reflexivity_adjustments",
        "wacc_benchmarks",
        "edgar_filings",
    }.issubset(ids)


def test_pos_endpoint_round_trip() -> None:
    payload = {
        "asset": {
            "asset_name": "Test",
            "phase": "phase_2",
            "therapeutic_area": "oncology",
            "modality": "small_molecule",
            "capital_position": "adequate",
            "biomarker_enrichment": True,
        }
    }
    r = _client().post("/api/modules/pos", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "pos" in body
    assert 0.0 < body["pos"]["final_loa"] < 1.0
    assert len(body["pos"]["adjustments"]) >= 2


def test_rnpv_endpoint_returns_monte_carlo_percentiles() -> None:
    asset = {
        "asset_name": "Test",
        "phase": "phase_2",
        "therapeutic_area": "oncology",
        "modality": "small_molecule",
        "capital_position": "adequate",
    }
    pos_resp = _client().post("/api/modules/pos", json={"asset": asset}).json()
    payload = {
        "asset": asset,
        "pos": pos_resp["pos"],
        "rnpv_inputs": {"peak_sales_usd_m": 1500.0, "wacc": 0.10},
    }
    r = _client().post("/api/modules/rnpv", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()["rnpv"]
    assert body["monte_carlo_paths"] == 10_000
    p25, p50, p75 = (
        body["monte_carlo_p25_usd_m"],
        body["monte_carlo_p50_usd_m"],
        body["monte_carlo_p75_usd_m"],
    )
    assert p25 < p50 < p75
    assert len(body["tornado"]) == 4


def test_scorecard_endpoint_round_trip() -> None:
    payload = {
        "asset": {
            "asset_name": "Test",
            "phase": "phase_2",
            "therapeutic_area": "oncology",
            "modality": "small_molecule",
        },
        "scorecard_input": {
            "clinical": {"score": 8.0, "rationale": "Strong P2 data"},
            "regulatory": {"score": 7.5},
            "competitive": {"score": 7.0},
            "manufacturing": {"score": 7.0},
            "ip": {"score": 8.0},
            "financial": {"score": 7.5},
            "team": {"score": 8.0},
            "computational": {"score": 6.0},
            "green_flags": ["Big Pharma partnership"],
        },
    }
    r = _client().post("/api/modules/scorecard", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()["scorecard"]
    assert body["recommendation"] in {"buy", "strong_buy"}
    assert len(body["pillars"]) == 8


def test_comparables_endpoint_returns_cohort_and_implied_value() -> None:
    payload = {
        "asset": {
            "asset_name": "adagrasib",
            "phase": "phase_2",
            "therapeutic_area": "oncology",
            "modality": "small_molecule",
        },
        "rnpv_inputs": {"peak_sales_usd_m": 1200.0, "wacc": 0.10},
    }
    r = _client().post("/api/modules/comparables", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()["comparables"]
    assert len(body["cohort"]) == 3
    assert body["median_ev_to_peak_sales"] is not None
    assert body["implied_value_usd_m"] is not None
