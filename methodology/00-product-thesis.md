---
title: "Product thesis — what Asclepius is, and what it's a proof of"
summary: "Asclepius is a biotech research / analysis / advising tool. Its value is the creativity, architecture, and methodology it embodies — a framework that forms a defensible view on a single asset, shows its work, and names what would change its mind. Read this first; it frames what the rest of the methodology folder is for."
audience: "Read this first. It frames what the rest of the methodology folder documents. The technical writeups (01–07, 09, 11, 22) describe what the framework computes and cite the evidence; this file describes what the framework is and why it exists."
---

# Product thesis

## What Asclepius is

A **biotech research / analysis / advising tool**. You give it a pre-approval asset — sponsor, phase, mechanism, capital position, supply situation — and it produces a *defensible view*: a probability-of-success chain with a full audit trail, a phase-gated rNPV with a Monte Carlo band, a routed comparable cohort, and an investment memo that makes a call, states its conviction, and names the single readout that would flip it.

It is used by its author and a small trusted circle to analyze real frontier assets. It is not a public product, not a SaaS, and not a forecasting service.

## What it's a proof of

The get-hired value of this project is **not a track record**. A live forecasting record takes years to mature and resolves after any plausible hiring decision. The value is the **creativity, structure, and methodology** the tool demonstrates — the kind of thing a skeptical biotech investor can read in an afternoon and conclude "this person thinks like an investor, and can build."

Three things carry that weight:

1. **Two named structural path-dependencies.** Most valuation tools price a drug as a probability-weighted cash-flow stream and stop. This one treats two *structural* facts as first-class value drivers: **who holds the capital** ([reflexivity](02-reflexivity-thesis.md) — a Spence-style signaling multiplier on PoS keyed to sponsor capital state) and **who controls the supply** ([supply constraint](22-supply-constraint-thesis.md) — a manufacturability multiplier on PoS *and* a peak-sales ceiling in rNPV). Both are reasoned structural hypotheses, grounded in named sources and honestly labeled as estimates, not calibrated corrections. They are the framework's point of view.

2. **A recommendation that earns itself.** The [memo synthesis](12-memo-synthesis.md) doesn't print a number — it forms a *view*: an explicit conviction level (orthogonal to the buy/hold direction), a one-line verdict on how the path-dependencies net-moved the call, and a **falsifiable kill criterion** (a named event with a threshold and a direction). It shows its work and it says what would change its mind.

3. **An architecture that generalizes.** A single [`DiligenceRecord`](../api/app/domain.py) is the source of truth; pluggable data-sources, analysis modules, and agents compose against it. Adding the supply-constraint dimension (a whole new path-dependency, with effects on two engines) required *no* core edits — it slotted into the same waterfall position reflexivity occupies. Every multiplier renders its real citation, including the frontier-modality ones that honestly say "Asclepius estimate, no BIO/Informa cohort." The audit trail is an engine output, not a UI decoration.

## Methodology applied to its own surface

The design discipline runs one level deeper than the math. The diligence page is organized by the *sequence of questions a senior investor actually asks* (recommendation first, then thesis, valuation, operational diligence, and — co-equal — risk & limits), mirroring equity-research and IC-memo convention rather than the order the backend modules happen to register. And it is **persona-aware**: a VC associate, an IC voter, a scientific reviewer, and a quant skeptic each open the same record and get a different first screen, because they ask different first questions. The framework's methodology informs not just *which* numbers to compute but *how to present* them — the persona system is the methodology admitting its readers are not interchangeable. (Implementation: [`web/lib/persona-config.ts`](../web/lib/persona-config.ts); design notes: [`docs/ia-redesign-notes.md`](../docs/ia-redesign-notes.md).)

## What it deliberately is not

- **Not a forecasting platform or a track record.** The framework's value is its reasoning structure, not a scoreboard. A second-opinion ML PoS prior is included (a model that *disagrees* with the rule-based estimate is a signal), and a per-asset segment reference gives directional cohort context — both explicitly caveated as analysis, not accountability.
- **Not a public launch.** It is gated for a small circle; there is no signup, billing, or growth surface.
- **Not calibrated truth.** The path-dependency magnitudes are structural hypotheses, honestly labeled. The tool's claim is "here is a defensible, auditable way to think about this asset," not "here is the right answer."

## See also

- [01-pos-framework.md](01-pos-framework.md) — the probability-of-success chain and its base rates
- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the load-bearing intellectual claim (capital → PoS)
- [22-supply-constraint-thesis.md](22-supply-constraint-thesis.md) — the second path-dependency (supply → PoS + a revenue ceiling)
- [12-memo-synthesis.md](12-memo-synthesis.md) — what makes a recommendation defensible
- [05-worked-example-adagrasib.md](05-worked-example-adagrasib.md) — the framework run end to end on one asset
