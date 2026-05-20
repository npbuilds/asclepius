"""WACC/discount-rate benchmark data source — feeds rNPV module."""

from __future__ import annotations

from typing import Any

from ..registry import DataSource
from ._paths import load_json


class WACCBenchmarks(DataSource):
    id = "wacc_benchmarks"
    provides_fields = ("default_wacc", "wacc_range")

    def __init__(self) -> None:
        self._data = load_json("wacc_benchmarks.json")

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        stage = query.get("company_stage", "phase_2_small_mid_cap")
        row = next(
            (r for r in self._data["benchmarks"] if r["company_stage"] == stage),
            None,
        )
        if row is None:
            row = next(
                r for r in self._data["benchmarks"]
                if r["company_stage"] == "phase_2_small_mid_cap"
            )
        return {
            "default_wacc": row["wacc"],
            "wacc_range": (row["range_low"], row["range_high"]),
            "rationale": row["rationale"],
            "company_stage_used": row["company_stage"],
        }
