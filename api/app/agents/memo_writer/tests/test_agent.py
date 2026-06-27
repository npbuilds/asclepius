"""Memo Writer tests — cache hit, tool-use live path (mocked SDK), error paths.

v1.9.2: the agent migrated from prose-parsing to tool-use. The model is forced
(tool_choice) to call `emit_memo`, returning a `tool_use` block whose `.input`
is a dict the Anthropic API already validated against MemoContent's schema. The
agent re-validates through MemoContent, renders body_markdown, and wraps the
envelope. These tests mock the SDK to return a tool_use block and assert the
assembled MemoOutput — there is no longer any prose parser to test.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.agents.memo_writer.agent import MEMO_TOOL, Agent, _slugify_asset_name
from app.agents.memo_writer.prompts import build_user_prompt
from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    RnpvInputs,
    RnpvResult,
    SupplyConstraint,
    TherapeuticArea,
)
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


# A complete, valid MemoContent payload — the shape the model returns as the
# emit_memo tool's `input`. The Anthropic API validates this against the tool
# schema before we ever see it; here we supply it directly.
_TOOL_INPUT = {
    "tldr": {
        "recommendation": "buy",
        "loa_pct": 16.1,
        "rnpv_base_usd_m": 516,
        "rnpv_range_low_usd_m": 290,
        "rnpv_range_high_usd_m": 698,
        "thesis_one_liner": "Phase 2 KRAS G12C asset with a documentable PoS chain.",
    },
    "asset_overview": {
        "paragraph": "Adagrasib is an oral KRAS G12C inhibitor in 2L+ NSCLC."
    },
    "pos_analysis": {
        "waterfall_narrative": (
            "From the base rate, biomarker-enrichment-boost x1.20 lifts the LOA, "
            "then target-validated x1.15 closes the validation question, BTD x1.10 "
            "reflects FDA pre-commitment."
        ),
        "reflexivity_note": "Mirati sits in the adequate reflexivity tier.",
        "supply_note": "Unconstrained small-molecule supply — not a binding factor.",
    },
    "valuation": {
        "valuation_narrative": (
            "Base rNPV $516M, MC P25-P75 $290-$698M. Top tornado driver: peak sales."
        )
    },
    "comparables": {
        "cohort_paragraph": (
            "Oncology small-molecule cohort, median EV/peak-sales 6.67x, closest "
            "analog selpercatinib/Lilly."
        )
    },
    "operational": {
        "pillars_paragraph": "Clinical 8/10, regulatory 8/10, competitive 6/10 — no red flags."
    },
    "risks": [
        {
            "label": "Peak-sales concentration",
            "description": "Second-mover share against sotorasib could compress the anchor.",
            "severity": "high",
        },
        {
            "label": "Single-asset concentration",
            "description": "Mirati corporate exposure if KRYSTAL-12 fails.",
            "severity": "medium",
        },
    ],
    "recommendation_close": {
        "recommendation": "buy",
        "conviction": "medium",
        "path_dependency_verdict": (
            "Adequate reflexivity tier (x1.00) and unconstrained supply leave the "
            "call unmoved by either path-dependency."
        ),
        "closing_paragraph": "At $474M asset-attributable, the framework brackets the entry as a buy.",
        "kill_criterion": "A KRYSTAL-12 confirmatory ORR < 30% at the H2'26 readout flips the call to avoid.",
    },
    "executive_summary": "Adagrasib is a Phase 2 KRAS G12C asset with a 16.1% LOA and base rNPV $516M.",
    "recommendation": "buy",
    "red_flags": ["Peak-sales concentration", "Single-asset concentration"],
}


def _fake_client_returning(tool_input):
    """A fake anthropic.Anthropic() whose messages.create returns a tool_use block."""
    block = SimpleNamespace(type="tool_use", name="emit_memo", input=tool_input)
    message = SimpleNamespace(content=[block])

    class FakeMessages:
        def create(self, **kwargs):
            # The migration must pass the tool + force its use.
            assert kwargs["model"] == "claude-opus-4-7"
            assert kwargs["tool_choice"] == {"type": "tool", "name": "emit_memo"}
            assert any(t["name"] == "emit_memo" for t in kwargs["tools"])
            return message

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    return FakeClient()


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


def test_slugify_strips_punctuation_and_lowercases():
    assert _slugify_asset_name("adagrasib (MRTX849)") == "adagrasib_mrtx849"
    assert _slugify_asset_name("ADAGRASIB") == "adagrasib"
    assert _slugify_asset_name("") == "unnamed"


# ---------------------------------------------------------------------------
# brief serialization — the supply differentiator must reach the agent
# ---------------------------------------------------------------------------


def test_brief_includes_supply_tier_and_rnpv_ceiling():
    """A severe-supply asset whose rNPV carries a peak ceiling must surface BOTH
    the supply tier (ASSET block) and the ceiling (RNPV block) in the brief.
    Regression guard: before the synthesis pass the memo agent was blind to
    supply entirely — capital_position was serialized but supply_constraint and
    the rNPV ceiling were not."""
    record = DiligenceRecord(
        asset=AssetInput(
            asset_name="ac-225 alpha emitter",
            phase=Phase.PHASE_1,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.RADIOPHARMACEUTICAL,
            supply_constraint=SupplyConstraint.SEVERE,
        ),
        rnpv_inputs=RnpvInputs(peak_sales_usd_m=1500.0),
        rnpv=RnpvResult(
            base_case_usd_m=900.0,
            supply_peak_ceiling_pct=0.65,
            supply_adjusted_peak_usd_m=975.0,
        ),
    )
    brief = build_user_prompt(record)
    assert "Supply constraint: severe" in brief
    assert "Supply ceiling: ×0.65" in brief
    assert "effective peak $975M" in brief


def test_brief_omits_supply_ceiling_when_unconstrained():
    """An unconstrained asset (ceiling 1.0 / None) gets NO ceiling line — the
    brief stays clean and the model isn't prompted to invent a supply effect."""
    record = DiligenceRecord(
        asset=AssetInput(
            asset_name="adagrasib",
            phase=Phase.PHASE_2,
            therapeutic_area=TherapeuticArea.ONCOLOGY,
            modality=Modality.SMALL_MOLECULE,
        ),
        rnpv_inputs=RnpvInputs(peak_sales_usd_m=1200.0),
        rnpv=RnpvResult(base_case_usd_m=516.0),
    )
    brief = build_user_prompt(record)
    assert "Supply constraint: unconstrained" in brief
    assert "Supply ceiling" not in brief


# ---------------------------------------------------------------------------
# tool schema
# ---------------------------------------------------------------------------


def test_memo_tool_schema_requires_all_sections():
    schema = MEMO_TOOL["input_schema"]
    required = set(schema.get("required", []))
    for section in (
        "tldr",
        "asset_overview",
        "pos_analysis",
        "valuation",
        "comparables",
        "operational",
        "risks",
        "recommendation_close",
        "executive_summary",
        "recommendation",
        "red_flags",
    ):
        assert section in required, f"{section} should be required in the tool schema"


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

    result = agent.run(_make_record("adagrasib"))
    assert result["from_cache"] is True
    assert result["body_markdown"] == "## Executive summary\ncached."


def test_cache_miss_when_asset_not_in_manifest_list(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    (tmp_path / "cache" / "adagrasib.json").write_text(json.dumps({"body_markdown": "x"}))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("adagrasib"))
    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# tool-use live path (mocked SDK)
# ---------------------------------------------------------------------------


def test_live_call_assembles_memo_from_tool_use(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])  # force live path
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    with patch("anthropic.Anthropic", return_value=_fake_client_returning(_TOOL_INPUT)):
        result = agent.run(_make_record("vorasidenib"))

    assert result["from_cache"] is False
    assert result["recommendation"] == "buy"
    assert result["tldr"]["rnpv_base_usd_m"] == 516
    # reflexivity_note nested correctly inside pos_analysis (the v1.7.10 bug)
    assert result["pos_analysis"]["reflexivity_note"] == "Mirati sits in the adequate reflexivity tier."
    # supply_note — the second path-dependency, paired with reflexivity
    assert "supply" in result["pos_analysis"]["supply_note"].lower()
    assert len(result["risks"]) == 2
    # defensibility fields on the close: explicit conviction + path-dependency verdict
    assert result["recommendation_close"]["conviction"] == "medium"
    assert "reflexivity" in result["recommendation_close"]["path_dependency_verdict"].lower()
    assert result["recommendation_close"]["kill_criterion"].endswith("avoid.")
    # body_markdown assembled from the structured sections, no fenced JSON
    assert "## TL;DR" in result["body_markdown"]
    assert "```json" not in result["body_markdown"]
    # the new defensibility fields propagate into the back-compat markdown too
    # (regression guard for the partial-propagation bug)
    assert "not a binding factor" in result["body_markdown"]  # supply_note
    assert "**Conviction:** medium" in result["body_markdown"]
    assert "Path-dependency verdict" in result["body_markdown"]


def test_live_call_502_when_model_omits_tool_block(tmp_path: Path, monkeypatch):
    """If the model returns no tool_use block, surface a clean 502 (not an empty memo)."""
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    text_only = SimpleNamespace(content=[SimpleNamespace(type="text", text="oops, prose")])

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
    """A tool payload missing a required section fails MemoContent validation."""
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")

    incomplete = {"tldr": _TOOL_INPUT["tldr"]}  # missing everything else
    with patch("anthropic.Anthropic", return_value=_fake_client_returning(incomplete)):
        with pytest.raises(Exception):  # pydantic ValidationError
            agent.run(_make_record("vorasidenib"))


def test_live_call_503_when_no_api_key(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 503
    assert "ANTHROPIC_API_KEY" in exc.value.detail
