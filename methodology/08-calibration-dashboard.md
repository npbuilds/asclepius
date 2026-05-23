# Calibration Dashboard

The framework makes predictions. The Calibration Dashboard logs them and
scores the framework against observed outcomes. It is the only mechanism
that converts the methodology from "opinionated guess" to "evidence-
tracked claim" — and it is the only honest answer to the question every
biotech VC eventually asks: *how do we know your model is calibrated?*

## What ships in v1.5

A new analysis module at `api/app/modules/calibration/`. Pluggable via
the existing registry — no edits to the core. Surfaces:

- `POST /api/modules/calibration` — segment-level stats for the asset on
  the diligence page.
- `POST /api/modules/calibration/log_prediction` — append a prediction
  to the SQLite-backed log.
- `POST /api/modules/calibration/resolve_prediction` — mark a logged
  prediction as approved (1) or failed (0).
- `GET /api/modules/calibration/report` — aggregate Brier scores by
  therapeutic area, modality, and capital-position tier.
- `GET /api/modules/calibration/predictions` — the full log table.

A frontend panel renders below the four core analysis modules and shows:
the current asset's segment stats, the framework's overall calibration,
a per-capital-position breakdown (the row the reflexivity adjustment
hinges on), and a sample-size disclaimer that names the survivorship-
bias problem directly.

## The Brier score, in one paragraph

The Brier score is the mean squared error between a predicted probability
and the observed outcome (0 or 1). For a single prediction it is
$(p - o)^2$. For a cohort it is the average across resolved predictions.
**Zero is perfect; 0.25 is the benchmark for an uninformative coin-flip
classifier; higher scores indicate systematic over- or under-prediction.**
The Brier score decomposes cleanly into a reliability term (calibration)
and a resolution term (discrimination), but for v1.5 we report the
aggregate and the mean-predicted-vs-mean-observed gap, which is the
operationally useful split for an investor.

## What the v1.5 seed cohort tells you

The seed log carries eight predictions across the framework's modality /
capital-position grid. Five are FDA-approved kinase inhibitors used as
the comparables cohort in the worked example (adagrasib, sotorasib,
selpercatinib, larotrectinib, encorafenib). Two are documented Phase 2
or Phase 3 failures (sintilimab US registration and Debiopharm's debio
1347 FGFR program). One is unresolved (tisotumab vedotin combination
arm) and demonstrates the dashboard's pending-state surface.

Run the framework against this seed and the dashboard tells you:

1. **The overall Brier score is high (~0.54)**. Not because the
   methodology is broken — because the seed sample is survivorship-
   biased toward known approvals. Mean predicted PoS is ~17%; observed
   approval rate is ~71%. The framework systematically under-predicts
   in *this* cohort because the cohort was selected by recognizing
   the survivors after the fact.

2. **The constrained-capital row Brier is excellent (0.008)**. One
   prediction (debio 1347; predicted 8.9% LOA, outcome 0). The
   reflexivity discount correctly captured the failure direction.
   N=1 means this is anecdotal, but directionally encouraging.

3. **The well-capitalized row Brier is the worst (0.72)**. Three
   predictions (sotorasib, selpercatinib, larotrectinib), all
   approved. The current reflexivity uplift (×1.08) is much smaller
   than what this cohort would suggest (×~5). This is precisely the
   kind of question a calibration dashboard is supposed to surface
   — but at n=3, drawing any conclusion would be premature. The
   selection mechanism (we picked famous approved kinase inhibitors)
   dominates the signal.

This is what an honest calibration dashboard looks like in its first
quarter: visible discipline, immediately educational about its own
limitations, with the path to a meaningful claim explicit. The
dashboard is shipping the *infrastructure*; the calibrated claim
accumulates over time as the framework is run on prospective assets
whose outcomes are not yet known.

## What's needed for the calibration claim to mean something

Two conditions, both achievable through the maintained-tool posture
(see [`README.md`](../README.md) and [`00-product-thesis.md`](00-product-thesis.md)
on Trajectory B):

**Unbiased prospective sampling.** The seed cohort is biased because the
analyst chose it knowing the outcomes. The way to fix this is to log
*every* asset the framework is applied to, regardless of whether you
ever publish a memo on it. The diligence page hits the engine; the
engine writes to the log; once the asset's readout happens (FDA action,
acquisition, discontinuation), the resolver script marks the outcome.
After roughly 30-50 prospective predictions, the Brier score becomes
attributable to the methodology rather than to the sampling.

**Time horizon discipline.** Most Phase 2 → approval cycles are 3-7
years. A meaningful Brier score therefore requires either (a) waiting
years for the prospective sample to resolve, or (b) including
intermediate phase-transition outcomes (Phase 2 → Phase 3 transition
within 24 months is a resolvable proxy). The dashboard's schema
supports both — `outcome` can capture any pre-specified resolution
criterion as long as the prediction was logged with that criterion
in mind.

## How the dashboard relates to the reflexivity claim

The framework's headline differentiator is the reflexivity adjustment —
the claim that sponsor capital position is a structural modifier on
PoS. Either that claim survives empirical contact with the data, or
it doesn't. The dashboard's per-capital-position row is where this is
ultimately tested. The Brier score for the well-capitalized tier
versus the constrained tier is the empirical specification of the
reflexivity argument.

Today (n=3 vs n=1), the dashboard cannot adjudicate the claim. In two
to three years of disciplined prospective logging, it will.

## The Archon-pattern origin

The dashboard's architectural pattern (log_prediction /
resolve_prediction / get_calibration_report) is ported from the
[Archon](https://github.com/) investing skill suite's calibration
mechanism, where the same pattern tracks macro and equity predictions
against realized outcomes. Asclepius's implementation is self-contained
— a single SQLite file in `api/app/data/calibration.db`, no MCP, no
external service — so the dashboard ships with the deploy. The seed
JSON is committed; the DB derives from it on first boot.

This is the second-instance proof of the [productization-of-methodology
thesis in 00-product-thesis.md](00-product-thesis.md): the same pattern
that tracks Archon's macro predictions also tracks Asclepius's PoS
predictions, because both are methodology-platforms that need to be
calibrated to remain credible.

## What's deliberately deferred to v1.6+

- **ML-PoS Prior as a second-opinion path.** v1.5.1 ships a rule-
  smoothed logistic surrogate at [`09-ml-pos-prior.md`](09-ml-pos-prior.md);
  the BioBERT-on-protocol-text path with real outcome labels is v1.5.2.
- **Public prediction log.** ✓ Shipped in v1.6 —
  [`10-public-prediction-log.md`](10-public-prediction-log.md). Every
  prediction the framework makes on a public asset lives as a committed
  JSON file in [`predictions/`](../predictions/), so the calibration
  claim becomes externally auditable rather than internally tracked.
- **Brier decomposition by phase.** A Phase 2 prediction's Brier is not
  comparable to an NDA prediction's Brier. v1.6 stratifies the
  dashboard.
- **Mendelson decomposition.** Splitting Brier into reliability and
  resolution components surfaces whether the framework's errors are
  systematic (calibration) or random (discrimination). v1.7+.

## See also

- [`02-reflexivity-thesis.md`](02-reflexivity-thesis.md) — the claim
  this dashboard ultimately tests.
- [`05-worked-example-adagrasib.md`](05-worked-example-adagrasib.md) —
  the first row in the prediction log.
- [`00-product-thesis.md`](00-product-thesis.md) — the
  productization-of-methodology argument the dashboard makes concrete.
