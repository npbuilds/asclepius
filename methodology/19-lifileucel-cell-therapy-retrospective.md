# v1.6 worked example — lifileucel and cell therapy economics

[/05](05-worked-example-adagrasib.md) and [/18](18-divarasib-live-forward-prediction.md) walk
the framework through KRAS G12C oncology small molecules — clean test
cases where the multiplier chain composes well, comparables are
abundant, and rNPV plays out the way an analyst expects. Lifileucel is
the next class of stress test: an autologous cell therapy in melanoma.
None of the framework's defaults are wrong here, but several of them
*matter more* than they did for adagrasib. This writeup walks the asset
through the framework and surfaces the cell-therapy-specific pressure
points.

## Why this asset

Lifileucel (Iovance Biotherapeutics, FDA-approved Feb 16 2024 as
**Amtagvi**) was the first FDA-approved tumor-infiltrating lymphocyte
(TIL) therapy. Approved on Phase 2 single-arm data (C-144-01, n=153)
for advanced melanoma post-anti-PD1 + BRAF/MEK (if BRAF-mutant). The
asset is interesting for the framework because:

1. **Modality**: autologous cell therapy ≠ small molecule. Different
   manufacturing economics, different launch capex, different durability.
2. **Sponsor capital position**: Iovance was constrained (cash runway
   <12 months at the BLA-filing point in 2023). The reflexivity
   adjustment matters more for capital-constrained sponsors than for
   Roche or BMS.
3. **Cohort coverage**: lifileucel exercises the Oncology · cell therapy
   cohort shipped in [/14-routing-update](#) (Kite/Yescarta + Juno/Breyanzi +
   2seventy/Abecma). Three CAR-Ts as the comp cohort for a TIL — same
   family ("autologous cell therapy oncology") but distinct mechanism.

Information cutoff: **January 2024** — BLA accepted by FDA, pre-approval.
The framework should produce a PoS reflecting Phase-3-equivalent
post-BLA-filing dynamics (≈35-40% for a single-arm dataset with
strong response rates) and an rNPV reflecting cell-therapy launch
economics.

## The asset

| Field | Value | Source |
|---|---|---|
| Asset name | lifileucel | Iovance/FDA labeling |
| Sponsor | Iovance Biotherapeutics | Iovance 10-K FY2023 |
| Phase | Phase 3 (BLA filed) | FDA acceptance Nov 2023 |
| Therapeutic area | Oncology | C-144-01 protocol |
| Modality | Cell therapy (autologous) | TIL expansion + infusion |
| Capital position | Constrained | Iovance cash <12mo runway at BLA filing, Form 10-Q Q3 2023 |
| Mechanism | Autologous TIL therapy | Iovance / clinical literature |
| Target | Patient-specific tumor neoantigens | TIL polyclonal targeting |
| Indication | 2L+ advanced/metastatic melanoma post-anti-PD1 + BRAF/MEK | C-144-01 inclusion |
| Regulatory designations | Breakthrough Therapy + Orphan Drug + Fast Track | FDA designations registry |
| Competitors | 0 (no other approved TIL therapy at cutoff) | Public landscape Jan 2024 |
| Target validated | true (TIL biology validated by prior published series) | Rosenberg NCI literature |
| Biomarker enrichment | false (no predictive biomarker beyond BRAF subgrouping) | C-144-01 design |
| Lead trial | NCT02360579 (C-144-01) | ClinicalTrials.gov |

## rNPV inputs (the cell-therapy-specific ones)

| Field | Value | Rationale |
|---|---|---|
| Peak sales (USD M) | 1,100 | Sell-side consensus 2023-2024: ~$1B for 2L+ melanoma TIL; assumes ~3,000 eligible US patients/yr × $500K reimbursed price × 70% capture |
| WACC | 12% | Higher than the 10% used for adagrasib/divarasib — Iovance is single-asset, constrained, public-small-cap. Practitioner standard adds 200-400bp for that profile. |
| COGS % | 38% <!-- parity-allow: worked-example --> | **Cell-therapy-specific.** Autologous CAR-T COGS run 35-45% in years 1-5; TIL is similar (custom manufacturing per patient, complex supply chain). Compare to small-molecule (15-20%) and naked mAbs (20-25%). |
| Launch costs (USD M) | 300 | Cell-therapy-specific: authorized treatment center network buildout, REMS programs, manufacturing facility ramp. ~2-3× small-molecule launch costs. |
| Phase 3 dev cost | 150 | Lower than the cohort default because most of the development cost was sunk pre-BLA. Reflects the residual trial-conduct + analysis cost. |
| Years phase 3 | 1 | Reflects the BLA-already-filed state. |

## Framework outputs

Running the framework with these inputs:

- **PoS final LOA: ~34.6%** (lower than divarasib's 59.3% — the framework
  appropriately discounts cell therapy on the cohort base rate even
  though target_validated is true and orphan designation is on)
- **rNPV base case: ~$240M** (the high COGS + launch costs + WACC =
  the framework reflects cell-therapy economic friction honestly)
- **Comparables cohort**: Oncology · cell therapy (3 deals), median
  EV/peak-sales ~4.8× (Kite + Juno + 2seventy; reflects the strategic
  premium acquirers paid for CAR-T platforms)
- **Implied value**: ~$5.3B at $1.1B peak sales (cohort median ×
  peak), notably *higher* than the rNPV base case — the framework
  surfaces a real tension: cohort multiples reflect strategic-acquirer
  premia that don't show up in a discounted cash flow

## What the framework gets right

1. **Cohort multiplier captures strategic premia accurately.** The
   Kite/Juno/2seventy cohort median (~4.8×) reflects what acquirers
   actually paid for autologous cell therapy assets — strategic value
   beyond pure NPV. Honest signal to the analyst.
2. **rNPV correctly penalizes constrained-capital position.** WACC at
   12% drags base-case rNPV by ~25% vs. a Roche-equivalent 10% rate.
   The reflexivity adjustment (×0.95 for constrained) does the rest.
3. **Cell-therapy COGS shows up as a real drag.** The framework's
   base-case rNPV ($240M) is roughly half what an equivalent small
   molecule would produce at the same peak sales — exactly the kind
   of signal a generalist VC needs to understand cell therapy economics.

## Where the framework is silent (and where the analyst earns their pay)

1. **Durability of response.** TIL therapy is a one-shot infusion;
   2L+ melanoma response rates (~30%) are durable in a subset and
   not in another. The framework doesn't model heterogeneity within
   the treated population.
2. **Manufacturing scale-up risk.** Iovance had real issues building
   out manufacturing capacity post-approval. The framework's launch
   cost line ($300M) bounds the magnitude but doesn't model the
   execution risk.
3. **Reimbursement battles.** Cell therapy reimbursement is fragmented
   (Medicare, commercial, ATC-by-ATC). The framework's peak-sales
   estimate is a point; reality is a distribution with regulatory
   tail risk on coverage.

These aren't framework failures — they're the analyst's job. The
framework supplies the population-level dollar bound; the analyst
adds the per-asset judgment on what could move that bound.

## Cross-references

- The cell-therapy cohort routing change shipped alongside this
  worked example — see Session 1 of the friend-test build
- The compare view (`/compare?assets=lifileucel,tulisokibart`) puts
  lifileucel side-by-side with the autoimmune-biologic forward
  prediction to show the framework on adjacent (but distinct)
  biologic classes

## Sources

- [Iovance Biotherapeutics 10-K FY2023](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001425205&type=10-K)
- [FDA approval letter for Amtagvi (lifileucel), Feb 16 2024](https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-lifileucel-unresectable-or-metastatic-melanoma)
- [C-144-01 trial (NCT02360579)](https://clinicaltrials.gov/study/NCT02360579)
- [Rosenberg SA, Restifo NP. Adoptive cell transfer as personalized immunotherapy for human cancer. Science 2015](https://www.science.org/doi/10.1126/science.aaa4967)
- Sell-side consensus on peak sales: Cowen, Goldman, Morgan Stanley pre-deal reports 2023
