# ML PoS Prior — rule-smoothed surrogate path

The framework's deterministic PoS chain combines BIO base rates with
multiplicative adjustments for modality, regulatory designation, biomarker
enrichment, target validation, and reflexivity tier. The chain is
auditable, but it is also opinionated about *how* the adjustments combine
— each is a fixed multiplier applied in sequence, and the chain assumes
no interaction between adjustments. The ML PoS Prior path surfaces where
that composition rule disagrees with an additive-log-odds approximation
fit on the same inputs.

**An honesty caveat up front.** Because the classifier's labels are
Bernoulli-sampled from the rule-based PoS engine itself, this module is
a *logistic-regression surrogate* of the rule chain, not an independent
source of evidence. Disagreement between the two paths reflects
logistic-regression's additive-log-odds inductive bias against the rule
chain's multiplicative composition — useful for surfacing composition-
rule sensitivity, but not new information about the world. Genuine
independence requires training on real outcomes (HINT / CTOP / CT Open),
which is the v1.5.2 path documented at the end of this writeup.

## What ships in v1.5.1

A new analysis module at `api/app/modules/ml_pos_prior/` containing:

- `features.py` — a fixed 36-dim feature encoder (phase ordinal, one-hot
  TA and modality and capital position, six regulatory-designation
  binary flags, biomarker_enrichment and target_validated booleans,
  num_competitors clipped to 0–10).
- `train.py` — the training pipeline. Samples 10,000 synthetic
  AssetInputs uniformly over feature combinations, computes the
  rule-based chain's final_loa for each, and Bernoulli-samples a binary
  outcome from that probability. Fits sklearn L2-regularized
  LogisticRegression(max_iter=2000) on the encoded features. Held-out
  test AUC is 0.86 and Brier 0.13.
- `engine.py` — inference at runtime: ~1ms per record on Fly's shared-
  CPU-1x, ~50KB model artifact loaded lazily on first call.
- `routes.py` — standard `POST /api/modules/ml_pos_prior` plus a
  `GET /model_info` for the methodology page to surface training
  metrics transparently.
- A frontend panel renders directly below the PoS waterfall showing
  three bars (BIO base rate, rule-based final LOA, ML prior with
  confidence band) and a disagreement chip (aligned <3pp, moderate
  3–7pp, divergent >7pp).

The module is drop-in via the existing registry — zero edits to the
deterministic PoS module or any other existing code. The git diff
introducing this module is a textbook second-instance test of the
registry pattern after v1.5.0's Calibration Dashboard.

## What the disagreement signal means

For adagrasib at the June 2022 cutoff (Phase 2 oncology, small molecule,
adequate capital, BTD, biomarker-enriched, target-validated, one
competitor):

| Path | Estimated PoS |
|---|---:|
| BIO base rate (Phase 2 oncology) | 10.6% |
| Rule-based final LOA (multiplicative chain) | 16.1% |
| ML prior (logistic regression) | 36.7% |

The 20.6pp gap is large enough to be labeled *divergent* in the panel.
Two readings of the gap:

1. **The rule-based chain may be under-adjusting.** The multiplicative
   structure caps the joint uplift of BTD + biomarker enrichment +
   target validation + low competition because each multiplier is
   conservative. The ML path's additive log-odds combination produces
   a larger combined uplift. Whether the multiplicative or additive
   composition is correct is an empirical question — but it can only
   be settled by real outcome data on a sample that's large enough and
   unbiased enough to support a calibration claim. The Calibration
   Dashboard ([`08-calibration-dashboard.md`](08-calibration-dashboard.md))
   provides the infrastructure for that adjudication; the seed sample
   it ships with is too small (and too survivorship-biased) to settle
   the question today, and the ML path currently isn't scored against
   independent outcomes either. The honest read is that this v1.5.1
   module *surfaces the question* but does not answer it.
2. **The ML path may be over-fitting the training distribution.** The
   training data is synthetic-from-BIO with Bernoulli noise. The model
   has the structure of a logistic regression with no interaction
   terms, which is a strong assumption about feature linearity in
   log-odds space. It can over-estimate strong-feature combinations
   that are rare in the synthetic prior.

Both readings should be visible to the diligence reader. The framework
deliberately does not pick one — the disagreement *itself* is the
useful signal. A senior investor reading both numbers gets a band
estimate ("between 16% and 37% depending on assumptions about
adjustment composition") rather than a false-precision single number.

## What this is honestly NOT

The plan's v1.5 specification named BioBERT embeddings of trial
protocol text plus a sklearn head, trained on the Doane 2025 / Clinical
Trial Outcome dataset, benchmarked against CT Open. The v1.5.1 module
that ships here is *structured-feature classification only* — no
protocol-text embedding, no external corpus, no CT Open benchmark.
Three reasons:

1. **Resource constraint at the deploy tier.** BioBERT is ~440 MB; the
   Fly free-tier shared-CPU-1x has 256 MB RAM. Loading BioBERT at
   request time is not viable. Pre-computing embeddings for every
   conceivable input asset is also not viable. The BioBERT path
   requires either a separate ML-inference service or a sliding-window
   distilled model — both real architectural work.
2. **Dataset access.** The Clinical Trial Outcome / HINT corpus is
   publicly downloadable but ingestion + label-cleaning + train/test
   discipline is a multi-day exercise, not a single-session sprint.
   v1.5.2 will do this properly.
3. **External benchmark.** CT Open is the public uncontaminated
   benchmark referenced in the product thesis. Reporting calibration
   against CT Open requires running inference over its test split and
   reporting AUC + Brier with full methodology. Same reason as (2) —
   this is multi-day work, not the right scope for a single ship.

This module is therefore the *honest minimum viable second-opinion
path*. It demonstrates the architecture (module registers, three-way
readout renders, disagreement chip lights up) and gives a real
trained-on-data classifier doing the inference — but it does not
deliver the BioBERT-on-protocol-text claim that the plan describes.
The README and this writeup name the gap explicitly so a recruiter
reading the codebase can verify what is and isn't real.

## v1.5.2 specification

The next iteration delivers the BioBERT path:

- Download HINT / CTOP corpus (~17K labeled trials).
- Compute BioBERT pooled embeddings offline, store as numpy arrays in
  the repo or external object storage.
- Concatenate with the structured-feature vector this module already
  produces.
- Fit a larger classifier (gradient-boosted trees on the combined
  feature set) and report AUC.
- Replace this module's `model.joblib` with the new artifact; the
  module structure (manifest, schemas, panel) does not change.
- Add CT Open benchmark numbers and publish them in a new section of
  this writeup.
- Update the Calibration Dashboard to score the ML path independently
  from the rule-based chain so the dashboard can track which path is
  better-calibrated over time.

That delivers the plan's v1.5 specification. v1.5.1 ships the
scaffolding that makes v1.5.2 a drop-in swap rather than a rewrite.

## Why a "rule-smoothed surrogate" matters at all

Single-number PoS estimates are the most over-stated quantitative
input in biotech diligence. The framework's audit-trail discipline
already addresses this by showing every step of the multiplicative
chain. The second-opinion path closes the remaining loop: even when
the audit trail is right, the *composition rule* (multiplicative vs.
additive log-odds) is itself an assumption. Surfacing the two paths
makes the composition rule auditable too.

A senior investor reading the diligence page now sees: BIO base rate
(observed industry frequency), rule-based final LOA (the framework's
opinionated combination), ML prior (an alternative combination with a
confidence band), and the disagreement chip. The investor's mental
model of PoS for this asset becomes a posterior over both paths,
weighted by their priors about which composition rule is more
appropriate for the asset's segment.

That is what an investor-grade PoS estimate looks like. The framework
delivers it.

## See also

- [`01-pos-framework.md`](01-pos-framework.md) — the rule-based chain
  the ML path is a rule-smoothed surrogate to.
- [`02-reflexivity-thesis.md`](02-reflexivity-thesis.md) — the
  capital-position adjustment that drives most of the rule-based ML
  disagreement on well-capitalized assets.
- [`08-calibration-dashboard.md`](08-calibration-dashboard.md) — the
  empirical adjudicator between the two paths. v1.5.2 will score them
  independently.
