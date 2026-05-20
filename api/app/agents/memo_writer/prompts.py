"""Prompt construction for the Memo Writer agent.

System prompt establishes the analyst voice and the required output shape.
build_user_prompt() serializes the DiligenceRecord into a structured brief
the model can read top-to-bottom without parsing nested JSON.
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
100-150 words. State the asset, phase, headline rNPV, and the recommendation \
in one tight paragraph. Lead with the verdict, not the setup.

## PoS read
Discuss what the audit trail tells you. Reference at least one adjustment \
multiplier by name and rationale (e.g., "the biomarker enrichment ×1.20 \
captures..."). Call out the reflexivity adjustment specifically — well- \
capitalized sponsors signal credibly, capital-constrained ones pool with \
low-PoS types. If the reflexivity tier matters to your verdict, say so.

## Valuation
Reference the rNPV base case and the Monte Carlo P25-P75 band. Triangulate \
against the comparables cohort's implied value. Discuss whether the asset \
trades at a discount or premium to the cohort and whether that gap is \
defensible. Mention the top tornado sensitivity.

## Red flags
Bullet list. Pull from scorecard.red_flags and any deduction the audit \
trail surfaces. Empty list is acceptable — say "None identified" rather \
than fabricating concerns.

## Recommendation
One paragraph. State the recommendation enum, explain the entry multiple \
or fair-value level, and name the *specific* condition under which you \
would revise. This is what the committee acts on.

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
- Do not hedge the recommendation. "Hold pending the Phase 3 readout" is \
  acceptable; "this is a complex asset with both upsides and risks" is not.
- The trailing JSON block is mandatory and must parse — the UI uses it to \
  colour the recommendation chip.
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
