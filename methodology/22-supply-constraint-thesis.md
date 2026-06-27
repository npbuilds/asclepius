---
title: "Supply constraint as a valuation path-dependency"
summary: "Manufacturing and raw-material supply constraints are a structural value-and-risk driver adjacent to reflexivity. They add trial-execution risk (a PoS effect) and, distinctively, cap achievable peak sales (an rNPV ceiling). Most rNPV tools price only the demand side of peak sales; Asclepius prices the supply side too."
audience: "Read this after 02-reflexivity-thesis.md. Reflexivity keys probability of success off sponsor capital; this is the second path-dependency, keying both PoS and the peak-sales ceiling off manufacturing / raw-material supply. The two share an intellectual structure: a known structural fact about the sponsor or the molecule that the population base rate silently averages over."
primary_sources:
  - "Asclepius framework dimension — supply-as-path-dependency. The tiers are reasoned estimates anchored on the actinium-225 isotope-supply constraint and on autologous cell-therapy manufacturing precedent. There is no published outcome cohort behind the tier magnitudes; this is stated plainly in the limitations section."
  - "Wong CH, Siah KW, Lo AW. Estimation of clinical trial success rates and related parameters. Biostatistics 20(2): 273-286 (2019). The population base rates the supply adjustment modifies."
---

# Supply constraint as a valuation path-dependency

## Thesis

A clinical asset's value is not a property of the molecule and its market alone. It is also a property of **whether the sponsor can manufacture the molecule at the scale the molecule's own clinical program and commercial opportunity demand.** For most assets this is a non-issue: small-molecule and standard biologic manufacturing scales with demand, and supply is not a binding constraint on either trials or sales. For a growing and economically important minority — radioligand therapies gated on scarce medical isotopes, autologous cell therapies gated on per-patient manufacturing throughput, modalities gated on limited viral-vector or fill-finish capacity — supply *is* binding, and it shapes the asset's value through two distinct channels.

This is the same intellectual move as the reflexivity adjustment. Reflexivity makes explicit a structural fact about the *sponsor* (its capital position) that the population PoS base rate silently averages over. The supply-constraint adjustment makes explicit a structural fact about the *molecule's manufacturability* that both the PoS base rate and the standard peak-sales assumption silently average over. In both cases the population statistic is the right starting point and the wrong ending point for a specific asset with a known structural feature.

## The two effects

Supply constraint enters the valuation in two places, which is what makes it a richer dimension than a single multiplier.

**Effect one — trial-execution risk (PoS).** A binding supply constraint gates trial throughput. If each dose of a radioligand therapy depends on an isotope whose global production is measured in grams per year, the sponsor cannot enroll and dose patients faster than the supply chain allows. Slower dosing means longer trials, more protocol amendments, more sites competing for the same constrained material, and a higher chance of accrual-driven trial failure. This is a probability-of-success effect, applied in the PoS chain as a multiplier right after the reflexivity adjustment — the second structural overlay in the same position in the waterfall.

**Effect two — the peak-sales ceiling (rNPV). This is the distinctive part.** The textbook rNPV takes a peak-sales figure — the analyst's estimate of annual revenue at maturity — and treats it as a demand-side quantity: addressable patients times price times penetration. But you cannot sell what you cannot make. If the same isotope constraint that slows the trial also caps the number of doses that can ever be produced in a year, then peak sales is bounded by supply, not demand, and the demand-side estimate overstates the achievable revenue. Asclepius applies a supply ceiling as a haircut on the effective peak sales that the revenue model uses. Every downstream computation — closed-form base case, tornado sensitivity, Monte Carlo distribution — runs off the supply-adjusted peak, so the ceiling propagates consistently rather than being bolted on at the end.

Most rNPV tools model only effect one, if they model supply at all, by nudging PoS. The peak-sales ceiling is the part the standard framework omits, and it is frequently the larger of the two effects in dollar terms.

## The worked case: actinium-225

The motivating example is the actinium-225 (Ac-225) alpha-emitter constraint in radiopharmaceuticals. Ac-225 is a short-half-life alpha-emitting isotope used in targeted radioligand therapy. Its global supply is genuinely scarce: historically it has been produced from a small number of legacy sources, and while accelerator-based and thorium-cyclotron production is expanding, the supply has been a recognized, repeatedly-cited bottleneck for the entire class of Ac-225-based therapeutics.

For an Ac-225 radioligand asset, supply gates *both* effects at once, which is why the worked case is clarifying:

- **It gates the trial.** Each patient dose consumes isotope; the trial cannot dose patients faster than the sponsor's allocation of a scarce global supply permits. The program's enrollment timeline is supply-bound, which raises execution risk.
- **It gates commercialization.** Even with a clean approval and strong demand, annual sales are capped by the number of doses producible from the available isotope. The demand-side peak-sales estimate — patients times price — is the wrong ceiling; the supply-side ceiling binds first.

An asset like this is correctly placed in the `severe` tier: a binding raw-material constraint that gates throughput and achievable peak sales simultaneously. By contrast, a complex-but-scalable modality — an autologous cell therapy whose per-patient manufacturing is intricate but whose capacity expands with investment, or a bispecific or viral-vector product with real but soluble capacity limits — belongs in the `moderate` tier: a modest execution-risk add and a soft revenue ceiling rather than a hard one.

## The tiers

The supply adjustment is implemented as a three-tier table, mirroring the reflexivity adjustment's structure. Each tier carries a PoS multiplier and a peak-sales ceiling.

| Tier | PoS multiplier | Peak ceiling | Description |
|---|---|---|---|
| Unconstrained | ×1.00 | 100% | No binding supply constraint; standard manufacturing scales with demand. The clean no-op default. |
| Moderate | ×0.97 | 85% | Complex but scalable manufacturing (autologous cell therapy, bispecifics, viral vectors). Modest execution risk; soft revenue ceiling. |
| Severe | ×0.93 | 65% | Binding raw-material / isotope / capacity constraint (e.g. Ac-225 alpha emitters). Gates both trial throughput and achievable peak sales. |

The unconstrained tier is a deliberate no-op: it applies a ×1.00 PoS multiplier and a 100% peak ceiling, and it still emits an audit-trail row. The row's presence is the point — it shows a reader that the supply dimension was considered and found non-binding, rather than silently omitted. This is the same discipline the rest of the framework applies: every dimension that *could* move the number leaves a visible trace even when it doesn't.

## Operationalization

The PoS effect is applied as a multiplicative factor in the PoS chain, immediately after the reflexivity adjustment, with the tier's rationale and the data layer's honest provenance string rendered verbatim into the audit trail. The placement is deliberate and parallel to reflexivity: base rate is population, modality is technology, mechanism is data, reflexivity is sponsor, and supply is manufacturability. A senior reader scanning the waterfall sees the two structural overlays — reflexivity and supply — sitting adjacent at the end of the chain.

The peak-sales ceiling is applied in the rNPV engine by folding it into the effective peak before any cash-flow computation runs. The engine surfaces both the ceiling percentage and the resulting supply-adjusted peak so the haircut is inspectable in the output, not buried in the math. Because the adjusted peak is the single input every downstream calculation reads, the tornado chart's peak-sales sensitivity swing correctly pivots around the constrained level rather than the nominal one.

For an asset where the severe ceiling binds, the effect on rNPV is roughly proportional to the haircut on peak sales, because rNPV weights revenue cash flows linearly in peak sales. A 65% ceiling therefore moves the revenue side of the valuation by roughly the same fraction, before the interaction with discounting and ramp. <!-- parity-allow: model-output --> That sensitivity is what makes the dimension consequential rather than cosmetic: for a supply-bound asset, the peak ceiling can be the single largest adjustment in the entire valuation.

## What we do not claim

This dimension is a reasoned structural overlay, not a calibrated empirical model. The honesty discipline here matters more than usual because the tiers are not backed by a published cohort.

- **The tier magnitudes are reasoned estimates, not cohort-derived statistics.** The ×0.97 / ×0.93 PoS multipliers and the 85% / 65% peak ceilings are anchored on two well-documented real-world constraints — the Ac-225 isotope-supply bottleneck and autologous cell-therapy manufacturing complexity — and on practitioner intuition about how binding those constraints are. They are not the output of a regression on supply-constrained-asset outcomes, because no such labeled cohort exists at the scale required to fit one. The data layer's `source` field says this in plain language, and that string is what the audit trail renders.

- **The two effects are modeled as independent multipliers, not a joint mechanism.** In reality the PoS effect and the peak-sales ceiling share a common cause (the same scarce isotope gates both), so they are correlated, not independent. The framework applies them as separate factors for transparency and inspectability; a fully joint structural model of supply-bound development and commercialization is out of scope.

- **The tier assignment is a judgment, not a measurement.** Whether a given asset is moderate or severe depends on the specific supply chain, the sponsor's secured allocations, and the trajectory of capacity expansion — all of which evolve. The framework asks the analyst to make and record that judgment; it does not infer the tier from the molecule automatically.

- **Capacity expansion can relax the constraint over a program's life.** A severe constraint today may be moderate by approval if isotope production scales as projected. The static tier is a snapshot; the analyst should revisit it as the supply picture changes, exactly as they would revisit the capital-position tier as the sponsor raises money.

We do claim that supply constraint is a real, structural, and frequently mispriced driver of biotech asset value; that pricing the supply side of peak sales — not just the demand side — is the distinctive and defensible contribution; and that the audit-trail discipline makes the adjustment inspectable rather than hidden, even though the tier magnitudes are reasoned estimates rather than fitted parameters.

## See also

- [02-reflexivity-thesis.md](02-reflexivity-thesis.md) — the first path-dependency (sponsor capital → PoS), whose structure this dimension mirrors
- [06-signaling-equilibrium.md](06-signaling-equilibrium.md) — the formal grounding for treating a known structural fact as a legitimate adjustment to a population prior
- [01-pos-framework.md](01-pos-framework.md) — the full PoS chain the supply multiplier joins, right after reflexivity
