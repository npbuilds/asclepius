"""Tests for the v1.1.3 methodology-loading mechanism on BaseAgent."""

from __future__ import annotations

from pathlib import Path

from app.agents.base import BaseAgent, _resolve_methodology_dir
from app.registry import AgentManifest


class _DummyAgent(BaseAgent):
    """Minimal concrete subclass for testing the loading logic without
    triggering the abstract-class check."""

    def run(self, record):  # type: ignore[override]
        return {}


def _manifest(refs: list[str]) -> AgentManifest:
    return AgentManifest(
        id="dummy",
        name="Dummy",
        version="0.1.0",
        description="test",
        methodology_refs=refs,
        trigger_label="Run",
        input_fields=[],
        output_fields=[],
    )


def test_methodology_context_loads_real_files(tmp_path: Path, monkeypatch):
    methodology = tmp_path / "methodology"
    methodology.mkdir()
    (methodology / "a.md").write_text("# Doc A\n\nFirst doc body.")
    (methodology / "b.md").write_text("# Doc B\n\nSecond doc body.")
    monkeypatch.setenv("ASCLEPIUS_METHODOLOGY_DIR", str(methodology))

    agent = _DummyAgent(
        manifest=_manifest(["a.md", "b.md"]), agent_dir=tmp_path
    )
    ctx = agent.methodology_context
    assert "a.md" in ctx
    assert "First doc body." in ctx
    assert "b.md" in ctx
    assert "Second doc body." in ctx
    # Helper composes context + base prompt
    composed = agent._system_prompt_with_methodology("BASE")
    assert composed.startswith("The following methodology writeups")
    assert composed.endswith("BASE")


def test_methodology_context_missing_file_is_graceful(tmp_path: Path, monkeypatch):
    methodology = tmp_path / "methodology"
    methodology.mkdir()
    (methodology / "real.md").write_text("# Real")
    monkeypatch.setenv("ASCLEPIUS_METHODOLOGY_DIR", str(methodology))

    agent = _DummyAgent(
        manifest=_manifest(["real.md", "missing.md"]), agent_dir=tmp_path
    )
    # Real file loads; missing one is skipped silently
    assert "Real" in agent.methodology_context
    assert "missing.md" not in agent.methodology_context


def test_methodology_context_empty_when_no_refs(tmp_path: Path):
    agent = _DummyAgent(manifest=_manifest([]), agent_dir=tmp_path)
    assert agent.methodology_context == ""
    # Helper returns the base prompt unchanged
    assert agent._system_prompt_with_methodology("BASE") == "BASE"


def test_methodology_context_rejects_path_traversal(tmp_path: Path, monkeypatch):
    methodology = tmp_path / "methodology"
    methodology.mkdir()
    (methodology / "ok.md").write_text("ok")
    # Sensitive file outside the methodology root
    (tmp_path / "secret.md").write_text("SHOULD NOT LOAD")
    monkeypatch.setenv("ASCLEPIUS_METHODOLOGY_DIR", str(methodology))

    agent = _DummyAgent(
        manifest=_manifest(["../secret.md", "ok.md"]), agent_dir=tmp_path
    )
    assert "SHOULD NOT LOAD" not in agent.methodology_context
    assert "ok" in agent.methodology_context


def test_resolve_methodology_dir_respects_env_var(tmp_path: Path, monkeypatch):
    target = tmp_path / "custom_methodology"
    target.mkdir()
    monkeypatch.setenv("ASCLEPIUS_METHODOLOGY_DIR", str(target))
    assert _resolve_methodology_dir() == target.resolve()
