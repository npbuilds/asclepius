---
title: "Probability of Success — the full framework reference"
summary: "The end-to-end documentation of how Asclepius computes cumulative likelihood of approval. Every multiplier in the chain is cited; every magnitude is grounded in either a peer-reviewed paper or a primary industry source; deviations from the published literature are explicit."
audience: "This is the reference doc. Read it first if you want to understand exactly what the framework computes. Read 02-reflexivity-thesis and 06-signaling-equilibrium for the deeper argument behind the headline reflexivity adjustment."
primary_sources:
  - "Biotechnology Innovation Organization, Informa Pharma Intelligence, QLS Advisors. Clinical Development Success Rates 2011-2020 (2021). The phase-transition base rates by therapeutic area."
  - "Wong CH, Siah KW, Lo AW. Estimation of clinical trial success rates and related parameters. Biostatistics 20(2): 273-286 (2019). The methodology paper that established modern PoS estimation; provides the disaggregation by trial-design features the framework's modifiers reference."
  - "Williamson J, et al. Economic and developmental impacts of FDA designations: a systematic review and meta-analysis. Expert Review of Pharmacoeconomics & Outcomes Research (2025). Pooled meta-analysis across 25 studies of BTD, FTD, ODD, RMAT designations."
  - "Hwang TJ, et al. Efficacy, Safety, and Regulatory Approval of FDA-Designated Breakthrough and Nonbreakthrough Cancer Medicines. Journal of Clinical Oncology (2018). Direct comparison of BTD vs non-BTD oncology drugs 2012-2017."
  - "Mao X, et al. Therapeutic value and regulatory characteristics of breakthrough therapy drugs in the USA and China (2021-2023). Drug Discovery Today (2025). Adversarial-check evidence on BTD's relationship to clinical benefit."
  - "Cannarile M, et al. Facts and hopes on biomarkers for successful early clinical immunotherapy trials. Clinical Cancer Research (2023). Modern review of patient-enrichment strategies in oncology drug development."
---

# Probability of Success — the full framework reference

## What this document is

The Asclepius PoS calculation is a multiplicative chain. The framework starts from a peer-reviewed population base rate, applies five categories of asset-specific modifiers, and produces a cumulative likelihood of approval with an explicit audit trail. Every multiplier is cited. This document is the reference for what each multiplier is, where its magnitude comes from, and what the framework does *not* claim.

If you want the deeper argument behind the headline modifier — the reflexivity adjustment — read [02-reflexivity-thesis.md](02-reflexivity-thesis.md) and [06-signaling-equilibrium.md](06-signaling-equilibrium.md). This document treats reflexivity as one row in the chain; those documents explain why it is the most important row.

## The chain

```
Final LOA = Base rate (BIO/Informa cohort)
          × Modality multiplier
          × (1 + biomarker enrichment boost)
          × (1 + target-validation boost)
          × (1 + competitive-density penalty)
          × (1 + regulatory-designation boosts)
          × Reflexivity multiplier (capital position)
```

The chain is strictly multiplicative. Adjustments are applied in the order shown above, which is also the order they appear in the audit trail rendered by the dashboard. Order does not affect the final number (multiplication is commutative), but the order shown is the order in which a reader naturally argues the chain: *"the population says X, the technology adjusts it to Y, what we know about this asset specifically modifies it to Z, regulatory designations add W, and the sponsor's situation produces the final value V."*

Final LOA is clamped to [0.0, 1.0]; in practice the framework's outputs are bounded well below 1.0 by the base rates themselves.

## Base rate — BIO/Informa cohort

The starting point of every PoS calculation is the cumulative likelihood-of-approval from the current phase to FDA approval, broken down by therapeutic area. The framework loads these from [api/app/data/base_rates.json](../api/app/data/base_rates.json), which in turn cites the [Biotechnology Innovation Organization's 2021 Clinical Development Success Rates report](https://go.bio.org/rs/490-EHZ-999/images/ClinicalDevelopmentSuccessRates2011_2020.pdf). The methodology is described in detail in [Wong, Siah, Lo (2019)](https://academic.oup.com/biostatistics/article/20/2/273/4817524).

Selected cumulative LOA from Phase 1 by therapeutic area:

| Therapeutic area | LOA from Phase 1 | P1→P2 | P2→P3 | P3→NDA | NDA→Approval |
|---|---:|---:|---:|---:|---:|
| All indications | 7.9% | 52% | 29% | 58% | 88% |
| Oncology | 4.7% | 45% | 24% | 52% | 85% |
| Rare/orphan | 16.3% | 65% | 42% | 65% | 92% |
| CNS | 4.1% | 48% | 20% | 50% | 85% |
| Hematology | 15.7% | 66% | 40% | 65% | 92% |
| Ophthalmology | 16.6% | 86% | 36% | 59% | 91% |

Values from Phase 2 onward are computed as the product of remaining transition probabilities (e.g., Phase 2 oncology = 0.24 × 0.52 × 0.85 = 10.6%).

### A note on the BIO cohort

The BIO 2021 report covers 2011-2020. Its successor cohort (BIO 2024 covering 2014-2023) is expected to refine some category values. The framework's [maintenance cadence](../README.md) anticipates refreshing the JSON when BIO publishes the next cohort; the values above will shift modestly, the chain structure will not.

The base rates have known limitations that the framework inherits:
- Therapeutic-area buckets are coarse. "Oncology" averages across solid tumors, hematologic malignancies, and immuno-oncology, which have materially different historical success rates.
- The cohort under-represents the most recent modalities (gene therapy, cell therapy, mRNA) because they have fewer approvals to estimate from. Modality multipliers below partially compensate.
- The cohort over-represents large-pharma trials. Small-biotech-sponsored programs are not separately analyzed.

## Modality multiplier

Different drug modalities have systematically different attrition profiles, observable in the BIO sub-analyses and in modality-specific reviews. The framework applies a multiplicative adjustment to the base rate per modality, loaded from [api/app/data/modality_multipliers.json](../api/app/data/modality_multipliers.json).

| Modality | Multiplier | Range | Source |
|---|---:|---|---|
| Small molecule | 1.00 | 0.95-1.05 | Reference modality (BIO cohort is small-molecule-dominant) |
| Monoclonal antibody | 1.15 | 1.10-1.20 | BIO 2021 sub-analysis — biologics LOA from P1 ~11% vs ~6% for NMEs |
| Antibody-drug conjugate | 0.85 | 0.80-0.90 | Higher CMC complexity and payload-toxicity attrition. See review in [Fu et al. 2022](https://consensus.app/papers/details/8605110184ec5d5bb066c82c31f5d36a/) (1,208 citations) |
| Gene therapy | 0.75 | 0.70-0.80 | Elevated Phase 3 attrition (durability, immunogenicity, dose-response); CMC scale-up risk |
| Cell therapy (autologous) | 0.65 | 0.60-0.70 | Per-patient manufacturing variability; complex logistics; higher commercial-stage attrition |
| Cell therapy (allogeneic) | 0.70 | 0.65-0.75 | Simplified supply chain vs autologous; persistence and immunogenicity risk |
| mRNA | 0.90 | 0.85-0.95 | Platform validated for vaccines; therapeutic mRNA still has limited Phase 3 readouts |
| Protein/recombinant | 1.10 | 1.05-1.15 | Tracks biologics with slight discount for immunogenicity risk |
| Oligonucleotide (ASO/siRNA) | 0.85 | 0.80-0.90 | Approvals exist (Spinraza, Onpattro, Leqvio) but high historical P2 attrition |
| Peptide | 1.00 | 0.95-1.05 | Behaves like small molecules; PK/PD challenges offset structural simplicity |

Two notes on the modality multipliers specifically:

**The cell-therapy multipliers are the most uncertain.** Cell therapy as a category is recent enough that the empirical base for the ×0.65 / ×0.70 multipliers is thin. The values reflect the BIO sub-analyses, the [Liu et al. 2024 cancer-treatment review](https://consensus.app/papers/details/d0f3c3f30fc05c0f98bb3547f2900a80/) (802 citations) documenting the operational challenges, and practitioner-side discussion in the biotech-investment community. As more cell-therapy assets reach Phase 3 readouts, these values should be recalibrated.

**Modality is treated as a single multiplier rather than a separate base rate.** Conceptually, a per-modality base rate would be cleaner; in practice, BIO's cohort splits are not granular enough to support per-modality cumulative LOAs by therapeutic area. The multiplicative-on-population-prior approach is a pragmatic compromise the framework is honest about.

The ranges in the table propagate into the framework's PoS confidence interval; the point estimate uses the central value.

## Mechanism modifiers

Three additive boosts capture asset-specific features that move PoS above or below the population prior.

### Biomarker enrichment — +20%

Trials that enrich the enrolled population using a predictive biomarker (e.g., HER2+ status for trastuzumab-class drugs; KRAS G12C status for adagrasib) show systematically higher probability of demonstrating effect at the powered effect size. The framework boosts running PoS by 20% (multiplier of 1.20) when the asset uses biomarker enrichment.

The magnitude is grounded in Wong, Siah, Lo (2019) §4.3 disaggregation of P2→P3 transition by trial-design features and in the modern literature on enrichment-design effectiveness. [Cannarile et al. (2023, Clinical Cancer Research)](https://consensus.app/papers/details/205e412125805f00b22971f69ec364e1/) review the immunotherapy-specific case and document that "identifying the appropriate patient population that would benefit most from the drug is on the critical path for successful clinical development." [Diao et al. (2025, J Biopharm Statistics)](https://consensus.app/papers/details/9239008bf7465166afde901610f72074/) and [Liu et al. (2022, Pharmaceutical Statistics)](https://consensus.app/papers/details/1e33adf0f5335e15ac540181dd6caace/) demonstrate the statistical-power gains of adaptive biomarker-enrichment designs.

The boost is meaningfully high (~20%) because biomarker enrichment changes the *expected effect size* the trial is powered to detect, not just the precision. A trial powered to detect a 5% absolute response improvement in an unenriched population may need only to detect a 25% improvement in a biomarker-positive subgroup; the conditional-power gain is large.

**Limitations:** The boost applies only when the biomarker is *predictive* of response, not merely *prognostic*. The framework currently does not distinguish, which means a sponsor running a trial with a prognostic-only biomarker would receive the modifier inappropriately. This is a known limitation; the partial mitigation is that practitioners using the framework are expected to understand the distinction and toggle the modifier accordingly.

### Target validation — +15%

When a drug acts on a target that has already been validated by a separately-approved drug in the same indication, the framework boosts PoS by 15%. The canonical example is adagrasib (KRAS G12C inhibitor for NSCLC): sotorasib received FDA accelerated approval for the same target and indication thirteen months before the adagrasib backtest cutoff. The target was no longer a target-validation question; the trial was a competitive-positioning question.

The magnitude is a practitioner heuristic informed by Wong (2019)'s discussion of prior-target validation as a Phase 2 transition predictor. The 15% reflects:
- Reduced biological-validation risk (the target is druggable; the mechanism is operative)
- Demonstrated regulatory pathway (FDA has accepted the target)
- Available comparator data to power confirmatory trials more efficiently

**Limitations:** This is the modifier with the weakest peer-reviewed grounding. The Wong 2019 disaggregation supports the direction (positive) but the precise magnitude is calibrated against practitioner intuition rather than against a specific empirical estimate. Reasonable values lie in [10%, 20%]; 15% is the central choice.

### Competitive density — -10%

When three or more direct competitors are in late-stage development in the same indication, the framework applies a 10% PoS penalty. The mechanism is enrollment competition (multiple trials chasing the same patient pool reduces enrollment speed and quality) and commercial-bar effects (later-arriving assets face a higher efficacy threshold to win share). The effect is documented qualitatively in the BD literature; the magnitude is a practitioner heuristic.

The threshold (≥3 competitors) is a discrete approximation of a continuous effect; below three competitors there is typically room for differentiation, above three the market becomes a margin-of-improvement battle.

## Regulatory-designation boosts

The framework adds boosts for FDA designations that have been associated with materially different approval outcomes in the empirical literature.

| Designation | Boost | Source |
|---|---:|---|
| Breakthrough Therapy Designation (BTD) | +10% | [Williamson et al. 2025](https://consensus.app/papers/details/a3b81c4fd00551388c04ae09715cabf6/), [Hwang et al. 2018](https://consensus.app/papers/details/b90d08ab18ea595099df11aab1bbb01b/) |
| Orphan Drug Designation | +5% | BIO 2021 rare-disease cohort shows ~16% LOA vs ~8% all-indications |
| Fast Track | +3% | Williamson et al. 2025 — strongest immediate market-impact designation |

**On BTD specifically:** Williamson et al.'s 2025 meta-analysis of 25 studies finds BTD has the shortest mean approval timeline at 69.96 months (95% CI: 60.25-79.67). Hwang et al. (2018) studied 58 cancer drugs approved between 2012-2017, of which 43% had BTD. BTD drugs reached approval 1.9 years faster than non-BTD drugs (5.2y vs 7.1y; p=0.01), with no statistically significant differences in PFS gains or response rates.

The Hwang finding is important and nuanced: **BTD does not primarily make drugs more likely to work — it makes the development path of already-promising drugs faster.** The framework's 10% boost reflects two effects: (1) BTD is a signal that FDA already agreed the preliminary clinical evidence is compelling, which is informative about underlying asset quality and (2) the faster development path itself reduces attrition opportunities (program-discontinuation risk for capital-constrained sponsors, competitive obsolescence). The framework treats the 10% as a combined-effect estimate, not a pure efficacy signal.

**Adversarial check on BTD.** [Mao et al. (2025, Drug Discovery Today)](https://consensus.app/papers/details/3eb389f2a8695841bab2605d8632d774/) analyzed BTD products approved 2021-2023 in the US and China and found that *"many offered only limited or insufficient therapeutic value, as assessed by hazard ratio analyses and independent health technology assessment ratings."* The +10% BTD boost is therefore a *probability-of-approval* signal, not a *probability-of-clinical-benefit* signal. The framework values assets at the FDA-approval gate, not at the clinical-utility gate; this is a design choice consistent with biotech-VC valuation practice but worth flagging.

**On Orphan and Fast Track:** Both are documented to associate with positive market-cap responses and accelerated development timelines (Williamson et al. 2025 finds Fast Track has the strongest Day-1 CAAR at 8.20%). The framework's smaller boosts (+5% and +3%) reflect that these designations are less selective than BTD and therefore carry weaker conditional information about asset quality.

## Reflexivity multiplier — sponsor capital position

This is the framework's headline modifier and the one most worth reading the deeper documents on. Briefly:

| Tier | Runway | Multiplier |
|---|---|---:|
| Well capitalized | ≥24 months | 1.08 |
| Adequate | 12-24 months | 1.00 |
| Constrained | 6-12 months | 0.88 |
| Distressed | <6 months | 0.78 |

The mechanism is Spence-style separating-equilibrium signaling: well-capitalized sponsors can credibly commit to costly trial-design features (large N, biomarker enrichment, active comparator, adaptive design) that capital-constrained sponsors cannot. The empirical anchor is [Ma et al. 2025 (Scientific Reports)](https://consensus.app/papers/details/e262d49916ee5d8a891fc05dedec8e30/), which predicts trial-accrual failure with AUC 0.74 using protocol-level features that track sponsor capital position. The theoretical foundation is laid out in [02-reflexivity-thesis.md](02-reflexivity-thesis.md) and [06-signaling-equilibrium.md](06-signaling-equilibrium.md).

The reflexivity multiplier is applied **last** in the PoS chain. The placement is intentional: a senior reader scanning the audit trail should see "this is the structural overlay on top of the asset-specific math," not "this is buried inside the chain." The ordering does not affect the math (multiplication is commutative), but it affects the readability of the chain as an argument.

## Confidence range

The framework produces a low-high confidence range alongside the point estimate. The range propagates uncertainty in two of the modifiers (modality and reflexivity), which is a partial — not complete — uncertainty quantification:

```
confidence_low  = final_LOA × (mod_range_low / mod_central) × (refl_range_low / refl_central)
confidence_high = final_LOA × (mod_range_high / mod_central) × (refl_range_high / refl_central)
```

For a Phase 2 oncology asset with biomarker enrichment, target validation, BTD, and adequate capital, this typically produces a range of roughly ±8% relative to the point estimate (~14.8% to ~17.4% around a 16.1% central LOA).

**The range is honestly understated.** It does not propagate uncertainty in the mechanism modifiers (biomarker, target validation, competition, regulatory designations), each of which has its own calibration uncertainty. A more complete propagation would widen the range, possibly by another factor of 1.5x. This is documented as a known limitation in [04-scorecard-pillars.md](04-scorecard-pillars.md) Limitations section and listed as a v1.5 enhancement; the current implementation favors readable point estimates over fully-propagated bands.

## The audit trail

Every modifier applied produces an entry in the PoS audit trail (the waterfall rendered on the dashboard). Each entry carries:
- **Name** — what was adjusted
- **Multiplier** — the multiplicative factor applied
- **Rationale** — one-sentence explanation
- **Source** — citation back to the underlying evidence

The audit trail is not a UI feature painted on top of the engine; it is the engine's native output. The engine returns `final_loa` *and* `adjustments: list[PoSAdjustment]` together. The waterfall renders that list. The number and the story are computed jointly, which is what prevents them from drifting.

A user clicking any modifier in the dashboard sees the source citation. The source for the BTD boost links to Williamson et al. 2025 and Hwang et al. 2018; the source for the reflexivity multiplier links to this document and to Ma et al. 2025; the source for the modality multiplier links to the BIO/Informa cohort and the relevant review paper. The chain from rendered number to peer-reviewed evidence is one click on the GitHub repo.

## Worked chain — adagrasib at June 2022 cutoff

To make the chain concrete, the [adagrasib worked example](05-worked-example-adagrasib.md) walks through every step. Summary:

| Step | Multiplier | Running LOA |
|---|---:|---:|
| Phase 2 oncology base rate | — | 10.6% |
| Modality: small molecule | ×1.00 | 10.6% |
| Biomarker enrichment (KRAS G12C selection) | ×1.20 | 12.7% |
| Target validation (sotorasib precedent) | ×1.15 | 14.7% |
| Breakthrough Therapy Designation | ×1.10 | 16.1% |
| Reflexivity: adequate capital | ×1.00 | 16.1% |

**Final pre-readout LOA: 16.1%, versus a population prior of 10.6% — a 52% relative uplift attributable to three observable, documentable features of the asset and trial.**

The post-readout (Phase = NDA) scenario, computed by the same chain with the phase variable changed, produces a final LOA of approximately 75%. The two numbers together produce the framework's pre-readout valuation of $516M and post-readout valuation of $4,581M, the latter bracketing BMS's actual $4.8B acquisition price within ~5%. See [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) for the full economic calculation.

## What the framework does *not* claim

Six honest limitations:

1. **The base rates are population priors, not asset-specific predictions.** Without modifiers, the framework would systematically over-price the capital-constrained sponsor with the compromised trial and under-price the well-capitalized sponsor with the rigorous one. The modifier chain corrects this directionally; the calibration of the magnitudes is approximate.

2. **The biomarker-enrichment boost assumes a *predictive* biomarker.** A sponsor running a prognostic-only biomarker would receive the modifier inappropriately. The framework relies on the user to make this distinction.

3. **The target-validation boost is the least well-grounded modifier.** Its magnitude (+15%) is calibrated against practitioner intuition rather than a specific empirical estimate. Reasonable values lie in [10%, 20%].

4. **The BTD boost reflects probability-of-approval, not probability-of-clinical-benefit.** [Mao et al. 2025](https://consensus.app/papers/details/3eb389f2a8695841bab2605d8632d774/) document that BTD products often have limited HTA-assessed clinical value. The framework values assets at the approval gate, which is consistent with biotech-VC valuation practice but worth knowing.

5. **The cell-therapy modality multipliers are the most uncertain.** The empirical base for ×0.65 (autologous) and ×0.70 (allogeneic) is thin because the modality is recent. These values are most likely to be recalibrated as more cell-therapy assets reach Phase 3 readouts.

6. **Confidence-range propagation is partial.** Only modality and reflexivity uncertainty propagate into the rendered band; mechanism-modifier uncertainty does not. The true uncertainty is larger than the rendered range. v1.5 work.

The framework is honest about each of these in code (every modifier has an inline rationale and source) and in documentation (this writeup). The honesty is what makes the chain defensible: a senior reader can point at any specific modifier and the answer to "where did this number come from?" is always specific.

## See also

- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the deeper argument behind the reflexivity multiplier
- [03-rnpv-monte-carlo.md](03-rnpv-monte-carlo.md) — how the PoS feeds into the phase-gated rNPV calculation
- [04-scorecard-pillars.md](04-scorecard-pillars.md) — the 8-pillar scorecard and the Known Limitations section
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the chain applied to a real asset with a known outcome
- [06-signaling-equilibrium.md](06-signaling-equilibrium.md) — the formal game-theoretic derivation of the reflexivity mechanism
- [00-product-thesis.md](00-product-thesis.md) — strategic framing: why this framework, why now, what kind of product it is becoming
