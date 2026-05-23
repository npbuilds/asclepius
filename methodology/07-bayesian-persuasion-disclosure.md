# Bayesian persuasion and biotech disclosure

The framework's Game-Theory Adversary agent treats biotech sponsor disclosures
not as exogenous information but as strategically chosen signals. This document
gives that lens its empirical grounding — the same discipline the reflexivity
adjustment gets from `06-signaling-equilibrium.md`.

## Why this matters

Every disclosure decision a biotech sponsor makes — which subgroup analyses
to report, which secondary endpoints to feature, when to issue press
releases relative to fund-raising — is a choice over what signal structure
to reveal. Kamenica and Gentzkow (2011) showed that a rational sender with
a known signal structure can move a receiver's posterior beliefs in any
direction the sender prefers, subject only to Bayes-plausibility. The
sponsor is the sender; the investor is the receiver; the signal structure
is the protocol-defined-but-discretionary disclosure pattern.

This frame is not cynical. Sponsors have legitimate reasons to disclose
strategically — protecting trial integrity, sequencing communications,
avoiding selective leakage. But from the investor's read, the framework's
recommendation should incorporate the *equilibrium-optimal* signal-
extraction behavior, not naive face-value reading of the press release.

## Four empirically-grounded patterns

The Adversary agent's persuasion lens pattern-matches against four
disclosure behaviors documented in peer-reviewed work. Each is detectable
from public information about an asset.

### 1. Competitor-approval-triggered disclosure suppression

[Kao (2024, *Management Science* 71(7):5948-5970)](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2022.01161)
applies a difference-in-differences design to FDAAA-mandated trial-results
disclosures and shows that a competitor's drug receiving FDA priority
review **reduces the focal firm's probability of disclosing its own trial
results within two years by approximately 13 percentage points**. Pharma
firms are roughly 25 percentage points worse than public institutions on
mandated disclosure compliance overall; the cross-firm cost imposed by a
competitor's approval is dominant.

The mechanism is information-economic: when a competitor's approval
shifts the receiver's prior about category viability, the focal firm's
posterior — conditional on no disclosure — drifts upward (Akerlof's
absence-of-bad-news read). Disclosure becomes costlier and is delayed
strategically. The FDA has not collected any of the $37B+ in potential
fines for FDAAA non-compliance, so the equilibrium is sustained.

**Detectable signal**: cross-reference the asset's named competitors'
priority-review/approval dates against the sponsor's last clinical-results
press release on the asset. Flag any sponsor whose competitor was
approved >18 months ago without a corresponding focal-asset disclosure.

### 2. Pre-announcement information leakage

[Rothenstein, Tomlinson, Tannock and Bouchard (2011, *JNCI* 103(20):1507)](https://academic.oup.com/jnci/article-abstract/103/20/1507/904625)
analyzed 23 randomized cancer trials whose Phase 3 readouts moved company
stock prices. They found that **price drift begins in the direction of
the eventual result well before the formal announcement**, with sustained
post-announcement movements of ~9.4% for positive Phase 3 readouts.
Negative readouts show asymmetric, larger drawdowns ([PLOS ONE
follow-up, PMC3737210](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3737210/)).
The drift is most plausibly explained by information leakage to a
restricted set of informed traders before the press release.

**Detectable signal**: if the sponsor's stock has drifted meaningfully —
say, >5% over the 30 trading days before a disclosed readout — the press
release is confirming an already-leaked private signal rather than
delivering new information. A framework's PoS estimate that has not been
explicitly contemporaneous (i.e., that reads current sell-side consensus)
has already double-counted the leakage. Flag and discount the
informational content of the disclosure.

### 3. Post-hoc subgroup disclosure as signal partition

The publication of post-hoc subgroup analyses in oncology trials grew
from 384 (2000-2014) to 695 (2019-2022) — a near-doubling on a per-trial
basis ([Yi et al. 2024, *Therapeutic Advances in Medical Oncology*,
PMC11025370](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11025370/)).
Roughly 95% of these analyses do not apply multiplicity adjustment.
Under Kamenica-Gentzkow's framework, this is the textbook persuasion-
optimal behavior: the sponsor chooses which subgroup to publish
*after* observing the data, and chooses the one whose posterior most
favors the sponsor's preferred receiver action.

**Detectable signal**: any press release whose headline names a subgroup
not pre-specified in the SAP — especially when the all-comers/ITT
result is omitted from the same release — is a textbook persuasion-
optimal signal partition. The Adversary should flag this as moderate-
to-critical, depending on whether the omitted ITT result is recoverable
from the underlying registration data.

### 4. Endpoint substitution and hierarchy omission

Documented commentary in the practitioner literature — most accessibly
[Derek Lowe in *Science*](https://www.science.org/content/blog-post/wait-we-didn-t-tell-you-about-endpoint)
— flags the pattern of biotech press releases that do not state the
prespecified primary endpoint's place in the testing hierarchy, or that
foreground secondary endpoints when the primary did not separate. The
SAP hierarchy is statistical preregistration; a release that buries it is
choosing a signal structure that obscures the analytical pre-commitment.

**Detectable signal**: a readout release that reports a P-value on a
secondary endpoint but not on the primary, or that does not name the
hierarchy position of the primary, is an equilibrium-optimal persuasion
move. Flag and downgrade.

## What this lens does *not* claim

This is a frame for investor reading, not a claim about sponsor intent.
A sponsor who engages in any of the four patterns above may be acting in
the best interests of the asset's development; the lens does not infer
motive. What it does do is treat the *disclosure choice itself* as
endogenous to the sponsor's information set, so the framework's
posterior on PoS is not contaminated by face-value reading of optimized
signals.

This is the analytical move that distinguishes investor-grade reading
of clinical disclosures from press-release-driven reading. The
Adversary's persuasion lens operationalizes it.

## Cross-references

- [`02-reflexivity-thesis.md`](02-reflexivity-thesis.md) — the framework's
  primary signaling claim, of which Bayesian persuasion is the
  receiver-side complement.
- [`06-signaling-equilibrium.md`](06-signaling-equilibrium.md) — Spence-
  style separating equilibrium and the formal grounding for reflexivity.
- [`05-worked-example-adagrasib.md`](05-worked-example-adagrasib.md) —
  applies the winner's-curse adjustment, the auction-theory complement
  to this lens.

## Canonical citations

- Kamenica, E. and Gentzkow, M. (2011). [Bayesian Persuasion](https://www.aeaweb.org/articles?id=10.1257%2Faer.101.6.2590). *American Economic Review* 101(6).
- Kao, A. (2024). [Information Disclosure and Competitive Dynamics](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2022.01161). *Management Science* 71(7):5948-5970.
- Rothenstein, J., Tomlinson, G., Tannock, I. and Bouchard, M. (2011). [Company stock prices before and after public announcements related to oncology drugs](https://academic.oup.com/jnci/article-abstract/103/20/1507/904625). *Journal of the National Cancer Institute* 103(20):1507.
- Yi, B. et al. (2024). [Characteristics of post-hoc subgroup analyses of oncology trials](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11025370/). *Therapeutic Advances in Medical Oncology*.
- Lo, A.W. and Thakor, R.T. (2022). [Financing Biomedical Innovation](https://www.annualreviews.org/content/journals/10.1146/annurev-financial-031721-081537). *Annual Review of Financial Economics* 14:231-270.
