"""Schemas for the ML PoS Prior module."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DisagreementLevel = Literal["aligned", "moderate", "divergent"]


class MLPosPriorResult(BaseModel):
    """The second-opinion PoS estimate from the structured-feature classifier."""

    model_config = ConfigDict(extra="forbid")

    predicted_pos: float = Field(
        ge=0.0,
        le=1.0,
        description="ML classifier's estimated phase-to-approval probability.",
    )
    confidence_low: float = Field(ge=0.0, le=1.0)
    confidence_high: float = Field(ge=0.0, le=1.0)
    rule_based_pos: float = Field(
        ge=0.0,
        le=1.0,
        description="The deterministic chain's final_loa, passed in for comparison.",
    )
    disagreement_pp: float = Field(
        description="ML - rule_based, in percentage-point units. Positive = ML more optimistic."
    )
    disagreement_level: DisagreementLevel = Field(
        description=(
            "aligned (|disagreement| < 3pp), "
            "moderate (3-7pp), "
            "divergent (>7pp) — signal that the rule-based chain may be too coarse "
            "for this segment, or that the ML classifier is under-fitting the "
            "structural adjustments."
        )
    )
    model_kind: str = Field(
        description="Identifier for the model artifact (e.g. 'logistic_regression_v0.1.0').",
    )
    n_features: int
