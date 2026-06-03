# v1.5.7 — Trial-design features: a label leak and a negative result

[v1.5.6](14-phase-stratified-retrain.md) left a specific, falsifiable
diagnosis: within-Phase-2 discrimination on held-out CT Open sat at
**0.554**, and a dedicated Phase-2 model didn't move it, so the ceiling
was *informational* — the feature set, not the architecture. The named
fix was v1.5.7: add the **CT.gov trial-design features** (enrollment,
number of arms, randomization, masking) that Doane et al. 2025 use to
reach 0.74. This writeup reports what happened. It is not the result we
hoped for, and that is exactly why it's here.

## What we built

A complete trial-design-feature pipeline:

1. **Fetch.** `hint_fetch_metadata.py` + an extended `cto_fetch_metadata.py`
   pull `enrollmentInfo`, `armGroups`, and `designInfo` (allocation +
   masking) from CT.gov v2 for all 11,552 HINT trials and all 2,429 CTO
   trials. Coverage came in strong (HINT: enrollment 99%, arms 90%,
   allocation 98%, masking 98%; CTO: 100% on all four), so these were
   real features, not a HINT-vs-CTO domain proxy.
2. **Encode.** Four new features appended to the structured vector
   (36 → 40 dims; combined 804 → 808), with a sentinel `0 = unknown` so the
   tree could branch on missingness, and an explicit open-label ≠ unknown
   distinction for masking.
3. **Retrain.** The v1.5.6 phase-stratified architecture, unchanged,
   on the 808-dim vectors.

## The result that looked too good

Held-out CTO test (the same 486 trials measured in v1.5.5/v1.5.6):

| phase | v1.5.5 | v1.5.6 | v1.5.7 (raw) |
|---|---|---|---|
| Phase 1 | 0.616 | 0.625 | 0.701 |
| **Phase 2** | 0.543 | 0.554 | **0.839** |
| Phase 3 | 0.590 | 0.556 | 0.760 |
| Overall | 0.600 | 0.660 | **0.824** |

Phase-2 AUC leapt from 0.554 to **0.839** — a 28-point jump, and *higher
than Doane 2025's headline 0.74*. That last fact is the tell. **When a
held-out number beats the published state of the art by a wide margin,
the prior should be "I have a leak," not "I have a breakthrough."**

## Finding the leak

Two checks, both fast, both damning.

**1. Feature importance.** On the Phase-2 model, `enrollment_bucket` was
the single most important feature of all 808 (rank 1, 3.1% gain) — ahead
of every one of the 768 PubMedBERT dimensions individually. A
*structured* feature out-ranking the entire language model is a red flag.

**2. What kind of enrollment?** CT.gov's `enrollmentInfo.count` carries a
`type`: ESTIMATED (planned at registration) or ACTUAL (recorded later).
A 30-trial sample of the CTO test set returned **30/30 ACTUAL**, with a
status mix of TERMINATED 15 / COMPLETED 10 / WITHDRAWN 5.

That is the leak. A trial **terminated early for futility** ends up with
**low actual enrollment *because* it failed** — patients stopped being
enrolled when the trial was halted. So "low enrollment → failure" isn't a
prediction available at trial start; it's the outcome leaking backward
into a feature. Doane 2025 uses *planned* enrollment specifically to
avoid this; we grabbed `count` regardless of type and walked straight
into it.

## Proving it was the whole effect

A controlled ablation — retrain the Phase-2 model dropping design features
one group at a time, held-out CTO Phase-2 AUC:

| Config | CTO Phase-2 AUC |
|---|---|
| All 4 design features | 0.824 |
| **Drop enrollment** | **0.602** |
| Drop enrollment + arms | 0.605 |
| Drop all 4 design features | 0.605 |

Removing actual enrollment collapses the gain entirely (0.824 → 0.602).
And the other three design features — arms, randomization, masking — add
**nothing**: 0.605 with none of them vs 0.602 with all three, inside the
noise.

A second, cleaner check ruled out a subtler confound. Comparing
*within the same data build* (same parquets, design columns toggled, so
no fetch-induced differences), design-features-on vs design-features-off:

| | design OFF | arms/rand/mask ON | Δ |
|---|---|---|---|
| Phase 1 | 0.638 | 0.612 | −0.026 |
| Phase 2 | 0.605 | 0.602 | −0.003 |
| Phase 3 | 0.602 | 0.612 | +0.010 |
| **Overall** | **0.694** | **0.688** | **−0.006** |

The legitimate (non-leaky) trial-design features move overall held-out AUC
by **−0.006** — i.e., not at all. The v1.5.7 hypothesis is **falsified**:
CT.gov trial-design features, as derivable from a trial's current snapshot,
carry no legitimate within-phase signal. The only "lift" was leakage.

> A note on the confound the second table controls for: the cross-version
> "v1.5.6 0.66 → v1.5.7 0.70" comparison is *not* trustworthy, because
> re-fetching CTO metadata changed some text-derived features between
> builds. The clean experiment is the within-build toggle, and it says
> zero. Trusting the +0.04 cross-version delta over the −0.006 within-build
> delta would be the same self-deception the enrollment leak already
> punished.

## What shipped

**Nothing changed in the model.** v1.5.6 remains the shipped artifact
(phase-stratified, 804-dim, no trial-design features). We do not ship a
0.84 we know is leaked, nor a set of features that a clean A/B shows add
nothing. The trial-design encoder change was reverted; the fetch pipeline
(`hint_fetch_metadata.py`, the extended `cto_fetch_metadata.py`) is kept
in the offline `data_pipeline/` layer as the reproducible record of this
experiment — it is not in the inference path.

## Why this is the right outcome to publish

A portfolio model that quietly used actual enrollment would report a
held-out Phase-2 AUC of 0.84 and look spectacular — until a biotech VC's
data-science diligence asked "is that planned or actual enrollment?" and
the number evaporated. The defensible posture is the one taken here:
build the feature, distrust the suspiciously-large gain, find the leak,
prove it's the whole effect with an ablation, and report the corrected
result honestly. Negative results that close off a tempting dead-end are
worth as much as positive ones — they're just rarer in portfolios because
they require admitting a hypothesis failed.

## The genuinely open path: v1.5.8

The leak was *actual* enrollment. *Planned* enrollment — the count
registered before the trial ran — is a legitimate pre-outcome predictor
(underpowered trials are *designed* small) and is what Doane 2025 uses.
It is not in the current CT.gov snapshot; it lives in the study's
**version history** (the first registered version's `enrollmentInfo`).
v1.5.8's question is narrow and honest: does *planned* enrollment, fetched
from CT.gov version history, provide the within-phase lift that *actual*
enrollment only faked? Given that arms/randomization/masking added
nothing, the expected lift is modest — but it's the one trial-design
feature with a real mechanism, and it's worth the targeted fetch.

Until then, the honest within-Phase-2 number is **~0.55-0.60**, and the
[LOA microsplit](14-phase-stratified-retrain.md) should still be read with
the skepticism v1.5.6 prescribed for standalone Phase-2 calls.

## Sources

- [Doane et al. 2025](https://arxiv.org/abs/2512.00586) — uses *planned*
  enrollment among trial-design features; the baseline we tried to match
- [Gao et al. 2024 (CT Open)](https://arxiv.org/abs/2406.10292)
- [/13 CT Open external benchmark](13-ct-open-benchmark.md) — the immutable 0.600
- [/14 Phase-stratified retrain](14-phase-stratified-retrain.md) — the 0.554 diagnosis this acted on
- `api/data_pipeline/hint_fetch_metadata.py`, `api/data_pipeline/cto_fetch_metadata.py` —
  the (reverted-from-inference) trial-design fetch layer
