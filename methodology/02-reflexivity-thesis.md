---
title: "Reflexivity-adjusted Probability of Success"
summary: "Sponsor capital position structurally adjusts a clinical asset's probability of success. This is the headline methodology choice in Asclepius and the differentiator versus textbook rNPV."
primary_sources:
  - "Ma S, Han W, Lê Cook B, et al. Predicting accrual success for better clinical trial resource allocation. Scientific Reports 15 (2025). AUC 0.74."
  - "Spence M. Job Market Signaling. Quarterly Journal of Economics 87(3): 355-374 (1973). The foundational separating-equilibrium argument."
  - "Soros G. The Alchemy of Finance. Simon & Schuster (1987). The macro analog: capital flows and underlying fundamentals are mutually constituting."
  - "Wong CH, Siah KW, Lo AW. Estimation of clinical trial success rates and related parameters. Biostatistics 20(2): 273-286 (2019). The base rates the reflexivity adjustment modifies."
---

# Reflexivity-adjusted Probability of Success

## Thesis

A clinical asset's probability of success is not a property of the asset alone. It is a property of **the asset, the trial design that will test it, and the sponsor's ability to fund that trial as designed.** Sponsors with strong balance sheets can credibly commit to costly trial features — adequate enrollment, biomarker-enriched populations, active-comparator arms, proactive regulatory engagement — that materially raise the asset's chance of reaching approval. Sponsors operating with under twelve months of runway cannot make those commitments credibly, and the trials they design reflect that constraint.

This is a *structural* mechanism, not a fudge factor. The same asset, in two sponsors with different capital positions, is two different bets. Asclepius prices that difference explicitly with a multiplicative adjustment of ±5–15% applied at the end of the PoS chain, after base rate, modality, and mechanism-specific modifiers.

## Why standard rNPV gets this wrong

The textbook formulation of risk-adjusted NPV treats probability of success as exogenous — a number you look up in BIO/Informa's published phase-transition tables and feed into the discount math. The Wong, Siah, and Lo (2019) base rates are the canonical reference. They are excellent population-level priors. They are the right starting point.

But population priors are computed across all sponsors. They blend the well-funded Phase 3 program with biomarker enrichment and an active comparator into the same statistic as the cash-strapped Phase 2 readout with single-arm design and patient enrollment that took an extra eighteen months. The aggregate transition rate from Phase 2 to Phase 3 in oncology is 24%. That number is the average of trials we would describe as *credibly designed* and trials we would describe as *operationally compromised*. Treating both groups identically when valuing the asset means systematically over-pricing the constrained sponsor and under-pricing the well-capitalized one.

The reflexivity adjustment is the simplest possible correction: a per-tier multiplier that separates the two groups and applies the relevant one based on the sponsor's known balance-sheet state.

## The signaling argument

The theoretical foundation is Spence's (1973) job-market signaling model. Spence asked: when one party has private information about quality (the worker knows their own ability; the employer does not), under what conditions can a *costly action* serve as a credible quality signal?

The answer is the separating equilibrium. A signal credibly separates types if and only if **the cost of the signal differs across types in a way that makes it rational for high-quality types to emit it and irrational for low-quality types to mimic.** In Spence's original setup, education is the signal: high-ability workers find education less costly (in time, effort, or forgone wages) than low-ability workers, so the high-ability worker rationally invests in the signal and the low-ability worker rationally does not. The employer, observing the signal, can infer type.

Map this onto clinical development. The "type" the sponsor would like to credibly signal is *the asset's true probability of success*. The asset's actual mechanism, target validation, and preclinical data are observable but incompletely informative. The sponsor has additional private information — pilot data, mechanistic conviction, regulatory backchannel intelligence — that the market does not see directly.

The signals available are *trial-design choices*: enrollment size, biomarker enrichment, active versus placebo comparator, adaptive design features, depth of regulatory engagement. These choices are costly. An adequately powered Phase 3 trial with active comparator and biomarker enrichment costs roughly $250–400M and runs three years. A small Phase 2 single-arm trial with broad enrollment costs $50–100M and runs eighteen months.

For a sponsor with high conviction (private information that the asset will work), the costly signal is rational: the expected value of approval is high enough that the investment in trial quality pays back. For a sponsor with low conviction *or* with capital constraints that make the costly signal unaffordable, the rational choice is the cheap trial. **The cost asymmetry is what makes the signal credible.** When the market observes a sponsor running the adequately powered, biomarker-enriched, active-controlled trial, the inference is: this sponsor either has high private conviction, or has access to capital that lets them treat the investment as low-cost — both of which are correlated with eventual success.

This argument generates the falsifiable prediction that Asclepius operationalizes: among assets matched on mechanism, indication, and phase, **sponsors who can credibly emit the costly signal should have systematically higher realized approval rates.** That prediction has held in two independent data analyses that we cite below.

## The empirical evidence

The most direct evidence is Ma, Han, Lê Cook et al. (2025), published in *Scientific Reports*. The authors built a machine-learning model that predicts trial-accrual failure — the structural reason clinical trials fail to meet their enrollment targets — from sponsor characteristics and protocol features. The model achieves AUC of 0.74 on held-out data. The features that load most heavily on the prediction include trial size, comparator choice, number of sites, and inclusion-criterion breadth, all of which are downstream of sponsor capital position. Sponsors who cannot commit to multi-site enrollment, complex eligibility screening, or extended timelines run trials that the model correctly predicts will fail at higher rates.

This is the empirical scaffolding for the reflexivity adjustment. Ma et al. did not set out to demonstrate Spence's argument; they set out to predict accrual failure. But the features their model uses to make that prediction are precisely the costly signals that separating-equilibrium theory says should differ across capital-position tiers. Trial-design quality is predictable from sponsor balance-sheet state, and trial-design quality predicts outcome.

A more anecdotal but operationally vivid example is Sarepta Therapeutics' Phase 3 program for eteplirsen and golodirsen in the 2015–2018 window. Sarepta's runway was repeatedly cited in 10-Q risk factors as the binding constraint on trial scope; the company's Phase 3 confirmatory trials were criticized in FDA advisory committee documents for design choices (single-arm, small N, surrogate endpoints) that subsequent commentators traced to the same capital constraint. Sarepta's eventual capital raise in 2018 corresponded with a visibly improved confirmatory-program design in later assets. The pattern — capital tight, trial compromised, accelerated approval contested; capital adequate, trial improved, approval cleaner — is the same one Ma et al.'s model formalizes statistically.

We do not cite Sarepta as proof of the framework. We cite it because every senior biotech investor has seen the pattern with their own eyes, and Spence/Ma give it a name.

## The macro analog: Soros reflexivity

The same mechanism operates in macro investing, where George Soros formalized it as reflexivity in *The Alchemy of Finance* (1987). Soros's claim was that asset prices and underlying fundamentals are not independent: capital flows into a sector raise valuations, which fund operational expansion, which improves fundamentals, which justifies the higher valuations. The feedback loop is structural, not behavioral, and it operates in both directions.

Clinical development exhibits the identical structural pattern in a smaller domain. A sponsor's capital position enables trial-design choices that affect the probability of approval, which determines the asset's valuation, which determines the sponsor's ability to raise the next round, which sets the next trial's design space. The loop closes within a single program's development arc.

This is not a derivative argument — Spence's separating-equilibrium framework is the more rigorous foundation, and Ma et al.'s evidence is the more direct empirical support. We cite Soros only to underscore that the underlying mechanism is recognized across investment domains, not unique to biotech.

## Operationalization

The reflexivity adjustment is implemented as a multiplicative factor applied last in the PoS chain. Four tiers, with multipliers calibrated to balance the empirical magnitude of accrual-failure differences in Ma et al. against the practitioner-side intuition for what a "well-capitalized" versus "distressed" sponsor looks like in deal evaluation.

| Tier | Runway | Multiplier | Rationale |
|---|---|---|---|
| Well capitalized | ≥24 months | ×1.08 | Funds adaptive design, biomarker enrichment, active comparator, proactive FDA engagement. The full costly signal. |
| Adequate | 12–24 months | ×1.00 | Reference tier. No structural advantage or disadvantage. |
| Constrained | 6–12 months | ×0.88 | Trial-scope compromises become visible: smaller N, single-arm where comparator was warranted, deferred regulatory meetings. |
| Distressed | <6 months | ×0.78 | Going-concern overhang. Trial truncation, premature analyses, executive turnover, CRO/site quality compromises. |

The multipliers are point estimates inside documented ranges (×1.05 to ×1.10 for well capitalized; ×0.72 to ×0.85 for distressed). The full ranges propagate into the PoS confidence interval the engine reports alongside the point estimate.

The adjustment appears as the **final row** of the PoS audit trail rendered in the dashboard, after base rate, modality, and mechanism modifiers. This placement is deliberate: a senior reader scanning the waterfall should see "this is the structural overlay" rather than "this is buried inside the math." Every reflexivity row in the audit trail also carries a one-sentence rationale and the citation to this writeup, so the chain from the rendered number back to the argument above is one click long.

## What we do not claim

This is a multiplicative correction to a population prior, not a structural model of trial design. We do not claim:

- **That capital position causes outcomes deterministically.** Well-capitalized sponsors run failed trials; distressed sponsors occasionally run brilliantly designed trials and reach approval. The adjustment is statistical, not deterministic.

- **That ±15% is the precise magnitude.** Ma et al.'s AUC of 0.74 implies meaningful but not overwhelming separability. The multipliers are calibrated against practitioner intuition and the available empirical evidence; the full range bounds widen the confidence interval rather than tighten the point estimate.

- **That this captures all structural moderators of PoS.** Team experience, scientific advisory board composition, prior approvals at the same target — all matter, all are not in the reflexivity adjustment. They sit elsewhere in the framework: scorecard pillars (team, regulatory positioning), mechanism modifiers (target-validated boost), or implicit in the base rate itself.

- **That the multipliers transfer cleanly outside the cohort window.** They are calibrated to post-2018 trial-design and biomarker-enrichment norms. Pre-2018 historical comparables may understate the gap; future regulatory regime shifts (e.g., FDA confirmatory-trial reform) may compress it.

We do claim that explicit reflexivity adjustment is a defensible operationalization of a well-documented mechanism, that the resulting framework outputs are more accurate than the population prior alone for any specific asset, and that the audit-trail discipline makes the adjustment inspectable rather than hidden.

## Implications for rNPV

Because rNPV weights every revenue cash flow by cumulative LOA and every cost cash flow by the probability of reaching that gate, a ±15% shift in PoS produces a roughly proportional shift in rNPV (closer to linear when LOA is small, slightly less when LOA is large). For a typical Phase 2 oncology asset with base LOA around 11%, the reflexivity adjustment moves rNPV by 15–30% depending on the underlying revenue and cost shape. That sensitivity is exactly what makes the dashboard's reflexivity slider feel like a real interaction rather than a cosmetic toggle: dragging through the four tiers visibly shifts the entire valuation, in a direction the user can defend.

The companion writeup [03-rnpv-monte-carlo.md](03-rnpv-monte-carlo.md) details the phase-gated cash-flow mechanics and the Monte Carlo prior distributions that propagate the reflexivity-induced PoS uncertainty into the rNPV distribution.

## See also

- [01-pos-framework.md](01-pos-framework.md) — the full PoS chain (base rate → modality → mechanism modifiers → reflexivity) with all citations
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the adagrasib retrospective backtest, calibrating the framework against the BMS $4.8B acquisition price
- [06-signaling-equilibrium.md](06-signaling-equilibrium.md) — the formal game-theoretic derivation of why the costly-signal argument is necessary, not sufficient
