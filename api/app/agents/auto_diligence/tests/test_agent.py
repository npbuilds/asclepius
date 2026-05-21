"""Auto-Diligence tests — cache hit, live path with mocked SDK, 503 no-key."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.agents.auto_diligence.agent import (
    Agent,
    _parse_diligence_response,
    _slugify_asset_name,
    _walk_response,
)
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
        id="auto_diligence",
        name="Auto-Diligence",
        version="0.1.0",
        description="test",
        skill_loadout=[],
        trigger_label="Auto-diligence",
        input_fields=["asset.asset_name"],
        output_fields=["extracted"],
        model="claude-opus-4-7",
        cached_assets=cached_assets,
    )
    (tmp_path / "cache").mkdir()
    return Agent(manifest=manifest, agent_dir=tmp_path)


# ---------------------------------------------------------------------------


def test_slugify_handles_typical_asset_names():
    assert _slugify_asset_name("adagrasib") == "adagrasib"
    assert _slugify_asset_name("Datopotamab Deruxtecan (Dato-DXd)") == "datopotamab_deruxtecan_dato_dxd"


def test_walk_response_counts_searches_and_collects_citations():
    fake_message = SimpleNamespace(
        content=[
            SimpleNamespace(type="server_tool_use", name="web_search"),
            SimpleNamespace(
                type="text",
                text="Found that adagrasib is Phase 2.",
                citations=[
                    SimpleNamespace(
                        type="web_search_result_location",
                        url="https://clinicaltrials.gov/study/NCT04685135",
                        title="KRYSTAL-1",
                        cited_text="Phase 2 study",
                    )
                ],
            ),
            SimpleNamespace(type="server_tool_use", name="web_search"),
            SimpleNamespace(type="text", text=" Source confirmed.", citations=None),
        ]
    )
    text, web_cites, count = _walk_response(fake_message)
    assert count == 2
    assert "Phase 2" in text
    assert len(web_cites) == 1
    assert web_cites[0]["url"] == "https://clinicaltrials.gov/study/NCT04685135"


def test_parse_extracts_fields_and_drops_invalid_citations():
    raw = """Searched CT.gov and FDA for adagrasib.

```json
{
  "extracted": {
    "asset_name": "adagrasib",
    "sponsor": "Mirati Therapeutics",
    "phase": "phase_2",
    "therapeutic_area": "oncology",
    "modality": "small_molecule",
    "regulatory_designations": ["breakthrough_therapy"],
    "biomarker_enrichment": true
  },
  "citations": [
    {"field": "phase", "url": "https://clinicaltrials.gov/study/NCT04685135", "title": "KRYSTAL-1", "span": "Phase 2 study"},
    {"field": "sponsor", "url": "https://sec.gov/MRTX-10K", "span": "Mirati Therapeutics, Inc."},
    {"field": "", "url": "", "span": ""}
  ],
  "field_confidence": {
    "phase": "high",
    "sponsor": "high",
    "mechanism": "missing",
    "invalid": "garbage"
  }
}
```"""
    out = _parse_diligence_response(
        raw_text=raw, web_citations=[], search_count=3, model_used="test"
    )
    assert out["extracted"]["asset_name"] == "adagrasib"
    assert out["extracted"]["phase"] == "phase_2"
    assert out["extracted"]["biomarker_enrichment"] is True
    # Empty-field/url/span citation dropped
    assert len(out["citations"]) == 2
    # Unknown confidence value dropped
    assert "invalid" not in out["field_confidence"]
    assert out["field_confidence"]["phase"] == "high"
    assert out["web_searches_used"] == 3


def test_parse_appends_web_search_citations_not_in_json():
    raw = '```json\n{"extracted": {}, "citations": [], "field_confidence": {}}\n```'
    web_citations = [
        {
            "url": "https://fda.gov/news-events/press-announcements/adagrasib-btd",
            "title": "FDA BTD announcement",
            "span": "Breakthrough Therapy Designation granted",
        }
    ]
    out = _parse_diligence_response(
        raw_text=raw, web_citations=web_citations, search_count=1, model_used="test"
    )
    assert len(out["citations"]) == 1
    assert out["citations"][0]["url"].startswith("https://fda.gov")
    assert out["citations"][0]["field"] == ""


def test_parse_falls_back_when_no_json():
    out = _parse_diligence_response(
        raw_text="Nothing structured here.",
        web_citations=[],
        search_count=0,
        model_used="test",
    )
    assert out["extracted"]["asset_name"] is None
    assert out["citations"] == []


def test_cache_hit(tmp_path: Path):
    agent = _make_agent(tmp_path, cached_assets=["adagrasib"])
    payload = {
        "extracted": {"asset_name": "adagrasib", "phase": "phase_2"},
        "citations": [],
        "field_confidence": {},
        "web_searches_used": 0,
        "model_used": "claude-opus-4-7",
        "from_cache": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (tmp_path / "cache" / "adagrasib.json").write_text(json.dumps(payload))
    out = agent.run(_make_record("adagrasib"))
    assert out["from_cache"] is True
    assert out["extracted"]["asset_name"] == "adagrasib"


def test_live_call_503_when_no_key(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 503


def test_live_call_with_mocked_anthropic_and_web_search(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    fake_message = SimpleNamespace(
        content=[
            SimpleNamespace(type="server_tool_use", name="web_search"),
            SimpleNamespace(
                type="text",
                text="""Searched CT.gov and SEC EDGAR.

```json
{
  "extracted": {
    "asset_name": "vorasidenib",
    "sponsor": "Servier",
    "phase": "approved",
    "modality": "small_molecule"
  },
  "citations": [
    {"field": "phase", "url": "https://fda.gov/news/vorasidenib", "span": "approved August 2024"}
  ],
  "field_confidence": {"phase": "high"}
}
```""",
                citations=None,
            ),
        ]
    )

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-7"
            # Confirm web_search tool was enabled with allowlist
            assert kwargs["tools"][0]["type"] == "web_search_20250305"
            assert "clinicaltrials.gov" in kwargs["tools"][0]["allowed_domains"]
            return fake_message

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    with patch("anthropic.Anthropic", return_value=FakeClient()):
        out = agent.run(_make_record("vorasidenib"))

    assert out["from_cache"] is False
    assert out["extracted"]["asset_name"] == "vorasidenib"
    assert out["extracted"]["phase"] == "approved"
    assert out["web_searches_used"] == 1
    assert len(out["citations"]) == 1
