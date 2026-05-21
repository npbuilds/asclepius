"""Output shape for the Auto-Diligence agent.

Extracted populates fields that mirror AssetInput. Citations are kept
flat (list of (field_path, url, span)) so the frontend can render them
as a punch-list next to each form field without nested traversal.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Confidence = Literal["high", "medium", "low", "missing"]


class Citation(BaseModel):
    field: str = Field(description="Dotted path into `extracted`, e.g. 'phase' or 'sponsor'.")
    url: str
    title: str | None = None
    span: str = Field(description="Verbatim cited text from the source (≤300 chars).")


class ExtractedAsset(BaseModel):
    """A subset of AssetInput plus a few Bioptic-style additions the prompt
    targets. Validated permissively (extras allowed) so the model can return
    partial extractions without rejection."""

    model_config = ConfigDict(extra="allow")

    asset_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    sponsor: str | None = None
    phase: str | None = None
    therapeutic_area: str | None = None
    modality: str | None = None
    indication: str | None = None
    target: str | None = None
    mechanism: str | None = None
    route_of_administration: str | None = None
    regulatory_designations: list[str] = Field(default_factory=list)
    num_competitors: int | None = None
    named_competitors: list[str] = Field(default_factory=list)
    target_validated: bool | None = None
    biomarker_enrichment: bool | None = None
    capital_position: str | None = None


class AutoDiligenceOutput(BaseModel):
    extracted: ExtractedAsset
    citations: list[Citation] = Field(default_factory=list)
    field_confidence: dict[str, Confidence] = Field(default_factory=dict)
    web_searches_used: int = 0
    model_used: str
    from_cache: bool
    generated_at: datetime
