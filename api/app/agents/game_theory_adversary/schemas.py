"""Output shape for the Game-Theory Adversary agent."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..memo_writer.schemas import Recommendation

Lens = Literal["signaling", "auction", "persuasion"]
Severity = Literal["minor", "moderate", "critical"]
VerdictShift = Literal["upgrade", "hold", "downgrade"]


class AdversarialFinding(BaseModel):
    lens: Lens
    claim: str = Field(description="Specific claim from the record/memo being challenged.")
    severity: Severity


class AdversaryOutput(BaseModel):
    body_markdown: str = Field(
        description="Critique body with required H2 sections (Signaling, Auction, Persuasion, Verdict)."
    )
    verdict_shift: VerdictShift = Field(
        description="Whether the adversarial pass upgrades, holds, or downgrades the memo's recommendation."
    )
    recommendation_shift_to: Recommendation | None = Field(
        default=None,
        description="If verdict_shift != 'hold', the proposed new recommendation enum.",
    )
    findings: list[AdversarialFinding] = Field(default_factory=list)
    model_used: str
    from_cache: bool
    generated_at: datetime
