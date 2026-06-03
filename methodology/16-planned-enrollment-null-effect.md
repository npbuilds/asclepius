# v1.5.8 — Planned enrollment: legitimate, leak-free, and null

[v1.5.7](15-trial-design-features-negative-result.md) discovered that
CT.gov's `enrollmentInfo.count` returns ACTUAL enrollment on completed
trials, and a Phase-2 model trained on it leaked the outcome backward
into the feature (terminated trials have low actual enrollment *because*
they failed). The corrected v1.5.7 ablation showed arms/randomization/
masking add zero held-out signal. The one design feature that v1.5.7
explicitly named as worth retrying was **planned enrollment** from CT.gov
version history — the registration-time count, before any outcome
information could contaminate it. That's what Doane et al. 2025 use.

v1.5.8 built that legitimate pipeline. The result is a clean negative
finding. This writeup is the record of how we proved it.

## What we built

**Planned-enrollment fetcher** (`api/data_pipeline/fetch_planned_enrollment.py`).
CT.gov's documented v2 API has no per-version history endpoint — that's
a known limitation researchers have flagged. The undocumented internal
endpoint that powers the public "History of Changes" tab does:

```
GET https://clinicaltrials.gov/api/int/studies/{nctId}/history/0
```

This returns a JSON snapshot of the trial's first registration, including
its `enrollmentInfo` block. For newer trials the block carries
`{"count": N, "type": "ESTIMATED"}`; for older trials registered before
CT.gov added the `type` field it carries just `{"count": N}`, which is
planned *by construction* because v0 is the registration submission.

**Coverage probe** (45 stratified HINT trials, 2026-06): 100% history-
endpoint success, 87% parseable v0 enrollment, **0 / 45 records were
ACTUAL** at v0 — exactly what the registration-time hypothesis predicted.

**The leak that almost happened anyway.** Production fetch (n=2,429 CTO,
n=11,552 HINT) revealed a secondary leak class: ~1.3% of CTO and ~4.5%
of HINT trials had `type: "ACTUAL"` at v0. These are **post-hoc
registrations** — trials registered with CT.gov *after* they ended,
typically older studies brought into compliance retroactively. Their
v0 count is the actual enrollment with outcome correlation baked in.
The `design_fields_from_metadata` helper now filters those out at
encoder time (treat as unknown, sentinel 0); they make it into the
JSONL cache for audit but never reach the model. The filter is one
line of defensive code that protects against a secondary leak class
that the v1.5.7 lesson would have missed.

**Effective coverage after the ACTUAL filter:**
- HINT: 9,712 / 11,552 = **84.1%** legitimate planned enrollment
- CTO: 2,391 / 2,429 = **98.4%**

The HINT 84% matches the 45-trial recon's 87% prediction once the
ACTUAL filter is applied — the recon was predictive of the production
result, not a sample artifact.

## What we measured

Three converging experiments. We ran the within-build A/B first (the
clean experiment v1.5.7 established as the standard), then verified
on the production model with two independent counterfactuals.

### Experiment 1 — within-build A/B

Same parquets, same hyperparameters, design columns toggled at training
time. Phase-stratified LightGBMs on HINT-ph + CTO-ph-train, evaluated on
held-out CTO-ph-test. Single seed (LightGBM is deterministic at our
hyperparams — feature_fraction and bagging_fraction both default to 1.0,
so multi-seed gave bit-identical results; confirmed across seeds 42, 7, 13).

| Config | Phase-2 AUC | Overall AUC |
|---|---|---|
| design OFF (all 4 zeroed) | 0.605 | 0.694 |
| **planned-enrollment ONLY** | **0.627** (+0.022) | **0.697** (+0.003) |
| arms / rand / mask ONLY | 0.602 | 0.688 |
| all 4 design ON | 0.598 | 0.694 |

Three patterns:
1. **Planned-enrollment alone showed +2.2pp on Ph2 vs baseline** — directionally consistent with the v1.5.6 diagnostic.
2. **Arms/rand/mask alone add −0.003 Ph2** — v1.5.7 finding reproduced in a clean A/B with no enrollment leak confound.
3. **All 4 together is worse than enrollment-only** — adding the null features dilutes the planned-enrollment signal.

This pattern argued for shipping the planned-enrollment-only configuration.

### Experiment 2 — bootstrap CI on the A/B's Δ

The Phase-2 test set is n = 224. A bootstrap on the A/B's predictions:

| | Phase-2 Δ |
|---|---|
| Point estimate | +0.022 |
| 95% CI | [−0.022, +0.073] |
| Fraction of bootstrap samples with Δ > 0 | 83.5% |

The CI **includes zero**. The lift is suggestive but statistically
marginal on n = 224.

At this point we could have shipped with appropriate caveats. We almost
did. The third experiment is what stopped us.

### Experiment 3 — production counterfactual (the one that mattered)

We retrained the full production pipeline with planned enrollment
enabled and arms/rand/mask gated off, shipped the result, and ran the
*decisive* check: **hold the production model fixed, toggle the
enrollment column to 0 at inference, measure Δ AUC.**

This isolates "what the model actually learned to do with enrollment"
from "any other run-to-run training variance."

| Surface | v1.5.8 (enrollment ON) | Counterfactual (zeroed) | Δ point | 95% CI | % Δ > 0 |
|---|---|---|---|---|---|
| Phase 1 | 0.6245 | 0.6245 | +0.000 | [+0.000, +0.000] | 0.0% |
| Phase 2 | 0.5803 | 0.5771 | +0.003 | [−0.004, +0.012] | 78.7% |
| Phase 3 | 0.5829 | 0.5827 | +0.000 | [−0.003, +0.003] | 54.8% |
| **Overall** | **0.6681** | **0.6672** | **+0.001** | [−0.002, +0.004] | 77.5% |

**The shipped model does not actually use the enrollment feature.**
Toggling its column at inference is a no-op (Phase-1 exactly zero;
overall +0.001). The +2.2pp A/B Phase-2 lift was training-run variance,
not the feature.

### Experiment 4 — feature importance

LightGBM's tree-split importance on the production phase models confirms:

| Phase model | Enrollment splits | Gain % | Rank |
|---|---|---|---|
| Phase-1 | **0** | 0.00% | 555 / 808 |
| Phase-2 | 5 | 0.14% | 227 / 808 |
| Phase-3 | 1 | 0.03% | 631 / 808 |
| Overall | 1 | 0.02% | 715 / 808 |

Compare to v1.5.7's leaky enrollment: **rank 1/808, 3.1% gain.** The
clean planned enrollment is essentially never split on. PubMedBERT
dimensions occupy ~95% of feature-importance mass, and what marginal
non-text signal exists comes from phase ordinal, biomarker enrichment,
and the existing 36-dim structured features — not the new design ones.

## Why three experiments and not one

The chain of reasoning matters. The within-build A/B by itself looked
positive (+2.2pp). The bootstrap CI suggested "marginal but possibly
real." The fix-the-model-toggle-the-column counterfactual is what made
the verdict crisp. **If we had stopped at the A/B and shipped, we'd be
shipping the same kind of training-noise-as-feature-effect mistake that
quietly ruins published ML claims.** The toggle experiment cost ~30
seconds of compute. The feature-importance check cost ~3 seconds. Both
disagreed with the A/B. Two-out-of-three independent analyses pointing
at "no effect" overrides one-out-of-three pointing at "small effect"
when the third one is the most direct measurement (the model's own use
of the feature).

This is the same discipline that caught v1.5.7's actual-enrollment leak.
v1.5.7 caught a *false positive* (huge gain → leak). v1.5.8 caught a
*false positive of a different kind* (small gain → run-to-run variance).
The first kind costs you a 0.84 you can't defend; the second kind costs
you a 0.63 that won't survive replication. Both deserve discovery.

## What shipped, what didn't

| Component | Status |
|---|---|
| Production inference model (`model.joblib`) | **Unchanged** — v1.5.6 phase-stratified, 804-dim |
| `fetch_planned_enrollment.py` + the v0-history endpoint discovery | Kept in `data_pipeline/` — the documented research artifact |
| Planned-enrollment caches (HINT + CTO JSONL) | Kept — usable for future feature attempts and audit |
| ACTUAL-at-v0 filter in `design_fields_from_metadata` | Reverted (the inference path no longer reads design fields), but documented here |
| Encoder / domain changes (40-dim with 4 design slots) | Reverted to v1.5.6 36-dim |

## What we know now that we didn't before

1. **CT.gov's v0 history endpoint exists** and returns parseable JSON
   for trials registered as far back as 2005. This is a reproducible
   data source for any future trial-design feature work.
2. **CT.gov has a secondary actual-enrollment leak class** at v0 — the
   ~1-4% of trials registered post-completion. Any future use of v0
   data must filter `type == "ACTUAL"`, not just trust v0 = registration.
3. **Trial-design features derivable from CT.gov metadata don't move
   within-phase AUC** above the PubMedBERT-text baseline, even after
   correcting v1.5.7's leak. This generalizes the v1.5.7 finding from
   "ACTUAL enrollment is leaky" to "the design features that can be
   sourced from CT.gov, leaky or not, don't carry signal the LightGBM
   can extract on top of 768-dim PubMedBERT embeddings of eligibility
   criteria."
4. **The within-Phase-2 ceiling (~0.55-0.60) is not movable from
   CT.gov-derivable features.** The honest path forward for closing
   that gap is either:
   - Richer features sourced *outside* CT.gov — e.g., literature-
     validated target priors, real-time competitor cohort counts —
     which v1.5.6 already flagged as the dead-defaulted features
     `target_validated` and `num_competitors`.
   - A different model class (transformer-on-full-protocol instead
     of pooled-embedding-plus-LightGBM) that can extract more from
     the criteria text directly.

Both are scope-larger than v1.5.x can absorb. v1.5.6 remains the
shipped model with its honest 0.554 Phase-2 number, and the LOA
microsplit caveat for standalone Phase-2 calls from [/14] is
**reaffirmed by this experiment, not loosened.**

## Why we ship the writeup, not the model

A portfolio version of this work would have stopped at the within-build
A/B's +2.2pp, shipped, and never run the production counterfactual.
Three reviewers in a junior-engineer interview would have nodded along.
A biotech VC's quant team running diligence on a "+2pp gain" would
have asked "did you bootstrap?" — and "is the model actually using
the feature?" — and the chain would have broken.

The defensible posture is the one here: built it, A/B'd it, found a
small effect, distrusted the small effect, ran the held-fixed
counterfactual, confirmed null, reverted the model, kept the
infrastructure for future revisit, and published the negative result
with all four experiments visible. That's the same discipline as
v1.5.7's leak discovery; this time the false signal was subtler.

## Sources

- [Doane et al. 2025](https://arxiv.org/abs/2512.00586) — uses *planned*
  enrollment among trial-design features; the baseline this attempted
  to follow up on
- [/13 CT Open external benchmark](13-ct-open-benchmark.md) — the
  immutable AUC 0.600 external validation
- [/14 Phase-stratified retrain](14-phase-stratified-retrain.md) — the
  v1.5.6 diagnostic naming within-Phase-2 informational ceiling
- [/15 Trial-design features negative result](15-trial-design-features-negative-result.md) —
  the v1.5.7 leak discovery this builds on
- `api/data_pipeline/fetch_planned_enrollment.py` — the v0-history
  fetch pipeline + ACTUAL filter, kept for posterity
