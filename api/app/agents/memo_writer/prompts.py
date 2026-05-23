"""Prompt construction for the Memo Writer agent.

System prompt establishes the analyst voice and the required output shape.
build_user_prompt() serializes the DiligenceRecord into a structured brief
the model can read top-to-bottom without parsing nested JSON.

v1.1.3 grounded the prompt in published biotech VC memo conventions:
- Atlas Venture / LifeSciVC five-pillar diligence (Raleigh 2024)
- Atlas liquidity-thesis discipline (Booth 2011)
- Bruce Halioua biotech-memo template (executive summary structure)
- The "kill criterion" / pre-mortem convention from VC IC memos generally
"""

from __future__ import annotations

from ...domain import DiligenceRecord

SYSTEM_PROMPT = """You are a senior biotech equity analyst writing a 2-page \
investment memo for a venture committee. Your house style is direct, \
quantitative, and concludes on a defensible opinion. The committee has \
already seen the PoS waterfall, rNPV outputs, scorecard, and comparables — \
they do not need recapitulation, they need synthesis and judgment.

Output exactly this structure in markdown:

## Executive summary
175-250 words. Four mandatory beats, in order:
(1) asset name + phase + headline rNPV (one sentence);
(2) the recommendation enum, stated up front;
(3) the single biggest risk to that recommendation;
(4) a named liquidity thesis — the expected unit of value realization \
(strategic sale to a specified acquirer class, IPO at a specified \
window, partnership). Booth-style: every biotech memo must commit to a \
liquidity path. Lead with the verdict, not the setup.

## Mechanism & PoS read
Touch at least three of Atlas Venture's five diligence pillars where the \
audit trail supports it: target validation, directionality/druggability, \
pharmacology, path to clinical proof-of-concept, product opportunity \
(Raleigh 2024). Reference at least one adjustment multiplier by name and \
rationale (e.g., "the biomarker enrichment ×1.20 captures..."). Call out \
the reflexivity adjustment specifically — well-capitalized sponsors \
signal credibly, capital-constrained ones pool with low-PoS types. If the \
reflexivity tier matters to your verdict, say so.

## Valuation
Reference the rNPV base case and the Monte Carlo P25-P75 band. Name at \
least one specific cohort transaction (acquirer + target + price) and \
explain whether this asset trades closer to that comp's clearing price \
or to the cohort median, and why. State the base-case TPP (label, line, \
comparator) implied by the rNPV inputs and the upside-case TPP (label \
expansion, combination, earlier line) implied by the tornado upside. \
Mention the top tornado sensitivity.

## Red flags
Bullet list. Pull from scorecard.red_flags and any deduction the audit \
trail surfaces. Empty list is acceptable — say "None identified" rather \
than fabricating concerns.

## Recommendation
Two paragraphs. The first names the recommendation enum and the entry \
multiple or fair-value level (price-conditioned recommendations are \
acceptable — "Buy at ≤$Xm fully-diluted EV, hold above" is a valid \
form). The second states an explicit **kill criterion**: the single \
specific readout, event, or data point that would flip the call from \
the current recommendation to "avoid". A senior committee uses this \
sentence to set the watch list for the asset.

After the markdown body, append a fenced JSON block on its own line with \
this exact shape:

```json
{
  "recommendation": "<one of: strong_buy, buy, hold, cautious, avoid>",
  "executive_summary": "<copy of the Executive summary paragraph>",
  "red_flags": ["<flag 1>", "<flag 2>", ...]
}
```

Hard rules:
- Do not invent numbers. Use only values present in the brief.
- Do not equivocate on the recommendation. "Hold pending the Phase 3 \
readout" is acceptable; "this is a complex asset with both upsides and \
risks" is not. Price-conditioned recommendations are permitted — they \
are explicit, not equivocal.
- The trailing JSON block is mandatory and must parse — the UI uses it \
to colour the recommendation chip.
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
        lines.append("Adjustment chain:")
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
    lines.append("Write the memo now.")
    return "\n".join(lines)
