"""Modality multiplier data source."""

from __future__ import annotations

from typing import Any

from ..registry import DataSource
from ._paths import load_json


class ModalityMultipliers(DataSource):
    id = "modality_multipliers"
    provides_fields = ("modality_multiplier", "modality_range")

    def __init__(self) -> None:
        self._data = load_json("modality_multipliers.json")

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        modality = query.get("modality", "small_molecule")
        row = next(
            (r for r in self._data["multipliers"] if r["modality"] == modality),
            None,
        )
        if row is None:
            row = next(r for r in self._data["multipliers"] if r["modality"] == "other")
        return {
            "modality_multiplier": row["multiplier"],
            "modality_range": (row["range_low"], row["range_high"]),
            "rationale": row["rationale"],
            "source": row["source"],
            "modality_used": row["modality"],
        }
