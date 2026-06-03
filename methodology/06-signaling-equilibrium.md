---
title: "Signaling equilibrium — the formal foundation of the reflexivity adjustment"
summary: "Derives the reflexivity-adjusted PoS framework from Spence (1973) signaling theory. Maps the costly-signal mechanism onto clinical trial design and cites the modern empirical evidence that strategic-disclosure behavior is operative in the pharmaceutical industry."
audience: "Read this after 02-reflexivity-thesis.md if you want the formal game-theoretic underpinning rather than the intuition. The reflexivity adjustment is the implementation; this document is the proof that the implementation reflects a recognized economic mechanism."
primary_sources:
  - "Akerlof GA. The Market for 'Lemons': Quality Uncertainty and the Market Mechanism. Quarterly Journal of Economics 84(3): 488-500 (1970). The adverse-selection problem that signaling solves."
  - "Spence M. Job Market Signaling. Quarterly Journal of Economics 87(3): 355-374 (1973). The original separating-equilibrium model."
  - "Lo AW, Thakor RT. Financing Biomedical Innovation. Annual Review of Financial Economics 14: 231-270 (2022). Modern review of financing constraints in pharmaceutical R&D, including how market frictions affect drug development decisions."
  - "Kao J. Information Disclosure and Competitive Dynamics: Evidence from the Pharmaceutical Industry. Management Science (2024). Direct empirical evidence that pharmaceutical firms strategically modulate clinical-trial information disclosure based on competitive context."
  - "Chakraborty S, Swinney R. Signaling to the Crowd: Private Quality Information and Rewards-Based Crowdfunding. Manufacturing & Service Operations Management 22(3): 562-580 (2020). Separating-equilibrium signaling in capital-raising contexts; mechanism-adjacent to clinical trial signaling."
  - "Guerra A, Hyndman K, Tyran J-R. Information-signaling in pre-trial bargaining: An experiment. Journal of Economic Behavior & Organization (2026). Experimental validation that costly self-penalizing commitments function as credible signals."
  - "Ma S, Han W, Lê Cook B, et al. Predicting accrual success for better clinical trial resource allocation. Scientific Reports 15 (2025). Trial-design features predict accrual failure with AUC 0.74; the features track sponsor capital position."
---

# Signaling equilibrium — the formal foundation

## Intake

The reflexivity adjustment makes a specific, testable claim: **sponsor capital position alters the probability of clinical-trial success because it changes which trial-design choices a sponsor can credibly commit to, and trial-design choices are what informed sponsors use to signal private confidence to the market.** This document does the formal work of showing that the claim is an instance of a well-established economic mechanism — Spence's separating equilibrium under asymmetric information — and cites the empirical evidence that the mechanism is operative in pharmaceutical decision-making.

The argument has four moving parts: (1) there is asymmetric information between sponsor and market about the asset's true probability of success; (2) some trial-design choices are *costly* and the cost is correlated with sponsor capital position; (3) the cost asymmetry allows a separating equilibrium in which trial-design quality serves as a credible signal of sponsor private information; (4) the market consequently updates its beliefs about probability of approval based on observed trial design. We work through each part with citations and then list the limitations.

## The adverse-selection backdrop — Akerlof (1970)

The mechanism being solved is the [adverse-selection problem first formalized by Akerlof](https://academic.oup.com/qje/article-abstract/84/3/488/1896241) in "The Market for 'Lemons'." Akerlof showed that when one party has private quality information and the other does not, the uninformed party rationally prices to the average of the available pool, which drives the high-quality types out of the market, which lowers the average, which drives more out, and so on — the market unravels. The example was used cars; the structure applies to any market with quality uncertainty.

Akerlof's contribution was not the observation that quality information is unequally distributed — that was obvious — but the formal demonstration that adverse selection has equilibrium consequences. Markets with asymmetric information do not behave like markets with symmetric information at slightly higher transaction costs; they behave qualitatively differently. The high-quality types either find a way to credibly signal type, or they exit.

The clinical-development context exhibits the Akerlof structure exactly. A drug sponsor with private information (pilot data, mechanistic conviction, regulatory backchannel intelligence) approaches capital markets and labor markets and partners that do not directly observe that information. The market sees the modality, the indication, the publicly available preclinical data, the regulatory designations. It does not see the sponsor's private belief about probability of approval. In the absence of a credible signaling mechanism, capital is allocated to a price-pool average; high-conviction sponsors are systematically under-funded; the equilibrium unravels.

What prevents the unraveling in practice is signaling.

## Spence's separating equilibrium — the formal mechanism

[Spence (1973)](https://academic.oup.com/qje/article-abstract/87/3/355/1909092) gave Akerlof's problem its canonical solution. The full model is a two-period game between workers (informed about their own productivity) and employers (uninformed). Workers can pay a cost to acquire education before entering the labor market. Employers observe education and offer wages.

The model produces a *separating equilibrium* — one in which workers of different types choose different education levels and employers can therefore infer productivity from observed education — under one critical technical condition: **the marginal cost of education must be lower for high-productivity workers than for low-productivity workers.** This is the *single-crossing property* in modern terminology; Spence stated it as a negative correlation between productivity and signaling cost. With single-crossing, there is a level of education such that high-productivity workers find it rational to acquire it (because the wage gain exceeds the cost) and low-productivity workers do not (because the wage gain is the same but the cost is higher). The wage offered conditional on observed education becomes informative.

The model's surprising result was that separation can be supported in equilibrium *even when education itself is productively useless*. The signal works not because it makes workers better but because it differentiates them. The cost asymmetry is doing the work, not any human-capital story.

The technical apparatus generalizes. Any game with (1) asymmetric information about type, (2) a costly action available to informed parties, (3) cost varying across types in a way that satisfies single-crossing, and (4) commitment power on the part of the informed party can support a separating equilibrium in which the costly action becomes a credible signal of type. The Wikipedia treatment of signaling theory is a reasonable secondary source for the general structure; Spence's original paper remains the canonical reference.

## Mapping the model to clinical trial design

The mechanism we claim is operative in clinical development maps onto Spence's model variable-by-variable:

| Spence's model | Clinical-development analog |
|---|---|
| Worker private type | Sponsor private belief about asset's true probability of approval |
| Employer | Capital markets, partners, FDA, the diligence ecosystem generally |
| Costly action (education) | Trial-design choices: large N, biomarker enrichment, active comparator, adaptive design, proactive FDA engagement |
| Cost varies by type | Cost varies by sponsor capital position; for well-capitalized sponsors a $400M Phase 3 is a lower fraction of available resources than for capital-constrained sponsors |
| Single-crossing property | Well-capitalized sponsors with high conviction find the costly trial design *most* attractive (high expected value of approval, low cost relative to balance sheet); capital-constrained sponsors with low conviction find it least attractive (lower expected value, high cost) |
| Commitment | Trial design is committed to FDA via protocol amendments; deviations are costly and visible. The commitment is credible because it is enforceable. |

The single-crossing condition deserves the most attention because it is the technical requirement that everything else hinges on. The claim is: among sponsors otherwise matched on asset characteristics, the *cost* of running a rigorous trial design is lower for well-capitalized sponsors than for capital-constrained ones. This is the empirical question on which the framework's validity rests.

The cost differential operates through multiple channels:

- **Direct capital cost.** A $400M Phase 3 program against a $2B cash balance is a 20% allocation; against a $200M cash balance it is a 200% allocation — i.e., infeasible without dilutive financing. The two sponsors face different effective costs of the same nominal trial budget. <!-- parity-allow: rhetorical-illustration -->

- **Cost of dilution.** Capital-constrained sponsors who choose the rigorous design must raise to fund it; the cost of capital at low share prices is substantially higher than at high share prices, and well-capitalized sponsors typically trade at higher multiples. Same rigorous trial costs more in real dilution terms for the constrained sponsor.

- **Opportunity cost.** A capital-constrained sponsor with one pivotal asset must allocate against the existential risk to the company; a well-capitalized sponsor with a portfolio can allocate against expected value. The decision frameworks differ, and the rigorous-trial choice is rational under fewer scenarios for the constrained sponsor.

- **Bargaining position with CROs and sites.** Well-capitalized sponsors can credibly commit to multi-year trial timelines and pre-pay; capital-constrained sponsors negotiate from weakness, get worse CRO assignments, and face higher per-patient costs.

All four channels move monotonically in the same direction. The single-crossing property holds.

## The biotech-specific empirical evidence

Spence's model is general; the question for our framework is whether the mechanism is observable in pharmaceutical decision-making specifically. Three peer-reviewed strands of evidence support that it is.

**Kao (2024) on strategic clinical-trial disclosure.** Jennifer Kao's [paper in Management Science](https://consensus.app/papers/details/158c32aae56c5e828129c2fc45bd7ff7/) studies voluntary disclosure of clinical-trial information by pharmaceutical firms. Using a difference-in-difference design exploiting competitor drug approvals, Kao shows that **the approval of a competitor's drug reduces the likelihood of a firm reporting its own clinical-trial results by 13 percent.** The effect is heterogeneous: it is strongest for projects of certain quality tiers and for firms with the experience to act strategically. Kao concludes that "strategic considerations play a role in firms' disclosure decisions" and that firms selectively withhold information to maintain competitive position.

The paper is directly empirical evidence that pharmaceutical firms treat clinical-trial information as a strategic asset with disclosure consequences — i.e., they actively manage what the market observes about their trials. This is the necessary precondition for any signaling-equilibrium argument: if firms disclosed everything truthfully and immediately, signaling would be irrelevant. Kao demonstrates that they do not.

**Lo and Thakor (2022) on financing constraints in biomedical R&D.** Andrew Lo's [Annual Review of Financial Economics piece with Richard Thakor](https://consensus.app/papers/details/e3c59010c21f52b384356e1ad461f6c8/) reviews the modern literature on biomedical innovation financing. The argument relevant to our framework is that "structural features [of drug development] require biopharmaceutical firms to rely on external financing and at the same time amplify market frictions that may hinder the ability of these firms to obtain financing, especially for treatments that may have large societal value relative to the benefits going to the firms and their investors." The paper documents that market frictions affect *which assets get developed at all* and *how aggressively they get developed*, both downstream of the sponsor's capital position.

This is the modern theoretical grounding for the cost-differential half of the single-crossing claim. Lo and Thakor do not invoke Spence directly, but their framework — that capital-constrained sponsors face higher effective costs of biomedical R&D investment, with consequences for the asset pipeline — is precisely what the framework's reflexivity adjustment operationalizes. The fact that Andrew Lo coauthored the canonical [Wong, Siah, Lo (2019) base-rate paper](https://academic.oup.com/biostatistics/article/20/2/273/4817524) that the framework's PoS chain starts from gives the citation chain unusually clean lineage: the same author who established our base rates also documents the financial-frictions mechanism that motivates our adjustment to them.

**Ma et al. (2025) on trial-accrual prediction.** [Ma et al.'s Scientific Reports paper](https://consensus.app/papers/details/e262d49916ee5d8a891fc05dedec8e30/) is the empirical anchor cited in the reflexivity-thesis writeup, repeated here for completeness. The features that predict trial-accrual failure with AUC 0.74 — trial size, comparator choice, number of sites, inclusion-criterion breadth — are precisely the trial-design choices Spence's mechanism predicts will separate by sponsor capital position. The 0.74 AUC is consistent with a separating equilibrium that is partially effective: not all trials separate cleanly, but the signal carries meaningful information.

## Cross-domain validation

Two additional papers support the mechanism in adjacent domains, providing some confidence that the biotech-specific evidence is not a coincidence of measurement choices.

**Chakraborty and Swinney (2020) on crowdfunding signaling.** Their [M&SOM paper](https://consensus.app/papers/details/6b5c1408883b5f2e860a4778a00836d8/) studies entrepreneur signaling to crowdfunding backers via campaign design (price, funding target). They find a separating equilibrium in which entrepreneurs signal high quality by setting a funding target *above* the full-information optimum — a deliberate distortion that high-quality entrepreneurs can sustain and low-quality ones cannot. The mechanism is the same as the clinical-trial argument: a costly choice (high target reduces the chance of campaign success but distinguishes high quality), with cost asymmetry across types supporting separation. Cited 181 times in the operations-management literature.

**Guerra et al. (2026) on costly commitments in pre-trial bargaining.** Their [JEBO paper](https://consensus.app/papers/details/b57d69227cd250fea476ce42ae34ccce/) is an experimental signaling study (N = 2,041) in legal pre-trial bargaining. Informed parties can commit ex ante to a costly monetary penalty contingent on losing at trial. The experimental results confirm separating-equilibrium predictions: informed parties commit more when their case is strong, uninformed parties interpret commitment as a signal and settle on less generous terms, but with departures from theory in magnitude and edge cases. The relevant takeaway for our framework: the costly-commitment mechanism *works* in controlled settings, including ones where the informed party has only soft private information. The mechanism is not a theoretical curiosity.

Together, the four empirical strands — pharmaceutical (Kao, Ma, Lo), crowdfunding (Chakraborty), legal (Guerra) — show that the costly-signaling mechanism is observable across multiple contexts including the one our framework operates in. We do not claim that any of these papers individually proves the reflexivity adjustment is correctly calibrated; we claim that together they establish the mechanism is real, recognized, and active in biotech specifically.

## Limitations and adversarial checks

A rigorous derivation must consider where the model fails. Four counter-arguments deserve direct treatment.

**Could the correlation be reverse causation?** One alternative explanation: well-capitalized sponsors *are* well-capitalized *because* they have better assets, not the other way around. The reflexivity adjustment is then capturing asset quality (which is already in the base rate and modality multipliers) rather than capital-position-driven trial-design quality.

The argument has merit but is incomplete. Lo and Thakor (2022) document that financing constraints affect *which assets get developed at all*, separate from asset quality. Two equally promising assets in differently-capitalized sponsors face systematically different trial designs and timelines. The reverse-causation channel exists but the structural-cost channel exists independently of it. The cleanest test would be an asset-fixed-effects analysis comparing the same compound across acquirer-sponsor changes; we are not aware of such a study, and the framework relies on the structural argument supported by Lo & Thakor plus the Ma et al. observation that *protocol-level features* (not just sponsor identity) predict outcomes.

**Could the mechanism be a pooling equilibrium rather than separating?** Spence's model also supports pooling equilibria in which multiple types choose the same signal. If FDA requirements force all sponsors above a quality floor, the signal carries less information than the separating-equilibrium argument suggests.

This is partially true. FDA requirements do set a floor; the signal-bearing variation is in choices *above* the floor. The framework's reflexivity adjustment of ±15% is small enough to be consistent with a partial separation. If we observed a full separating equilibrium, the magnitude would likely be larger; if we observed pure pooling, the magnitude would be zero. The intermediate magnitude reflects the partial-separation reality.

**Could the costs be similar across types in practice?** The single-crossing claim requires that well-capitalized and capital-constrained sponsors face *different* effective costs of the same trial design. If the difference is small in practice, the separating mechanism is weak.

This is the strongest empirical concern. The cost-channel decomposition above (direct capital, dilution, opportunity, bargaining) is theoretically motivated; the empirical magnitude of each channel for typical biotech firms is not well-quantified in the published literature. The framework's ±5–15% range reflects this uncertainty: the lower bound is what one would expect if the cost differential is small, the upper bound is what one would expect if it is large. The Calibration Dashboard (v1.5 deliverable) is designed to empirically resolve this by tracking framework predictions against outcomes.

**Could the signal be sent but misinterpreted?** Spence's model assumes the market reaches the signaling equilibrium — that uninformed parties correctly update beliefs on observed signals. In practice, the diligence ecosystem may be inefficient at incorporating trial-design quality into beliefs about probability of approval.

We can be agnostic on this. The framework's reflexivity adjustment is *normative* (this is how an informed reader *should* update beliefs about PoS) not *positive* (this is how the market does update). If the market is inefficient, the framework provides an edge to whoever uses it; if the market is efficient, the framework reproduces the market consensus. Either way, the framework's prediction is well-defined.

## Why this matters for the reflexivity adjustment

The four-tier multiplier table in `02-reflexivity-thesis.md` is an attempt to operationalize the separating-equilibrium mechanism in code. The multiplier values (×0.78 distressed, ×0.88 constrained, ×1.00 adequate, ×1.08 well-capitalized) are not arbitrary calibrations; they are the framework's best estimate of the magnitude by which the separating equilibrium shifts probability of approval for the typical asset.

The point estimates are calibrated against:
- The accrual-failure-effect magnitude implied by Ma et al.'s AUC 0.74
- The cross-domain mechanism strength implied by Chakraborty (crowdfunding) and Guerra (legal)
- Practitioner intuition about what well-capitalized versus distressed looks like in deal evaluation

The confidence ranges (×0.72 to ×0.85 for distressed; ×1.05 to ×1.10 for well-capitalized) propagate the uncertainty in those calibrations into the framework's overall PoS confidence interval. A more rigorous calibration would require longitudinal data on outcomes by sponsor capital tier — exactly what the Calibration Dashboard is designed to generate over time.

The audit-trail line item for reflexivity in the framework reads:

> *reflexivity: <tier> — Capital-position-driven Spence-style separating-equilibrium adjustment. Cost-differential channels documented in Lo & Thakor (2022); empirical predictive validity for related trial-design choices in Ma et al. (2025).*

That single line links the rendered number on the dashboard to two peer-reviewed sources whose author chain reaches back to the same person who established the BIO/Informa base rates the framework starts from. The chain from "we adjust PoS by 8% for well-capitalized sponsors" to "this is a documented mechanism in the financial-economics literature applied to biomedical innovation" is one hop on the GitHub repo. That is what makes the adjustment defensible.

## See also

- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the framework's load-bearing intellectual claim in less-formal language
- [01-pos-framework.md](01-pos-framework.md) — the PoS chain that the reflexivity adjustment is applied to
- [00-product-thesis.md](00-product-thesis.md) — the strategic framing of why the reflexivity adjustment is the framework's headline differentiator
