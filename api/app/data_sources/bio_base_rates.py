"""BIO/Informa base-rate data source.

Looks up phase-transition probabilities by therapeutic area.
"""

from __future__ import annotations

from typing import Any

from ..registry import DataSource
from ._paths import load_json


class BIOBaseRates(DataSource):
    id = "bio_base_rates"
    provides_fields = ("base_rate", "phase_transitions")

    def __init__(self) -> None:
        self._data = load_json("base_rates.json")

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        """Query keys: therapeutic_area (str), phase (str)."""
        ta = query.get("therapeutic_area", "all")
        phase = query.get("phase", "phase_1")

        row = next(
            (r for r in self._data["transitions"] if r["therapeutic_area"] == ta),
            None,
        )
        if row is None:
            row = next(r for r in self._data["transitions"] if r["therapeutic_area"] == "all")

        base_rate = self._loa_from_phase(row, phase)
        return {
            "base_rate": base_rate,
            "phase_transitions": {
                "p1_to_p2": row["p1_to_p2"],
                "p2_to_p3": row["p2_to_p3"],
                "p3_to_nda": row["p3_to_nda"],
                "nda_to_approval": row["nda_to_approval"],
            },
            "source": row["source"],
            "therapeutic_area_used": row["therapeutic_area"],
        }

    @staticmethod
    def _loa_from_phase(row: dict[str, Any], phase: str) -> float:
        """Cumulative probability of reaching approval from current phase."""
        match phase:
            case "preclinical":
                # Preclinical-to-Phase-1 transition not in BIO table; use 50% prior.
                return 0.50 * row["loa_from_p1"]
            case "phase_1":
                return row["loa_from_p1"]
            case "phase_2":
                return row["p2_to_p3"] * row["p3_to_nda"] * row["nda_to_approval"]
            case "phase_3":
                return row["p3_to_nda"] * row["nda_to_approval"]
            case "nda":
                return row["nda_to_approval"]
            case "approved":
                return 1.0
            case _:
                return row["loa_from_p1"]
