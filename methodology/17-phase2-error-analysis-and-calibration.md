# v1.5.9 — Phase-2 error analysis: hypothesis falsified, calibration shipped

[v1.5.6](14-phase-stratified-retrain.md) named the open thread that
v1.5.7 and v1.5.8 didn't close: **within-Phase-2 AUC on held-out CTO is
0.55, and the ceiling is informational.** Two consecutive feature-
engineering experiments tried to lift it and both produced negative
results — a label leak ([/15](15-trial-design-features-negative-result.md))
and a null effect ([/16](16-planned-enrollment-null-effect.md)).

v1.5.9 takes a different angle. Not "find a better feature" — *characterize
the existing model's failure mode*. If we can describe *when* the model
is unreliable, we can flag it at inference. The original hypothesis was
specific and falsifiable: **the wrongest Phase-2 predictions have a
characterizable structure (specific therapeutic areas? modalities?
biomarker enrichment?)** that we can use to mark a "low-confidence"
segment.

That hypothesis was falsified. But the investigation surfaced a different,
generalizable failure mode that *is* fixable — and v1.5.9 ships the fix.

## The investigation

### Step 1 — Inspect the wrongest predictions per direction

On the held-out CTO Phase-2 test set (n=212, base rate 23%), rank trials
by `(prediction - truth)²` and inspect the top 10 in each direction:

**False-positive cluster** (model predicted high, was failure):
- **9/10 are `small_molecule`**
- **0/10 have biomarker enrichment**
- 0/10 are oncology; mix of `other`, `autoimmune`, `infectious`, `metabolic`
- Predictions in [0.54, 0.64]

**False-negative cluster** (model predicted low, was success):
- 5/10 have biomarker enrichment
- 4/10 are oncology
- Predictions in [0.18, 0.25]

Two crisp patterns. The model appears to be over-confident on
non-oncology small-molecules without biomarkers and under-confident on
biomarker-enriched oncology trials.

### Step 2 — Slice-AUC by feature

Group the test set by therapeutic area, modality, biomarker enrichment,
and modality × biomarker. Look for slices where AUC collapses:

| Slice | n | base | mean_pred | AUC |
|---|---|---|---|---|
| Phase-2 overall | 212 | 0.23 | 0.35 | 0.555 |
| oncology | 92 | 0.20 | 0.30 | 0.563 |
| autoimmune | 12 | 0.17 | 0.43 | 0.450 |
| infectious | 16 | 0.25 | 0.42 | 0.500 |
| **cns** | 12 | 0.25 | 0.34 | **0.222** |
| small_molecule × biomarker=False | 100 | 0.25 | 0.37 | **0.484** |
| small_molecule × biomarker=True | 42 | 0.26 | 0.36 | **0.707** |
| mAb × biomarker=True | 35 | 0.26 | 0.29 | 0.457 |

The model's discrimination is **strong** on small-molecule + biomarker
(AUC 0.71) and **at or below random** on small-molecule without
biomarker (0.48), infectious (0.50), autoimmune (0.45), and CNS (0.22).
A natural candidate rule emerges:

> **High-trust segment** = `oncology OR biomarker_enrichment=True`
> **Low-trust segment** = the rest

Bootstrap-tested on the Phase-2 test set: high-trust AUC 0.59,
low-trust AUC **0.500 exactly**, Δ +0.09 with 95% CI [−0.11, +0.28]
and 82% of bootstrap samples positive. The point estimate is
encouraging; the CI is wide due to n=92 / n=120 subgroup sizes.

### Step 3 — Cross-phase falsification (the test that killed the rule)

Before shipping a low-confidence flag, the discipline lesson from v1.5.7
+ v1.5.8 says: *test the rule on the data you didn't use to derive it.*
If the high-trust / low-trust split is a real structural pattern of how
PubMedBERT + LightGBM uses eligibility-criteria text, it should hold on
Phase-1 and Phase-3 too. Same rule, same model, different held-out
phase-test sets:

| Phase | Overall AUC | High-trust AUC | Low-trust AUC |
|---|---|---|---|
| Phase 1 | 0.624 | 0.509 | **0.754** ← *inverted* |
| Phase 2 | 0.555 | 0.592 | 0.500 |
| Phase 3 | 0.556 | 0.515 | 0.604 ← *inverted* |

**The rule inverts on Phase 1 and weakly on Phase 3.** If the
high-trust segment were structurally where the model discriminates well,
we'd expect at least directional consistency. We get the opposite. The
Phase-2 pattern is **overfit to Phase-2 test-set noise**, not a real
characterization of the model's failure mode.

A v1.5.9 that shipped a "low-confidence flag for non-oncology,
non-biomarker assets" would have been a methodologically-quiet version
of the v1.5.7 enrollment leak: a real-looking pattern on n=212 that
doesn't survive contact with n=134+140 from adjacent phases. Don't
ship it.

### Step 4 — The pattern that *did* generalize: systematic over-prediction

While testing the rule cross-phase, a different pattern stood out:

| Phase | Mean prediction | Actual base rate | Over-prediction |
|---|---|---|---|
| Phase 1 | 0.273 | 0.119 | **+15.4 pp** |
| Phase 2 | 0.351 | 0.231 | **+12.0 pp** |
| Phase 3 | 0.554 | 0.436 | **+11.8 pp** |

**The model over-predicts success by 12-15 pp across all three phases**
on held-out CTO. Consistent. Generalizable. Diagnosable.

The mechanism is mechanical: the training set is HINT-dominated. For
Phase 2, 5,489 of 6,179 training rows come from HINT, which has a 49%
Phase-2 success rate. CTO Phase 2 train (which was also in training)
has only 690 rows. The model's marginal-distribution prior is pulled
toward HINT's 49%. When evaluated on the CTO distribution (23%), it
systematically overshoots.

This isn't a feature problem — it's a calibration problem.

### Step 5 — Post-hoc isotonic calibration

The standard fix for "well-discriminating model with bad calibration"
is a monotonic post-hoc transform. Two candidates:

**Platt scaling** (2-parameter logistic):
- Phase-1: Brier 0.133 → 0.103 (−22%), AUC unchanged
- Phase-2: Brier 0.195 → 0.180 (−8%), **AUC 0.555 → 0.445** (rank-flipped — fails)
- Phase-3: Brier 0.277 → 0.244 (−12%), AUC unchanged

The Phase-2 Platt collapse is diagnostic: it means the LightGBM logit on
Phase-2 *valid* is anti-correlated with the label (i.e. the valid AUC <
0.5), so Platt's logistic refit learns to invert. Phase-2 valid and
Phase-2 test disagree on which direction the predictions should go —
a second-order overfit signal. Platt is dangerous here.

**Isotonic regression** (non-parametric monotonic):
- Phase-1: Brier 0.133 → 0.127 (−5%), AUC 0.624 → 0.554 (−0.07)
- Phase-2: Brier 0.195 → 0.175 (−10%), AUC 0.555 → 0.535 (−0.02)
- Phase-3: Brier 0.277 → 0.242 (−13%), AUC 0.556 → 0.557 (no change)

Isotonic is safer. Brier (the calibration-relevant metric — *how
close is the predicted PoS to the actual frequency?*) improves
substantially everywhere. AUC (the ranking-relevant metric) is
essentially preserved on Phase 2 and Phase 3 and drops 7 pp on Phase 1.

The Phase-1 AUC cost deserves explicit framing. **AUC measures
ranking; Brier measures calibration.** They can move in opposite
directions under a monotonic transform when the calibration set and
test set disagree on the ordering of low-probability cases. For a
biotech-VC use case where the PoS number anchors investment math
(an rNPV multiplier), calibration is the load-bearing metric;
the LOA microsplit in the diligence UI shows a probability not a
ranking. Better calibration > marginally better ranking.

## What ships

**Per-phase isotonic calibrators**, fit on the CTO valid split per phase
(n=100, 159, 105 respectively), attached to the existing
`api/app/modules/ml_pos_prior/model.joblib` artifact as a new
`calibrators` key alongside the existing `phase_models`, `bootstrap_models`,
and `conformal` payloads.

The engine's `_load_model` picks up the calibrators on next start
(absent → legacy raw-prediction path, fully backward-compatible). At
inference, after the raw `predict_proba` and the bootstrap-band
computation, the engine applies the phase-appropriate calibrator to the
point estimate AND to the band endpoints. Isotonic is monotonic, so
transforming endpoints preserves the band's coverage guarantee.

Code surfaces touched:
- `scripts/fit_isotonic_calibrators.py` — fits and writes calibrators
- `api/app/modules/ml_pos_prior/engine.py` — load + apply at inference
- `api/app/modules/ml_pos_prior/tests/test_engine.py` — covers the new
  load tuple shape; the legacy synthetic-artifact test path stays
  uncalibrated (empty calibrators dict)

The artifact now carries a `calibration_meta` block recording the
method (`isotonic_regression`), the fit set (`cto_valid_per_phase`),
the out-of-bounds policy (`clip`), and the per-phase n.

**No retraining.** The v1.5.6 phase-stratified LightGBM is unchanged.
v1.5.9 is a post-hoc calibration layer on top of it. That's deliberate
— retraining would have introduced run-to-run variance (the same
training-noise issue that confounded v1.5.8's apparent +2.2pp lift) and
made the calibration effect un-isolable.

## Why we ship the negative result too

The four-experiment chain — *wrongest-prediction inspection* → *slice
AUC* → *cross-phase falsification* → *systematic-bias diagnosis* — is
the deliverable here, not just the calibrator. A reader who absorbs
this writeup learns:

1. **The model's failure mode is not a feature segment.** Don't try to
   "flag low-confidence Ph2 oncology" — the obvious-looking rule
   doesn't generalize.
2. **The model's failure mode IS a calibration drift.** The +12-15 pp
   over-prediction is consistent across phases and mechanistically
   explained by training-set base-rate domination.
3. **The fix is cheap.** Isotonic regression on n=100-159 per phase,
   applied at inference. No retraining. Backward-compatible artifact.
4. **The remaining problem is honest.** Within-phase AUC is still
   0.55-0.62. Calibration improves the *value* of the prediction; it
   doesn't restore lost discrimination. The LOA microsplit caveat
   from /14 stays in force: "standalone Phase-2 calls have weak
   discrimination, the strength is in mixed-phase portfolio ranking."

## What's still unaddressed (for v1.6+ or a future model class)

- **The within-phase ceiling.** Three consecutive feature attempts
  (/15 design features, /16 planned enrollment, /17 calibration) have
  improved calibration but not discrimination. The remaining open path
  is the model-class change /16 named: transformer-on-full-protocol
  instead of pooled-PubMedBERT + LightGBM. Significant lift, significant
  scope.
- **The `target_validated` and `num_competitors` dead-defaulted
  features.** Both /14 and /16 identified these as the remaining
  legitimate signal source. Requires literature lookup + cohort
  query — not on the v1.5.x track.

## Sources

- [/13 CT Open external benchmark](13-ct-open-benchmark.md) — the
  immutable AUC 0.600 external baseline this builds on
- [/14 Phase-stratified retrain](14-phase-stratified-retrain.md) —
  v1.5.6 diagnosis of the within-Phase-2 informational ceiling
- [/15 Trial-design features](15-trial-design-features-negative-result.md) —
  v1.5.7 leak discovery
- [/16 Planned enrollment null effect](16-planned-enrollment-null-effect.md) —
  v1.5.8 counterfactual that proved the apparent lift was variance
- [Doane et al. 2025](https://arxiv.org/abs/2512.00586) — the
  trial-design-feature-baseline reference
- `scripts/fit_isotonic_calibrators.py` — the fit pipeline
- `api/app/modules/ml_pos_prior/engine.py` — the at-inference application
