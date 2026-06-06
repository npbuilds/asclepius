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
    """The /05-style opinion-paragraph close."""

    recommendation: Recommendation
    closing_paragraph: str = Field(
        description="The 'at $X, the framework brackets...' close from methodology/05. "
        "Names the entry-price discipline if price-conditioned."
    )
    kill_criterion: str = Field(
        description="The single specific readout, event, or data point that would "
        "flip the verdict to avoid."
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
