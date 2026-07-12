---
title: "Memo synthesis — what makes a recommendation defensible"
summary: "A number is not a recommendation. This writeup states the discipline the memo agent enforces: a defensible call carries an explicit conviction level, a verdict on how the structural path-dependencies moved it, a priced close, and a falsifiable kill criterion. The schema forces all four — a memo cannot come back without them."
primary_sources:
  - "Booth, R. (2011) — liquidity-thesis discipline: name the expected unit of value realization (strategic sale, IPO window, partnership), not just a valuation."
  - "IC-memo practitioner literature (Qubit Capital; The VC Factory) — partners read an investment memo for risk-awareness and for what the analyst would need to see to change their mind, not for the emphasized upside."
  - "Spence (1973) signaling + the reflexivity thesis (methodology/02) and supply-constraint thesis (methodology/22) — the two path-dependencies the close must reconcile."
framing: "This is the discipline that turns the deterministic engines' outputs into an advising output — a view a reader can act on and argue with."
related_implementations:
  - "api/app/agents/memo_writer/schemas.py — RecommendationClose forces conviction + path_dependency_verdict + kill_criterion as REQUIRED fields."
  - "api/app/agents/memo_writer/prompts.py — the defensibility hard-rules and the framework vocabulary the prose must use."
---

# Memo synthesis — what makes a recommendation defensible

## The problem a memo solves

The deterministic engines produce numbers: a likelihood of approval, an rNPV base case with a Monte Carlo band, a comparable-cohort multiple, a scorecard. Numbers are necessary and not sufficient. An investment committee does not vote on a number; it votes on a **view** — a recommendation someone is willing to defend, together with the one thing that would make them abandon it.

The memo is the surface that turns computation into advice. Its job is *synthesis and judgment*, not recapitulation — the committee has already seen the waterfall and the tornado. A memo that restates them has done nothing. A memo earns its place by making a call and standing behind it.

The failure mode this discipline exists to prevent is the **hedge**: "a complex asset with meaningful upside and material risks." That sentence is true of every asset ever financed. It is not a recommendation; it is the absence of one.

## Four moves that make a call defensible

A recommendation is defensible when it carries all four of these. The memo agent's `RecommendationClose` makes each a **required** field — because the model is forced (tool-use with a mandatory schema) to emit the structure, a memo *cannot* be returned without them.

### 1. Explicit conviction — orthogonal to the direction

`conviction ∈ {high, medium, low}`, stated separately from the buy/hold/avoid call. Direction and confidence are different axes: a "buy" can be high-conviction (the rNPV bracket and the comp read agree, and no single tornado driver flips the sign) or low-conviction (the whole verdict hinges on one contested input). Collapsing them — as a bare "buy" does — hides exactly the information a committee needs to size the position. Naming conviction, and being made to justify it from the body, is the first thing that separates a view from a guess.

### 2. The path-dependency verdict — how the structure moved the call

The two things this framework sees that a generic DCF does not are the [reflexivity tier](02-reflexivity-thesis.md) (sponsor capital → PoS) and the [supply constraint](22-supply-constraint-thesis.md) (manufacturability → PoS *and* a peak-sales ceiling). A defensible close states, in one or two sentences, **how those two net-moved the verdict** — citing the multipliers ("a distressed reflexivity tier ×0.85 and a severe supply ceiling −35% together pull this from buy to cautious"). When both are neutral (adequate capital, unconstrained supply) the memo says so explicitly rather than inventing an effect. This is the framework's differentiated thinking loaded *into the recommendation*, not left as decoration in the PoS section.

### 3. The priced close — a call is only a call at a price

Following the worked-example pattern ([05](05-worked-example-adagrasib.md)), the close is a single opinion paragraph in the form "at $X, the framework brackets the asset as ...". A price-conditioned recommendation ("buy at ≤ $Xm fully-diluted EV, hold above") is *explicit*, not hedged — it states the discipline. And per Booth's liquidity-thesis rule, the memo names the expected unit of value realization (a strategic sale to a specified acquirer class, an IPO window, a partnership), because a valuation with no path to realization is a spreadsheet artifact, not a thesis.

### 4. The falsifiable kill criterion — what would change your mind

The single most decision-load-bearing sentence in the memo. IC partners read for what the analyst *failed to think about*; the kill criterion is the analyst pre-empting that read by naming the disconfirming evidence themselves. It must be **falsifiable**: a named, observable event with a threshold and a direction — *"Phase 3 ORR < 40% at the H2'26 readout"* or *"failure to secure a multi-year Ac-225 supply agreement before the Phase 2 start"* — not a vague sentiment ("if efficacy disappoints"). A recommendation you cannot state a kill criterion for is a recommendation you have not finished thinking through.

## Why the schema enforces it

Discipline that depends on the writer remembering it is not discipline. The memo agent uses forced tool-use: the model must call the emit tool, whose input schema makes `conviction`, `path_dependency_verdict`, and `kill_criterion` required. The API validates the structure before the agent ever sees it, so the failure mode isn't "a memo that forgot to name a kill criterion" — it's a validation error the model has to fix. The structure is not a template the writer fills in when convenient; it is the contract the writer cannot exit without satisfying.

Two further guards live in the prompt rules: the memo may **not invent numbers** (it uses only values present in the computed brief), and it may not equivocate on the recommendation. Price-conditioned and readout-conditioned calls are acceptable because they are explicit; "complex asset with upsides and risks" is rejected because it is not.

## What this is, in one line

The memo synthesis is where the framework stops being a calculator and becomes an **advisor**: it forms a view, shows the structural reasons for it, prices it, and names — in advance, falsifiably — the evidence that would make it wrong.

## See also

- [00-product-thesis.md](00-product-thesis.md) — why the defensible recommendation is the product's point
- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) and [22-supply-constraint-thesis.md](22-supply-constraint-thesis.md) — the two path-dependencies the close must reconcile
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the priced-close prose pattern the memo mirrors
