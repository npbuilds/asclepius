"""Scorecard request/response — user supplies pillar scores + flags."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from ...domain import AssetInput, ScorecardResult


# A 1.0-10.0 numeric score per pillar with optional rationale.
Score = Annotated[float, Field(ge=1.0, le=10.0)]


class PillarInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: Score
    rationale: str | None = None


class ScorecardInput(BaseModel):
    """User-supplied scores for each pillar. Order is fixed in the engine."""

    model_config = ConfigDict(extra="forbid")

    clinical: PillarInput
    regulatory: PillarInput
    competitive: PillarInput
    manufacturing: PillarInput
    ip: PillarInput
    financial: PillarInput
    team: PillarInput
    computational: PillarInput
    red_flags: list[str] = Field(default_factory=list)
    green_flags: list[str] = Field(default_factory=list)


class ScorecardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    scorecard_input: ScorecardInput


class ScorecardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scorecard: ScorecardResult
