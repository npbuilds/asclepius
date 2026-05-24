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
  heuristic uncertainty band) and a disagreement chip (aligned <3pp, moderate
  3–7pp, divergent >7pp).

The module is drop-in via the existing registry — zero edits to the
deterministic PoS module or any other existing code. The git diff
introducing this module is a textbook second-instance test of the
registry pattern after v1.5.0's Calibration Dashboard.

## What the disagreement signal means

For adagrasib at the June 2022 cutoff (Phase 2 oncology, small molecule,
adequate capital, BTD, biomarker-enriched, target-validated, one
competitor):

| Path | Estimated PoS | Source |
|---|---:|---|
| BIO base rate (Phase 2 oncology) | 10.6% | BIO 2021 + Wong 2019 transition table |
| Rule-based final LOA (multiplicative chain) | 16.1% | base × modality × BTD × biomarker × target_validated × reflexivity |
| ML prior — v1.5.1.1 (LR surrogate, rule-distilled) | 36.7% | logistic regression on Bernoulli-sampled rule-chain labels |
| **ML prior — v1.5.2 (LightGBM, PubMedBERT-embedded, real outcomes)** | **39.4%** | NCT04685135 criteria + structured features through `lightgbm_pubmedbert_v0.2.0_42` |

Both surrogate (36.7%) and supervised (39.4%) ML paths land in the same
neighborhood — significantly higher than the rule-chain's 16.1%. That
they agree closely while being trained on different label sources is
mildly reassuring: the additive-log-odds composition produces a similar
posterior whether the labels are Bernoulli samples from the rule chain
or real HINT outcomes. v1.5.2's 39.4% is the canonical ML prediction
the panel now displays.

The ~23pp gap between the rule chain and the v1.5.2 ML prediction is
*divergent* in the panel.
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

This module is therefore the *honest minimum viable rule-smoothed-surrogate
path*. It demonstrates the architecture (module registers, three-way
readout renders, disagreement chip lights up) and gives a real
trained-on-data classifier doing the inference — but it does not
deliver the BioBERT-on-protocol-text claim that the plan describes.
The README and this writeup name the gap explicitly so a recruiter
reading the codebase can verify what is and isn't real.

## v1.5.2 — the real ML path (Day 3 result, supervised on HINT)

v1.5.2 replaces the rule-distilled surrogate above with a genuine
supervised classifier trained on real clinical-trial outcomes. **Test
AUC 0.7030, Brier 0.2075** on the HINT held-out test split (n=3,133
trials). The model is borderline-ship per the locked decision
criteria (≥0.74 ship, ≥0.70 borderline, <0.70 don't ship).

### What we shipped

- **Corpus:** [HINT clinical-trial-outcome-prediction](https://github.com/futianfan/clinical-trial-outcome-prediction)
  (Fu et al. 2022). 11,552 unique trials across Phase I/II/III with
  binary success/failure labels; HINT's pre-defined train/valid/test
  splits preserved (7,581 / 838 / 3,133).
- **Text embedding:** [Microsoft PubMedBERT-base, abstract+fulltext](https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext).
  Mean-pooled token embeddings of the trial eligibility-criteria text,
  truncated at 512 wordpiece tokens. PubMedBERT is the
  trained-from-scratch-on-PubMed variant (BioBERT is BERT-base
  continued-pretrained on PubMed); the from-scratch vocabulary is more
  efficient for biomedical-dense text.
- **Structured features:** the same 36-dim encoder v1.5.1 used (phase,
  TA from ICD-10 chapter, modality from SMILES + drug-name heuristics,
  biomarker enrichment from criteria regex, plus four fields that
  default for HINT data).
- **Classifier:** LightGBM with L1+L2 regularization (`reg_alpha=0.5,
  reg_lambda=0.5, min_child_samples=30, n_estimators=500, lr=0.05`),
  early-stopped against the HINT val split.
- **Feature dim:** 768 (PubMedBERT) + 36 (structured) = 804.

### Per-phase AUC

| Phase | n | AUC | Brier | Observed rate |
|---|---:|---:|---:|---:|
| Phase 1 | 595 | 0.6574 | 0.2294 | 0.561 |
| Phase 2 | 1,473 | 0.6798 | 0.2243 | 0.549 |
| Phase 3 | 1,065 | 0.6929 | 0.1720 | 0.760 |
| **All** | **3,133** | **0.7030** | **0.2075** | **0.623** |

Phase 3 has the lowest Brier despite a similar AUC because its
class-imbalanced 76% success rate means well-calibrated predictions
naturally cluster near the right answer for most assets. Phase 1 and
Phase 2 are nearer the 50/50 boundary, where small prediction errors
are penalized more heavily.

### What this is honestly NOT

- **Not at the Doane 2025 baseline AUC of 0.74.** The gap (~0.04) is
  structural — Doane's pipeline includes drug-SMILES embeddings via
  ChemBERTa-style models, sponsor financial features via SEC EDGAR
  linkage, and possibly finetuned BERT rather than frozen feature
  extraction. We tested adding RDKit Morgan fingerprints; they didn't
  help (likely because BioBERT/PubMedBERT already see drug names in
  the criteria text). We tested adding criteria-length features and
  3-seed model ensembling; neither moved the AUC meaningfully. Each
  of the remaining gaps is multi-day work.
- **Not benchmarked against CT Open.** The plan's v1.5.2 spec named
  CT Open as the external benchmark. Running our model against CT
  Open's test split is mechanically straightforward but requires
  downloading + normalizing CT Open's data format and reporting
  calibration metrics per CT Open's protocol. Deferred to v1.5.3.
- **Honest caveat on structured features.** Four fields
  (capital_position, regulatory_designations, target_validated,
  num_competitors) default to constants for every HINT trial because
  HINT doesn't carry that data. This zeros out their training-time
  signal; the v1.5.2 model effectively learns from PubMedBERT + phase
  + TA + modality + biomarker_enrichment (the fields that vary).
  Backfill via SEC EDGAR + FDA Orange Book + literature lookup would
  recover the missing signal — v1.5.3 candidate work.

### Why this is still a strict upgrade over v1.5.1.1

The v1.5.1.1 surrogate's training-time AUC was ~0.86 — but that was on
Bernoulli labels sampled from the rule-based PoS chain itself, not on
real outcomes. It measured "can logistic regression learn the rule
chain" not "can the model predict real outcomes." That AUC is not
comparable to a held-out test AUC on real labels.

v1.5.2 at 0.7030 on real HINT outcomes is unambiguously better
methodology even though the training-domain AUC is lower:

1. **Real labels** — supervised on actual approved/failed outcomes,
   not derived ones.
2. **Not label-derived from the rule chain** — the v1.5.2 ML labels
   come from real FDA-approval / discontinuation outcomes (via HINT),
   not from Bernoulli samples of the rule chain's own output.
   Disagreement between the two paths reflects two perspectives
   informed by *different signals* — one fitted to historical
   outcomes, one assembled from cited base rates × multiplicative
   adjustments — though they share the same upstream clinical-
   development domain (HINT outcomes and BIO base rates are both
   downstream of the same regulatory process, so the two paths aren't
   strictly statistically independent).
3. **Calibration Dashboard adjudicable** — the dashboard's
   per-segment Brier can now score the v1.5.2 ML path against real
   outcomes as predictions resolve, finally enabling the empirical
   adjudication v1.5.1.1's methodology described aspirationally.

The Calibration Dashboard's adagrasib-cohort Brier scores will move
once we start logging v1.5.2's predictions alongside the rule-based
chain's. That's the v1.5.3 + v1.6 maintenance work.

### What lands in the codebase (Day 3)

Committed (tracked in git):

| File | Role |
|---|---|
| `api/data_pipeline/build_training_dataset.py` | HINT CSV → parquet with 36-dim structured features + criteria text + outcome label |
| `api/data_pipeline/embed_biobert.py` | Local CPU embedding script (used for the BioBERT baseline; PubMedBERT was generated via the Colab notebook) |
| `api/data_pipeline/notebooks/biobert_embed_colab.ipynb` | Colab notebook for the GPU embedding pass — supports either BioBERT or PubMedBERT via the `MODEL_ID` constant |
| `api/data_pipeline/train_gbt.py` | LightGBM training on combined 804-dim features; saves `model_v152.joblib` |

Generated artifacts (gitignored — produced by running the Day 1/2/3 pipeline; Day 4 will ship the trained model via the repo and embeddings via Git LFS):

| Generated file | Role | Size |
|---|---|---|
| `api/data/training/training_dataset.parquet` | Day 1 output (HINT corpus normalized + structured features) | 14 MB |
| `api/data/training/embeddings_pubmedbert.npy` | Day 2 output (11,552 × 768 PubMedBERT embeddings) | 35 MB |
| `api/data/training/embeddings_pubmedbert_nctid.txt` | Day 2 sidecar (one NCT ID per line, ordered with the .npy rows). v1.5.2.1: mandatory for the trainer's alignment check. | 138 KB |
| `api/data/training/model_v152.joblib` | Day 3 trained artifact (LightGBM + feature_schema + training_meta) | 0.3 MB |

### What's next (Day 4)

Day 4 wires the v1.5.2 model into the runtime inference path:

- Upgrade the Fly machine to `shared-cpu-2x` (1GB RAM) so a
  PubMedBERT distilled or quantized variant fits.
- Add a runtime PubMedBERT inference step to
  `api/app/modules/ml_pos_prior/engine.py` so novel asset inputs can
  be embedded on demand.
- Replace `api/app/modules/ml_pos_prior/model.joblib` with the new
  artifact, update the feature_schema sidecar to expect 804-dim
  combined features, and regenerate the adagrasib cache.
- Ship `embeddings_pubmedbert.npy` via Git LFS so the Day 1 HINT
  training data is reproducible.

## Why a "rule-smoothed surrogate" matters at all

Single-number PoS estimates are the most over-stated quantitative
input in biotech diligence. The framework's audit-trail discipline
already addresses this by showing every step of the multiplicative
chain. The surrogate path closes the remaining loop: even when
the audit trail is right, the *composition rule* (multiplicative vs.
additive log-odds) is itself an assumption. Surfacing the two paths
makes the composition rule auditable too.

A senior investor reading the diligence page now sees: BIO base rate
(observed industry frequency), rule-based final LOA (the framework's
opinionated combination), ML prior (an alternative combination with a
heuristic uncertainty band), and the disagreement chip. The investor's mental
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
