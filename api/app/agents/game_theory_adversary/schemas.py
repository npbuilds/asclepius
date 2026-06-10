"""Output shape for the Game-Theory Adversary agent.

v1.7.7 introduces structured *flags* — a richer alternative to the older
``findings`` list. Each flag names its framework hook (``flag_type``),
attaches a falsifiable ``test`` so the user can confirm or refute the
concern, and ``cite``s the methodology file(s) the concern is grounded in.

The legacy ``findings`` field is retained for backwards compatibility with
older cached payloads and downstream consumers; new live runs are expected
to populate ``flags`` as the primary structured output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from ..memo_writer.schemas import Recommendation

# --- legacy shape (kept for back-compat with cached outputs) ---------------
Lens = Literal["signaling", "auction", "persuasion"]
Severity = Literal["minor", "moderate", "critical"]
VerdictShift = Literal["upgrade", "hold", "downgrade"]


class AdversarialFinding(BaseModel):
    lens: Lens
    claim: str = Field(description="Specific claim from the record/memo being challenged.")
    severity: Severity


# --- v1.7.7 structured flag shape ------------------------------------------
FlagType = Literal[
    "signaling_equilibrium",
    "winners_curse",
    "bayesian_persuasion",
    "cohort_base_rate_check",
    "data_quality",
    "regulatory_path",
]
FlagSeverity = Literal["high", "medium", "low"]


class AdversaryFlag(BaseModel):
    """A single structured adversarial flag.

    Each flag names the formal framework it leans on (``flag_type``),
    carries a short ``title`` for the UI card header, a 1-2 paragraph
    ``rationale`` that applies the framework to specific brief content,
    and a ``test`` describing how to falsify or confirm the concern.
    ``cite`` lists methodology filenames the flag is grounded in.
    """

    flag_type: FlagType = Field(
        description="Which formal framework the flag invokes."
    )
    severity: FlagSeverity = Field(
        description="high → meaningful enough to alter the recommendation; "
        "medium → worth investigating; low → noted but not blocking."
    )
    title: str = Field(
        description="Short label, e.g. 'Single-arm Phase 3 with well-capitalized sponsor'."
    )
    rationale: str = Field(
        description="1-2 paragraphs applying the framework to specific brief claims."
    )
    test: str = Field(
        description="How to falsify or confirm — e.g. 'compare trial N to BIO cohort median'."
    )
    cite: list[str] = Field(
        default_factory=list,
        description="Methodology filenames the flag is grounded in (e.g. ['06-signaling-equilibrium.md']).",
    )


class AdversaryContent(BaseModel):
    """The model-generated portion of the critique — the emit_critique tool's
    input_schema (v1.9.2 tool-use migration).

    tool_choice forces this tool, so Anthropic validates the model's output
    against this schema before returning and the agent does no prose parsing.
    The agent wraps this with the envelope (model_used / from_cache /
    generated_at) and an empty legacy `findings` list to build AdversaryOutput.
    All fields required — a live critique always returns flags + a verdict.
    """

    body_markdown: str = Field(
        description="Critique body markdown, rendered above the flag cards."
    )
    verdict_shift: VerdictShift = Field(
        description="upgrade / hold / downgrade vs the memo's recommendation."
    )
    recommendation_shift_to: Recommendation | None = Field(
        default=None,
        description="The proposed new recommendation if verdict_shift != 'hold'.",
    )
    flags: list[AdversaryFlag] = Field(
        description="3-5 framework-hooked flags, highest-severity first."
    )


class AdversaryOutput(BaseModel):
    body_markdown: str = Field(
        description="Critique body markdown (rendered above the structured flag cards)."
    )
    verdict_shift: VerdictShift = Field(
        description="Whether the adversarial pass upgrades, holds, or downgrades the memo's recommendation."
    )
    recommendation_shift_to: Recommendation | None = Field(
        default=None,
        description="If verdict_shift != 'hold', the proposed new recommendation enum.",
    )
    # New primary structured output as of v1.7.7
    flags: list[AdversaryFlag] = Field(
        default_factory=list,
        description="Structured framework-hooked flags (3-5 per asset on a live run).",
    )
    # Legacy field, retained for back-compat with older cached payloads
    findings: list[AdversarialFinding] = Field(default_factory=list)
    model_used: str
    from_cache: bool
    generated_at: datetime
