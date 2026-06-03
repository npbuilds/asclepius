# v1.5.6 — Phase-stratified retrain on HINT ∪ CTO

[v1.5.5](13-ct-open-benchmark.md) reported the honest external number:
**AUC 0.600** on 2,429 uncontaminated CT Open trials the model had never
seen, vs 0.703 on HINT-internal test. It also produced a *diagnostic*:
Phase-2 AUC collapsed to **0.543**, barely above random. v1.5.6 acts on
both findings. It does not fully solve the harder one, and this writeup
says so plainly.

## What changed

Two architectural changes, one data change.

### 1. Phase-stratified models (architecture)

The v1.5.x model was a single global LightGBM. One model, one decision
boundary, three phases with wildly different base rates (CTO: Ph1 = 12%,
Ph2 = 23%, Ph3 = 44% success). A global boundary cannot be simultaneously
well-placed for all three.

v1.5.6 trains **one LightGBM per phase** — `phase_1`, `phase_2`,
`phase_3` — plus a global fallback for off-distribution phases
(preclinical, NDA). At inference, the engine routes on `asset.phase`:

```python
model = phase_models.get(asset.phase.value, overall_model)
```

Each phase model fits on only its phase's rows, so its boundary calibrates
to that phase's base rate and eligibility-criteria style (dose-finding in
Ph1, indication-specific in Ph2, registration-pivotal in Ph3).

### 2. HINT ∪ CTO training corpus (data)

v1.5.5 was the external-validation milestone: the model had **never seen**
the 2,429 CTO trials. That number (0.600) is permanently recorded in
[/13](13-ct-open-benchmark.md) and is immutable.

v1.5.6 now **trains** on those trials. This is standard ML practice — you
open-source a benchmark, then you train on the labelled data it provided.
The combined corpus:

| Source | Rows | Success rate |
|---|---|---|
| HINT (Fu et al. 2022) | 11,552 | 57.7% |
| CTO (Gao et al. 2024, the v1.5.5 benchmark set) | 2,429 | 26.0% |
| **Union** | **13,981** | **52.2%** |

CTO rows get a stratified 65/15/20 train/valid/test split within each
(phase × label) cell, so the v1.5.6 test set contains ~486 held-out CTO
trials the model never trained on.

### 3. Conformal calibration carries over

The Mondrian split-conformal machinery from [v1.5.3](#) re-runs on the
union validation split, per phase. Coverage on the union test split holds
at ≥90% for all three phases (Ph1 = 90.3%, Ph2 = 91.6%, Ph3 = 93.4%).

## Results — and the honest caveat

### Headline: overall AUC improved

| Surface | AUC | Notes |
|---|---|---|
| v1.5.2 HINT-internal test | 0.703 | original ship |
| **v1.5.5 external CTO** | **0.600** | immutable benchmark, model unseen |
| v1.5.6 union test (HINT+CTO) | **0.726** | model saw CTO-style data |
| v1.5.6 held-out CTO test only | **0.660** | the fair v1.5.5 comparison |

On the held-out CTO test split — the apples-to-apples comparison to
v1.5.5 — AUC rose from **0.600 → 0.660** (+6 pp). Phase routing
contributed +2.4 pp of that (the global model alone scored 0.636 on the
same set).

### The caveat: this is a Simpson's-paradox gain

The overall 0.660 is **higher than any individual phase's AUC**:

| Phase | v1.5.6 held-out CTO AUC | Base rate |
|---|---|---|
| Phase 1 | 0.625 | 0.119 |
| Phase 2 | **0.554** | 0.231 |
| Phase 3 | 0.556 | 0.436 |
| **Overall (pooled)** | **0.660** | 0.260 |

This is not a contradiction — it is
[Simpson's paradox](https://en.wikipedia.org/wiki/Simpson%27s_paradox)
in the AUC. The pooled metric is inflated because the model correctly
assigns higher probabilities to Phase-3 trials (44% base rate) than to
Phase-1 trials (12%). That **between-phase** ranking boosts the pooled
AUC even when **within-phase** discrimination is weak.

The honest reading:

- **Phase routing genuinely helps the headline number.** A consumer who
  asks "rank these mixed-phase assets by PoS" gets a meaningfully better
  ordering (0.66 vs 0.60).
- **The within-Phase-2 problem is NOT solved.** Phase-2 discrimination is
  0.554 — statistically indistinguishable from the 0.543 collapse v1.5.5
  diagnosed. A dedicated Phase-2 model did not fix it, because the failure
  mode is informational, not architectural: Phase-2 eligibility criteria
  are the most indication-specific, and the structured features we can
  derive from CT.gov metadata are too coarse to separate Phase-2 winners
  from losers.

A model that claims "phase-stratified training fixed the Phase-2 collapse"
would be overselling. v1.5.6 improved the *ranking* of mixed-phase
portfolios; it left the *single-phase Phase-2 call* roughly where v1.5.5
found it.

## Why the within-phase ceiling is informational, not architectural

We tried the obvious architectural fix (a dedicated Phase-2 model) and it
moved Phase-2 AUC by <1 pp. That rules out "wrong model shape" and points
at the inputs. The Phase-2 model sees:

- **PubMedBERT embedding of eligibility criteria** (768-dim) — carries
  real signal (it's why AUC is 0.55 not 0.50), but eligibility text alone
  doesn't encode the indication-specific efficacy priors that determine
  Phase-2 outcomes.
- **36 structured features** — of which `target_validated` and
  `num_competitors` are *constants* (defaulted to False / 0 across the
  entire corpus, because neither HINT nor CTO ships them). Two of the
  features most predictive of Phase-2 success contribute zero signal.

The ceiling is the feature set, not the classifier.

## Next steps — ranked by expected within-phase lift

### v1.5.7 — CT.gov trial-design features (highest leverage)

Doane et al. 2025 reach 0.74 partly by using trial-design features we
don't: **enrollment count, number of arms, randomization, masking,
primary-endpoint type.** These are in CT.gov v2 metadata. We already
fetched them for the 2,429 CTO trials (`metadata_cache.jsonl`); the
blocker is HINT — its 11,552 trials ship only criteria text + SMILES +
ICD codes, so the design features would require a ~70-minute batch fetch
against CT.gov v2 (with uncertain coverage for pre-2015 trials). This is
the single change most likely to move within-Phase-2 AUC, because
enrollment + endpoint-type are exactly the axes that separate a
well-powered Phase-2 from an underpowered one.

### v1.5.8 — activate the dead structured features

`target_validated` (literature lookup: is the drug target genetically or
clinically validated for this indication?) and `num_competitors` (CT.gov
cohort query: how many other trials target the same indication+mechanism?)
are currently constants. Deriving real values would activate the ML
model's analogue of the framework's reflexivity mechanism — sponsor- and
competition-aware risk.

### v1.5.9 — Phase-2 error analysis

Examine the Phase-2 model's most-wrong predictions for systematic
structure (specific indications? sponsor tiers? intervention classes?). If
the failure mode is narrowly characterizable, the model can degrade
gracefully — flagging "low-confidence Phase-2 oncology" rather than
emitting a confident-but-wrong number.

## Why we ship v1.5.6 anyway

The overall ranking improved by a real 6 pp, the phase-stratified
architecture is the correct foundation for the v1.5.7 feature work, and
the honest within-phase caveat is itself the portfolio signal: a candidate
who reports "I improved the headline metric but the underlying Phase-2
discrimination problem is informational and here's exactly what would fix
it" demonstrates the diagnostic discipline a senior biotech investor wants
in an analyst. The number that matters for the framework's *use* — ranking
a pipeline of mixed-phase assets — got better. The number that's still
hard — a standalone Phase-2 efficacy call — is honestly flagged as such,
in the UI and here.

## Sources

- [Fu et al. 2022 (HINT)](https://www.cell.com/patterns/abstract/S2666-3899%2822%2900018-6)
- [Gao et al. 2024 (CT Open)](https://arxiv.org/abs/2406.10292)
- [Doane et al. 2025](https://arxiv.org/abs/2512.00586) — trial-design-feature baseline
- [`api/data_pipeline/train_gbt_v156.py`](../api/data_pipeline/train_gbt_v156.py) — phase-stratified trainer
- [`api/data_pipeline/build_cto_training_dataset.py`](../api/data_pipeline/build_cto_training_dataset.py) — CTO → training parquet
- [/13 CT Open external benchmark](13-ct-open-benchmark.md) — the immutable v1.5.5 result
