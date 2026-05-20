---
title: "8-pillar diligence scorecard — the qualitative overlay on the quantitative core"
summary: "Documents the 8 pillars Asclepius uses to convert qualitative diligence judgments into a single weighted score and a recommendation tier. Seven pillars are practitioner-standard biotech BD scorecard items; the 8th (computational infrastructure) is the framework's novel contribution. Documents the red-flag auto-cap and green-flag boost mechanics, and consolidates the methodology's Known Limitations."
audience: "Read this after the PoS framework (01) and rNPV (03) writeups. The scorecard sits alongside the quantitative core — both inform the same diligence judgment, neither replaces the other."
primary_sources:
  - "Practitioner taxonomy of biotech BD diligence (Clinical / Regulatory / Competitive / Manufacturing / IP / Financial / Team) — widely used across sell-side and BD literature; no single canonical source."
  - "Enholm IM, Papagiannidis E, Mikalef P, Krogstie J. Artificial Intelligence and Business Value: A Literature Review. Information Systems Frontiers 23 (2021). 651 citations. Foundational review of AI/ML as a source of organizational value."
  - "Tang Y, et al. Data asset valuation model based on generative artificial intelligence. PLOS One (2025). Documents the quantifiable commercial value of data assets in data-intensive industries."
  - "Fang X, et al. Anchoring AI Capabilities in Market Valuations: The Capability Realization Rate Model and Valuation Misalignment Risk (2025). Quantifies AI-capability premium in equity valuations."
---

# 8-pillar diligence scorecard

## Why a scorecard alongside the quantitative core

The PoS chain and rNPV engine produce one number — risk-adjusted fair value. That number is well-defined, traceable, and defensible. It is also incomplete. Two assets with the same rNPV can have different *qualitative* profiles, and biotech investment judgment relies on those profiles as much as on the math.

A scorecard sits alongside the quantitative core to capture what rNPV cannot:

- The clinical-evidence strength relative to the regulatory bar (rNPV uses LOA; the scorecard distinguishes "12% LOA from a thin Phase 1" from "12% LOA from a robust Phase 2")
- The team's track record at executing programs under pressure
- The IP fortress's durability through peak sales
- The manufacturing scalability under commercial-scale demand
- The sponsor's computational infrastructure as a developmental accelerant

None of these are absent from rNPV — they're priced into peak sales, PoS, and cost assumptions implicitly. The scorecard makes them *explicit and weighted*. A user filling out the scorecard is forced to take a position on each pillar; the resulting aggregate score becomes a check against the rNPV number. If the rNPV is positive but the scorecard reads "cautious," the math and the judgment disagree, and the user has to reconcile.

The framework reports both numbers and lets the user read them together.

## The 8 pillars

The pillar weights sum to 1.0. The weights are practitioner-calibrated against the relative diligence depth biotech BD teams typically allocate; they are not derived from a published study.

| Pillar | Weight | Question the pillar answers |
|---|---:|---|
| **Clinical strength** | 20% | Is the clinical evidence compelling enough to justify Phase 3 (or commercialization)? |
| **Regulatory positioning** | 15% | Does the regulatory pathway have precedent and manageable risk? |
| **Competitive position** | 15% | Can this asset win meaningful share against current and projected competitors? |
| **Financial attractiveness** | 15% | Does the rNPV justify the capital at risk under the planned investment? |
| **Manufacturing feasibility** | 10% | Can the drug be manufactured at commercial scale with acceptable COGS? |
| **IP fortress** | 10% | Does the IP protect returns through peak sales (typically 12+ years of exclusivity)? |
| **Team & execution** | 10% | Can this team execute the plan and navigate inevitable setbacks? |
| **Computational infrastructure** | 5% | Does the sponsor have AI/ML/data assets that materially accelerate development? |

The first seven are practitioner-standard biotech BD scorecard items. The eighth is the framework's novel contribution, documented below.

Each pillar is scored 1.0 to 10.0 by the user, with optional rationale text. The framework computes:

```
aggregate = Σ (weight × score)
         + 0.5 × len(green_flags)   # green-flag boost
aggregate = min(10.0, aggregate)    # clamp to scale
```

Aggregate score maps to a recommendation tier, which is then auto-capped by any red flags:

| Aggregate | Tier | If any red flag |
|---|---|---|
| ≥ 8.0 | strong_buy | → cautious |
| 6.5 - 7.9 | buy | → cautious |
| 5.0 - 6.4 | hold | → cautious |
| 3.5 - 4.9 | cautious | → cautious (unchanged) |
| < 3.5 | avoid | → avoid (unchanged) |

The framework returns both the numeric aggregate and the tier so a reader can see the *underlying score* even when a red flag has capped the recommendation. This is important: a 9.0 aggregate with a red flag still reports as 9.0 + "cautious," not as 4.0 + "cautious." The cap is on the *action*, not on the *judgment* of the underlying asset.

## The seven practitioner-standard pillars

These pillars are widely used in biotech BD diligence and sell-side analysis; no single citation owns them, but the framing across them is consistent in the literature.

**Clinical strength (20%)** is the highest weight because clinical evidence is the single best predictor of approval and commercial success. A scorer evaluates: the trial design's rigor (powered N, comparator, biomarker enrichment, blinding), the magnitude and durability of the observed effect, the consistency across patient subgroups, the safety profile relative to the indication's standard of care. A score of 8.0 means "the data would justify Phase 3 enrollment without further confirmatory work"; a score of 4.0 means "the data is suggestive but the trial design has gaps a regulator will challenge."

**Regulatory positioning (15%)** evaluates whether the regulatory pathway has precedent and how much sponsor work is required to clear it. A scorer evaluates: pathway clarity (well-trodden indications score higher; novel pathway requires more work), interaction history with FDA, presence of designations (BTD, Orphan, Fast Track — already captured in the PoS chain, but the scorecard captures the *strength* of the designation case as a separate signal), and the specificity of the FDA's communicated expectations. The PoS chain captures regulatory designations as discrete boosts; this pillar captures the *judgment* about regulatory strategy.

**Competitive position (15%)** evaluates the asset's positioning against current and projected competitors. A scorer evaluates: differentiated mechanism, differentiated patient population, head-to-head efficacy or safety advantage, and the breadth of the competitive set five years from launch. This is where the PoS chain's "competitive density penalty" gets a qualitative complement — three direct competitors is the discrete threshold; the pillar captures the *texture* of that competition.

**Financial attractiveness (15%)** evaluates whether the rNPV justifies the capital at risk. A scorer evaluates: rNPV as a multiple of remaining capital required, expected dilution to reach approval, comparable-deal pricing, and the strategic-vs-financial-buyer pool. This is the pillar most aligned with the quantitative core; it forces the user to take a position on whether the rNPV is *enough* given other available investments.

**Manufacturing feasibility (10%)** evaluates whether the drug can be made at commercial scale with acceptable COGS. A scorer evaluates: process complexity, scale-up risk from clinical to commercial volumes, third-party manufacturer availability, and supply-chain vulnerabilities (single-source raw materials, geographic concentration). For small molecules this typically scores 7-8; for cell therapies it can drop to 4-5 because manufacturing complexity is structurally higher.

**IP fortress (10%)** evaluates whether intellectual property protects returns through the asset's economic life. A scorer evaluates: composition-of-matter patent strength, method-of-use coverage, formulation patents, regulatory exclusivity (orphan, NCE), and the litigation track record at the relevant patent office and courts. A score of 8.0 means "IP is durable through projected peak sales (>=12 years remaining); generic entry probability is low"; a score of 4.0 means "IP coverage has known weaknesses; generic challenge is likely within the exclusivity window."

**Team & execution (10%)** evaluates whether the team has the experience to execute the plan and navigate setbacks. A scorer evaluates: CEO track record (especially prior approvals or successful exits), CMO/Chief Medical Officer regulatory experience, board composition (presence of repeat winners, independence), and the track record of major equity holders' prior portfolio companies. A score of 8.0 means "the senior team has run programs of this scope before and won"; a score of 4.0 means "first-time CEO or first-time CMO running a pivotal program."

These seven pillars are not novel. They reflect what every biotech BD diligence checklist contains. The framework's contribution at this level is *making them explicit and weighted*, not inventing them.

## The novel 8th pillar — computational infrastructure (5%)

This is the framework's novel contribution at the scorecard layer. The pillar evaluates whether the sponsor has AI/ML/data assets that materially accelerate development.

The pillar's existence is grounded in a recent literature that quantifies AI/data-asset value as a real source of firm value:

- [Enholm et al. (2021, Information Systems Frontiers, 651 citations)](https://consensus.app/papers/details/d7bfacf0db725b348f99158a48068022/) is the canonical systematic review of how organizations leverage AI to generate business value. The review identifies the first-order effects (process automation, decision support) and second-order effects (capability building, organizational learning) of AI adoption. For biotech, the relevant second-order effects are most relevant: AI-augmented target identification, ML-based trial design optimization, computational chemistry pipelines.
- [Tang et al. (2025, PLOS One)](https://consensus.app/papers/details/b37b4a1a403a5aa1bc67a285834bc80b/) develops a generative-AI-based data-asset valuation model and validates it on Chinese A-share companies, demonstrating that data assets exhibit measurable commercial value in data-intensive industries.
- [Fang et al. (2025)](https://consensus.app/papers/details/7f55ac6f22e2516485d181145a5f4569/) quantifies the AI-capability premium in market valuations, finding that AI-native firms command "outsized valuation premiums anchored to future potential" while traditional firms integrating AI experience re-rating subject to proof of returns.

The biotech-specific case is downstream of these findings but not yet rigorously quantified in the peer-reviewed literature. The practitioner-side argument: sponsors with proprietary clinical-data lakes, well-developed ML pipelines for trial-design optimization, real-world-evidence aggregation capabilities, or strong computational-chemistry stacks should be advantaged in development speed, capital efficiency, and probability of regulatory success. The 5% weight on this pillar reflects:

- The literature supports the *direction* (AI/data assets create value) strongly
- The biotech-specific *magnitude* is not yet quantified rigorously
- The 5% weight is small enough to be defensible as exploratory
- A senior reader sees the pillar's existence as a sign the framework anticipates where the field is going, not as a forecast that it has already moved

**What scores high on this pillar:**
- Proprietary clinical or real-world-evidence datasets at scale
- Demonstrated ML/AI capabilities applied to internal pipeline decisions (target ID, trial design, biomarker discovery)
- Computational-chemistry or AI-driven small-molecule design with credible publications
- Senior technical leadership with depth in ML, not just hires for headcount

**What scores low:**
- "AI partnership" announcements with no internal capability
- Headcount-only signal (a Director of AI/ML reporting to nobody specific)
- ML capabilities focused on commercial functions (CRM, sales) rather than R&D

A typical 2026 biotech sponsor scores 4-6 on this pillar. A score above 8 currently belongs to a small set of platform-AI biotechs (Recursion, Insitro, Exscientia-style operations).

## Red flags and green flags

The framework provides two flag mechanisms that override the pure aggregate-driven recommendation.

**Red flags** auto-cap the recommendation tier at "cautious" regardless of aggregate score. The framework treats certain risks as *categorical*, not *gradient* — they should not be averageable against high scores in other pillars.

Standard red flags (the framework accepts arbitrary text but the practitioner-canonical list is):

- **Going-concern risk** — sponsor under 6 months runway with no committed financing
- **Data integrity issue** — FDA Form 483 or CRL citing data-quality concerns at any active site
- **CRL without resubmission path** — most-recent FDA decision was a Complete Response Letter and the company has not articulated the response strategy
- **Core patent invalidated** — composition-of-matter or key method-of-use patent successfully challenged
- **Management exodus** — CEO, CMO, or CFO departure in the prior 90 days without a credible successor announced

The cap mechanism is one-sided: red flags only cap downward, never upward. A red flag in the context of an otherwise 9.0 aggregate produces "9.0 aggregate, cautious recommendation" — the aggregate is still reported because the underlying asset can be reconsidered after the red flag resolves.

**Green flags** boost the aggregate score by 0.5 points each (capped at 10.0). These reflect positive signals that the standard 7-pillar evaluation may not capture:

- **Insider buying >$500K** in the prior 90 days, especially by C-suite or board
- **Top-tier VC validation** — recent Series B+ from a fund with 3+ approvals in the same therapeutic area
- **Big Pharma partnership** with material economics (>$100M upfront or strong milestone structure)
- **Multi-indication platform** with at least one follow-on indication in clinical development
- **Senior team prior approvals** at the same target or in the same indication

The boost mechanism is one-sided in the opposite direction: green flags only boost, never penalize. The maximum boost from green flags is bounded by the 10.0 aggregate ceiling, so beyond a few flags additional ones have no effect (which is correct — a 9.5 score with 8 green flags should not become 13.5).

The asymmetry between red flags (categorical caps) and green flags (additive boosts) is deliberate. The decision-theoretic argument: in biotech investing, *avoiding catastrophic outcomes is more valuable than capturing marginal upside*. A red flag's information is "this asset has a specific risk that can sink it"; treating that information categorically reflects the true distribution of outcomes. A green flag's information is "this asset has a positive feature beyond the standard rubric"; treating it additively reflects that positive features compound less dramatically than catastrophic risks.

## How the scorecard interacts with rNPV

The framework reports both numbers — rNPV from the quantitative core, recommendation tier from the scorecard — and lets the user read them together. Four interaction patterns commonly emerge:

1. **High rNPV + high score + no red flag** → strong buy. The rare confluence; this is the asset to overweight in a portfolio.
2. **High rNPV + low score** → math says yes, judgment says no. Investigate the disagreement. Usually one or more pillars is flagging a structural concern that the rNPV's assumptions are not yet pricing.
3. **Low rNPV + high score** → judgment says yes, math says no. Investigate the assumptions. Usually peak sales or WACC are conservatively set; the qualitative read suggests the assumption should be revisited.
4. **High rNPV + high score + red flag** → cautious. The asset may be excellent, but a categorical risk needs resolution before the investment is actionable.

Patterns 2 and 3 are the most informative. The cases where the math and the qualitative read disagree are where the framework's two-layer structure earns its keep — neither layer alone would catch the discrepancy.

## Known limitations (consolidated for the whole methodology)

This section consolidates the limitations documented across the methodology folder. It is the single document a senior reader should consult to understand *what the framework does not claim*.

### From the PoS chain (01-pos-framework.md)

- **Base rates are population priors, not asset-specific predictions.** The modifier chain corrects this directionally; calibration of the magnitudes is approximate.
- **Biomarker-enrichment boost assumes a predictive biomarker.** The framework relies on the user to distinguish predictive from prognostic.
- **Target-validation boost is the least-empirically-grounded modifier** (+15%, calibrated against practitioner intuition).
- **BTD boost reflects probability-of-approval, not probability-of-clinical-benefit** (Mao 2025 finds BTD products often have limited HTA-assessed clinical value).
- **Cell-therapy modality multipliers are the most uncertain** (×0.65 / ×0.70 — the modality has too few Phase 3 readouts to calibrate against historical cohorts).
- **Confidence-range propagation is partial** — only modality and reflexivity uncertainty propagate into the rendered band.

### From the reflexivity adjustment (02-reflexivity-thesis.md, 06-signaling-equilibrium.md)

- **Statistical, not deterministic** — well-capitalized sponsors run failed trials; distressed sponsors occasionally succeed.
- **±15% magnitude is approximate** — Ma 2025's AUC of 0.74 implies meaningful but not overwhelming separability.
- **Does not capture all structural moderators of PoS** — team experience, scientific advisory board composition, prior approvals at the same target sit elsewhere in the framework.
- **Calibrated to post-2018 trial-design norms** — pre-2018 historical comparables may understate the gap.

### From the rNPV engine (03-rnpv-monte-carlo.md)

- **Single peak-sales draw across the exclusivity period** — no time-series sampling.
- **No competitive entry dynamics in revenue model** — peak sales is static.
- **No deal-structure modeling** — values the asset on a standalone basis; doesn't model upfronts, milestones, royalties.
- **WACC is constant across the asset's life** — dynamic-risk-rate rNPV (Dando 2020) cited but not implemented.
- **No platform optionality** — multi-indication assets valued only at lead indication.

### From the worked example (05-worked-example-adagrasib.md)

- **Cannot prove the framework would have produced the same answer prospectively** — the writeup is retrospective backtest, not prediction.
- **Generalizability beyond adagrasib's profile uncertain** — small-molecule oncology with sotorasib precedent is exactly the kind of asset BIO base rates fit; framework accuracy on rare disease, complex modalities, or distressed sponsors is more uncertain.

### From the scorecard (this document)

- **The 7 standard pillars are practitioner taxonomy, not empirically derived.** The 20% / 15% / 15% / 15% / 10% / 10% / 10% / 5% weights reflect practitioner intuition about diligence depth; they are not optimized against a held-out set of outcomes.
- **The computational-infrastructure pillar is exploratory.** The literature supports the direction (AI/data assets create value) but the biotech-specific magnitude is not rigorously quantified. The 5% weight is small enough to be defensible.
- **Red and green flag lists are practitioner heuristics**, not derived from a labeled dataset.

### Cross-cutting

- **The framework values assets at the FDA-approval gate**, not at the clinical-utility gate. This is consistent with biotech-VC valuation practice but worth knowing.
- **The framework treats US/EU regulatory pathways as primary.** China-origin assets with NMPA-first development paths require modifier choices the framework does not currently surface.
- **The framework's outputs are *normative* (this is how a disciplined reader should value the asset)**, not *positive* (this is how the market does value it). When the framework and the market disagree, the framework's prediction is well-defined; whether it's correct is an empirical question the Calibration Dashboard (v1.5) is designed to resolve over time.

These limitations are not flaws. They are the visible edges of a framework that has chosen explicit trade-offs over generality. A senior reader who reviews the limitations and disagrees with one of them should understand exactly what choice was made and where in the codebase to change it.

## See also

- [00-product-thesis.md](00-product-thesis.md) — strategic framing of the framework
- [01-pos-framework.md](01-pos-framework.md) — the PoS chain
- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the headline differentiator
- [03-rnpv-monte-carlo.md](03-rnpv-monte-carlo.md) — the rNPV engine
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the calibration narrative
- [06-signaling-equilibrium.md](06-signaling-equilibrium.md) — the formal game-theoretic foundation
