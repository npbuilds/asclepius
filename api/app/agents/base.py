"""BaseAgent ABC — implemented by runtime agents in v1.1.

Each agent has a narrow contract:
  * skill_loadout: which skills (by relative path) it loads at runtime
  * input/output schemas declared in the manifest
  * `run(record)` returns a structured result that gets merged onto the
    DiligenceRecord at well-defined field paths
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..domain import DiligenceRecord


class BaseAgent(ABC):
    """All runtime agents subclass this."""

    id: str = ""

    @abstractmethod
    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        """Run the agent against a diligence record.

        Returns a dict whose keys must match the manifest's `output_fields`.
        The caller is responsible for merging onto the record.
        """
