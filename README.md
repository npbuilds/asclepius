# Asclepius

**Live:** <https://asclepius-lyart.vercel.app> · [methodology index](https://asclepius-lyart.vercel.app/methodology) · [worked example](https://asclepius-lyart.vercel.app/diligence/adagrasib)

> Asclepius is the first open rNPV tool that prices the path-dependency between a sponsor's
> balance sheet and their trial's probability of success. Capital-constrained sponsors run
> worse trials; well-capitalized sponsors enable adaptive designs and stronger regulatory
> engagement. We make that explicit and quantifiable, with citations on every number.

A biotech venture valuation workbench: phase-gated probability of success with an explicit
**reflexivity adjustment**, risk-adjusted NPV with 10,000-path Monte Carlo and tornado
sensitivity, an 8-pillar diligence scorecard (including a novel computational-infrastructure
pillar), and cited deal comparables — all built on a **modular registry pattern** so new
analysis modules, data sources, and runtime agents can be added by dropping a folder.

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
| Pre-readout (Phase 2) base case | **$516M** | Mirati's market cap at cutoff |
| Pre-readout Monte Carlo P25–P75 | **$290M – $700M** | Distribution over 10K simulated paths |
| Post-readout (at NDA) base case | **$4,581M** | — |
| Actual BMS acquisition (Oct 2022) | $4,800M | Brackets within 5% |
| Winner's-curse-adjusted private value | $4,400M – $4,600M | Pfizer was reported as competing bidder |

**The verdict:** BMS paid a 4.6% premium to the success-weighted central case — defensible
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

**The hero interaction**: drag the reflexivity slider in the left sidebar from "Adequate" to
"Well capitalized" and watch the PoS waterfall, rNPV base case, Monte Carlo distribution, and
tornado all update live. That single interaction is the framework's load-bearing demo.

## Architecture in one sentence

A `DiligenceRecord` pydantic model is the single source of truth; three auto-discovered
registries (`data_sources/`, `modules/`, `agents/`) plug into FastAPI on startup; the Next.js
frontend reads the `/api/modules` manifest endpoint and dynamically renders one panel per
module.

See [`docs/architecture.md`](docs/architecture.md) for the full contract on adding a new
module, data source, agent, or exporter without touching the core.

## What ships in v1

- **PoS engine** with a six-step adjustment chain (base rate → modality → mechanism modifiers
  → regulatory designations → reflexivity), every step logged in the audit trail with a
  primary-source citation
- **rNPV engine** with phase-gated cash flows, mid-year discount convention, Monte Carlo over
  log-normal peak sales / beta LOA / normal WACC / triangular COGS, and tornado sensitivity
- **8-pillar diligence scorecard** with red/green flag mechanics — including the novel
  computational-infrastructure pillar that explicitly prices a sponsor's AI/ML/data assets
- **Cited deal comparables** with provenance on every cohort row (encorafenib, selpercatinib,
  larotrectinib; the kinase-TKI single-asset M&A cohort)
- **Methodology folder** — seven writeups, ~20,000 words, every empirical claim cited to a
  peer-reviewed source or labeled as an analytical choice with explicit rationale
- **Worked example** anchored to the BMS / Mirati adagrasib transaction, framed as
  retrospective calibration (not prediction)
- **CI workflow** running `ruff` + `pytest` + `pnpm typecheck` + `pnpm build` on every push

## What's deferred (and why)

- **v1.1 — three runtime agents**: Auto-Diligence (spelunker-powered), Memo Writer
  (investment-memo-writer skill), Game-Theory Adversary (signaling-screening +
  auction-theory + bayesian-persuasion). Each maps to one UI button; coordination is via
  the deterministic core, not agent-to-agent calls.
- **v1.5 — ML-PoS Prior + Calibration Dashboard**: BioBERT classifier as a second-opinion
  PoS path benchmarked against the [CT Open public benchmark](https://arxiv.org/abs/2604.16742),
  plus SQLite-backed Brier-score tracking. Architectural test of the registry pattern —
  zero edits to existing core code.
- **v2 — portfolio-sizing tab and conversational "Ask Asclepius"**: different audience
  (biotech fund manager) and different surface (chat). The chat tab is *seductive but
  weakly differentiated*; the portfolio tab is a separate product.

See the [product thesis](methodology/00-product-thesis.md) for the three strategic
trajectories (portfolio artifact, maintained methodology platform, embedded in real
workflows) and why Trajectory B is the realistic ceiling.

## Maintenance cadence

Asclepius is positioned as a maintained tool, not a frozen artifact:

| Trigger | Effort |
|---|---|
| BIO/Informa publishes the next annual cohort (typically Q2) | 30 min — refresh `api/app/data/base_rates.json` |
| Damodaran's January cost-of-capital update | 15 min — refresh `api/app/data/wacc_benchmarks.json` |
| Major biotech M&A closes | 30 min per deal — add a new JSON to `api/app/data/comparables/` |
| Semi-annual methodology sweep | 2–3 hours — re-read writeups against current values |

Reference data is JSON-first with `source` fields on every row, so refreshes don't require
code changes. See [`docs/architecture.md`](docs/architecture.md) for the
contract.

## Reading the methodology folder

The seven writeups are designed to be read in any order, but for a first pass:

1. [`02-reflexivity-thesis.md`](methodology/02-reflexivity-thesis.md) — the framework's
   load-bearing intellectual claim. ~2,000 words. Reads as an investor memo.
2. [`05-worked-example-adagrasib.md`](methodology/05-worked-example-adagrasib.md) — the
   retrospective backtest applied to the BMS / Mirati transaction. ~2,400 words. Ends with a
   verdict paragraph an investment committee can act on.
3. [`06-signaling-equilibrium.md`](methodology/06-signaling-equilibrium.md) — the formal
   game-theoretic derivation of the reflexivity adjustment from Spence (1973) and Akerlof
   (1970), with modern empirical support from Kao (2024 Management Science), Lo & Thakor
   (2022 Annual Review), and Ma et al. (2025). ~3,000 words.
4. [`00-product-thesis.md`](methodology/00-product-thesis.md) — strategic framing of the
   project itself, via The Loom's six-phase AI-native product framework. Read if you want
   to understand what kind of thing Asclepius is becoming, not just what it computes.

Or browse the [methodology index](https://asclepius-lyart.vercel.app/methodology) on the live
deployment.

## Stack

- **API**: Python 3.11+, FastAPI, pydantic v2, numpy/scipy. 56 tests, all passing.
- **Web**: Next.js 14 (App Router), Tailwind, recharts, react-markdown, TypeScript.
  Production build clean.
- **Deploy**: Vercel (web) + Fly.io (api) — live at `asclepius-api.fly.dev`. See [`docs/deployment.md`](docs/deployment.md).
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
address rNPV, scorecards, or comparables — useful as a future reference for the v1.5 ML-PoS
module's training pipeline.

Asclepius is positioned as **the first open-source implementation tying phase-gated cash
flows + reflexivity-adjusted PoS + Monte Carlo with documented prior distributions +
audit-trail discipline in one codebase**.

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
- BIO / Informa Pharma Intelligence / QLS Advisors (2021). Clinical Development Success
  Rates 2011-2020.
- Damodaran, A. (2025). Cost of Capital by Industry (US). NYU Stern.

Full per-writeup citations are in [`methodology/`](methodology/).

## License

MIT — see [LICENSE](LICENSE).

The methodology writeups are released under the same license. If you build on the
reflexivity adjustment, the productization-of-methodology framing, or the audit-trail
discipline, an acknowledgment in the relevant docs is appreciated but not required.
