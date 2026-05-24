"""Schemas for the ML PoS Prior module.

v1.5.2 (current): supervised on real HINT clinical-trial outcomes via the
offline LightGBM trainer at api/data_pipeline/train_gbt.py. PubMedBERT
pooled embeddings of the eligibility-criteria text + 36-dim structured
feature vector → 804-dim combined → LGBM. The runtime engine loads
PubMedBERT in-container and embeds criteria text per request.

Request schema gains optional criteria_text + nct_id (with NCT-ID
fallback fetching from ClinicalTrials.gov v2). Both optional — if
neither is supplied AND the feature-fingerprint cache misses, the
engine returns HTTPException(422) because the v1.5.2 ML path requires
text to embed.

The MLPosPriorResult shape is unchanged from v1.5.1.1 (only the
descriptions were rewritten for honesty) so the existing frontend
panel renders without modification.

v1.5.1.1 (deprecated): rule-smoothed logistic surrogate trained on
Bernoulli samples of the rule-based chain. Retained in version
history for context; not part of the current request/response surface.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DisagreementLevel = Literal["aligned", "moderate", "divergent"]


class MLPosPriorResult(BaseModel):
    """v1.5.3 ML PoS Prior result — supervised LightGBM over PubMedBERT
    embeddings of the eligibility-criteria text concatenated with the 36-dim
    structured feature vector (804-dim total), trained on the HINT
    clinical-trial outcome corpus (Fu et al. 2022).

    `uncertainty_low` / `uncertainty_high` are now (v1.5.3) the 90%
    bootstrap-percentile interval across an ensemble of 10 LightGBM
    classifiers trained on independent bootstrap resamples of the train
    split. This is an *epistemic* model-resampling uncertainty (how much
    the LGBM disagrees with itself under different training-set draws);
    a complementary Mondrian split-conformal *coverage* interval is
    recorded in the artifact's `conformal` block and surfaced in
    methodology/09-ml-pos-prior.md (90% test-set marginal coverage = 91.5%).
    """

    model_config = ConfigDict(extra="forbid")

    predicted_pos: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Supervised LightGBM prediction of phase-to-approval "
            "probability. Inputs: PubMedBERT-pooled embedding of the trial's "
            "eligibility-criteria text + 36-dim structured feature vector. "
            "Trained on HINT clinical-trial outcomes (Fu 2022). The point "
            "estimate is the single main model's prediction (not the "
            "ensemble mean) so the disagreement-pp delta stays comparable "
            "across versions."
        ),
    )
    uncertainty_low: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Lower bound of the 90% bootstrap-percentile interval (α=0.10) "
            "across an ensemble of 10 LightGBM classifiers trained on "
            "independent bootstrap resamples of the HINT train split. "
            "Reflects epistemic model-resampling uncertainty: where the "
            "10 LGBMs agree, the band is tight; where they disagree, the "
            "band widens. Distinct from frequentist coverage — see "
            "methodology/09-ml-pos-prior.md for the conformal coverage "
            "result on the same artifact (91.5% marginal on test)."
        ),
    )
    uncertainty_high: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Upper bound of the 90% bootstrap-percentile interval — see "
            "uncertainty_low for the construction."
        ),
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
            "divergent (>7pp). For v1.5.2 this surfaces *independent* "
            "evidence: the rule chain encodes BIO base rates + modality + "
            "reflexivity, while the ML head encodes protocol-text + "
            "structured-feature signal supervised on real HINT outcomes."
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
