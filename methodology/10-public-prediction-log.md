# Public prediction log

The Calibration Dashboard ([`08-calibration-dashboard.md`](08-calibration-dashboard.md))
ships the *infrastructure* for tracking framework predictions against
realized outcomes — a SQLite-backed log per the Archon-pattern
`log_prediction` / `resolve_prediction` / `get_calibration_report`
trio. The dashboard's seed cohort (8 predictions) is enough to render
the Brier-score machinery but not enough to support a calibration
claim. v1.6 closes the credibility loop by publishing every
prediction the framework makes on a public asset as a committed JSON
file under [`predictions/`](../predictions/).

This is the discipline that converts the calibration claim from
"trust us, we have a SQLite log" to "here is every prediction we
have ever made, with git history showing when each one was made and
when it was resolved."

## What's in the public log

Each file in `predictions/` represents one prediction:

```
predictions/<YYYY-MM-DD>-<asset-slug>-<prediction-id-slug>.json
```

The prediction-id segment ensures uniqueness when two predictions
share a (date, asset) pair — see the schema discussion below.

Schema:

```json
{
  "prediction_id": "<stable text id assigned at log_prediction time>",
  "asset": {
    "name": "...",
    "phase": "...",
    "therapeutic_area": "...",
    "modality": "...",
    "capital_position": "..."
  },
  "framework": {
    "predicted_pos": 0.161,
    "reflexivity_multiplier": 1.0
  },
  "prediction_date": "YYYY-MM-DD",
  "resolution": {
    "outcome": 1 | 0 | null,
    "date": "YYYY-MM-DD" | null,
    "source": "<verbatim citation of the resolving event>"
  },
  "schema_version": "1.0"
}
```

The schema is intentionally minimal. The framework's *internal* state
for a prediction can be much richer (full PoS waterfall, rNPV
sensitivities, scorecard pillars, agent outputs). The public log
captures the load-bearing information for a calibration claim — the
prediction itself, when it was made, and what happened. Anything else
the diligence reader needs is reconstructible from the methodology
writeups and the asset's name.

The `prediction_id` is a stable text identifier assigned when the
prediction is first logged (UUID for runtime predictions; descriptive
slug like `seed-adagrasib-2022-06` for the v1.6 seed cohort). It exists
to give the file a unique, citable handle independent of the asset name
and date — needed because two predictions on the same asset on the same
day are otherwise indistinguishable in the public log (a common case
during a parameter sweep or methodology revision).

## How the log is maintained

The flow is:

1. **The framework runs.** A diligence record is computed; the PoS
   engine logs the prediction to SQLite via the calibration
   module's `log_prediction` route.
2. **A sync script publishes the row.**
   `python api/scripts/sync_predictions_to_public_log.py` reads the
   SQLite log and writes one JSON file per row to `predictions/`.
   The script is idempotent — re-running produces the same files
   modulo new predictions and resolutions.
3. **The JSON is committed.** When the analyst commits the
   diligence work, the new `predictions/<date>-<slug>.json` is
   committed alongside it. The git history of that file is the
   audit trail.
4. **The prediction resolves.** When the FDA action, M&A, or
   discontinuation happens, the analyst marks the outcome via the
   `resolve_prediction` route, re-runs the sync script, and commits
   the updated JSON. The diff shows when each resolution happened.

The script is tested ([`api/tests/test_public_prediction_log.py`](../api/tests/test_public_prediction_log.py))
for the contract that's load-bearing: one file per row, idempotency,
the documented schema. CI ensures the sync stays consistent with the
calibration module.

## What this answers that the SQLite log alone could not

The SQLite log lives inside the running API container. It is
inaccessible to anyone who doesn't have shell on the deploy. A
calibration claim grounded in a private log is unfalsifiable; the
methodology platform owner could be silently updating predictions
after the fact to make the Brier score look better.

The public JSON files are the opposite. Every prediction is in a
git commit. The commit history of `predictions/2022-06-01-adagrasib.json`
shows: when the prediction was made (the file's creation commit),
when it was resolved (the subsequent commit that filled in
`resolution.outcome`), and any changes in between. A skeptic can
inspect every cell.

This is the same move the [open-source-paper](https://github.com/futianfan/clinical-trial-outcome-prediction)
community makes with public datasets and test splits — separate the
*claim* from the *opportunity to revise the claim after seeing the
outcome*. The framework's calibration claim becomes externally
auditable rather than internally tracked.

## What's in the public log today

The seed cohort of 8 predictions described in the [Calibration
Dashboard writeup](08-calibration-dashboard.md) is now present in the
public log:

- 5 approved kinase inhibitors (adagrasib, sotorasib, selpercatinib,
  larotrectinib, encorafenib) — retrospective backtest entries
- 2 documented failures (sintilimab US registration; debio 1347
  FGFR program discontinuation)
- 1 unresolved (tisotumab vedotin combination arm GOG-3023)

All seeded as retrospective backtests of the framework. The
honest read is that this cohort is survivorship-biased toward known
approvals — the calibration claim cannot rest on it. What this v1.6
release ships is the *discipline*: every future prediction the
framework makes is expected to land in `predictions/` and become
publicly auditable. Quarterly forward predictions on public
catalysts (FDA PDUFA dates, planned readouts) will accumulate the
unbiased sample over time.

## The maintenance cadence

The [README.md's Maintenance section](../README.md#maintenance-cadence)
already covers BIO base-rate refreshes, Damodaran WACC updates, and
methodology sweeps. v1.6 adds one more cadence:

| Trigger | Effort |
|---|---|
| Framework run on a public asset (new diligence) | 1 min — log_prediction, then sync_predictions_to_public_log.py + commit |
| Public catalyst lands (FDA action, M&A, readout) | 5 min — resolve_prediction with the source citation, sync + commit |
| Quarterly: scan resolved-but-unlogged outcomes | 30 min — backfill known resolutions, sync + commit |

The point of putting this on a cadence is to make the framework's
predictions a recurring artifact rather than a one-time portfolio
piece. The maintained-tool framing the project commits to
elsewhere ([`00-product-thesis.md`](00-product-thesis.md)
Trajectory B) requires this kind of cadence to be real, not
aspirational.

## Cross-references

- [`08-calibration-dashboard.md`](08-calibration-dashboard.md) — the
  Brier-score machinery this log feeds.
- [`02-reflexivity-thesis.md`](02-reflexivity-thesis.md) — the
  framework's headline claim that this log ultimately tests against
  realized capital-position-stratified outcomes.
- [`00-product-thesis.md`](00-product-thesis.md) — the
  productization-of-methodology argument that requires public
  auditability to credibly support Trajectory B.
- [`../predictions/`](../predictions/) — the live log itself.
