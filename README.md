# Asclepius

**Live:** <https://asclepius-bio.vercel.app> · [methodology index](https://asclepius-bio.vercel.app/methodology) · [how the tool thinks — a worked case](https://asclepius-bio.vercel.app/showcase) · [worked example](https://asclepius-bio.vercel.app/diligence/adagrasib)

> A biotech research / analysis / advising tool. It treats two *structural* facts as
> first-class value drivers that generic valuation tools ignore — **who holds the capital**
> and **who controls the supply** — and it produces a *defensible view* on a single asset:
> a call, a conviction, and the one readout that would flip it. Every number ships its citation.

Asclepius is used by its author and a small trusted circle to analyze real pre-approval biotech
assets. It is **not** a public product, a SaaS, or a forecasting service. Its value is the
**creativity, architecture, and methodology** it embodies — a framework that forms a view, shows
its work, and names what would change its mind.

## The differentiators

1. **Two named structural path-dependencies.** Most tools price a drug as a probability-weighted
   cash-flow stream and stop. This one adds:
   - **[Reflexivity](methodology/02-reflexivity-thesis.md)** — a Spence-style signaling multiplier
     on probability-of-success keyed to sponsor capital state. Capital-constrained sponsors run
     worse trials; well-capitalized sponsors enable adaptive designs and stronger regulatory
     engagement. Grounded in Spence (1973) with modern empirical support (Kao 2024, Lo & Thakor
     2022, Ma 2025).
   - **[Supply constraint](methodology/22-supply-constraint-thesis.md)** — a manufacturability
     multiplier on PoS *and* a peak-sales ceiling in rNPV. A binding isotope/raw-material/capacity
     constraint is execution risk on the way in and a revenue cap at the top. Generic DCF models
     put neither on the revenue line.

   Both are reasoned structural hypotheses, grounded in named sources and **honestly labeled as
   estimates, not calibrated corrections.**

2. **A recommendation that earns itself.** The [memo synthesis](methodology/12-memo-synthesis.md)
   doesn't print a number — it forms a *view*: an explicit conviction level (orthogonal to
   buy/hold), a one-line verdict on how the path-dependencies net-moved the call, a priced close,
   and a **falsifiable kill criterion** (a named event with a threshold and a direction). The
   schema forces all four — a memo cannot come back without them.

3. **An architecture that generalizes.** A single [`DiligenceRecord`](api/app/domain.py) pydantic
   model is the source of truth; three auto-discovered registries (`data_sources/`, `modules/`,
   `agents/`) plug into FastAPI on startup; the Next.js frontend renders one panel per module from
   the `/api/modules` manifest. Adding the entire supply-constraint dimension (a new path-dependency
   affecting two engines) required **no core edits** — it slotted into the same waterfall position
   reflexivity occupies. See [`docs/architecture.md`](docs/architecture.md).

## A worked case

The [showcase](https://asclepius-bio.vercel.app/showcase) narrates one hard asset end to end — an
Actinium-225 alpha-emitter from a capital-constrained junior — the one asset that lights up every
differentiator at once (both path-dependencies bite, and it routes to the curated radiopharmaceutical
comp cohort). Every number on that page is real engine output; the reading is editorial.

The canonical **retrospective calibration example** is adagrasib, run on only public information
available before the KRYSTAL-12 Phase 3 readout (June 2022 cutoff):

| Scenario | Framework value | Reality |
|---|---:|---|
| Rule-based PoS (BIO base → reflexivity → final LOA) | **~13%** | — |
| ML PoS Prior (second opinion; PubMedBERT + LightGBM on HINT) | **~24%** | Real-outcome-supervised |
| Pre-readout (Phase 2) base-case rNPV | **~$570M** | Mirati's market cap at cutoff |
| Post-readout (at NDA) base case | **~$4.9B** | — |
| Actual BMS acquisition (Oct 2022) | $4.8B | Brackets within ~2% |

BMS paid a small premium to the success-weighted central case — defensible as strategic
KRAS-franchise value, no margin of safety for a financial buyer. Full write-up:
[05-worked-example-adagrasib.md](methodology/05-worked-example-adagrasib.md). This is *calibration
against a known outcome*, not a prediction.

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

**Two hero interactions:**

1. **Reflexivity slider** (top of the Thesis section). Drag from "Adequate" to "Well capitalized"
   and watch the LOA microsplit, PoS waterfall, ML PoS band, rNPV base case, Monte Carlo
   distribution, and tornado all recompute live — the headline differentiator visibly moving rNPV.
2. **Persona toggle** (global header). Cycle VC Associate / IC Voter / Scientific Reviewer / Quant
   and watch the whole page reorganize around each reader's first question. Same data, four reads —
   "methodology applied to its own presentation" ([product thesis](methodology/00-product-thesis.md)).

## What's in the build

**The deterministic spine:**

- **PoS engine** — a `base × Π(multipliers)` chain (base rate → modality → mechanism/biomarker →
  target validation → regulatory designations → **reflexivity** → **supply constraint**), every
  step logged in the audit trail with a primary-source citation. Frontier modalities (degrader,
  radiopharmaceutical, epigenetic editing) carry honest "Asclepius estimate, no BIO/Informa cohort"
  provenance rather than borrowing a citation they aren't entitled to.
- **rNPV engine** — phase-gated cash flows, mid-year discount convention, 10,000-path Monte Carlo
  (log-normal peak / beta LOA / normal WACC / triangular COGS), tornado sensitivity, and the
  supply-constraint peak-sales ceiling.
- **8-pillar diligence scorecard** — including a computational-infrastructure pillar that prices a
  sponsor's AI/ML/data assets.
- **Cited deal comparables** — cohort routing by (therapeutic area, modality family) with a curated
  radiopharma cohort and an honest same-TA-approximation fallback; provenance on every row.

**Three runtime agents** (each one UI button; coordination via the deterministic core):

- **Auto-Diligence** — asset name → structured `AssetInput` with citations from a high-signal
  domain allowlist (CT.gov, FDA, EDGAR, top journals); output coerced to the domain enums at the
  boundary.
- **Memo Writer** — diligence record → a structured investment memo with the defensible-recommendation
  discipline ([12-memo-synthesis.md](methodology/12-memo-synthesis.md)).
- **Game-Theory Adversary** — a devil's-advocate pass surfacing signaling-equilibrium violations,
  winner's-curse adjustments, and Bayesian-persuasion flags on selective disclosure.

**A second-opinion ML PoS prior** — PubMedBERT-embedded eligibility text + structured features →
LightGBM (phase-stratified), supervised on real HINT trial→approval outcomes, with a
bootstrap-percentile band and split-conformal coverage exposed at `/api/modules/ml_pos_prior/model_info`.
It is a *check on* the rule-based estimate, not a forecast: agreement raises confidence, divergence
flags an asset for closer review.

**Product surfaces:**

- **Persona-aware diligence page** — the same record through four audience-specific reads
  (VC Associate / IC Voter / Scientific Reviewer / Quant).
- **Narrated showcase** — the "how the tool thinks" case study.
- **Saved analyses** — persist / list / reload a completed analysis (gated).
- **Portfolio sizing** — Kelly + conviction + barbell allocation for the fund-manager view
  ([`/portfolio`](https://asclepius-bio.vercel.app/portfolio)).

## Access

The live app's AI features (the three agents, saved analyses) are gated behind a shared passphrase
so they don't spend the owner's API key — it is a tool for a small trusted circle, not a public
service. The deterministic modules and the methodology are open.

## Stack

- **API**: Python 3.11+, FastAPI, pydantic v2, numpy/scipy. Full app test suite passing.
- **ML inference**: torch (cpu) + transformers + lightgbm; PubMedBERT loaded in-container, the
  LightGBM artifact shipped with the Docker image.
- **Web**: Next.js 14 (App Router), Tailwind, recharts, react-markdown, TypeScript.
- **Deploy**: Vercel (web) + Fly.io (api). See [`docs/deployment.md`](docs/deployment.md).
- **CI**: GitHub Actions — ruff + pytest + pnpm typecheck + pnpm build on every push.

## Reading the methodology folder

A first pass:

1. [`00-product-thesis.md`](methodology/00-product-thesis.md) — what the tool is and what it's a proof of.
2. [`02-reflexivity-thesis.md`](methodology/02-reflexivity-thesis.md) — the load-bearing claim (capital → PoS).
3. [`22-supply-constraint-thesis.md`](methodology/22-supply-constraint-thesis.md) — the second path-dependency (supply → PoS + a revenue ceiling).
4. [`12-memo-synthesis.md`](methodology/12-memo-synthesis.md) — what makes a recommendation defensible.
5. [`06-signaling-equilibrium.md`](methodology/06-signaling-equilibrium.md) — the game-theoretic derivation of reflexivity from Spence (1973).
6. [`05-worked-example-adagrasib.md`](methodology/05-worked-example-adagrasib.md) — the framework run end to end.

Or browse the [methodology index](https://asclepius-bio.vercel.app/methodology) live.

## Sources and citations

Every empirical claim cites peer-reviewed work or a primary industry source. Canonical references:

- Spence, M. (1973). Job Market Signaling. *Quarterly Journal of Economics*.
- Akerlof, G.A. (1970). The Market for "Lemons". *Quarterly Journal of Economics*.
- Wong, C.H., Siah, K.W., Lo, A.W. (2019). Estimation of clinical trial success rates. *Biostatistics* 20(2).
- Lo, A.W., Thakor, R.T. (2022). Financing Biomedical Innovation. *Annual Review of Financial Economics* 14.
- Kao, J. (2024). Information Disclosure and Competitive Dynamics. *Management Science*.
- Ma, S., et al. (2025). Predicting accrual success for better clinical trial resource allocation. *Scientific Reports* 15.
- Fu, T., et al. (2022). HINT: Hierarchical Interaction Network for Trial Outcome Prediction. *Patterns*.
- Gu, Y., et al. (2021). Domain-Specific Language Model Pretraining for Biomedical NLP (PubMedBERT). *ACM TOCH*.
- BIO / Informa / QLS Advisors (2021). Clinical Development Success Rates 2011–2020.
- Damodaran, A. (2025). Cost of Capital by Industry (US). NYU Stern.

Full per-writeup citations are in [`methodology/`](methodology/).

## License

MIT — see [LICENSE](LICENSE). The methodology writeups are released under the same license.
