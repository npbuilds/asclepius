"""Memo Writer tests — exercise cache hit, live path with mocked SDK, error path."""

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
        skill_loadout=[],
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
# JSON-block parser
# ---------------------------------------------------------------------------


def test_parse_memo_response_extracts_json_and_strips_body():
    raw = """## Executive summary
A tight summary paragraph.

## Recommendation
Buy.

```json
{
  "recommendation": "buy",
  "executive_summary": "A tight summary paragraph.",
  "red_flags": ["funding"]
}
```"""
    out = _parse_memo_response(raw, model_used="test-model")
    assert out["recommendation"] == "buy"
    assert out["red_flags"] == ["funding"]
    assert "```json" not in out["body_markdown"]
    assert "Buy." in out["body_markdown"]


def test_parse_memo_response_falls_back_when_json_missing():
    raw = "## Executive summary\nA paragraph.\n\n## Recommendation\nHold."
    out = _parse_memo_response(raw, model_used="test-model")
    assert out["recommendation"] == "hold"
    assert out["red_flags"] == []
    assert "## Executive summary" in out["body_markdown"]


def test_parse_memo_response_handles_malformed_json_block():
    raw = "## Executive summary\nA.\n\n```json\n{not valid}\n```"
    out = _parse_memo_response(raw, model_used="test-model")
    # Falls back to hold; raw body preserved
    assert out["recommendation"] == "hold"


def test_parse_memo_response_rejects_unknown_recommendation_enum():
    raw = """## Executive summary
foo.

```json
{"recommendation": "love_it", "executive_summary": "foo.", "red_flags": []}
```"""
    out = _parse_memo_response(raw, model_used="test-model")
    assert out["recommendation"] == "hold"  # unknown → hold


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
    fake_response = """## Executive summary
Mock memo.

## Recommendation
Buy.

```json
{
  "recommendation": "buy",
  "executive_summary": "Mock memo.",
  "red_flags": []
}
```"""

    fake_block = SimpleNamespace(type="text", text=fake_response)
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
    assert "Mock memo" in result["body_markdown"]
    assert "```json" not in result["body_markdown"]


def test_live_call_503_when_no_api_key(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 503
    assert "ANTHROPIC_API_KEY" in exc.value.detail
