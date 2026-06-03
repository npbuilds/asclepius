# Asclepius

**Live:** <https://asclepius-lyart.vercel.app> · [methodology index](https://asclepius-lyart.vercel.app/methodology) · [worked example](https://asclepius-lyart.vercel.app/diligence/adagrasib)

> Asclepius is the first open rNPV tool that prices the path-dependency between a sponsor's
> balance sheet and their trial's probability of success. Capital-constrained sponsors run
> worse trials; well-capitalized sponsors enable adaptive designs and stronger regulatory
> engagement. We make that explicit and quantifiable, with citations on every number.

A biotech venture valuation workbench: phase-gated probability of success with an explicit
**reflexivity adjustment**, risk-adjusted NPV with 10,000-path Monte Carlo and tornado
sensitivity, a supervised **ML PoS Prior** on real HINT clinical-trial outcomes (PubMedBERT +
**phase-stratified LightGBM**, bootstrap-percentile uncertainty bands + Mondrian split-conformal
coverage; **externally validated against CTO uncontaminated at AUC 0.600, then retrained on
HINT ∪ CTO with one model per phase → 0.660 on held-out CTO (+6pp) — see
[methodology/13](methodology/13-ct-open-benchmark.md) +
[/14](methodology/14-phase-stratified-retrain.md) for the honest generalization-gap and
Simpson's-paradox analysis, [/15](methodology/15-trial-design-features-negative-result.md)
for a documented label-leak discovery, and
[/16](methodology/16-planned-enrollment-null-effect.md) for the leak-free planned-enrollment
counterfactual showing the lift was training-noise**), an
8-pillar diligence scorecard, cited deal comparables, three
runtime agents (Auto-Diligence, Memo Writer, Game-Theory Adversary), and **four persona-aware
reader views** (VC Associate, IC Voter, Scientific Reviewer, Quant) — all built on a **modular
registry pattern** that has now successfully absorbed five major feature lines (v1.5 calibrated
ML, v1.5.5 external validation, v1.5.6 phase-stratified retrain, v1.7 reader-journey IA, v1.8
persona views) without core edits.

The architecture is intentional and replicable. Every methodology decision is documented in
[`methodology/`](methodology/); every reference value is in versioned JSON with a `source` field;
every PoS adjustment is logged with rationale and citation. Asclepius is built as a *maintained*
methodology platform with a quarterly refresh cadence tied to BIO/Informa and Damodaran's
publication calendars — not a one-shot portfolio artifact.

## What you're looking at

**The headline result** — adagrasib, applied as a retrospective backtest using only public
information available before the KRYSTAL-12 Phase 3 readout (June 2022 cutoff):

| Scenario | Framework value | Reality |
|---|---:|---|
| Rule-based PoS (BIO 7.9% → reflexivity → final LOA) | **13.2%** | — |
| ML PoS Prior (PubMedBERT-embedded KRYSTAL-1 criteria + LGBM) | **23.6%** [24%–53% bootstrap band] | Real-outcome-supervised, AUC 0.7030 |
| Pre-readout (Phase 2) base case rNPV | **$570M** | Mirati's market cap at cutoff |
| Pre-readout Monte Carlo P25–P75 | **$440M – $680M** | Distribution over 10K simulated paths |
| Post-readout (at NDA) base case | **~$4.9B** | — |
| Actual BMS acquisition (Oct 2022) | $4.8B | Brackets within 2% |
| Winner's-curse-adjusted private value | $4,400M – $4,600M | Pfizer was reported as competing bidder |

**The verdict:** BMS paid a small premium to the success-weighted central case — defensible
as strategic KRAS-franchise value, but no margin of safety for a financial buyer. Read the
[full worked example](methodology/05-worked-example-adagrasib.md).

## Try it

```bash
# Backend (Python 3.11+)
cd api
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend (Node 20+, pnpm 10+)
cd web
pnpm install
pnpm dev
```

Then open <http://localhost:3000/diligence/adagrasib>.

**Two hero interactions** to try:

1. **Reflexivity slider** (at the top of the Thesis section). Drag from "Adequate" to "Well
   capitalized" and watch the HeroBanner's LOA microsplit, the PoS waterfall, the ML PoS
   Prior band, the rNPV base case, the Monte Carlo distribution, and the tornado all update
   live. That single drag is the framework's load-bearing demo — the headline differentiator
   visibly moving rNPV 20%+.

2. **Persona toggle** (in the global header). Cycle among VC Associate (default) / IC Voter /
   Scientific Reviewer / Quant and watch the entire page transform: different banner content,
   different module ordering, different leading-element cards (TrialDesignCard for science,
   ModelInfoRawCard for quant). Same underlying data, four audience-specific reads. The
   v1.8.0 evolution of "methodology applied to its own presentation" — see
   [`methodology/00-product-thesis.md`](methodology/00-product-thesis.md) §Persona modes.

## Architecture in one sentence

A `DiligenceRecord` pydantic model is the single source of truth; three auto-discovered
registries (`data_sources/`, `modules/`, `agents/`) plug into FastAPI on startup; the Next.js
frontend reads the `/api/modules` manifest endpoint and dynamically renders one panel per
module.

See [`docs/architecture.md`](docs/architecture.md) for the full contract on adding a new
module, data source, agent, or exporter without touching the core.

## What's in the live build

The v1 baseline (shipped Weeks 1-4):

- **PoS engine** with a six-step adjustment chain (base rate → modality → mechanism modifiers
  → regulatory designations → reflexivity), every step logged in the audit trail with a
  primary-source citation
- **rNPV engine** with phase-gated cash flows, mid-year discount convention, Monte Carlo over
  log-normal peak sales / beta LOA / normal WACC / triangular COGS, and tornado sensitivity
- **8-pillar diligence scorecard** with red/green flag mechanics — including the novel
  computational-infrastructure pillar that explicitly prices a sponsor's AI/ML/data assets
- **Cited deal comparables** with provenance on every cohort row (encorafenib, selpercatinib,
  larotrectinib; the kinase-TKI single-asset M&A cohort)
- **Worked example** anchored to the BMS / Mirati adagrasib transaction, framed as
  retrospective calibration (not prediction)
- **CI workflow** running `ruff` + `pytest` + `pnpm typecheck` + `pnpm build` on every push

### v1.1 — Three runtime agents (shipped)

Each maps to one UI button; coordination is via the deterministic core, not agent-to-agent calls:

- **Auto-Diligence** — asset name → structured AssetInput fields with citations from a
  high-signal domain allowlist (CT.gov, FDA, NEJM, EDGAR, top journals). Defensive
  normalization filter at the agent boundary drops drift between LLM output and the
  domain enum
- **Memo Writer** — diligence record → 2-page narrative investment memo ending with a
  recommendation paragraph
- **Game-Theory Adversary** — devil's-advocate critique surfacing signaling-equilibrium
  violations, winner's-curse adjustments on M&A comparables, and Bayesian-persuasion flags
  on selective disclosure patterns

### v1.5 — ML PoS Prior with calibrated uncertainty (shipped)

- **PubMedBERT-embedded eligibility-criteria text** + 36-dim structured features = 804-dim
  feature vector → **LightGBM regularized**, supervised on real Phase 1/2/3 → approval
  outcomes from the HINT clinical-trial corpus (Fu et al. 2022)
- **Test AUC 0.7030** on HINT held-out test split (Doane 2025 baseline: 0.7404)
- **Two-axis uncertainty**: (1) 90% bootstrap-percentile interval across an ensemble of 10
  LGBMs trained on independent bootstrap resamples (displayed in UI), (2) **Mondrian
  split-conformal coverage** per phase, recorded in the artifact and exposed at
  `/api/modules/ml_pos_prior/model_info` (overall test coverage 91.7%, per-phase
  89.1%/92.2%/92.4%). The bootstrap band is the epistemic "how much does the model
  disagree with itself"; the conformal radii are the formal frequentist coverage report
- **Cache-first inference pattern** with feature-fingerprint validation — canonical
  assets serve from disk; novel inputs hit the in-container PubMedBERT
- **Calibration Dashboard** — SQLite-backed `log_prediction` / `resolve_prediction` with
  Brier-score tracking by TA / modality / capital-position tier. Public prediction log
  at [`predictions/`](predictions/)

### v1.7 — Reader-journey IA redesign (shipped)

The `/diligence/[asset]` page restructured from module-registry-discovery order to an
equity-research / IC-memo reading order. Six named sections, each answering one specific
question the reader is trying to answer at that moment:

- **HeroBanner** ("30-second read") — recommendation chip + rNPV range + LOA microsplit
  (BIO → Reflexivity → ML) + reflexivity tier + catalyst
- **Thesis** — reflexivity slider promoted out of the sidebar to the section's leading
  element; PoS waterfall + ML PoS Prior follow
- **Valuation** — rNPV + Comparables (Comparables before Scorecard per equity-research
  convention; number-readers anchor rNPV to deal comps before qualitative review)
- **Operational** — Scorecard + Calibration
- **Risk & Limits** — consolidated LimitationsPanel + AdversaryPanel (per the healthcare-VC
  research, "the section that determines a yes/no vote")
- **Take Action** — Auto-Diligence + Memo Writer + methodology link

Section grouping is configuration; the dynamic-registry pattern is preserved.

### v1.8 — Persona views (shipped)

Four reader personas selectable from the global header. Same underlying diligence record
through four audience-specific presentations:

- **VC Associate** (default) — the v1.7 reader-journey layout
- **IC Voter** — 1-page summary: recommendation + top-3 risks + top-3 reasons + catalyst
  (auto-derived from scorecard's red_flags / green_flags), single "Decision view"
  section, no ActionSection. ~2-minute read.
- **Scientific Reviewer** — mechanism + target + biomarker + trial design upfront, ML
  PoS Prior elevated, rNPV + comparables hidden. TrialDesignCard with CT.gov link leads
  the Science section.
- **Quant / Calibration-focused** — AUC + Brier + per-phase conformal coverage
  (color-coded against 90% target) + ML-vs-rule disagreement, **no recommendation chip**.
  ModelInfoRawCard exposes the literal `/model_info` JSON in a lazy-loading collapsible.

Reuses the theme-toggle infrastructure pattern (localStorage + DOM attribute + anti-FOUC
inline script). Persona toggle ships with two Codex review passes addressed.

### v2.0 — Portfolio Sizing (shipped, separate audience)

Kelly + conviction multiplier + barbell allocation. Targets the biotech *fund manager*
(not single-asset diligence). Lives at [`/portfolio`](https://asclepius-lyart.vercel.app/portfolio).

## Roadmap

What's still ahead, in rough priority order:

- **v1.5.4 — Locally-adaptive conformal**: scale conformal residual by bootstrap std to
  unify both uncertainty axes (formal coverage AND useful band shape). Documented as a
  next-up candidate in `methodology/09-ml-pos-prior.md`.
- **CT Open benchmark**: external AUC + calibration metrics against the April-2026
  uncontaminated public benchmark ([arXiv:2604.16742](https://arxiv.org/abs/2604.16742)).
  Originally planned for v1.5; pending.
- **Methodology parity lint**: small CI script grep-asserting that every cited percentage
  in `methodology/*.md` appears in `api/app/data/*.json` or `app/modules/*/engine.py`.
- **Fresh Loom demo**: persona toggle now joins the reflexivity slider as a headline beat;
  worth re-recording.
- **Compact panel rendering for IC Voter**: when shipping a persona that explicitly
  collapses tornado / MC histogram / audit-trail details to literalize the 1-page summary.

Deliberately *not* on the roadmap: conversational "Ask Asclepius" chat tab (different
surface, weakly differentiated vs the existing agent buttons). See the
[product thesis](methodology/00-product-thesis.md) for the three strategic trajectories
(portfolio artifact, maintained methodology platform, embedded in real workflows) and
why Trajectory B is the realistic ceiling.

## Maintenance cadence

Asclepius is positioned as a maintained tool, not a frozen artifact:

| Trigger | Effort |
|---|---|
| BIO/Informa publishes the next annual cohort (typically Q2) | 30 min — refresh `api/app/data/base_rates.json` |
| Damodaran's January cost-of-capital update | 15 min — refresh `api/app/data/wacc_benchmarks.json` |
| Major biotech M&A closes | 30 min per deal — add a new JSON to `api/app/data/comparables/` |
| Semi-annual methodology sweep | 2–3 hours — re-read writeups against current values |
| Framework run on a public asset | 1 min — log_prediction, then `python api/scripts/sync_predictions_to_public_log.py` + commit. See [`methodology/10-public-prediction-log.md`](methodology/10-public-prediction-log.md). |
| Public catalyst lands (FDA action, M&A, readout) | 5 min — resolve_prediction with source citation, sync + commit |

### Concrete prediction-log workflow

Log a new prediction (replace placeholders with the asset's actual values):

```bash
curl -s -X POST https://asclepius-api.fly.dev/api/modules/calibration/log_prediction \
  -H "Content-Type: application/json" \
  -d '{
    "asset_name": "<asset>",
    "phase": "phase_2",
    "therapeutic_area": "oncology",
    "modality": "small_molecule",
    "capital_position": "adequate",
    "predicted_pos": 0.161,
    "reflexivity_multiplier": 1.0
  }'
# → {"id": "<uuid>"}
```

Resolve a prediction when the catalyst lands:

```bash
curl -s -X POST https://asclepius-api.fly.dev/api/modules/calibration/resolve_prediction \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_id": "<uuid-from-log_prediction>",
    "outcome": 1,
    "outcome_source": "FDA accelerated approval, NDA 216340, Dec 12 2022."
  }'
# → {"updated": true}
```

Publish to the public log + commit:

```bash
cd "$(git rev-parse --show-toplevel)"
python api/scripts/sync_predictions_to_public_log.py
git add predictions/
git commit -m "Log <asset> prediction" -m "<outcome source if resolved>"
```

Reference data is JSON-first with `source` fields on every row, so refreshes don't require
code changes. See [`docs/architecture.md`](docs/architecture.md) for the
contract.

## Reading the methodology folder

Sixteen writeups, designed to be read in any order. For a first pass:

1. [`02-reflexivity-thesis.md`](methodology/02-reflexivity-thesis.md) — the framework's
   load-bearing intellectual claim. Reads as an investor memo.
2. [`05-worked-example-adagrasib.md`](methodology/05-worked-example-adagrasib.md) — the
   retrospective backtest applied to the BMS / Mirati transaction. Ends with a verdict
   paragraph an investment committee can act on.
3. [`06-signaling-equilibrium.md`](methodology/06-signaling-equilibrium.md) — the formal
   game-theoretic derivation of the reflexivity adjustment from Spence (1973) and Akerlof
   (1970), with modern empirical support from Kao (2024 Management Science), Lo & Thakor
   (2022 Annual Review), and Ma et al. (2025).
4. [`09-ml-pos-prior.md`](methodology/09-ml-pos-prior.md) — the supervised ML PoS Prior
   on real HINT outcomes, including the bootstrap-percentile + Mondrian-split-conformal
   two-axis uncertainty story.
5. [`13-ct-open-benchmark.md`](methodology/13-ct-open-benchmark.md) — the v1.5.5 honest
   external validation against CTO's manually-annotated uncontaminated tier. AUC drops
   10.3 pp on out-of-distribution data; the writeup unpacks why and what it means for
   how to read the ML prior on assets outside HINT's coverage.
6. [`00-product-thesis.md`](methodology/00-product-thesis.md) — strategic framing of the
   project itself, via The Loom's six-phase AI-native product framework. Includes the
   v1.7 "Reading order" and v1.8 "Persona modes" subsections explaining the
   audience-modeling thesis behind the UI itself.

Or browse the [methodology index](https://asclepius-lyart.vercel.app/methodology) on the live
deployment.

## Stack

- **API**: Python 3.11+, FastAPI, pydantic v2, numpy/scipy. 176 tests, all passing
  (includes the parity test that grep-asserts `web/lib/reflexivity-tiers.ts` stays in
  sync with `api/app/data/reflexivity_adjustments.json`, plus 4 bootstrap-path tests
  + 1 real-LightGBM integration test for the ML PoS Prior engine).
- **ML inference**: torch 2.6.0+cpu + transformers 4.46.x + lightgbm 4.x. PubMedBERT
  loaded in-container; LightGBM artifact (~3 MB; main model + 10 bootstrap models +
  conformal radii + per-phase coverage) shipped with the Docker image.
- **Web**: Next.js 14 (App Router), Tailwind, recharts, react-markdown, TypeScript.
  Production build clean. 18 static pages prerendered.
- **Deploy**: Vercel (web) + Fly.io (api) — live at `asclepius-api.fly.dev` (image size
  733 MB). See [`docs/deployment.md`](docs/deployment.md).
- **CI**: GitHub Actions running ruff + pytest + pnpm typecheck + pnpm build on every push.

## Related work

To our knowledge, no widely-used open-source Python rNPV library for biotech exists.
Educational content in the space ([Models Hub](https://financialmodelshub.com/risk-adjusted-npv-explained-the-gold-standard-for-biotech-valuation/),
[Vision Lifesciences](https://visionlifesciences.com/insights/rnpv-valuation-guide-pharma),
[BiopharmaVantage](https://www.biopharmavantage.com/pharma-biotech-valuation-best-practices))
is methodology articles; operational tools (Vision Lifesciences' product, vendor offerings)
are closed-source/commercial. [Wong, Siah, Lo (2019)](https://academic.oup.com/biostatistics/article/20/2/273/4817524) did not release code or
data — both are constrained by Informa's proprietary licensing.

Adjacent open project: [bvssaisantoshi19/clinical-trial-outcome-prediction](https://github.com/bvssaisantoshi19/clinical-trial-outcome-prediction)
solves the prediction-end of the PoS problem using AACT (ClinicalTrials.gov) data. Doesn't
address rNPV, scorecards, or comparables. Asclepius's v1.5 ML PoS Prior takes a different
approach — supervised on the HINT clinical-trial-outcome corpus (Fu et al. 2022) with
PubMedBERT-embedded eligibility-criteria features rather than AACT structured fields.

Asclepius is positioned as **the first open-source implementation tying phase-gated cash
flows + reflexivity-adjusted PoS + supervised ML-PoS on real outcomes (with bootstrap +
Mondrian conformal uncertainty) + Monte Carlo with documented priors + audit-trail
discipline + persona-aware presentation in one codebase**.

## Sources and citations

The methodology cites peer-reviewed work or primary industry sources for every empirical
claim. The canonical references:

- Spence, M. (1973). Job Market Signaling. *Quarterly Journal of Economics*.
- Akerlof, G.A. (1970). The Market for "Lemons". *Quarterly Journal of Economics*.
- Stewart, J.J., Allison, P.N., Johnson, R.S. (2001). Putting a Price on Biotechnology.
  *Nature Biotechnology* 19(9).
- Wong, C.H., Siah, K.W., Lo, A.W. (2019). Estimation of clinical trial success rates and
  related parameters. *Biostatistics* 20(2).
- Lo, A.W., Thakor, R.T. (2022). Financing Biomedical Innovation. *Annual Review of
  Financial Economics* 14.
- Kao, J. (2024). Information Disclosure and Competitive Dynamics. *Management Science*.
- Ma, S., Han, W., Lê Cook, B., et al. (2025). Predicting accrual success for better
  clinical trial resource allocation. *Scientific Reports* 15.
- Fu, T., Huang, K., Xiao, C., Glass, L.M., Sun, J. (2022). HINT: Hierarchical Interaction
  Network for Trial Outcome Prediction. *Patterns* (Cell Press). Backbone of the v1.5 ML
  PoS Prior's supervised labels.
- Gu, Y., Tinn, R., Cheng, H., et al. (2021). Domain-Specific Language Model Pretraining
  for Biomedical NLP. *ACM Transactions on Computing for Healthcare* — the PubMedBERT
  paper. Backbone of the v1.5 eligibility-criteria embedding.
- Vovk, V., Gammerman, A., Shafer, G. (2005). *Algorithmic Learning in a Random World*.
  Foundation for the v1.5.3 Mondrian split-conformal coverage discipline.
- BIO / Informa Pharma Intelligence / QLS Advisors (2021). Clinical Development Success
  Rates 2011-2020.
- Damodaran, A. (2025). Cost of Capital by Industry (US). NYU Stern.

Full per-writeup citations are in [`methodology/`](methodology/).

## License

MIT — see [LICENSE](LICENSE).

The methodology writeups are released under the same license. If you build on the
reflexivity adjustment, the productization-of-methodology framing, or the audit-trail
discipline, an acknowledgment in the relevant docs is appreciated but not required.
