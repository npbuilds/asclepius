"""Prompt construction for the Memo Writer agent (v1.7.7).

The system prompt asks Claude to return a structured JSON memo whose prose
mirrors the worked-example pattern in methodology/05-worked-example-adagrasib.md.
build_user_prompt() serializes the DiligenceRecord into a flat brief.

The model returns ONE fenced JSON object with the full structured memo. The
agent parses it directly into the MemoOutput schema. No more "markdown body
with trailing JSON" — the body is reconstructed from the structured fields.
"""

from __future__ import annotations

from ...domain import DiligenceRecord

SYSTEM_PROMPT = """You are a senior biotech equity analyst writing a 2-3 page \
investment memo for a venture committee that has already seen the underlying \
PoS waterfall, rNPV outputs, scorecard, and comparables. They need synthesis \
and judgment, not recapitulation.

Your prose pattern is the Asclepius worked example (methodology/05-worked-example\
-adagrasib.md): direct, quantitative, conclusive. Read it as your template — \
every section earns its place, the verdict appears at the top, and the close \
is a single opinion paragraph in the form "at $X, the framework brackets ...".

Framework vocabulary you MUST use by name in the prose where the audit trail \
warrants it:
  - "biomarker-enrichment-boost" (the ×1.20 multiplier from Wong 2019 §4.3)
  - "target-validated" (the ×1.15 modifier when a same-target asset has cleared FDA)
  - "Breakthrough Therapy Designation" / "BTD" (×1.10)
  - "reflexivity-multiplier" or "reflexivity tier" (Spence-style signaling \
    via capital position: well_capitalized ×1.08, adequate ×1.00, constrained \
    ×0.92, distressed ×0.85)
  - "supply-constraint tier" / "supply ceiling" (the second path-dependency, \
    parallel to reflexivity: a moderate/severe manufacturing or raw-material/\
    isotope constraint has TWO effects — a PoS multiplier AND a peak-sales \
    ceiling in rNPV. Name it whenever the brief carries a supply tier above \
    unconstrained; the rNPV revenue ceiling is the distinctive part a generic \
    DCF/rNPV model does NOT capture.)
  - "Monte Carlo P25-P75 band"
  - "tornado driver" / "top tornado sensitivity"
  - "winner's-curse-adjusted private value" if comparables include a contested \
    process

Return ONLY a single fenced ```json``` block matching this exact shape \
(comments are illustrative, do not include them in your output):

```json
{
  "tldr": {
    "recommendation": "<strong_buy|buy|hold|cautious|avoid>",
    "loa_pct": <number, e.g. 16.1>,
    "rnpv_base_usd_m": <number>,
    "rnpv_range_low_usd_m": <number or null>,
    "rnpv_range_high_usd_m": <number or null>,
    "thesis_one_liner": "<one sentence, <200 chars>"
  },
  "asset_overview": {
    "paragraph": "<1-2 paragraphs: sponsor, phase, indication, mechanism, any direct-precedent>"
  },
  "pos_analysis": {
    "waterfall_narrative": "<2-3 paragraphs walking the PoS chain in the framework's named multipliers>",
    "reflexivity_note": "<1 paragraph: Spence-style read of the capital tier and whether it changes the verdict>",
    "supply_note": "<1 paragraph: the supply-constraint tier, its dual effect (PoS multiplier + rNPV peak-sales ceiling), and whether it changes the verdict. One sentence if unconstrained.>"
  },
  "valuation": {
    "valuation_narrative": "<2 paragraphs: rNPV base, P25-P75, downside, top tornado driver, comp-clearing vs cohort-median>"
  },
  "comparables": {
    "cohort_paragraph": "<1 paragraph: cohort name, median EV/peak-sales, implied value, closest structural analog>"
  },
  "operational": {
    "pillars_paragraph": "<1 paragraph: 3+ scorecard pillars + flagged reds>"
  },
  "risks": [
    {"label": "<short>", "description": "<one sentence>", "severity": "low|medium|high"},
    ... (top 3 risks)
  ],
  "recommendation_close": {
    "recommendation": "<same enum as tldr.recommendation>",
    "conviction": "<high|medium|low — explicit, orthogonal to the buy/hold direction>",
    "path_dependency_verdict": "<1-2 sentences: how the reflexivity tier AND the supply tier net moved the call; say so if both neutral>",
    "closing_paragraph": "<the methodology/05-style 'at $X, the framework brackets...' close>",
    "kill_criterion": "<a FALSIFIABLE kill criterion: named event + threshold + direction>"
  },
  "executive_summary": "<copy the tldr.thesis_one_liner + 2-3 supporting sentences, 100-200 words total>",
  "red_flags": ["<flag1>", "<flag2>", ...]
}
```

Hard rules:
- Do NOT invent numbers. Use only values present in the brief.
- Do NOT equivocate on the recommendation. Price-conditioned calls ("buy at \
≤$Xm fully-diluted EV, hold above") are acceptable — they are explicit, not \
hedged. "Hold pending the Phase 3 readout" is acceptable. "Complex asset with \
upsides and risks" is not.
- The JSON object is mandatory and must parse — the UI uses every field.
- If a section's brief data is absent (e.g. no comparables in the record), \
write one short sentence noting that the section is data-limited, rather \
than fabricating content.
- Liquidity-thesis discipline (Booth 2011): name the expected unit of value \
realization in tldr.thesis_one_liner or executive_summary — strategic sale \
to a specified acquirer class, IPO at a specified window, or partnership.
- Defensibility (the close must EARN the call):
  • recommendation_close.conviction is mandatory and must be justified by the \
    body — "high" only when the rNPV bracket and the comp read agree and no \
    single tornado driver flips the sign; "low" when the verdict hinges on one \
    contested input.
  • recommendation_close.path_dependency_verdict must state, in one or two \
    sentences, how the reflexivity tier AND the supply tier net moved the \
    verdict (cite the multipliers, e.g. "distressed ×0.85 + severe supply \
    ceiling −35%"). If both are neutral (adequate capital, unconstrained \
    supply), say so explicitly — do not invent an effect.
  • kill_criterion must be FALSIFIABLE: a named, observable event with a \
    threshold and a direction ("Phase 3 ORR < 40% at the H2'26 readout"), not \
    a vague sentiment ("if efficacy disappoints").
"""


def build_user_prompt(record: DiligenceRecord) -> str:
    """Serialize a computed DiligenceRecord into a flat brief."""
    lines: list[str] = []
    a = record.asset
    lines.append("=== ASSET ===")
    lines.append(f"Name: {a.asset_name}")
    if a.sponsor:
        lines.append(f"Sponsor: {a.sponsor}")
    lines.append(f"Phase: {a.phase.value}")
    if a.indication:
        lines.append(f"Indication: {a.indication}")
    if a.target:
        lines.append(f"Target: {a.target}")
    lines.append(f"Modality: {a.modality.value}")
    lines.append(f"Therapeutic area: {a.therapeutic_area.value}")
    lines.append(f"Capital position: {a.capital_position.value}")
    lines.append(f"Supply constraint: {a.supply_constraint.value}")
    if a.regulatory_designations:
        lines.append(
            "Regulatory designations: "
            + ", ".join(d.value for d in a.regulatory_designations)
        )
    if a.mechanism:
        lines.append(f"Mechanism: {a.mechanism}")

    if record.pos:
        p = record.pos
        lines.append("")
        lines.append("=== POS ===")
        lines.append(f"Base rate: {p.base_rate:.1%}")
        lines.append(f"Final LOA: {p.final_loa:.1%}")
        lines.append(f"Confidence: {p.confidence_low:.1%} – {p.confidence_high:.1%}")
        lines.append("Adjustment chain (use these multiplier names verbatim in prose):")
        for adj in p.adjustments:
            lines.append(
                f"  • {adj.name}: ×{adj.multiplier:.3f} — {adj.rationale} "
                f"[{adj.source}]"
            )

    if record.rnpv:
        r = record.rnpv
        lines.append("")
        lines.append("=== RNPV ($M) ===")
        lines.append(f"Base case: ${r.base_case_usd_m:.0f}M")
        # Supply-constraint peak-sales ceiling — the distinctive second-path
        # effect. Only surfaced when it actually bites (ceiling < 1.0), so an
        # unconstrained asset's brief stays clean.
        if (
            r.supply_peak_ceiling_pct is not None
            and r.supply_peak_ceiling_pct < 1.0
            and r.supply_adjusted_peak_usd_m is not None
        ):
            nominal = (
                f" on nominal ${record.rnpv_inputs.peak_sales_usd_m:.0f}M"
                if record.rnpv_inputs is not None
                else ""
            )
            lines.append(
                f"Supply ceiling: ×{r.supply_peak_ceiling_pct:.2f}{nominal} "
                f"→ effective peak ${r.supply_adjusted_peak_usd_m:.0f}M "
                f"(supply-constraint tier caps achievable revenue)"
            )
        if r.monte_carlo_p25_usd_m is not None:
            lines.append(
                f"Monte Carlo P25 / P50 / P75: "
                f"${r.monte_carlo_p25_usd_m:.0f}M / "
                f"${r.monte_carlo_p50_usd_m:.0f}M / "
                f"${r.monte_carlo_p75_usd_m:.0f}M"
            )
        if r.downside_failed_p3_usd_m is not None:
            lines.append(f"Downside (P3 fail): ${r.downside_failed_p3_usd_m:.0f}M")
        if r.tornado:
            lines.append("Tornado sensitivity (top 3):")
            sorted_tornado = sorted(
                r.tornado, key=lambda b: abs(b.swing_usd_m), reverse=True
            )[:3]
            for b in sorted_tornado:
                lines.append(
                    f"  • {b.variable}: low ${b.low_value_usd_m:.0f}M, "
                    f"high ${b.high_value_usd_m:.0f}M (swing ${b.swing_usd_m:.0f}M)"
                )

    if record.scorecard:
        s = record.scorecard
        lines.append("")
        lines.append("=== SCORECARD ===")
        lines.append(f"Aggregate: {s.aggregate_score:.2f} / 10")
        lines.append(f"Recommendation (heuristic): {s.recommendation}")
        if s.red_flags:
            lines.append("Red flags: " + "; ".join(s.red_flags))
        if s.green_flags:
            lines.append("Green flags: " + "; ".join(s.green_flags))
        lines.append("Pillar scores (weighted):")
        for pillar in s.pillars:
            lines.append(
                f"  • {pillar.name}: {pillar.score:.1f}/10 (weight {pillar.weight:.2f})"
            )

    if record.comparables:
        c = record.comparables
        lines.append("")
        lines.append("=== COMPARABLES ===")
        if c.median_ev_to_peak_sales is not None:
            lines.append(
                f"Median EV/peak-sales (cohort): {c.median_ev_to_peak_sales:.2f}x"
            )
        if c.implied_value_usd_m is not None:
            lines.append(f"Implied value: ${c.implied_value_usd_m:.0f}M")
        for comp in c.cohort:
            line = f"  • {comp.asset_name}"
            if comp.acquirer:
                line += f" / {comp.acquirer}"
            if comp.deal_value_usd_m is not None:
                line += f" — ${comp.deal_value_usd_m:.0f}M"
            if comp.ev_to_peak_sales is not None:
                line += f" ({comp.ev_to_peak_sales:.2f}x peak)"
            lines.append(line)

    lines.append("")
    lines.append("Write the structured memo JSON now.")
    return "\n".join(lines)
