# v1.6 — Divarasib: the first live forward prediction

The [adagrasib worked example](05-worked-example-adagrasib.md) is a
**retrospective backtest**: the framework was run with a June-2022
information cutoff to reconstruct what an analyst should have concluded
*before* BMS's $4.8B acquisition. That's a calibration exercise, not a
prediction — the outcome was already known when the writeup was drafted.

The Asclepius public log has eight other entries
([`predictions/`](../predictions/)), all also retrospective seeds.
**Divarasib (NCT06497556) is the first forward prediction.** The
framework's output is locked in today and the public catalyst is dated
**2027-09-30**; the prediction will resolve when Roche reports the
Phase 3 primary analysis. Both numbers are committed to the public
repository before any outcome is known.

This is the discipline that converts the framework from "interesting
methodology" to "auditable forecasting tool."

## Why divarasib

Selection criteria, applied today (2026-06-03):

1. **Pre-readout** with a public, dated catalyst inside a portfolio-
   review window.
2. **In the model's training distribution** so the prediction isn't
   extrapolating outside HINT+CTO coverage.
3. **Sponsor-public**, so anyone can replicate the inputs.
4. **Comparators in our worked-example cohort** — narrative continuity.
5. **Phase 2 or Phase 3** — Phase 1 is too early to score; approved is
   too late to be a "prediction."

Divarasib clears all five:

| Criterion | Divarasib |
|---|---|
| Pre-readout | ✓ NCT06497556 active, **enrollment complete** (ACTUAL n=338) but primary readout 2027-Q3 |
| In distribution | ✓ Sotorasib (KRAS G12C, FDA 2021) is in HINT training; adagrasib (KRAS G12C, FDA 2022) is in the model's competitive cohort |
| Sponsor-public | ✓ Hoffmann-La Roche, $50B+ annual revenue, $250B+ market cap |
| Comparator continuity | ✓ Active-comparator arm is **sotorasib OR adagrasib** — the two FDA-approved drugs from the [adagrasib worked example](05-worked-example-adagrasib.md) |
| Phase | ✓ Phase 3, randomized, PFS primary endpoint |

The asset's narrative completes the framework's arc: the retrospective
exercise asked "would Asclepius have called the 2022 BMS-Mirati deal
range correctly?" — the forward exercise asks "what will Asclepius
predict about the *next* KRAS G12C inhibitor, the one that hasn't
been approved or acquired yet?"

## The asset

All inputs from public sources, cited inline. The full framework
run + JSON record is at
[`predictions/2026-06-03-divarasib-divarasib_nct06497556_2026_06.json`](../predictions/2026-06-03-divarasib-divarasib_nct06497556_2026_06.json).
The script that produced it is
[`scripts/log_divarasib_prediction.py`](../scripts/log_divarasib_prediction.py).

| Field | Value | Source |
|---|---|---|
| Asset name | divarasib | Roche / Genentech public filings; INN |
| Sponsor | Hoffmann-La Roche | NCT06497556 lead sponsor |
| Phase | Phase 3 | NCT06497556 designModule.phases |
| Therapeutic area | Oncology | NCT06497556 conditionsModule |
| Modality | small_molecule | KRAS G12C selective covalent inhibitor; same modality class as sotorasib, adagrasib |
| Capital position | well_capitalized | Roche 2025 cash >$15B, no near-term raise pressure, top-3 global pharma. The maximum-confidence reflexivity tier; the multi-decade signal-credibility argument from [`methodology/06-signaling-equilibrium.md`](06-signaling-equilibrium.md) applies in full. |
| Mechanism | KRAS G12C inhibitor (covalent, second-generation) | Sacher et al., Lancet Oncology Dec 2023: divarasib monotherapy Phase 1/2 NSCLC ORR 56%, mPFS 13.1mo (vs sotorasib 36%/6.8mo, adagrasib 42%/6.5mo from their respective registration trials) |
| Target | KRAS G12C | NCT06497556 eligibility |
| Indication | Previously treated KRAS G12C+ advanced/metastatic NSCLC | NCT06497556 eligibility ("at least one prior systemic therapy but no more than three lines") |
| Biomarker enrichment | True | "Documentation of the presence of a KRAS G12C mutation" — explicit inclusion |
| Target validated | True | Sotorasib (Lumakras) FDA 2021; adagrasib (Krazati) FDA 2022 — two prior FDA approvals against the same target in the same indication. The strongest possible "target validated" evidence. |
| Number of competitors | 3 | sotorasib (approved), adagrasib (approved), olomorasib (Lilly Ph2). Other earlier-stage entrants (glecirasib, BBP-454, etc.) excluded — competitive density count uses near-term commercialization risk, not all-stage pipeline. |
| Regulatory designations | (none recorded) | Divarasib has not received a public BTD/Fast Track/Orphan designation as of 2026-06-03. Conservative: leave empty. |
| NCT ID | NCT06497556 | https://clinicaltrials.gov/study/NCT06497556 |
| Trial design | Phase 3, randomized, open-label, head-to-head | NCT06497556 designModule |
| Enrollment | 338 (ACTUAL) | NCT06497556 enrollmentInfo. **Enrollment is complete** — meaningful for the prediction because trial-accrual-failure risk (the Ma 2025 mechanism cited in [/02](02-reflexivity-thesis.md)) is already past. |
| Primary endpoint | PFS | NCT06497556 outcomesModule.primaryOutcomes |
| Primary completion (estimated) | 2027-09-30 | NCT06497556 statusModule |

## The framework's prediction

Running the v1.5.9 calibrated framework on these inputs, today
(2026-06-03):

**PoS — rule chain:**
- BIO 2021 Phase 3 oncology base rate: **44.2%**
- × 1.000 (small_molecule reference modality)
- × 1.20  (biomarker enrichment)
- × 1.15  (target validated — two FDA-approved KRAS G12C inhibitors)
- × 0.90  (3 direct competitors)
- × 1.08  (reflexivity: well_capitalized)
- = **Final LOA: 59.3%** [95% CI 54.8% — 63.4%]

**rNPV** (assuming $700M peak sales, 12yr exclusivity, 10% WACC, 20% COGS):
- Base case: **$948M**
- Low / high: $637M / $1,337M
- Monte Carlo P25 / P50 / P75 (10K paths): **$637M / $935M / $1,337M**
- Downside (P3 failure terminal value): −$178M

The PoS number sits cleanly above the BIO 44% base rate, driven by the
two strongest signals in the chain — target validation (×1.15, since
two FDA-approved drugs exist against the same target) and biomarker
enrichment (×1.20, since KRAS G12C is an inclusion criterion). The
reflexivity uplift is modest (×1.08), capped by the framework — the
prediction isn't a Roche-faith bet; it's a mechanism-validity bet.

## What "outcome = 1" means precisely

Pre-registered resolution criteria (committed in the public JSON):

- **outcome = 1** if Roche reports a statistically significant PFS
  benefit (or pre-specified non-inferiority threshold met) on the
  primary analysis at PCD or via a pre-specified interim, AND a
  regulatory submission follows within 12 months of the readout.
- **outcome = 0** if the trial misses its primary endpoint or is
  terminated for futility/safety.
- **outcome = 0.5** for ambiguous cases (significant PFS but no
  submission within the 12-month window, mixed primary/secondary
  signals, ROW-only approvals without FDA/EMA paths, etc.). Treated
  as a half-Brier penalty in the calibration accounting.

The "submission within 12 months" component is deliberate: a
statistically significant PFS that Roche chooses *not* to file on
(commercial-strategy decision) is not a clinical-development
success in the framework's intended sense. Capital is the binding
constraint we're tracking, and a sponsor that wins the trial but
withdraws the asset is functionally indistinguishable, in
PoS-arithmetic terms, from a sponsor that lost the trial.

## What would surprise us in either direction

The framework's 59% LOA is committed. The interesting cases are
the deviations we'd update on:

**Surprise (outcome = 0):**
- Divarasib's Phase 1/2 data (ORR 56%, mPFS 13.1mo) was on a
  selected, smaller cohort. The Phase 3 head-to-head might show
  the differentiation collapsing — sotorasib/adagrasib could pull
  closer in a 338-patient randomized setting than in cross-trial
  comparisons. *If divarasib reads out non-significant on PFS,
  it's evidence the cross-trial monotherapy advantage was
  cohort artifact.*
- KRAS G12C tumors that progress on sotorasib/adagrasib may
  carry resistance mutations divarasib also can't overcome.
  *A null result would also be evidence for class-wide resistance
  in the second-line+ setting.*

**Surprise (outcome = 1 with much larger effect):**
- The Lancet Oncology Dec 2023 PFS gap (13.1mo vs 6.5-6.8mo) is
  ~2× the comparator. If that holds in randomized Phase 3, it's
  the largest within-class differentiation in this drug class.
  *A strongly positive readout would re-anchor the rNPV closer
  to the high case ($1.3B) and make divarasib the new
  standard-of-care in 2L+ KRAS G12C NSCLC — a much larger
  commercial outcome than the framework's central case suggests.*

**Surprise that doesn't change the call:**
- A modestly positive readout (non-significant but trending,
  or NI-margin scrape) would be intermediate — outcome = 0 for
  the binary prediction but rNPV-realistic for the asset value.
  This is the "framework was directionally right but the magnitude
  underwhelmed" zone.

## Calibration tie-in

This prediction joins the public log alongside the eight retrospective
seeds. Once resolved, it contributes one row to the Phase-3 Brier
score in the [Calibration Dashboard](08-calibration-dashboard.md). A
59.3% prediction that resolves outcome = 1 contributes a Brier of
~0.17; resolving outcome = 0 contributes ~0.35. The asymmetry is
deliberate — high-confidence predictions get more credit for being
right and bigger penalties for being wrong.

## Reading order for context

- [`05-worked-example-adagrasib.md`](05-worked-example-adagrasib.md) —
  the retrospective backtest this forward prediction mirrors
- [`02-reflexivity-thesis.md`](02-reflexivity-thesis.md) — why
  well-capitalized sponsorship matters (the ×1.08 in the chain)
- [`06-signaling-equilibrium.md`](06-signaling-equilibrium.md) — the
  formal game-theoretic argument behind reflexivity
- [`10-public-prediction-log.md`](10-public-prediction-log.md) — the
  log's design + the resolve_prediction workflow this prediction
  will eventually go through
- [`14-phase-stratified-retrain.md`](14-phase-stratified-retrain.md) —
  the diagnostic caveat about standalone Phase calls; this prediction
  benefits from being a Phase 3 (the strongest within-phase
  AUC band in our analysis)

## Sources

- [NCT06497556 on ClinicalTrials.gov](https://clinicaltrials.gov/study/NCT06497556) — full protocol, fetched 2026-06-03
- [Sacher AG, et al. Lancet Oncology (Dec 2023)](https://www.thelancet.com/journals/lanonc/article/PIIS1470-2045%2823%2900548-1/abstract) — divarasib Phase 1/2 NSCLC monotherapy data
- [FDA approval of sotorasib (Lumakras), May 2021](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-grants-accelerated-approval-sotorasib-kras-g12c-mutated-nsclc)
- [FDA approval of adagrasib (Krazati), Dec 2022](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-grants-accelerated-approval-adagrasib-kras-g12c-mutated-nsclc)
- [BIO/Informa 2021 Clinical Development Success Rates 2011-2020](https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf)
