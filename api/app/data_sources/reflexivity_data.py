"""Reflexivity adjustment data source — the headline differentiator's data layer."""

from __future__ import annotations

from typing import Any

from ..registry import DataSource
from ._paths import load_json


class ReflexivityAdjustments(DataSource):
    id = "reflexivity_adjustments"
    provides_fields = ("reflexivity_multiplier", "reflexivity_rationale")

    def __init__(self) -> None:
        self._data = load_json("reflexivity_adjustments.json")

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        position = query.get("capital_position", "adequate")
        row = next(
            (r for r in self._data["adjustments"] if r["capital_position"] == position),
            None,
        )
        if row is None:
            row = next(
                r for r in self._data["adjustments"] if r["capital_position"] == "adequate"
            )
        return {
            "reflexivity_multiplier": row["multiplier"],
            "reflexivity_rationale": row["rationale"],
            "reflexivity_range": (row["range_low"], row["range_high"]),
            "capital_position_used": row["capital_position"],
        }
