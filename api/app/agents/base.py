"""BaseAgent ABC — implemented by runtime agents in v1.1.

Each agent has a narrow contract:
  * manifest declares id, skill_loadout, model, cached_assets, etc.
  * `run(record)` returns a structured result that gets serialized to the
    /api/agents/<id>/run response

The constructor receives the manifest and the agent's directory so subclasses
can find their cache/ subfolder and prompt assets without hardcoded paths.

KNOWN LIMITATION (v1.1.0 / v1.1.1 — to be addressed in v1.1.3):
  The manifest's `skill_loadout` field lists paths into the Asclepius
  skill-suite (e.g. "biotech-venture/leaf/investment-memo-writer/SKILL.md")
  but the agent classes do not currently load those files at runtime — the
  prompts in each agent's prompts.py are hardcoded heuristics inspired by
  the same methodology, not the verbatim skill content. This is honest
  documentation, not a runtime contract.

  v1.1.3 will add a `_load_skill_context()` hook that reads the listed
  skill files at startup and injects them into the system prompt. The
  research dive for the Auto-Diligence agent (v1.1.2) is the forcing
  function — once Auto-Diligence proves the skill-loading mechanism, the
  Memo Writer and Adversary will be backported in v1.1.3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..domain import DiligenceRecord

if TYPE_CHECKING:
    from ..registry import AgentManifest


class BaseAgent(ABC):
    """All runtime agents subclass this."""

    def __init__(self, manifest: "AgentManifest", agent_dir: Path) -> None:
        self.manifest = manifest
        self.agent_dir = agent_dir

    @property
    def id(self) -> str:
        return self.manifest.id

    @abstractmethod
    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        """Run the agent against a diligence record.

        Returns a dict whose keys match the manifest's `output_fields`. The
        caller serializes this to the HTTP response without further shaping.
        """
