"""Game-Theory Adversary tests — cache, tool-use live path (mocked SDK), errors.

v1.9.2: migrated from prose-parsing to tool-use (mirrors memo_writer). The model
is forced (tool_choice) to call `emit_critique`, returning a tool_use block whose
`.input` the Anthropic API validated against AdversaryContent's schema. The agent
re-validates and wraps the envelope — no prose parser remains to test.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.agents.game_theory_adversary.agent import (
    ADVERSARY_TOOL,
    Agent,
    _slugify_asset_name,
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
        id="game_theory_adversary",
        name="Game-Theory Adversary",
        version="0.1.0",
        description="test",
        methodology_refs=[],
        trigger_label="Stress-test thesis",
        input_fields=["asset"],
        output_fields=["body_markdown"],
        model="claude-opus-4-7",
        cached_assets=cached_assets,
    )
    (tmp_path / "cache").mkdir()
    return Agent(manifest=manifest, agent_dir=tmp_path)


# A complete, valid AdversaryContent payload — the emit_critique tool `input`.
_TOOL_INPUT = {
    "body_markdown": "## Signaling lens\nA finding.\n\n## Verdict\nHold.",
    "verdict_shift": "hold",
    "recommendation_shift_to": None,
    "flags": [
        {
            "flag_type": "data_quality",
            "severity": "low",
            "title": "Missing target_validated flag",
            "rationale": "The brief does not set target_validated, which makes the "
            "cohort_base_rate_check inert.",
            "test": "Confirm the target's mechanistic validation against the literature.",
            "cite": ["methodology/01-pos-framework.md"],
        },
        {
            "flag_type": "signaling_equilibrium",
            "severity": "medium",
            "title": "Adequate-capital sponsor running a standard trial",
            "rationale": "Capital tier sits at adequate, so the costly-signal read is muted.",
            "test": "Compare trial N and design rigor to the BIO cohort median.",
            "cite": ["methodology/06-signaling-equilibrium.md"],
        },
    ],
}


def _fake_client_returning(tool_input):
    block = SimpleNamespace(type="tool_use", name="emit_critique", input=tool_input)
    message = SimpleNamespace(content=[block])

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-7"
            assert kwargs["tool_choice"] == {"type": "tool", "name": "emit_critique"}
            assert any(t["name"] == "emit_critique" for t in kwargs["tools"])
            return message

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    return FakeClient()


# ---------------------------------------------------------------------------


def test_slugify_handles_real_asset_names():
    assert _slugify_asset_name("adagrasib (MRTX849)") == "adagrasib_mrtx849"


def test_adversary_tool_schema_requires_core_fields():
    required = set(ADVERSARY_TOOL["input_schema"].get("required", []))
    for field in ("body_markdown", "verdict_shift", "flags"):
        assert field in required, f"{field} should be required in the tool schema"


def test_cache_hit_serves_disk(tmp_path: Path):
    agent = _make_agent(tmp_path, cached_assets=["adagrasib"])
    payload = {
        "body_markdown": "cached body",
        "verdict_shift": "hold",
        "recommendation_shift_to": None,
        "findings": [],
        "model_used": "claude-opus-4-7",
        "from_cache": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (tmp_path / "cache" / "adagrasib.json").write_text(json.dumps(payload))
    out = agent.run(_make_record("adagrasib"))
    assert out["from_cache"] is True
    assert out["body_markdown"] == "cached body"


def test_live_call_503_when_no_key(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 503


def test_live_call_assembles_from_tool_use(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    with patch("anthropic.Anthropic", return_value=_fake_client_returning(_TOOL_INPUT)):
        out = agent.run(_make_record("vorasidenib"))

    assert out["from_cache"] is False
    assert out["verdict_shift"] == "hold"
    assert len(out["flags"]) == 2
    assert out["flags"][0]["flag_type"] == "data_quality"
    assert out["flags"][1]["cite"] == ["methodology/06-signaling-equilibrium.md"]
    # legacy findings backfilled empty
    assert out["findings"] == []
    assert "## Verdict" in out["body_markdown"]


def test_live_call_502_when_model_omits_tool_block(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    text_only = SimpleNamespace(content=[SimpleNamespace(type="text", text="prose")])

    class FakeMessages:
        def create(self, **kwargs):
            return text_only

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    with patch("anthropic.Anthropic", return_value=FakeClient()):
        with pytest.raises(HTTPException) as exc:
            agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 502


def test_live_call_rejects_incomplete_tool_input(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    incomplete = {"body_markdown": "x"}  # missing verdict_shift + flags
    with patch("anthropic.Anthropic", return_value=_fake_client_returning(incomplete)):
        with pytest.raises(Exception):  # pydantic ValidationError
            agent.run(_make_record("vorasidenib"))
