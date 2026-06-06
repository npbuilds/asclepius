"""Memo Writer tests — exercise cache hit, live path with mocked SDK, error path.

v1.7.7: tests updated for the new structured-JSON response format. The model
now returns a single fenced JSON object with named sections; the agent
assembles a markdown body from those sections.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.agents.memo_writer.agent import Agent, _parse_memo_response, _slugify_asset_name
from app.domain import AssetInput, CapitalPosition, DiligenceRecord, Modality, Phase, TherapeuticArea
from app.registry import AgentManifest


def _make_record(name: str = "adagrasib") -> DiligenceRecord:
    return DiligenceRecord(
        asset=AssetInput(
            asset_name=name,
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.SMALL_MOLECULE,
            capital_position=CapitalPosition.ADEQUATE,
        )
    )


def _make_agent(tmp_path: Path, cached_assets: list[str]) -> Agent:
    manifest = AgentManifest(
        id="memo_writer",
        name="Memo Writer",
        version="0.1.0",
        description="test",
        methodology_refs=[],
        trigger_label="Generate memo",
        input_fields=["asset"],
        output_fields=["body_markdown"],
        model="claude-opus-4-7",
        cached_assets=cached_assets,
    )
    (tmp_path / "cache").mkdir()
    return Agent(manifest=manifest, agent_dir=tmp_path)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_strips_punctuation_and_lowercases():
    assert _slugify_asset_name("adagrasib (MRTX849)") == "adagrasib_mrtx849"
    assert _slugify_asset_name("ADAGRASIB") == "adagrasib"
    assert _slugify_asset_name("") == "unnamed"


# ---------------------------------------------------------------------------
# Structured-JSON parser
# ---------------------------------------------------------------------------


_FULL_STRUCTURED_RESPONSE = """```json
{
  "tldr": {
    "recommendation": "buy",
    "loa_pct": 16.1,
    "rnpv_base_usd_m": 516,
    "rnpv_range_low_usd_m": 290,
    "rnpv_range_high_usd_m": 698,
    "thesis_one_liner": "Phase 2 KRAS G12C asset with a documentable PoS chain and a strategic-sale liquidity unit."
  },
  "asset_overview": {
    "paragraph": "Adagrasib is an oral KRAS G12C inhibitor in 2L+ NSCLC."
  },
  "pos_analysis": {
    "waterfall_narrative": "From the 10.6% base rate, biomarker-enrichment-boost x1.20 lifts the LOA, then target-validated x1.15 closes the validation question, BTD x1.10 reflects FDA pre-commitment.",
    "reflexivity_note": "Mirati sits in the adequate reflexivity tier — neither signaling deepest commitment nor pooling with distressed types."
  },
  "valuation": {
    "valuation_narrative": "Base rNPV $516M, MC P25-P75 $290-$698M. Top tornado driver: peak sales. The asset trades closer to the cohort median than the precedent clearing price."
  },
  "comparables": {
    "cohort_paragraph": "Oncology · small molecule cohort, median EV/peak-sales 6.67x, closest analog selpercatinib/Lilly."
  },
  "operational": {
    "pillars_paragraph": "Clinical 8/10, regulatory 8/10, competitive 6/10 — no red flags."
  },
  "risks": [
    {"label": "Peak-sales concentration", "description": "Second-mover share against sotorasib could collapse the $1.2B anchor.", "severity": "high"},
    {"label": "Single-asset concentration", "description": "Mirati corporate exposure if KRYSTAL-12 fails.", "severity": "medium"}
  ],
  "recommendation_close": {
    "recommendation": "buy",
    "closing_paragraph": "At $474M asset-attributable, the framework brackets the entry as a buy.",
    "kill_criterion": "A KRYSTAL-12 primary-endpoint miss flips the call to avoid."
  },
  "executive_summary": "Adagrasib is a Phase 2 KRAS G12C asset with a 16.1% LOA, base rNPV $516M, and a price-conditioned buy at or below the P50.",
  "red_flags": []
}
```"""


def test_parse_memo_response_extracts_structured_sections():
    out = _parse_memo_response(_FULL_STRUCTURED_RESPONSE, model_used="test-model")
    assert out["recommendation"] == "buy"
    assert out["tldr"]["loa_pct"] == 16.1
    assert out["tldr"]["rnpv_base_usd_m"] == 516
    assert out["pos_analysis"]["waterfall_narrative"].startswith("From the 10.6%")
    assert len(out["risks"]) == 2
    assert out["risks"][0]["label"] == "Peak-sales concentration"
    assert out["recommendation_close"]["kill_criterion"].endswith("avoid.")
    # body_markdown should be assembled from the structured sections
    assert "## TL;DR" in out["body_markdown"]
    assert "## Recommendation" in out["body_markdown"]
    assert "Kill criterion" in out["body_markdown"]
    assert "```json" not in out["body_markdown"]


def test_parse_memo_response_falls_back_when_json_missing():
    raw = "## Executive summary\nA paragraph.\n\n## Recommendation\nHold."
    out = _parse_memo_response(raw, model_used="test-model")
    assert out["recommendation"] == "hold"
    assert out["red_flags"] == []
    # No structured sections at all when JSON is missing
    assert out["tldr"] is None
    assert out["pos_analysis"] is None
    # Raw body preserved as the markdown body
    assert "## Executive summary" in out["body_markdown"]


def test_parse_memo_response_handles_malformed_json_block():
    raw = "## Executive summary\nA.\n\n```json\n{not valid}\n```"
    out = _parse_memo_response(raw, model_used="test-model")
    assert out["recommendation"] == "hold"


def test_parse_memo_response_rejects_unknown_recommendation_enum():
    raw = """```json
{
  "tldr": {"recommendation": "love_it", "loa_pct": 10.0, "rnpv_base_usd_m": 100, "thesis_one_liner": "x"},
  "executive_summary": "foo.",
  "red_flags": []
}
```"""
    out = _parse_memo_response(raw, model_used="test-model")
    # tldr.recommendation is invalid → top-level coerced to "hold"
    assert out["recommendation"] == "hold"


def test_parse_memo_response_derives_red_flags_from_risks_when_missing():
    raw = """```json
{
  "tldr": {"recommendation": "cautious", "loa_pct": 8.0, "rnpv_base_usd_m": 100, "thesis_one_liner": "x"},
  "risks": [
    {"label": "Competitive entry", "description": "...", "severity": "high"},
    {"label": "Capital runway", "description": "...", "severity": "medium"}
  ],
  "executive_summary": "Foo."
}
```"""
    out = _parse_memo_response(raw, model_used="test-model")
    assert out["recommendation"] == "cautious"
    assert "Competitive entry" in out["red_flags"]
    assert "Capital runway" in out["red_flags"]


# ---------------------------------------------------------------------------
# cache lookup
# ---------------------------------------------------------------------------


def test_cache_hit_returns_disk_payload_with_from_cache_true(tmp_path: Path):
    agent = _make_agent(tmp_path, cached_assets=["adagrasib"])
    cached_payload = {
        "body_markdown": "## Executive summary\ncached.",
        "executive_summary": "cached.",
        "recommendation": "buy",
        "red_flags": [],
        "model_used": "claude-opus-4-7",
        "from_cache": False,  # script-written value; agent must overwrite
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (tmp_path / "cache" / "adagrasib.json").write_text(json.dumps(cached_payload))

    record = _make_record("adagrasib")
    result = agent.run(record)
    assert result["from_cache"] is True
    assert result["body_markdown"] == "## Executive summary\ncached."


def test_cache_miss_when_asset_not_in_manifest_list(tmp_path: Path, monkeypatch):
    # Cache file exists, but asset not in manifest's cached_assets → miss
    agent = _make_agent(tmp_path, cached_assets=[])
    (tmp_path / "cache" / "adagrasib.json").write_text(json.dumps({"body_markdown": "x"}))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("adagrasib"))
    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# live call with mocked SDK
# ---------------------------------------------------------------------------


def test_live_call_with_mocked_anthropic(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])  # force live path

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    fake_block = SimpleNamespace(type="text", text=_FULL_STRUCTURED_RESPONSE)
    fake_message = SimpleNamespace(content=[fake_block])

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-7"
            assert kwargs["system"]  # non-empty
            return fake_message

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    with patch("anthropic.Anthropic", return_value=FakeClient()):
        result = agent.run(_make_record("vorasidenib"))

    assert result["from_cache"] is False
    assert result["recommendation"] == "buy"
    assert result["tldr"]["rnpv_base_usd_m"] == 516
    assert "## TL;DR" in result["body_markdown"]
    assert "```json" not in result["body_markdown"]


def test_live_call_503_when_no_api_key(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 503
    assert "ANTHROPIC_API_KEY" in exc.value.detail
