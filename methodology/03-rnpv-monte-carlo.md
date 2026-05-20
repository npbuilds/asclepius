---
title: "Risk-adjusted NPV — phase-gated cash flows, Monte Carlo priors, and discount conventions"
summary: "The full mechanics of how Asclepius computes risk-adjusted NPV. Documents the phase-gated cash-flow structure, the four Monte Carlo prior distributions, the mid-year discount convention, and the closed-form-vs-simulation relationship. Every methodology choice is cited or labeled as analytical convention."
audience: "Read this if you want to understand or modify the rNPV engine. The PoS chain (01-pos-framework.md) produces the LOA inputs this document consumes; the worked example (05-worked-example-adagrasib.md) shows the full math against a real asset."
primary_sources:
  - "Stewart JJ, Allison PN, Johnson RS. Putting a price on biotechnology. Nature Biotechnology 19(9): 813-818 (2001). The foundational rNPV-for-biotech paper."
  - "Wong CH, Siah KW, Lo AW. Estimation of clinical trial success rates and related parameters. Biostatistics 20(2): 273-286 (2019). The PoS estimates the rNPV engine multiplies cash flows by."
  - "Damodaran A. Cost of Capital by Industry (US), updated January 2025. NYU Stern. The WACC benchmarks by company stage."
  - "Brennan MJ, Schwartz ES. Evaluating Natural Resource Investments. Journal of Business 58(2): 135-157 (1985). The mid-year discount convention's standard treatment in capital-budgeting literature."
  - "Cassimon D, Engelen PJ, Yordanov V. Compound real option valuation with phase-specific volatility. Journal of Business Research 96 (2019). Modern treatment of phase-gated optionality in biotech valuation."
related_implementations:
  - "No widely-used open-source Python rNPV library for biotech exists. The educational and consulting content in the space (Models Hub, Inbistra, Vision Lifesciences, BiopharmaVantage) is methodology articles. Operational tools (SparkCo, vendor offerings) are closed-source/commercial. Asclepius's rNPV engine is, to our knowledge, the first open-source implementation tying phase-gated cash flows + reflexivity-adjusted PoS + Monte Carlo with documented prior distributions + audit-trail discipline in one codebase."
  - "Wong, Siah, Lo (2019) did not release replication code or data publicly. The underlying Informa Pharma Intelligence dataset is proprietary regardless."
  - "Adjacent open-source work: [bvssaisantoshi19/clinical-trial-outcome-prediction](https://github.com/bvssaisantoshi19/clinical-trial-outcome-prediction) — ML for predicting trial completion using AACT (ClinicalTrials.gov) data. Solves the prediction-end of the PoS problem; does not address rNPV, scorecards, or comparables. Useful reference for the v1.5 ML-PoS prior module."
---

# Risk-adjusted NPV

## Why rNPV and not regular NPV

[Stewart, Allison, and Johnson (2001)](https://www.nature.com/articles/nbt0901-813) gave the modern biotech-valuation literature its canonical move: separate clinical-development risk from financial risk. The intuition is that probability-of-approval is *binary-outcome risk* — the drug either works or it doesn't — and capturing it via the discount rate is wrong on two counts:

1. **It double-counts risk.** A high discount rate compounds over time; multiplying a 50% PoS by another 50% over the same multi-year horizon does not. The math produces different answers, and the discount-rate approach systematically under-values long-horizon clinical assets.

2. **It hides the assumption.** A 25% discount rate is a number; "we used a 25% discount rate" is a methodology statement. Whether 25% reflects "high WACC for early biotech" or "low WACC + 60% phase-failure probability bundled together" is invisible to the reader. The rNPV approach forces the assumption into the open: probability adjustments are explicit and probability-weighted cash flows are visible.

Stewart's framework — multiply each year's cash flow by the cumulative probability of reaching that point, then discount at the company's normal cost of capital — has been the standard biotech-investment-banking valuation model for two decades. Every major biotech BD team and sell-side analyst uses some variant of it.

Asclepius implements Stewart's framework with three deliberate design choices that go beyond the 2001 baseline: (1) **phase-gated cost optionality** (costs stop when the trial fails, not just revenues), (2) **Monte Carlo over four input distributions** rather than a single point estimate, and (3) **mid-year discount convention** rather than year-end or beginning-of-year. Each is documented below with the choice's rationale.

## The phase-gated cash flow structure

Standard rNPV (Stewart 2001) weights *revenue* by cumulative LOA from the current phase. Asclepius extends this to *costs as well*. The rationale is that development costs are decision-dependent: when a trial fails at Phase 3, the sponsor stops spending — Phase 4 trial costs are never incurred. Costs are options, not certainties, and should be priced as options.

The framework's cost-side math weights each future cost by the **probability of reaching that gate**, not the cumulative LOA. For an asset currently in Phase 2:

```
PV(cost of Phase 3) = P(reach Phase 3) × Cost(P3) × discount(midpoint of P3 timeline)
                    = (P2→P3 transition) × Cost(P3) × discount factor

PV(launch cost) = cumulative LOA × Launch cost × discount(launch year)
```

Phase costs and launch costs are different probability weights because they happen at different gates. The Phase 3 program is conditional on reaching Phase 3 (one transition from Phase 2); the launch program is conditional on the full LOA (Phase 3 success + NDA approval + FDA approval). Treating them with separate probability weights captures the real shape of the development option.

The revenue side uses the cumulative LOA from the current phase, weighting each future year of revenue by the same number (the probability that the drug reaches market at all). This is the same as Stewart's formulation.

### Why phase-gated costs matter

Without phase-gated costs, the framework would treat a $250M Phase 3 program as a $250M certain outflow regardless of probability of success. For a 30% PoS asset, that over-weights the cost by ~$170M (the $250M cost is only incurred conditionally on reaching Phase 3, which happens 30% of the time, so its expected value is $75M, not $250M). The over-weighting flows directly into rNPV, biasing valuations downward for capital-constrained sponsors who have more development cost still to incur.

This matters most for early-stage assets where the cumulative cost-of-development is large relative to the risk-weighted revenue. For commercial-stage assets the effect is small (most costs are sunk). For Phase 1 and Phase 2 oncology assets the effect can be 20-40% of valuation.

## The closed-form base case

The framework computes a deterministic point estimate first, then runs Monte Carlo around it. The closed-form math is the readable equation; the Monte Carlo is the uncertainty propagation.

For asset in current phase `p` with cumulative LOA `loa`, peak sales `S`, COGS fraction `c`, WACC `r`, years-to-peak `T_peak`, years-of-exclusivity `T_excl`, launch year `t_launch`, and phase-cost array `C_phase`:

**Revenue side** (mid-year convention; see next section):
```
PV_revenue = loa × Σ_{i=0}^{T_excl-1} [ S × min(1, (i+1)/T_peak) × (1 - c) / (1+r)^(t_launch + i + 0.5) ]
```

**Cost side**:
```
PV_cost = Σ_{phase ∈ remaining_phases} [ P(reach phase) × C_phase × discount(midpoint of phase) ]
        + loa × Launch_cost × (1+r)^{-t_launch}
```

**Base case rNPV** = PV_revenue − PV_cost.

For an asset whose current phase has `years_per_phase[current] = 0` (i.e., the asset is at the end of its current phase, transitioning), Phase-cost terms for the current phase are zero. This is the convention used in the adagrasib worked example, where Phase 2 was effectively complete at the June 2022 cutoff.

The closed-form is the reference number the dashboard displays as the "base case." The Monte Carlo (below) bounds it with a distribution.

## The mid-year discount convention

Each annual cash flow is discounted as if received at the **midpoint of its year**, not at year-start or year-end. The math:

```
discount(t) = (1+r)^{-(t + 0.5)}   for revenue or cost received during year t
```

The choice is documented as a deliberate convention because it matters and is contestable:

| Convention | Treatment of year-t cash flow | Bias vs reality |
|---|---|---|
| Year-end | `(1+r)^{-(t+1)}` | Under-states rNPV by ~half a year of discounting (~5% at WACC=10%) |
| **Mid-year** ✓ | `(1+r)^{-(t+0.5)}` | Splits the difference — typical practitioner default |
| Beginning-of-year | `(1+r)^{-t}` | Over-states rNPV by ~half a year of discounting (~5% at WACC=10%) |

Mid-year is the standard in capital-budgeting and corporate-finance practice (see [Brennan & Schwartz 1985](https://www.jstor.org/stable/2352819) for the canonical treatment in natural-resources investment, the closest analog to biotech option valuation). It is also the convention most major investment banks use in their biotech sell-side rNPV models.

**Why the framework had to choose this explicitly:** an earlier implementation used the beginning-of-year convention (`(1+r)^{-t}`), which produced rNPV outputs systematically ~5% above the mid-year and ~10% above the year-end convention. A code review caught the inconsistency between the cost-side discounting (which used midpoint) and the revenue-side discounting (which used beginning-of-year), and the framework was corrected to mid-year on both sides. The adagrasib backtest's post-NDA rNPV dropped from $4,900M to $4,581M after the fix — *closer* to the actual BMS $4,800M deal price, not further away. The fix improved calibration as a side effect.

## Monte Carlo over four input distributions

The closed-form math is deterministic. The Monte Carlo runs the same math 10,000 times with each iteration sampling four uncertain inputs from documented prior distributions:

| Input | Distribution | Parameters | Rationale |
|---|---|---|---|
| **Peak sales** | Log-normal | median = user input, σ_log = 0.35 | Peak sales is always positive, right-skewed (blockbuster upside, bounded downside). Log-normal is the standard distribution for right-skewed continuous quantities. σ_log = 0.35 produces ~67% of mass within ±42% of the median — moderate but meaningful uncertainty. |
| **LOA** | Beta | mean = pos.final_loa, concentration κ = 30 | LOA is bounded [0, 1]. Beta is the standard distribution for bounded quantities. κ = 30 produces tight clustering around the point estimate; α/β at low LOA values produces right-skew which propagates into the rNPV distribution. |
| **WACC** | Normal | mean = user input, σ = 0.02 (200 bps) | WACC is continuous and approximately symmetric around the practitioner's estimate. 200 bps is the typical analyst-to-analyst spread on the same asset. Clipped to [4%, 25%] to avoid implausible draws. |
| **COGS** | Triangular | mode = user input, range = ±10pp clipped [0, 0.95] | COGS is bounded and the practitioner has a central estimate; triangular is the standard distribution when you have a mode + bounded range but not enough data for a more sophisticated prior. |

The Monte Carlo outputs P25, P50, and P75 of the resulting rNPV distribution. The dashboard renders the band visually alongside the closed-form point estimate.

### Why these specific distributions

The framework's distributional choices are pragmatic, not optimal. The right way to think about them:

- **Log-normal for peak sales is consensus.** No widely-used biotech-valuation model uses a different distribution for peak sales because no other distribution captures the right-skew that real revenue outcomes show (the long tail of unexpected blockbusters; the bounded downside of zero sales is captured by the LOA distribution, not the revenue distribution).

- **Beta for LOA is standard for bounded probabilities.** The Bayesian-statistics literature uses beta as the natural conjugate prior for binomial probabilities. κ = 30 is a tuning choice: smaller κ widens the distribution (more uncertainty about LOA); larger κ tightens it (the point estimate is taken as more precise). The framework's κ = 30 reflects the analyst's stated PoS being moderately reliable but not perfect.

- **Normal for WACC is symmetric and analytically convenient.** The empirical distribution of analyst WACC estimates for the same asset is approximately symmetric, so the normal works.

- **Triangular for COGS is honest about limited prior information.** When you have a central estimate and bounds but not a real distribution, triangular is the standard choice (used widely in operations research and project management).

Each distributional choice has tunable parameters in the engine (σ_log, κ, σ_wacc, COGS bounds). The Monte Carlo Dashboard (v1.5 deliverable) is the mechanism for empirically tuning these against realized outcomes; the v1 defaults are based on practitioner intuition and the published-distribution literature.

### Reproducibility

The Monte Carlo uses numpy's default random number generator seeded by default for reproducibility — same inputs always produce the same histogram. This matters for snapshot tests (the adagrasib backtest must reproduce its bracketing of the BMS deal across CI runs) and for demo reliability (the user can drag the reflexivity slider and see the same MC distribution shift in the same direction every time).

The seed is configurable per-call but defaults to `42`. For production deployments where users care about *their* simulation being reproducible across sessions, the seed can be made user-controlled.

### A subtle bias the framework documents but does not yet fix

The Monte Carlo's median is generally close to the closed-form base case, but not identical. For low-LOA regimes (Phase 2 oncology at ~11% LOA), the beta distribution's right-skew produces an MC median that sits ~15% below the closed-form base. This is *expected behavior*, not a bug: when the LOA distribution has skew, the rNPV distribution inherits the skew, and median ≠ mean.

The framework's test suite asserts that the MC peak-sales draws have median equal to the input (a targeted regression test against an earlier sampling bug — see the verification section below), but does not assert that the rNPV MC median equals the closed-form base. The two numbers are documented in the dashboard as separate quantities, and a senior reader looking at both should understand why they differ.

For high-LOA regimes (Phase 3+ assets, rare-disease assets with strong cohorts), the skew is smaller and the two converge to within ~5%.

## WACC defaults and benchmarks

The framework's WACC defaults are stage-keyed and loaded from [api/app/data/wacc_benchmarks.json](../api/app/data/wacc_benchmarks.json):

| Company stage | Default WACC | Range | Rationale |
|---|---:|---|---|
| Preclinical private | 20% | 18-25% | Highest cost of capital for un-validated private biotech |
| Phase 1 small-cap | 15% | 13-18% | Public micro-cap with one or two clinical assets |
| Phase 2 small/mid-cap | 12% | 10-14% | Reference tier (adagrasib backtest uses 10%, justified by BTD) |
| Phase 3 mid-cap | 10% | 9-12% | Substantial Phase 3 program, near-term commercial |
| Commercial large-cap | 8% | 7-9% | Closer to industry beta |

The benchmarks are calibrated against [Damodaran's industry cost-of-capital tables](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/datafile/wacc.html) for biotech (cost-of-equity ~10-11%, beta ~1.2 as of January 2025) and against [Stewart, Allison, Johnson (2001)](https://www.nature.com/articles/nbt0901-813)'s discussion of stage-appropriate discount rates in the foundational rNPV paper.

**A note on what WACC captures in rNPV.** Stewart's separation of clinical risk from financial risk means WACC in rNPV models is *not* the same as WACC in a standard DCF. In rNPV, WACC captures only the time-value of money plus systemic (market) risk; idiosyncratic clinical risk is captured by the PoS chain. This is why typical rNPV WACCs (8-15%) are lower than DCF WACCs for the same companies might be (15-25%) — they are not the same number, even though they are both called "WACC."

The framework loads stage defaults but accepts user override via the rNPV inputs panel. The adagrasib worked example uses 10% rather than the Phase 2 small-mid-cap default of 12% because BTD typically warrants a slight discount-rate reduction (regulatory tailwind reduces late-stage uncertainty). The override is documented in the worked example.

## Tornado sensitivity

The framework computes one-at-a-time low/high swings on four variables to identify the dominant rNPV drivers:

| Variable | Low / High swing | Rationale |
|---|---|---|
| Peak sales | ×0.70 / ×1.30 | ±30% reflects typical analyst-to-analyst spread on the same asset |
| WACC | ×0.80 / ×1.20 | ±20% reflects practitioner-side discount-rate disagreement |
| COGS | ×0.75 / ×1.25 | ±25% reflects modality-cohort COGS variance |
| Phase 3 dev cost | ×0.80 / ×1.20 | ±20% reflects program-scope variance |

The bars are sorted by swing magnitude (descending) in the rendered chart. For typical early-commercial-stage biotech the top driver is peak sales; for capital-constrained sponsors the WACC sensitivity rises in rank.

The tornado is computed deterministically (each swing applied to the closed-form math, no MC). This is intentional: tornado is for understanding *which variables matter*, MC is for understanding *how much the answer moves under joint uncertainty*. Combining them in one chart would obscure both.

## Downside scenario — Phase 3 failure

The framework computes an explicit downside: the value of the asset if the principal remaining trial fails. For a Phase 2 asset, this is Phase 3 failure; for a Phase 3 asset, this is FDA non-approval after a clean trial.

The calculation:
```
Downside_value = − PV(Phase 3 cost committed) + 0.10 × PV(forgone peak revenue)
```

The first term is the capital lost when the trial fails (the cost is incurred; the asset has zero value to recover). The second term is a 10% recovery of forgone revenue, representing the value that might be salvaged via a fire-sale licensing deal to a follow-on developer with a different mechanism or indication. The 10% is a practitioner heuristic; the precise value matters less than acknowledging the downside is not pure-zero.

The downside is rendered in red on the dashboard. A user reading the diligence output should see the upside (base case + MC band) and the downside (Phase 3 failure value) as the two ends of the realistic outcome distribution. The PoS chain tells the user how those outcomes are weighted.

## Verification and the Codex audit

The framework's rNPV math has been audited externally (a Codex/GPT-5 review pass on the codebase, completed 2026-05-18). Two material findings emerged and were fixed:

1. **Lognormal sampling bias.** The original implementation used `μ_log = log(input) − 0.5 × σ²`, which produces a lognormal with *mean* equal to the input but *median* ~6% below the input. The test docstring claimed median = input. The code was corrected to `μ_log = log(input)`, which produces median = input (and mean = input × exp(σ²/2), the slight upward skew documented in the distribution choices above). A targeted regression test (`test_mc_peak_sales_sampling_has_median_at_input`) catches any reintroduction of the bias.

2. **Discount convention.** The original implementation discounted revenue at year-start (`(1+r)^{-t}`) but cost at midpoint, producing an internal inconsistency. The framework was corrected to use mid-year on both sides. The adagrasib backtest's post-NDA rNPV shifted from $4,900M to $4,581M as a result — *closer* to the BMS $4,800M deal price.

Both fixes are tested. The full test suite (`pytest -q` from the api/ directory) covers 56 unit and integration tests; the adagrasib snapshot test asserts the framework still brackets the BMS deal within 5% after the discount fix.

## Limitations

Five honest limitations the framework does not yet address:

1. **Single peak-sales draw across the exclusivity period.** The Monte Carlo samples one peak-sales value per path and applies it to all years (with the linear ramp). A more sophisticated model would sample a time-series of revenue with auto-correlated shocks. The current implementation is consistent with practitioner-standard rNPV models.

2. **No competitive entry dynamics in the revenue model.** Peak sales is a static assumption; in reality, a competitor's approval or pricing action can shift the trajectory. The framework's "competitive density" PoS penalty is the only adjustment for this. v2 could add a revenue-erosion-from-competition model.

3. **No deal-structure modeling.** The framework values the asset on a standalone basis. A real deal involves upfront, milestones, royalties, contingent value rights — none of which are modeled. The `deal_economics` skill in the source skill-suite addresses this; it is deferred to v1.1.

4. **WACC is constant across the asset's life.** In reality, the appropriate WACC declines as the asset matures (a Phase 3 program warrants a lower discount rate than the same compound at preclinical). Dynamic-risk-rate rNPV (Dando 2020) addresses this; the framework cites it in the methodology folder but does not implement.

5. **No platform optionality.** Multi-indication assets have option value beyond the lead indication. The framework prices the lead indication only. Platform optionality is documented as deferred in the v1.1 plan.

These are real limitations, not flaws. They reflect the choice to ship a defensible single-asset rNPV in v1 rather than a feature-complete platform valuation tool. Each limitation has a forward reference to where it could be addressed.

## See also

- [01-pos-framework.md](01-pos-framework.md) — the PoS chain that feeds the LOA inputs the rNPV engine consumes
- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the reflexivity multiplier that adjusts the PoS before it reaches the rNPV
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the full chain applied to a real asset with a known deal outcome
- [04-scorecard-pillars.md](04-scorecard-pillars.md) — the qualitative-overlay layer that complements rNPV in the diligence workflow
- [00-product-thesis.md](00-product-thesis.md) — strategic framing of the rNPV engine as the framework's deterministic core
