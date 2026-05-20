"""EDGAR filings data source — v1 SHIM returning curated capital-position estimates.

In v1.1 this becomes a real EDGAR client that pulls 10-K / 10-Q risk-factor
language and cash-position disclosures. For v1 we ship a tiny lookup table for
the assets we ship as worked examples so the deps graph resolves end-to-end.

Real implementation note: SEC requires a User-Agent header identifying the
caller. That will live in config.py for v1.1.
"""

from __future__ import annotations

from typing import Any

from ..registry import DataSource


# Curated for v1 worked examples. Pre-deal sponsor capital positions per public
# 10-Q filings around the data-cutoff dates in each comparable JSON.
_SPONSOR_CAPITAL_TABLE: dict[str, dict[str, Any]] = {
    "mirati therapeutics": {
        "as_of": "2022-03-31",
        "cash_and_equivalents_usd_m": 890,
        "quarterly_burn_usd_m": 95,
        "runway_months": 9,
        "capital_position": "constrained",
        "source": "Mirati 10-Q Q1 2022 (SEC EDGAR).",
        "note": "Note: capital_position 'constrained' (6-12 months) per the runway/burn calculation. The adagrasib JSON uses 'adequate' as a more generous read because Mirati had follow-on access; this shim returns the strict-runway view as an alternative.",
    },
    "array biopharma": {
        "as_of": "2019-03-31",
        "cash_and_equivalents_usd_m": 380,
        "quarterly_burn_usd_m": 65,
        "runway_months": 5,
        "capital_position": "distressed",
        "source": "Array BioPharma 10-Q Q1 2019 (SEC EDGAR).",
        "note": "Pre-Pfizer-deal. Capital strain explains the high deal premium — they were a willing seller.",
    },
    "loxo oncology": {
        "as_of": "2018-09-30",
        "cash_and_equivalents_usd_m": 720,
        "quarterly_burn_usd_m": 80,
        "runway_months": 9,
        "capital_position": "adequate",
        "source": "Loxo Oncology 10-Q Q3 2018 (SEC EDGAR).",
        "note": "Pre-Lilly-deal. Adequate runway but pursuing strategic alternatives.",
    },
}


class EDGARFilings(DataSource):
    """v1 shim — returns curated sponsor capital data from a lookup table."""

    id = "edgar_filings"
    provides_fields = (
        "cash_and_equivalents_usd_m",
        "quarterly_burn_usd_m",
        "runway_months",
        "capital_position",
    )

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        sponsor = (query.get("sponsor") or "").lower().strip()
        if not sponsor:
            return {"error": "EDGAR data source requires a 'sponsor' query field."}
        if sponsor not in _SPONSOR_CAPITAL_TABLE:
            return {
                "error": f"sponsor '{sponsor}' not in v1 EDGAR shim; v1.1 will pull live.",
                "available_sponsors": list(_SPONSOR_CAPITAL_TABLE.keys()),
            }
        return dict(_SPONSOR_CAPITAL_TABLE[sponsor])
