"""BaseAgent ABC — implemented by runtime agents in v1.1.

Each agent has a narrow contract:
  * manifest declares id, skill_loadout, model, cached_assets, etc.
  * `run(record)` returns a structured result that gets serialized to the
    /api/agents/<id>/run response

The constructor receives the manifest and the agent's directory so subclasses
can find their cache/ subfolder and prompt assets without hardcoded paths.
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
