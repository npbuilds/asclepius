"""v1.6 — Live forward prediction for divarasib (Roche, KRAS G12C, NSCLC).

This is the first FORWARD prediction in Asclepius's public log: a Phase 3
asset with a future, public, dated catalyst that we record before any
outcome is known. Contrast with adagrasib in
methodology/05-worked-example-adagrasib.md, which was a retrospective
backtest run with a deliberate June 2022 information cutoff.

The catalyst:
  - NCT06497556 — Phase 3, divarasib vs sotorasib OR adagrasib (head-to-
    head against the only two FDA-approved KRAS G12C inhibitors), n=338,
    ACTIVE_NOT_RECRUITING (enrollment complete), PFS primary endpoint,
    primary completion date 2027-09-30 (ESTIMATED).
  - Outcome = 1 if Roche reports a statistically significant PFS benefit
    (or non-inferiority on the primary analysis if pre-specified) at PCD
    or via interim, AND files a regulatory submission within 12 months.
  - Outcome = 0 if the trial misses its primary endpoint or is terminated.

Asset inputs are all from public sources (CT.gov v2 metadata + the
Lancet Oncology Dec 2023 paper by Sacher et al. + Roche public filings),
cited inline. Information cutoff: today's date.

This script:
  1. Builds the AssetInput + RnpvInputs from researched values.
  2. Runs the PoS, rNPV, and scorecard engines.
  3. Writes a public prediction JSON to predictions/.
  4. Logs the prediction to the Calibration SQLite store (so the Brier
     dashboard tracks it once a future resolve_prediction lands).

Run with:
    python scripts/log_divarasib_prediction.py
    python scripts/log_divarasib_prediction.py --dry-run  # show only
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "api"
sys.path.insert(0, str(API_DIR))

from app.domain import (  # noqa: E402
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    RegulatoryDesignation,
    RnpvInputs,
    TherapeuticArea,
)
from app.modules.calibration import db as calib_db  # noqa: E402
from app.modules.pos.engine import compute as compute_pos  # noqa: E402
from app.modules.rnpv.engine import compute as compute_rnpv  # noqa: E402

warnings.filterwarnings("ignore")

PREDICTION_ID = "divarasib-nct06497556-2026-06"
PREDICTION_DATE = "2026-06-03"
RESOLUTION_DUE = "2027-09-30"  # PCD from CT.gov v2
OUT_PATH = REPO_ROOT / "predictions" / f"{PREDICTION_DATE}-divarasib-{PREDICTION_ID.replace('-', '_')}.json"


# ---------------------------------------------------------------------------
# Asset definition (every value carries a citation in the writeup
# methodology/18; this script just assembles them).
# ---------------------------------------------------------------------------


def build_asset() -> AssetInput:
    return AssetInput(
        asset_name="divarasib",
        sponsor="Hoffmann-La Roche",
        phase=Phase.PHASE_3,
        therapeutic_area=TherapeuticArea.ONCOLOGY,
        modality=Modality.SMALL_MOLECULE,
        capital_position=CapitalPosition.WELL_CAPITALIZED,
        mechanism="KRAS G12C inhibitor (covalent, second-generation)",
        target="KRAS G12C",
        indication="Previously treated KRAS G12C+ advanced/metastatic NSCLC",
        biomarker_enrichment=True,
        target_validated=True,
        num_competitors=3,  # sotorasib (approved), adagrasib (approved), olomorasib (Lilly Ph2)
        regulatory_designations=[],  # No public BTD/Fast Track as of 2026-06-03; conservative
    )


def build_rnpv_inputs() -> RnpvInputs:
    return RnpvInputs(
        # KRAS G12C class is bounded: ~13% of NSCLC patients × second-line+
        # = ~8K addressable in US/EU. Sotorasib 2024 sales ~$370M (full
        # year), adagrasib ~$170M, declining since BMS/Mirati had launch
        # execution issues. Divarasib's Lancet Oncology Dec 2023 paper
        # (Sacher et al.) shows numerically better ORR (56% vs ~13-42%)
        # and mPFS (13.1mo vs 6.5-6.8mo) on monotherapy — clinically
        # meaningful differentiation. Conservative peak: $700M reflecting
        # share gain on better profile, ROW + 1L expansion contributions.
        peak_sales_usd_m=700.0,
        years_to_peak=5,
        years_of_exclusivity=12,
        cogs_pct=0.20,
        # Roche pharma WACC is meaningfully below the biotech-startup
        # benchmark — large-cap diversified pharma, public-equity discount
        # rate ~7-9% per Damodaran 2026. Use the framework's mid-range
        # default rather than asset-specific to keep portfolio comparability.
        wacc=0.10,
        dev_cost_phase_3_usd_m=250.0,
        launch_cost_usd_m=150.0,
    )


# ---------------------------------------------------------------------------
# Run framework + assemble outputs
# ---------------------------------------------------------------------------


def run_framework() -> dict:
    asset = build_asset()
    record = DiligenceRecord(asset=asset, rnpv_inputs=build_rnpv_inputs())

    pos_result = compute_pos(record)
    record.pos = pos_result
    rnpv_result = compute_rnpv(record)

    return {
        "asset": asset,
        "pos": pos_result,
        "rnpv": rnpv_result,
        "record": record,
    }


def pos_adjustment_summary(adjustments) -> list[dict]:
    """Compact PoS audit trail for the public log."""
    return [
        {"name": a.name, "multiplier": round(a.multiplier, 4), "rationale": a.rationale}
        for a in adjustments
    ]


def write_public_json(outputs: dict, *, dry_run: bool) -> None:
    asset = outputs["asset"]
    pos = outputs["pos"]
    rnpv = outputs["rnpv"]

    # The seed predictions use a minimal schema (asset + framework: {predicted_pos,
    # reflexivity_multiplier}). For divarasib we include the full PoS audit
    # trail + rNPV summary so the public record is self-contained — this
    # prediction is the showcase, not a seed row.
    reflexivity_mult = next(
        (a.multiplier for a in pos.adjustments if "reflexivity" in a.name.lower()),
        1.0,
    )

    payload = {
        "schema_version": "1.1",
        "prediction_id": PREDICTION_ID,
        "prediction_date": PREDICTION_DATE,
        "asset": {
            "name": asset.asset_name,
            "sponsor": asset.sponsor,
            "phase": asset.phase.value,
            "therapeutic_area": asset.therapeutic_area.value,
            "modality": asset.modality.value,
            "capital_position": asset.capital_position.value,
            "mechanism": asset.mechanism,
            "target": asset.target,
            "indication": asset.indication,
            "biomarker_enrichment": asset.biomarker_enrichment,
            "target_validated": asset.target_validated,
            "num_competitors": asset.num_competitors,
            "regulatory_designations": [d.value for d in asset.regulatory_designations],
        },
        "trial": {
            "nct_id": "NCT06497556",
            "title": (
                "Divarasib Versus Sotorasib or Adagrasib in Previously Treated "
                "KRAS G12C+ Advanced or Metastatic NSCLC"
            ),
            "design": "Phase 3, randomized, open-label, 2-arm head-to-head",
            "enrollment": 338,
            "enrollment_status": "ACTUAL (recruitment complete as of 2026-06-03)",
            "primary_endpoint": "Progression-Free Survival (PFS)",
            "primary_completion_date": RESOLUTION_DUE,
            "primary_completion_type": "ESTIMATED",
            "source": "https://clinicaltrials.gov/study/NCT06497556 (fetched 2026-06-03)",
        },
        "framework": {
            "predicted_pos": round(pos.final_loa, 4),
            "predicted_pos_ci_low": round(pos.confidence_low, 4),
            "predicted_pos_ci_high": round(pos.confidence_high, 4),
            "base_rate": round(pos.base_rate, 4),
            "reflexivity_multiplier": round(reflexivity_mult, 4),
            "rnpv_base_usd_m": round(rnpv.base_case_usd_m, 1),
            "rnpv_low_usd_m": round(rnpv.low_case_usd_m, 1) if rnpv.low_case_usd_m else None,
            "rnpv_high_usd_m": round(rnpv.high_case_usd_m, 1) if rnpv.high_case_usd_m else None,
            "monte_carlo_p25_usd_m": round(rnpv.monte_carlo_p25_usd_m, 1) if rnpv.monte_carlo_p25_usd_m else None,
            "monte_carlo_p50_usd_m": round(rnpv.monte_carlo_p50_usd_m, 1) if rnpv.monte_carlo_p50_usd_m else None,
            "monte_carlo_p75_usd_m": round(rnpv.monte_carlo_p75_usd_m, 1) if rnpv.monte_carlo_p75_usd_m else None,
            "monte_carlo_paths": rnpv.monte_carlo_paths,
            "pos_adjustments": pos_adjustment_summary(pos.adjustments),
        },
        "resolution_criteria": (
            "outcome = 1 if Roche reports a statistically significant PFS "
            "benefit (or pre-specified non-inferiority threshold met) on the "
            "primary analysis at PCD or via a pre-specified interim, AND a "
            "regulatory submission follows within 12 months. outcome = 0 if "
            "the trial misses its primary endpoint or is terminated for "
            "futility/safety. Partial/ambiguous outcomes (sig PFS but no "
            "submission, etc.) noted in resolution.note and treated as 0.5 "
            "for Brier scoring."
        ),
        "resolution": {
            "date": None,
            "outcome": None,
            "source": None,
            "note": f"Awaiting catalyst — primary completion estimated {RESOLUTION_DUE}.",
        },
        "methodology_writeup": "methodology/18-divarasib-live-forward-prediction.md",
    }

    if dry_run:
        print(json.dumps(payload, indent=2))
        print(f"\n(dry-run) would have written to {OUT_PATH}")
        return

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote prediction JSON → {OUT_PATH}")


def log_to_calibration(outputs: dict, *, dry_run: bool) -> None:
    """Insert into the calibration SQLite so the Brier dashboard tracks
    this prediction once resolved. Idempotent — the db.log_prediction
    function generates a fresh prediction_id, so re-running this script
    creates a new row. The public JSON's prediction_id is the immutable
    public reference; the SQLite row is the framework-internal tracker.
    """
    if dry_run:
        print("(dry-run) would have logged to calibration SQLite")
        return
    asset = outputs["asset"]
    pos = outputs["pos"]
    # Reflexivity multiplier is the one PoS adjustment the calibration
    # SQLite tracks separately (it's the headline differentiator). Pull it
    # from the PoS audit trail.
    reflexivity_mult = next(
        (a.multiplier for a in pos.adjustments if "reflexivity" in a.name.lower()),
        1.0,
    )
    pid = calib_db.log_prediction(
        asset_name=asset.asset_name,
        phase=asset.phase.value,
        therapeutic_area=asset.therapeutic_area.value,
        modality=asset.modality.value,
        capital_position=asset.capital_position.value,
        predicted_pos=pos.final_loa,
        reflexivity_multiplier=reflexivity_mult,
        prediction_date=date.fromisoformat(PREDICTION_DATE),
    )
    print(f"logged to calibration SQLite, prediction_id={pid}")


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Print outputs; don't write JSON or log to SQLite.")
    args = ap.parse_args(argv)

    outputs = run_framework()
    pos = outputs["pos"]
    rnpv = outputs["rnpv"]

    print("=== Asclepius framework outputs for divarasib (NCT06497556) ===")
    print(f"PoS final LOA: {pos.final_loa:.3f}  [{pos.confidence_low:.3f}, {pos.confidence_high:.3f}]")
    print(f"PoS base rate: {pos.base_rate:.3f} (BIO 2021 Phase 3 oncology)")
    print(f"PoS adjustment chain:")
    for a in pos.adjustments:
        print(f"  ×{a.multiplier:.3f}  {a.name}")
    print()
    print(f"rNPV base case: ${rnpv.base_case_usd_m:,.1f}M")
    if rnpv.low_case_usd_m and rnpv.high_case_usd_m:
        print(f"rNPV low / high: ${rnpv.low_case_usd_m:,.1f}M / ${rnpv.high_case_usd_m:,.1f}M")
    if rnpv.monte_carlo_p50_usd_m:
        print(f"Monte Carlo p25 / p50 / p75: ${rnpv.monte_carlo_p25_usd_m:,.1f}M / ${rnpv.monte_carlo_p50_usd_m:,.1f}M / ${rnpv.monte_carlo_p75_usd_m:,.1f}M  ({rnpv.monte_carlo_paths:,} paths)")
    if rnpv.downside_failed_p3_usd_m is not None:
        print(f"Downside (failed P3): ${rnpv.downside_failed_p3_usd_m:,.1f}M")
    print()

    write_public_json(outputs, dry_run=args.dry_run)
    log_to_calibration(outputs, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
