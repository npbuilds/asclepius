"""Game-Theory Adversary tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.agents.game_theory_adversary.agent import (
    Agent,
    _parse_adversary_response,
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


# ---------------------------------------------------------------------------


def test_slugify_handles_real_asset_names():
    assert _slugify_asset_name("adagrasib (MRTX849)") == "adagrasib_mrtx849"


def test_parse_extracts_findings_and_verdict_shift():
    raw = """## Signaling lens
Finding A here.

## Verdict
Hold the recommendation.

```json
{
  "verdict_shift": "hold",
  "recommendation_shift_to": null,
  "findings": [
    {"lens": "signaling", "claim": "Capital adequate but single-arm trial reads as constrained-tier", "severity": "moderate"},
    {"lens": "auction", "claim": "Comparable median biased upward by winner's-curse on Encorafenib bid", "severity": "minor"}
  ]
}
```"""
    out = _parse_adversary_response(raw, model_used="test")
    assert out["verdict_shift"] == "hold"
    assert out["recommendation_shift_to"] is None
    assert len(out["findings"]) == 2
    assert out["findings"][0]["lens"] == "signaling"
    # New structured flags absent in legacy input → empty list, not missing
    assert out["flags"] == []
    assert "```json" not in out["body_markdown"]


def test_parse_rejects_invalid_lens_severity_verdict():
    raw = """## Verdict
text.

```json
{
  "verdict_shift": "ascend",
  "recommendation_shift_to": "yolo",
  "findings": [
    {"lens": "garbage", "claim": "x", "severity": "moderate"},
    {"lens": "signaling", "claim": "y", "severity": "fatal"},
    {"lens": "signaling", "claim": "valid one", "severity": "critical"}
  ]
}
```"""
    out = _parse_adversary_response(raw, model_used="test")
    assert out["verdict_shift"] == "hold"  # invalid → hold
    assert out["recommendation_shift_to"] is None  # invalid → None
    assert len(out["findings"]) == 1
    assert out["findings"][0]["claim"] == "valid one"


def test_parse_downgrade_with_recommendation_shift():
    raw = """## Verdict
Downgrade to cautious.

```json
{
  "verdict_shift": "downgrade",
  "recommendation_shift_to": "cautious",
  "findings": []
}
```"""
    out = _parse_adversary_response(raw, model_used="test")
    assert out["verdict_shift"] == "downgrade"
    assert out["recommendation_shift_to"] == "cautious"


def test_parse_fallback_when_no_json_block():
    raw = "## Verdict\nNothing structured.\n\n(no json block)"
    out = _parse_adversary_response(raw, model_used="test")
    assert out["verdict_shift"] == "hold"
    assert out["findings"] == []
    assert out["flags"] == []


def test_parse_extracts_structured_flags():
    raw = """Overall posture: cautious on the thesis.

## Verdict
Downgrade.

```json
{
  "verdict_shift": "downgrade",
  "recommendation_shift_to": "cautious",
  "flags": [
    {
      "flag_type": "signaling_equilibrium",
      "severity": "high",
      "title": "Single-arm Ph3 with well-capitalized sponsor",
      "rationale": "Sponsor has 18 months runway yet ran a single-arm registrational trial. Under Spence (1973), a well-capitalized sponsor with a high-PoS asset would have committed to the costly randomized design; the chosen design reads as constrained-tier signaling and breaks the separating equilibrium.",
      "test": "Compare the trial's N to the BIO cohort median for similar phase; if N is below the 25th percentile despite capital adequacy, the read holds.",
      "cite": ["methodology/06-signaling-equilibrium.md"]
    },
    {
      "flag_type": "bayesian_persuasion",
      "severity": "medium",
      "title": "Post-hoc subgroup highlighted in press release",
      "rationale": "The Q3 release foregrounds a KRAS G12C subgroup not pre-specified in the SAP while omitting the ITT result. Under Kamenica-Gentzkow, this is the textbook persuasion-optimal signal partition (Yi et al. 2024).",
      "test": "Pull the trial's SAP from ClinicalTrials.gov and confirm the subgroup is not pre-specified; recover the ITT P-value from the registration data.",
      "cite": ["methodology/07-bayesian-persuasion-disclosure.md"]
    }
  ]
}
```"""
    out = _parse_adversary_response(raw, model_used="test")
    assert out["verdict_shift"] == "downgrade"
    assert out["recommendation_shift_to"] == "cautious"
    assert len(out["flags"]) == 2
    f0 = out["flags"][0]
    assert f0["flag_type"] == "signaling_equilibrium"
    assert f0["severity"] == "high"
    assert f0["title"].startswith("Single-arm")
    assert "Spence" in f0["rationale"]
    assert "cohort" in f0["test"].lower()
    assert f0["cite"] == ["methodology/06-signaling-equilibrium.md"]
    assert out["flags"][1]["flag_type"] == "bayesian_persuasion"


def test_parse_rejects_flags_with_invalid_type_or_missing_fields():
    raw = """## Verdict
Hold.

```json
{
  "verdict_shift": "hold",
  "flags": [
    {"flag_type": "unicorn_curse", "severity": "high", "title": "x", "rationale": "y", "test": "z"},
    {"flag_type": "signaling_equilibrium", "severity": "catastrophic", "title": "x", "rationale": "y", "test": "z"},
    {"flag_type": "winners_curse", "severity": "high", "title": "", "rationale": "y", "test": "z"},
    {"flag_type": "winners_curse", "severity": "high", "title": "kept", "rationale": "valid rationale", "test": "valid test", "cite": "methodology/05-worked-example-adagrasib.md"}
  ]
}
```"""
    out = _parse_adversary_response(raw, model_used="test")
    assert len(out["flags"]) == 1
    kept = out["flags"][0]
    assert kept["title"] == "kept"
    # cite passed as a bare string should be normalized to a single-item list
    assert kept["cite"] == ["methodology/05-worked-example-adagrasib.md"]


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
    # Older cache payloads predate ``flags`` — the agent should backfill it.
    assert out["flags"] == []


def test_live_call_503_when_no_key(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ASCLEPIUS_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        agent.run(_make_record("vorasidenib"))
    assert exc.value.status_code == 503


def test_live_call_with_mocked_anthropic(tmp_path: Path, monkeypatch):
    agent = _make_agent(tmp_path, cached_assets=[])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-fake")
    fake_text = """## Signaling lens
A finding.

## Verdict
Hold.

```json
{
  "verdict_shift": "hold",
  "recommendation_shift_to": null,
  "flags": [
    {"flag_type": "data_quality", "severity": "low", "title": "Missing target_validated flag", "rationale": "The brief does not set target_validated, which makes the cohort_base_rate_check inert. Downstream PoS adjustments may rest on an implicit assumption.", "test": "Confirm the target's mechanistic validation status against the published literature.", "cite": ["methodology/01-pos-framework.md"]}
  ],
  "findings": [{"lens":"signaling","claim":"sample","severity":"minor"}]
}
```"""
    fake_message = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=fake_text)]
    )

    class FakeMessages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-7"
            return fake_message

    class FakeClient:
        def __init__(self):
            self.messages = FakeMessages()

    with patch("anthropic.Anthropic", return_value=FakeClient()):
        out = agent.run(_make_record("vorasidenib"))
    assert out["from_cache"] is False
    assert out["verdict_shift"] == "hold"
    assert len(out["flags"]) == 1
    assert out["flags"][0]["flag_type"] == "data_quality"
    # Legacy findings still flow through
    assert len(out["findings"]) == 1
