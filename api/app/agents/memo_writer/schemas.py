"""Output shape for the Memo Writer agent (v1.7.7).

The Memo Writer returns a structured, multi-section investment memo. The
frontend renders each section in its own visual block — not just a single
markdown blob — so the schema separates concerns. We keep `body_markdown`
for back-compat with any older renderer code, but each named section is
also surfaced as its own field.

Sections mirror the prose pattern in methodology/05-worked-example-adagrasib.md:
TL;DR → asset overview → PoS waterfall narration → valuation →
comparables interpretation → operational diligence → risks → recommendation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Recommendation = Literal["strong_buy", "buy", "hold", "cautious", "avoid"]


class TLDR(BaseModel):
    """The committee's one-screen verdict."""

    recommendation: Recommendation
    loa_pct: float = Field(description="Final LOA as a percent, e.g. 16.1 for 16.1%.")
    rnpv_base_usd_m: float = Field(description="Base-case rNPV in USD millions.")
    rnpv_range_low_usd_m: float | None = Field(
        default=None, description="Monte Carlo P25 (USD M)."
    )
    rnpv_range_high_usd_m: float | None = Field(
        default=None, description="Monte Carlo P75 (USD M)."
    )
    thesis_one_liner: str = Field(
        description="One-sentence thesis. <=200 characters."
    )


class AssetOverview(BaseModel):
    """Two-paragraph framing of the asset (sponsor, phase, mechanism, indication)."""

    paragraph: str = Field(
        description="One or two compact paragraphs describing the asset, sponsor, "
        "phase, indication, mechanism. Names sotorasib-style precedents where the "
        "audit trail supports it."
    )


class PoSAnalysis(BaseModel):
    """Narrate the PoS waterfall in the framework's vocabulary.

    The prose must reference specific multiplier names from the chain
    (e.g. 'biomarker-enrichment-boost', 'target-validated', 'reflexivity').

    Carries the tool's TWO path-dependency reads side by side:
    `reflexivity_note` (capital -> PoS) and `supply_note` (supply -> PoS AND
    a peak-sales ceiling in rNPV). Pairing them is deliberate — they are the
    framework's distinctive structural overlays.
    """

    waterfall_narrative: str = Field(
        description="2-3 paragraphs walking from base rate -> modality -> mechanism/"
        "biomarker -> target validation -> reflexivity tier. Cite multiplier names "
        "verbatim from the adjustment chain."
    )
    reflexivity_note: str = Field(
        description="One paragraph on the Spence-style reflexivity reading: what "
        "the capital tier signals and whether it changes the verdict."
    )
    supply_note: str = Field(
        description="One paragraph on the supply-constraint reading: the supply tier "
        "(unconstrained/moderate/severe), its DUAL effect — a PoS multiplier AND a "
        "peak-sales ceiling in rNPV — and whether it changes the verdict. If the asset "
        "is unconstrained, say so in one sentence (it is not a binding factor) rather "
        "than padding."
    )


class ValuationAnalysis(BaseModel):
    """rNPV base, MC band, downside, top tornado sensitivity."""

    valuation_narrative: str = Field(
        description="2 paragraphs. State base rNPV, P25-P75 band, downside. Name "
        "the top tornado driver. Explain whether the asset trades closer to the "
        "comp clearing price or to the cohort median, and why."
    )


class ComparablesInterpretation(BaseModel):
    """Cohort label + interpretation of where this asset sits within it."""

    cohort_paragraph: str = Field(
        description="One paragraph: name the cohort, the median EV/peak-sales "
        "multiple, the implied value, and which specific cohort transaction "
        "(acquirer + target + price) is the closest structural analog."
    )


class OperationalDiligence(BaseModel):
    """Atlas-style five-pillar scorecard read."""

    pillars_paragraph: str = Field(
        description="One paragraph touching at least three pillars from the "
        "scorecard (clinical, regulatory, competitive, financial, team) "
        "with the weighted score and any flagged red items."
    )


class RiskItem(BaseModel):
    label: str = Field(description="Short risk label, e.g. 'Peak-sales concentration'.")
    description: str = Field(description="One sentence of detail.")
    severity: Literal["low", "medium", "high"] = "medium"


class RecommendationClose(BaseModel):
    """The /05-style opinion-paragraph close.

    This is where the call is made *defensible*: an explicit conviction level,
    a one-line statement of how the two path-dependencies (reflexivity + supply)
    net moved the verdict, the priced opinion paragraph, and a falsifiable kill
    criterion.
    """

    recommendation: Recommendation
    conviction: Literal["high", "medium", "low"] = Field(
        description="Explicit conviction in the call — orthogonal to the buy/hold/avoid "
        "direction. 'high' only when the rNPV bracket and the comp-clearing read agree "
        "and no single tornado driver can flip the sign; 'low' when the verdict hinges "
        "on one contested input."
    )
    path_dependency_verdict: str = Field(
        description="One or two sentences naming how the reflexivity tier AND the supply "
        "tier net moved the call — e.g. 'the distressed reflexivity tier (×0.85) and "
        "severe supply ceiling (peak −35%) together pull this from buy to cautious.' "
        "If both are neutral, say so explicitly."
    )
    closing_paragraph: str = Field(
        description="The 'at $X, the framework brackets...' close from methodology/05. "
        "Names the entry-price discipline if price-conditioned."
    )
    kill_criterion: str = Field(
        description="A FALSIFIABLE kill criterion: a NAMED, observable event with a "
        "THRESHOLD and DIRECTION that would flip the verdict to avoid — e.g. 'Phase 3 "
        "ORR < 40% at the H2'26 readout' or 'a competitor's confirmatory survival "
        "miss reopens the endpoint debate'. NOT a vague 'if efficacy disappoints'."
    )


class MemoContent(BaseModel):
    """The model-generated portion of the memo — everything the LLM fills in.

    v1.9.2: used as the tool-use `input_schema` for the Memo Writer's live
    call. With `tool_choice` forcing this tool, the model returns a
    schema-validated object (Anthropic validates against this schema before
    returning), so the agent does NO prose parsing — `block.input` is already
    a dict matching these fields. Every section is REQUIRED (no `| None`):
    the whole point of the migration is that a memo can't come back empty.

    The agent assembles the full `MemoOutput` from this + the envelope fields
    (`body_markdown`, `model_used`, `from_cache`, `generated_at`) in code.
    """

    tldr: TLDR
    asset_overview: AssetOverview
    pos_analysis: PoSAnalysis
    valuation: ValuationAnalysis
    comparables: ComparablesInterpretation
    operational: OperationalDiligence
    risks: list[RiskItem] = Field(
        description="2-5 ranked risks, highest-severity first."
    )
    recommendation_close: RecommendationClose
    executive_summary: str = Field(description="100-200 word stand-alone summary.")
    recommendation: Recommendation
    red_flags: list[str] = Field(
        description="Flat list of critical concerns (mirrors risks[].label).",
    )


class MemoOutput(BaseModel):
    # --- new structured fields ---
    tldr: TLDR | None = Field(
        default=None, description="One-screen verdict block."
    )
    asset_overview: AssetOverview | None = None
    pos_analysis: PoSAnalysis | None = None
    valuation: ValuationAnalysis | None = None
    comparables: ComparablesInterpretation | None = None
    operational: OperationalDiligence | None = None
    risks: list[RiskItem] = Field(default_factory=list)
    recommendation_close: RecommendationClose | None = None

    # --- back-compat / fallback fields ---
    body_markdown: str = Field(
        description="Full memo as a single markdown string. Kept for renderers that "
        "haven't migrated to the structured sections yet."
    )
    executive_summary: str = Field(
        description="100-200 word stand-alone summary."
    )
    recommendation: Recommendation
    red_flags: list[str] = Field(
        default_factory=list,
        description="Flat list of critical concerns (mirrors risks[].label for back-compat).",
    )

    # --- envelope ---
    model_used: str = Field(description="Anthropic model id or 'cache' if served from disk.")
    from_cache: bool
    generated_at: datetime
