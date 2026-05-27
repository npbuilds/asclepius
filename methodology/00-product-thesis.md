---
title: "Product thesis — what Asclepius is, what it's becoming, what it's a proof of"
summary: "Applies The Loom's six-phase product framework (Sense / Envision / Seed / Surface / Evolve / Synthesize) to Asclepius itself. Reframes the project from 'portfolio biotech-valuation tool' to 'first proof point of a method for productizing skill-based AI methodology.'"
framework: "The Loom — an AI-native product-orchestration framework with six cognitive modes (Sense / Envision / Seed / Surface / Evolve / Synthesize). The author's private skill library; not directly distributed with this repo."
audience: "Read this first. It frames what the rest of the methodology folder is *for*. The technical writeups (01-06) document the framework's mechanics; this document documents the framework's *strategic position*."
---

# Product thesis

## Why this document exists

The Loom's first principle is that intelligence products are not features you ship — they are living systems you cultivate. Most portfolio projects fail not because the code is bad but because the candidate cannot articulate **what kind of thing it is becoming**. A biotech-valuation web app is a feature. A maintained methodology platform with quarterly refresh discipline and an explicit reflexivity thesis is a position. The same code, framed differently, lands as either.

This document does the framing. The technical methodology files (01-06) describe what the framework computes and cite the evidence. This file describes *why the framework exists*, *what it is becoming*, and *what it is a proof of*.

## Phase 1 — Sense the field

What is becoming possible at the intersection of skill-based AI methodology and biotech investment intelligence in mid-2026?

**Three independent signals converging:**

1. **Peer-reviewed ML for clinical-trial outcome prediction has crossed a usefulness threshold.** [Doane (December 2025)](https://arxiv.org/abs/2512.00586) reports a BioBERT-based pTRS classifier with ROC-AUC 0.74, materially better than industry base rates on 70% of trials in a held-out sample. [CT Open (April 2026)](https://arxiv.org/abs/2604.16742) provides a public uncontaminated benchmark for this category of model. Until 2025 the question "can an ML model beat BIO/Informa base rates?" was unsettled. It is now settled in the affirmative for narrow scopes.

2. **LLM agents are entering biotech diligence as a published technique.** [LLM-Based Agents for Competitive Landscape Mapping in Drug Asset Due Diligence (AAAI 2026)](https://arxiv.org/html/2508.16571v4) is the first peer-reviewed agentic system for the diligence workflow. It establishes that the architecture works for *competitive landscape mapping*; it does not address probability of success, rNPV, or scorecard aggregation. Those remain open.

3. **"Agentic VC" is now a commercial category.** Decile Hub's deal-memo agent, Affinity's AI surfaces, V7 Go's diligence-report automation — generic AI for venture diligence is past the prototype stage. Biotech-specific tooling is mostly closed (Insilico, Owkin, Recursion's internal stack) and is *upstream* of valuation (target identification, molecule design, trial design optimization). There is no equivalent open or shippable tool focused on *post-target, pre-readout valuation* with the reflexivity discipline.

**The capability shift this implies:** A solo builder can now ship a biotech-diligence tool whose intellectual content (the methodology) was infeasible to write from scratch a year ago, whose computational core (Monte Carlo over phase-gated cash flows with calibrated priors) is well-established, and whose agentic layer is a published-technique slot-in rather than an unsolved research problem. The pieces exist independently; the integration is the move.

**What is *not* yet happening, and what Asclepius positions against:**

- No publicly visible tool exposes the **reflexivity adjustment** explicitly as a sponsor-capital-state multiplier on PoS. Practitioners adjust for it implicitly when sizing positions; no framework codifies it.
- No publicly visible tool combines **deterministic auditable math + LLM-agent augmentation + cited provenance on every number** in one diligence surface. Existing tools are either deterministic-only (Bloomberg-style) or LLM-only (the agentic-VC category).
- No open biotech-diligence tool ships with a **maintained refresh cadence** tied to industry-data publication calendars. The closed tools have it; the open ones are one-shot research artifacts.

Asclepius's position in this field is not "first AI-for-biotech-diligence tool." That field is too crowded for that claim. The position is *"first open tool that prices reflexivity, ships with audit-trail discipline, and is designed for quarterly refresh."* That is a much narrower and more defensible flag to plant.

## Phase 2 — Envision the shape

What is Asclepius *becoming*?

The surface answer is: a biotech-VC-targeted portfolio web app demonstrating diligence methodology, anchored to the adagrasib retrospective backtest. That is what it *looks like*.

The Loom's deeper question is: what *kind of thing* is it becoming? Three trajectories are real, with different ceilings and different work to reach them.

### Trajectory A — Portfolio artifact only (the floor)

Ship v1. Deploy to Vercel + Railway. Record the three-beat Loom demo. Put the URL on the resume. The methodology folder serves as a writing sample. After the candidate's job search closes, the project enters dormant maintenance — no quarterly refreshes, no new methodology, no new comparables.

This is the floor. It works as a portfolio piece. It dies in 18 months as the BIO base rates age and the comparables become stale.

**Effort: 0 incremental after v1 ships. Career ceiling: gets the candidate the first interview.**

### Trajectory B — Maintained methodology platform (the realistic ceiling)

Ship v1. **Also** start a paired Substack — "The Reflexivity Brief" or similar — applying the framework to current public biotech assets once a quarter or once a month. Each post is a worked example with the same discipline as `05-worked-example-adagrasib.md`: pre-readout valuation, framework-output rNPV, opinion paragraph.

The Substack accomplishes three things simultaneously:
- Forces the quarterly refresh discipline (you can't write the post without re-running the framework with current data)
- Generates an ongoing writing sample at scale (recruiters who read 02-reflexivity-thesis can read seven more pieces in your voice)
- Builds a small audience of biotech investors and analysts who recognize your name and methodology

The framework's existence is what makes this content cheap to produce — the Substack post is largely "drag through the sliders, paste the verdict paragraph, cite the post-NDA bracket." The methodology is the moat; the Substack is the surface that exposes it.

**Effort: v1 ship + ~4 hours/month for posts. Career ceiling: gets the candidate identified as "the reflexivity person" in biotech VC. Same ceiling that a few specific quant-investing bloggers have reached for retail-friendly macro analysis.**

### Trajectory C — Embedded in real workflows (the aspirational ceiling)

A biotech VC firm or biotech BD team adopts Asclepius internally. They license the methodology privately, fork the codebase, and use it on real deals. The reflexivity adjustment shows up in their investment committee decks. The candidate becomes a methodology advisor or joins the firm.

The realistic version of this is a single-firm adoption, not a product-market category. The framework is too opinionated to win head-to-head against established platforms (Bloomberg, Capital IQ, internal Excel models), but it might win as the *opinionated layer on top of* those platforms for a firm whose investment thesis aligns with the reflexivity adjustment (i.e., a firm that already trades on sponsor capital quality).

**Effort: v1 ship + v1.1 agents + v1.5 ML-PoS + active business development. Career ceiling: at most one firm; possibly nothing; possibly meaningful.**

### Recommendation

**Aim for Trajectory B; do the work that keeps Trajectory C alive.** The Substack is the highest-leverage non-code surface and the maintenance-cadence section of the plan (added 2026-05-20) already supports it mechanically. Trajectory C requires Trajectory B to even be visible to the right people; B is the necessary path.

Trajectory A is the failure mode to actively avoid. The plan's framing of "deploy and record Loom" implicitly aims at A. The Substack — or some equivalent recurring writing surface — is the one addition that converts the project from artifact to platform.

## Phase 3 — Seed: what conditions are already planted

The Loom's third phase asks: what seeds enable the right behaviors to emerge?

Asclepius's v1 architecture has seeded six things that are doing their work whether or not we name them:

1. **Three-registry modular pattern** (data sources / modules / agents). Seeds the ability to add v1.5 ML-PoS without rewriting v1. Already proven to work — the four v1 modules use the same pattern that v1.5 will.

2. **DiligenceRecord as single source of truth.** Seeds future composability. Any new module that reads/writes this record automatically integrates with everything else.

3. **Audit-trail-as-engine-output.** Seeds methodology trustworthiness. The waterfall isn't a UI feature painted on top of a number; the number and the waterfall are computed together. This is what makes the framework defensible under scrutiny.

4. **JSON-first cited reference data.** Seeds maintainability. Quarterly refreshes are JSON edits, not code changes. Methodology updates are tracked in version control with their own commits.

5. **Methodology folder with primary citations.** Seeds writing-sample compounding. Each writeup is a standalone document that can be linked, excerpted, or syndicated. The Substack trajectory is mechanically supported.

6. **Reflexivity thesis as named concept.** Seeds intellectual identity. "The reflexivity person" is a position only if there is a position to take, and there is now a position with a writeup, a code implementation, an empirical citation (Ma 2025), and a theoretical foundation (Spence 1973).

What has *not* yet been seeded that Trajectory B requires:

- **A real prediction backlog.** The v1.5 Calibration Dashboard is a planned feature; for it to mean anything, the framework needs to have *made* predictions on public assets and *resolved* them against outcomes. This is content that has to be written, not code that has to be built.

- **A reader community.** GitHub stars, Substack subscribers, biotech-Twitter mentions. None of these exist for a tool that hasn't shipped. They are seeded by the Loom demo + the first Substack post, not by code.

- **A named position that other investors react to.** The reflexivity thesis is currently the framework's claim. For it to become a *position* in biotech VC, someone other than the candidate has to either adopt it or argue against it. That requires the writeups to be public, and ideally to be applied to current live readouts where investors will form their own view.

## Phase 4 — Surface: how the intelligence meets the world

The Loom's fourth phase is the most concrete. What surfaces are exposed today? What surfaces should be?

**Current surfaces (v1):**

| Surface | What it does | Audience | Coverage |
|---|---|---|---|
| Web app at `/diligence/[asset]` | Interactive valuation workbench | Anyone with the URL | Strong for technical demo; weak for shareable analysis |
| Methodology folder (`methodology/*.md`) | Cited writeup of the framework | VC associates reading the GitHub repo | Strong for technical credibility; weak for distribution |
| FastAPI service at `/api/*` | Programmatic access to the engines | Developers / future agents | Strong technical surface; no consumer-facing version |
| GitHub repo | Portfolio artifact + writing sample | Recruiters | Strong; the primary discovery surface today |

**Surfaces deliberately not in v1.x (defer or never):**

- **Conversational chat tab** — the "Ask Asclepius" idea. Deferred to v2 in the plan. The Loom's read: this is a *seductive* surface that wouldn't materially improve the product's positioning. Biotech VCs are not looking for a chatbot; they are looking for a defensible methodology. Chat is a *demonstration* of agent infrastructure, not a *use case* for diligence work. Build it only if the agentic infrastructure has another reason to exist (v1.1 agents already provide that reason).

- **Internal-tools API integration** (Notion, Obsidian, Excel) — interesting for Trajectory C; not v1.

**The underexposed surface — recurring writing**

There is one surface that costs nearly nothing in code and would compound dramatically over twelve months: **a maintained writing surface that uses the framework on real assets, posted publicly on a cadence.**

The format that fits the framework's discipline:
- One post per public biotech catalyst (Phase 3 readout, BTD grant, M&A close)
- Each post: contemporaneous-inputs valuation → framework output → opinion paragraph
- Embedded screenshots of the diligence workbench at the asset's URL
- Cross-linked to the relevant methodology files

Substrate exists for ten of these without writing a single new line of code: adagrasib (done — repurpose as Post 1), sotorasib, vorasidenib, datopotamab deruxtecan, every recent biotech M&A. A weekly cadence is unrealistic; monthly is realistic; quarterly is the floor.

**This is the highest-leverage suggestion in this entire document.** The framework's distribution problem dominates its capability problem. The capabilities are in place; the surface that exposes them to the right audience is not.

## Phase 5 — Evolve: how the system grows from use

Already planned (v1.5):

- **Calibration Dashboard.** Brier scores by therapeutic area, modality, capital-position tier. Tells the user whether the reflexivity adjustment is actually improving calibration relative to base rates. This is the *only* mechanism that converts the framework from "opinionated guess" to "evidence-tracked methodology."

- **ML-PoS Prior alongside the deterministic engine.** Adds a second opinion. Convergence between the deterministic and ML estimates increases confidence; divergence flags an asset for closer human review. Not a replacement for the deterministic engine — a check on it.

What should be added that is not currently in the plan:

- **A public prediction log.** Every framework run on a real public asset is logged to a file in the repo (`predictions/<asset>-<date>.json` or similar) with the input snapshot and the framework output. When the readout happens, the prediction is resolved against the outcome. This is the data the Calibration Dashboard runs on, but the *transparency* of the log being public is what gives the calibration claim teeth. A private dataset of "our model is calibrated" is unfalsifiable; a public log is auditable.

- **A methodology changelog.** When BIO 2024 ships and `base_rates.json` updates, that's a methodology change. Every methodology change is committed with a note about which assets it affects (if any are in the prediction log) and which historical numbers are now stale. The discipline of *naming* methodology changes is what converts "we updated the data" into "v1.4 of the methodology shipped 2026-Q3 with the BIO 2024 cohort."

- **A failure post-mortem template.** When the framework's prediction misses badly, write the post-mortem. Format: what we thought we were measuring, what we actually measured, what the framework would need to do differently. These are the most valuable Substack posts. The "framework predicted X, actual was Y, here's what went wrong" piece is more credible than ten "framework predicted X, actual was X" pieces.

## Phase 6 — Synthesize: the meta-pattern

This is the highest-altitude observation The Loom is qualified to make.

**Asclepius is not the user's first project. It is the user's first proof point.**

The user has been building a skill library — Asclepius skill-suite (biotech diligence), spelunker (research), the-loom (this), Archon (investing), binding-vow (problem-solving), and others. Each skill suite is *methodology*. Methodology is powerful when invoked inside a Claude session. It is not a product.

Up to now, the implicit hypothesis was: *"the skill library is the IP; people will invoke skills directly."* That hypothesis has a ceiling — most people don't run Claude Code sessions, and the ones who do have their own skill libraries.

Asclepius tests a different hypothesis: ***"the skill library is the IP, but the productized form is a deterministic engine wrapping the methodology, with the skills running as v1.1 agents on top."*** The architecture is the test: domain.py is the skill methodology rewritten as a pydantic model; the engines are the skill methodology rewritten as pure functions; the v1.1 agents are the skills, reinstated, doing the work skills are uniquely good at (research, writing, adversarial critique) while the deterministic layer handles the math.

If this hypothesis is right, every domain in the skill library is similarly productizable. Archon (investing skill suite) → a maintained methodology platform for cross-asset diligence with a calibration dashboard. Binding-vow (problem-solving suite) → a productized problem-statement-quality service. The pattern is general.

If Asclepius works as a portfolio piece, it is *not* "the candidate built a biotech valuation tool." It is *"the candidate demonstrated a method for productizing skill-based AI methodology, and biotech valuation is the first instance."* That positioning matters because:

- It signals strategic awareness, not just execution
- It implies the next thing the candidate builds will look architecturally similar (modular registry, audit-trail discipline, methodology folder, maintenance cadence) but operate in a different domain
- It treats the skill library as a generative asset rather than a feature roadmap
- It is the kind of claim that converts a portfolio review into a strategic conversation about what the candidate would build next, which is the conversation that closes hires

The README should make this thesis visible. Not in marketing-copy form — in one paragraph, in the first 200 words after the reflexivity hook, signaling that the architecture is intentional and replicable.

## Reading order — how the diligence page is shaped

A senior biotech investor opening `/diligence/<asset>` carries a specific
sequence of questions, generated one by the previous. The page's
information architecture (v1.7.0+) is anchored to that sequence rather
than to the order in which our backend modules happen to be registered.

The framing this borrows from is **equity-research convention**: a public
sell-side report's first page is *not* the company overview or the
financial model — it is the recommendation banner (Buy / Hold / Sell)
+ target-price range + recent catalysts. The reader's first question is
"do I keep reading?", not "show me the math." Standardized across decades
of sell-side practice (see the
[Mergers & Inquisitions guide to equity research reports](https://mergersandinquisitions.com/equity-research-report/),
the public
[Bessemer Venture Partners memo collection](https://www.bvp.com/memos),
and the
[Danske Bank Pharma Equity Group sample report](https://research.danskebank.com/link/PharmaEquityGroup030724cr/$file/Pharma%20Equity%20Group_030724_cr.pdf)),
this pattern reliably matches how investors actually consume single-asset
analyses.

The IC-memo literature points the same way. Healthcare-VC IC voters
specifically scan for **risk awareness** as the partner-killer dimension
(see
[Inside an Early-Stage VC Investment Memo, Qubit Capital](https://qubit.capital/blog/early-stage-vc-investment-memo)
and
[The Ultimate Guide To VC Investment Committee Memos, The VC Factory](https://thevcfactory.com/investment-committee-memos/));
risk-section depth is the single most decision-load-bearing surface
because partners read for what the analyst *failed to think about*, not
what they emphasized. A diligence tool that buries its limitations panel
in a sidebar is signaling the wrong priorities.

### The 30-second / 2-minute / 5-minute / 10-minute / IC-vote read

The page is organized into five named beats, each answering one specific
reader question generated by the previous. Each beat targets a
characteristic time budget — what fraction of a 10-minute first read
the section earns. Section headers carry the question explicitly in
the live UI as one-line italic microcopy.

| Section | Reader time | Question it answers |
|---|---|---|
| **Hero banner** | 30 seconds | "Should I keep reading? Is this in my fund's mandate?" |
| **Thesis** | 2 minutes | "What's the framework's edge on this asset?" |
| **Valuation** | 5 minutes | "What's the number, and is the comp set consistent?" |
| **Operational diligence** | 10 minutes | "What's qualitatively true beyond the math?" |
| **Risk & limits** | the IC-vote read | "What could break this thesis?" |
| **Take action** | the action read | "What do I do with this diligence?" |

### Design choices that fall out of this framing

- **The recommendation chip is in the banner, not buried below a memo
  button.** A reader's first question is the recommendation; equity
  research puts it on page 1; this page does too. Color-coded by
  Buy/Hold/Avoid tone so the at-a-glance read is unambiguous.

- **The reflexivity slider sits inside the Thesis section, not in a
  sidebar.** The slider is the framework's headline differentiator
  (see [02-reflexivity-thesis.md](02-reflexivity-thesis.md)); placing
  it as a parallel control rather than a step *inside* the PoS math it
  modifies side-channels the differentiator. Inline placement turns
  dragging it into the live recomputation demo the framework was
  built for — the user watches the PoS waterfall, ML PoS Prior band,
  and HeroBanner LOA row all update in real time.

- **Comparables render before Scorecard.** Equity-research convention:
  number-driven readers anchor rNPV against deal comps before
  consuming the qualitative 8-pillar scorecard. The order matches
  what the audience expects from a single-asset write-up.

- **Risk consolidated into a named co-equal section.** Pre-v1.7.0 had
  LimitationsPanel in the left aside and the Adversary's output behind
  a button — two warning surfaces fragmented across the page. The
  consolidated Risk section reads at the same visual register as
  Valuation, which is the right priority weight per the healthcare-VC
  research.

- **The asset form collapses by default for pre-staged assets.** A
  reader opening adagrasib doesn't need to edit fields — the canonical
  record is already populated. A one-line summary in the collapsed
  state tells the story; expand-on-click recovers full editability.

- **Action surfaces (Auto-Diligence, Memo Writer, methodology link,
  PDF export stub) live in a final "Take action" section.** Frames
  active controls as "what you DO with the diligence," not "another
  module to read." The disabled `[ export pdf · v1.8+ ]` button is
  deliberate: signals roadmap rather than hiding capability gaps.

### Why this matters for the productization thesis

The deeper point: the diligence page is itself an artifact of the
methodology — it doesn't just *contain* PoS / rNPV / scorecard, it is
*presented in* a way that respects the same investor-grade reading
discipline the math underneath does. Methodology applied to its own
surface, not just to its content.

For the reader who notices, this is the second-order signal: the
candidate didn't only build the math, they built the read. The
internal research notes that informed this design live at
[`docs/ia-redesign-notes.md`](../docs/ia-redesign-notes.md) for any
reviewer who wants the audit trail.

## What this changes about the build plan

Concrete adjustments to consider, listed in descending order of leverage:

1. **Add a recurring-writing surface to v1.x.** A Substack, a Notion-published series, or a methodology-folder running log of monthly worked examples. Costs ~4 hours/month. Highest-leverage non-code addition.

2. **Make the prediction log public from v1.** Currently the Calibration Dashboard is a v1.5 deliverable. The dashboard can wait; the *log file* that the dashboard runs on can be seeded in v1, with the adagrasib backtest as the first row. This costs an hour; it changes the framing from "we'll have a calibration story later" to "we have a calibration story already, here is the data."

3. **README's opening paragraph should articulate the productization-of-methodology thesis**, not just the reflexivity hook. The reflexivity hook is the headline. The productization thesis is the second sentence that converts the recruiter's read from "biotech tool" to "first proof of a method."

4. **Defer the chat tab indefinitely.** v2's "Ask Asclepius" is a vanity feature. Cut it from the plan or move it to v3+. The runtime agents (Auto-Diligence, Memo Writer, Game-Theory Adversary) already justify the agent infrastructure.

5. **The v1.1 agent rollout should be framed as "the methodology layer extended with agents,"** not "the chat layer added." Auto-Diligence augments the human reading press releases; Memo Writer augments the human writing investment memos; Game-Theory Adversary augments the human's adversarial pass. Each is a methodology amplifier, not a chat interface. This framing aligns with the productization thesis.

These are suggestions, not requirements. The plan is approved as-is; this document is the strategic context that should inform how Week 4 is *positioned* in the README and Loom demo, not how it is built.

## See also

- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the framework's load-bearing intellectual claim
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the first instance of what monthly Substack posts could look like
- [../README.md](../README.md) — should articulate the productization thesis in its second paragraph after the reflexivity hook
