"""Schemas for the ML PoS Prior module.

v1.5.1.1 framing: rule-smoothed logistic surrogate. Labels were Bernoulli
samples from the rule-based PoS chain itself; disagreement reflected
composition-rule sensitivity (multiplicative vs additive log-odds), not
independent evidence.

v1.5.2 (this version): supervised on real HINT clinical-trial outcomes
via the offline LightGBM trainer at api/data_pipeline/train_gbt.py.
PubMedBERT pooled embeddings of the eligibility-criteria text +
36-dim structured feature vector → 804-dim combined → LGBM. The
runtime engine loads PubMedBERT in-container and embeds criteria text
per request.

Request schema gains optional criteria_text + nct_id (with NCT-ID
fallback fetching from ClinicalTrials.gov v2). Both optional — if
neither is supplied, the engine returns HTTPException(422) because
the v1.5.2 ML path requires text to embed.

The MLPosPriorResult shape is unchanged from v1.5.1.1 so the existing
frontend panel renders without modification.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DisagreementLevel = Literal["aligned", "moderate", "divergent"]


class MLPosPriorResult(BaseModel):
    """Rule-smoothed logistic surrogate PoS, with a heuristic uncertainty band.

    `uncertainty_low` / `uncertainty_high` are NOT a statistical confidence
    interval — see the field descriptions. The pre-Codex-review version of
    this schema named these `confidence_low/high` which overclaimed.
    """

    model_config = ConfigDict(extra="forbid")

    predicted_pos: float = Field(
        ge=0.0,
        le=1.0,
        description="Logistic-surrogate estimate of phase-to-approval probability.",
    )
    uncertainty_low: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Lower bound of a fixed-width heuristic band (±0.30 in logit "
            "space from the point estimate, mapped back to probability). "
            "NOT a calibrated statistical interval — the width is a "
            "conservative heuristic, not derived from x' Cov(beta) x or "
            "bootstrap. See methodology/09-ml-pos-prior.md for the v1.5.2 "
            "path to proper coverage intervals."
        ),
    )
    uncertainty_high: float = Field(
        ge=0.0,
        le=1.0,
        description="Upper bound of the heuristic uncertainty band.",
    )
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
            "divergent (>7pp). Surfaces composition-rule sensitivity "
            "(multiplicative vs. additive log-odds) — NOT independent evidence."
        )
    )
    model_kind: str
    n_features: int

    @model_validator(mode="after")
    def _check_band_ordering(self) -> "MLPosPriorResult":
        if not (self.uncertainty_low <= self.predicted_pos <= self.uncertainty_high):
            raise ValueError(
                f"uncertainty band must enclose point estimate: "
                f"{self.uncertainty_low} <= {self.predicted_pos} <= "
                f"{self.uncertainty_high}"
            )
        return self
