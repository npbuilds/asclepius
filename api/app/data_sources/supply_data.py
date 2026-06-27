"""Supply-constraint adjustment data source — the second path-dependency's data layer.

Mirrors reflexivity_data.py. Auto-registered by the filesystem-based discovery in
registry.discover_data_sources() (it globs every non-underscore *.py here), so no
explicit import in __init__.py is required.
"""

from __future__ import annotations

from typing import Any

from ..registry import DataSource
from ._paths import load_json


class SupplyAdjustments(DataSource):
    id = "supply_adjustments"
    provides_fields = (
        "supply_pos_multiplier",
        "supply_peak_ceiling_pct",
        "supply_rationale",
        "supply_source",
    )

    def __init__(self) -> None:
        self._data = load_json("supply_adjustments.json")

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        tier = query.get("supply_constraint", "unconstrained")
        row = next(
            (r for r in self._data["adjustments"] if r["supply_constraint"] == tier),
            None,
        )
        if row is None:
            row = next(
                r
                for r in self._data["adjustments"]
                if r["supply_constraint"] == "unconstrained"
            )
        return {
            "supply_pos_multiplier": row["pos_multiplier"],
            "supply_peak_ceiling_pct": row["peak_ceiling_pct"],
            "supply_rationale": row["rationale"],
            "supply_source": row["source"],
            "supply_constraint_used": row["supply_constraint"],
        }
