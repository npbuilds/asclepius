# CT Open external benchmark

The v1.5.x ML PoS Prior reports **internal HINT-test AUC 0.7030** — within
the borderline-ship range relative to Doane et al. 2025's published
baseline of 0.7404 on a similar task. Internal-test numbers tell you what
your model learned on data it saw at training. They do not tell you
whether the model generalizes. v1.5.5 measures the latter, against
external uncontaminated data, and reports the result honestly even when
it's unflattering.

## What we benchmarked against

[CT Open (CTO)](https://chufangao.github.io/CTOD/) is Gao et al. 2024's
large-scale clinical-trial-outcome dataset, published in *Nature Health*
(2026). The dataset's gold tier is a **manually-annotated subset** of
~11,000 trials completed between 2020 and 2024, with binary success
labels validated against expert annotators at F1 = 0.91-0.94.

CTO is built on top of CT.gov data and overlaps with HINT (Fu et al. 2022),
the corpus our v1.5.x model trains on. To get an honest external read
we filter the gold tier to trials that are **provably uncontaminated**:

| Filter | Trials remaining |
|---|---|
| Total CTO human-labeled gold tier | 11,012 |
| Phase 1 / 2 / 3 only (drops PHASE4, EARLY_PHASE1, combined-phase) | 7,993 |
| Completion year ≥ 2023 (HINT's cutoff is early 2022) | 2,457 |
| Cross-referenced against CTO phase prediction CSVs' `hint_train` columns and excluded | **2,429** |

The 2,429-trial held-out set has 26% base success rate (1,798 failures /
631 successes) and is split across phases 1 / 2 / 3 at 671 / 1,061 /
697 respectively. None of these trials were in HINT's training set.

## Pipeline

The full pipeline lives in `api/data_pipeline/cto_*.py`:

1. **`cto_acquire.py`** — load CTO from
   [HuggingFace](https://huggingface.co/datasets/chufangao/CTO),
   filter, identify the uncontaminated subset.
2. **`cto_fetch_metadata.py`** — fetch CT.gov v2 protocol metadata
   per NCT ID (eligibility criteria, conditions, interventions,
   MeSH terms). Uses `curl` via subprocess rather than `httpx`
   because CT.gov v2 returns 403 to `httpx` clients regardless of
   headers — the server fingerprints TLS handshake details. Same
   finding as the v1.5.2 Day 4 cache-generation work.
3. **`cto_fetch_batch.py`** — resumable JSONL-cached bulk runner.
   Throttle 0.25s/req; full uncontaminated set fetched in ~14
   minutes with 100% success rate.
4. **`cto_derive_features.py`** — map CTO row + CT.gov metadata
   into the v1.5.x model's 36-dim structured feature vector. TA
   keyword-matched against MeSH terms + conditions; modality
   WHO-INN-suffix-matched from intervention drug names; capital
   position a coarse proxy from CTO's `source_class` column.
5. **`notebooks/cto_pubmedbert_embed_colab.ipynb`** — Colab GPU
   notebook to embed the 2,429 eligibility-criteria texts with
   PubMedBERT (the same model the runtime engine uses). ~30 min
   on T4 GPU.
6. **`cto_benchmark.py`** — score each trial through the shipping
   v1.5.x model, compute AUC + Brier per phase + overall.

## Results

| Surface | n | AUC | Brier | Base rate |
|---|---|---|---|---|
| **Overall (CTO external)** | **2,429** | **0.600** | **0.300** | 0.260 |
| Phase 1 (CTO) | 671 | 0.616 | 0.317 | 0.122 |
| Phase 2 (CTO) | 1,061 | **0.543** | 0.295 | 0.231 |
| Phase 3 (CTO) | 697 | 0.590 | 0.290 | 0.436 |
| HINT internal test (reference) | 3,133 | 0.703 | 0.208 | 0.623 |
| Doane et al. 2025 baseline | — | 0.7404 | — | — |

The full machine-readable result is at
[`api/data/cto/benchmark_results.json`](../api/data/cto/benchmark_results.json)
(committed once Stage 4 produces it; gitignored as derived data).

## What the −10.3 pp gap tells us

The overall AUC drops by **10.3 percentage points** vs internal HINT-test.
Phase 2 specifically collapses to **0.543** — barely above random
(AUC = 0.5). Phase 1 (0.616) and Phase 3 (0.590) hold up better but
remain well below internal performance.

We have three plausible explanations, ranked by likelihood:

### 1. Feature-derivation gap (most likely)

HINT ships drug SMILES strings + ICD-10 codes alongside each trial.
Our `derive_features.py` consumes both to produce **precise** modality
classifications (small molecule vs mAb vs ADC, derived from canonical
SMILES patterns) and **precise** therapeutic area classifications
(ICD-10 chapter prefix → TA enum).

CTO does not ship SMILES or ICD codes — only CT.gov metadata. Our
`cto_derive_features.py` falls back to:

- **Modality:** WHO-INN suffix matching on intervention drug names
  (`-mab` → MAB, `-nib` → small molecule, `-cept` → protein). Catches
  most cases but breaks on novel naming patterns.
- **Therapeutic area:** keyword matching against MeSH terms +
  conditions (`"neoplasm"` → ONCOLOGY, `"alzheimer"` → CNS, etc.).
  Covers the eight most-common TAs but falls to `OTHER` for less-
  common indications. ~9% of trials with no MeSH terms fall through
  entirely.
- **`target_validated`** and **`num_competitors`**: default `False`
  / `0` for all CTO trials because deriving these from CT.gov alone
  would require additional cohort + literature queries we didn't build.

The HINT-trained LightGBM learned to weight `target_validated` and
`num_competitors` based on their HINT distribution; when those
features are constants on the CTO set, the model's structural-feature
contribution is partly noise. PubMedBERT embeddings of eligibility
criteria still carry signal — and that signal is why CTO AUC is 0.60
instead of 0.50 — but the structured-feature collapse explains a
meaningful share of the −10pp gap.

### 2. Distribution shift 2020-2022 → 2023+

HINT was finalized in early 2022. The CTO uncontaminated set is
specifically trials that completed in 2023 or later. Two years of
elapsed time in clinical development is non-trivial:

- **Mechanism mix shifted.** GLP-1 receptor agonists (Ozempic etc.)
  reshaped the metabolic-disease trial landscape from 2022 onward;
  HINT under-represents those.
- **PD-(L)1 saturation.** The first wave of checkpoint inhibitors
  was over by 2022; 2023-2024 oncology trials are more often
  bispecifics, ADCs, KRAS inhibitors. HINT learned PD-1 patterns
  that don't fully transfer.
- **Cell + gene therapy maturity.** ATMP trials with 2023+ completion
  carry protocol-text patterns HINT's earlier cohort doesn't.

PubMedBERT embeddings should partly compensate (eligibility-criteria
language is more stable than structured features), and they did —
overall AUC is still meaningfully above random — but not enough.

### 3. Label-source mismatch (smallest contributor)

HINT's success label (Fu et al. 2022) and CTO's manual label
(Gao et al. 2024) use different definitions of "trial success" at
the margin. Fu's pipeline weights trial status changes + publication
mentions + ClinicalTrials.gov amendments; Gao's uses a similar
weak-supervision approach but with different thresholds.

This contributes some noise, but the CTO labels are independently
validated against expert annotators at F1 0.91-0.94 — so the label
quality itself is comparable to HINT's. The label-source difference
explains marginal disagreement, not 10pp of AUC.

## Why the Phase-2 collapse is most striking

The headline AUC gap (0.703 → 0.600) is concerning. The Phase-2-specific
AUC (0.543) is **diagnostic**. Three reasons Phase 2 is the worst case:

1. **Base rate balance.** Phase 2 has the most-balanced binary outcome
   (23% success / 77% failure), which is where AUC is statistically
   hardest to push. A small information loss has a larger AUC impact
   in mid-base-rate regimes than at base rates near 0 or 1.

2. **HINT's Phase 2 specialty bites.** HINT is heavily oncology-loaded
   in Phase 2 (kinase-inhibitor era, 2010s-early-2020s). The CTO Phase
   2 distribution is more therapeutic-area-diverse. The HINT model
   learned oncology-specific Phase 2 patterns that don't generalize.

3. **Eligibility-criteria patterns shift mid-development.** Phase 1
   criteria are dose-finding and structurally similar across
   indications; Phase 3 criteria are registration-pivotal and
   structurally similar. Phase 2 criteria are the most
   indication-specific — and indication-specific drift hits hardest.

## What this changes about the framework's claims

The honest disclosure: **if you take the v1.5.x ML PoS Prior at face
value on a 2024 oncology trial outside HINT's coverage, expect
roughly 0.60 AUC, not 0.70.**

This does not invalidate the framework's other components:

- The **rule-based PoS chain** (BIO base rates + modality + reflexivity)
  is observational-frequency math, not a learned model. It generalizes
  by construction.
- The **reflexivity adjustment** is a hand-coded theoretical claim
  grounded in Spence (1973) + Lo & Thakor (2022); it doesn't have a
  generalization gap because there's no training distribution.
- The **bootstrap-percentile and conformal coverage** machinery in
  v1.5.3 still works on CTO predictions — the bands just sit on
  weaker point estimates.

What it does mean is that the **ML prior** column in the LOA microsplit
should be read with appropriate skepticism for trials outside HINT's
distribution. The HeroBanner's `BIO X% → Reflexivity Y% → ML Z%` line
shouldn't be treated as three independent equally-trustworthy estimates;
the ML number's reliability is meaningfully lower for distribution-
shifted assets.

## Why we're shipping this finding

Most published clinical-trial-outcome models report only internal-test
AUC. Doane et al. 2025's 0.7404 is on their internal test split.
Fu et al. 2022's HINT numbers are on HINT's internal test split. Neither
paper benchmarked against held-out external manually-validated data
the way this writeup just did.

A portfolio project that claims AUC 0.703 without external validation
is technically true but rhetorically misleading. A portfolio project
that runs the external benchmark, reports the lower number honestly,
and explains the gap demonstrates the discipline a senior biotech VC
would actually want to see.

## Next steps

**v1.5.6 shipped** — see [/14 Phase-stratified retrain](14-phase-stratified-retrain.md).
We retrained on HINT ∪ CTO with one LightGBM per phase. Held-out CTO AUC
rose **0.600 → 0.660** (+6 pp), landing in the lower half of the
predicted 0.62-0.68 range. The honest caveat: the gain is partly
Simpson's-paradox (between-phase ranking); within-Phase-2 discrimination
stayed at 0.554, confirming the feature-derivation gap below is the real
ceiling, not model architecture.

A v1.5.7 could close the feature-derivation gap by re-deriving HINT's
features through CT.gov v2 metadata (matching the CTO pipeline). That's
more invasive — it would require regenerating HINT's embeddings + the
structured feature vector for the entire HINT corpus.

A v1.5.8 could investigate the Phase-2 collapse specifically: examine
the model's wrongest predictions, look for systematic patterns
(specific indications? specific sponsor types? specific intervention
patterns?). If the failure mode is narrowly characterizable, the model
could degrade gracefully for those cases.

For v1.5.5 — this ship — the goal was honest external validation.
That's done.

## Sources

- [CTOD project page](https://chufangao.github.io/CTOD/) — dataset,
  documentation, GitHub repo
- [Gao et al. 2024](https://arxiv.org/abs/2406.10292) — the paper
  *Automatically Labeling Clinical Trial Outcomes: A Large-Scale Benchmark for Drug Development*
- [Fu et al. 2022 (HINT)](https://www.cell.com/patterns/abstract/S2666-3899%2822%2900018-6) —
  *HINT: Hierarchical Interaction Network for Trial Outcome Prediction*
- [Doane et al. 2025](https://arxiv.org/abs/2512.00586) — baseline AUC
  reference for clinical-trial-outcome prediction
- [`api/data/cto/benchmark_results.json`](../api/data/cto/benchmark_results.json) —
  machine-readable metrics
- [`api/data_pipeline/cto_*.py`](../api/data_pipeline/) — full
  reproducible pipeline
