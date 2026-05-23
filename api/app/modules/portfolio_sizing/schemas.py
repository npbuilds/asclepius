"""Schemas for the Portfolio Sizing module.

Two output shapes:
- AssetKellyResult: per-asset sizing decision (Kelly raw, fractional,
  conviction-adjusted, final cap-applied weight). Returned by the
  standard compute(record) entrypoint AND embedded in the multi-asset
  PortfolioRecommendation.
- PortfolioRecommendation: full portfolio output — list of per-asset
  recommendations + portfolio-level summary (total deployed, cash
  residual, gini coefficient on weights, expected-value rNPV).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...domain import AssetInput, PoSResult, RnpvResult


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class FundParameters(BaseModel):
    """Fund-level constraints applied across the portfolio."""

    model_config = ConfigDict(extra="forbid")

    total_capital_usd_m: float = Field(
        gt=0,
        description="Total capital available to deploy across positions ($M).",
    )
    kelly_fraction: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description=(
            "Multiplier on Kelly-optimal sizing (Thorp's 'fractional Kelly'). "
            "0.25 is the practitioner default for biotech VC because LOA "
            "estimates are noisy; full Kelly would over-bet on PoS error."
        ),
    )
    max_position_pct: float = Field(
        default=0.20,
        gt=0.0,
        le=1.0,
        description="Hard cap on any single position as fraction of fund (barbell ceiling).",
    )
    min_position_pct: float = Field(
        default=0.02,
        ge=0.0,
        le=0.20,
        description=(
            "Floor — positions below this are dropped (no token-size "
            "allocations that don't move the needle). Set to 0 to disable."
        ),
    )

    @model_validator(mode="after")
    def _check_ordering(self) -> "FundParameters":
        if self.min_position_pct >= self.max_position_pct:
            raise ValueError(
                f"min_position_pct ({self.min_position_pct}) must be < "
                f"max_position_pct ({self.max_position_pct})"
            )
        return self


class AssetSizingInput(BaseModel):
    """One asset to include in the portfolio. Conviction is analyst-supplied;
    the framework's PoS/rNPV outputs are pre-computed and passed in verbatim."""

    model_config = ConfigDict(extra="forbid")

    asset: AssetInput
    pos: PoSResult
    rnpv: RnpvResult
    conviction: float = Field(
        default=1.0,
        ge=0.5,
        le=1.5,
        description=(
            "Analyst conviction multiplier. 1.0 = baseline (use Kelly × "
            "fractional verbatim). 0.5 = low conviction (cut sizing in "
            "half). 1.5 = high conviction (1.5× sizing, capped by max). "
            "This is the human-judgment input the math leaves room for."
        ),
    )


class PortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assets: list[AssetSizingInput] = Field(min_length=1, max_length=50)
    fund: FundParameters


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


PositionStatus = Literal["recommended", "below_floor", "above_cap", "negative_kelly"]


class AssetKellyResult(BaseModel):
    """Per-asset sizing breakdown — every step in the Kelly → fractional →
    conviction → cap chain is visible. Auditable like the PoS waterfall."""

    model_config = ConfigDict(extra="forbid")

    asset_name: str
    pos: float = Field(ge=0.0, le=1.0, description="LOA used in Kelly math.")
    payoff_multiple: float = Field(
        description=(
            "b in Kelly's f* = (bp - q)/b. Derived from rNPV base case ÷ "
            "|downside loss| for biotech assets. Capped at 100x to avoid "
            "numerical instability on infinitesimal downsides."
        )
    )
    kelly_optimal: float = Field(
        description="Raw Kelly fraction. Can be negative (= don't bet) or >1."
    )
    kelly_fractional: float = Field(
        description="kelly_optimal × fund.kelly_fraction. Clipped to [0, 1]."
    )
    conviction_applied: float = Field(
        description="kelly_fractional × asset.conviction. Clipped to [0, 1]."
    )
    final_weight: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "After applying fund.max_position_pct cap and fund.min_position_pct "
            "floor. The portfolio's allocator uses this."
        ),
    )
    status: PositionStatus
    rationale: str


class PortfolioRecommendation(BaseModel):
    """The multi-asset allocator's output."""

    model_config = ConfigDict(extra="forbid")

    positions: list[AssetKellyResult]
    total_deployed_pct: float = Field(
        ge=0.0,
        description="Sum of final_weights across recommended positions.",
    )
    total_deployed_usd_m: float = Field(ge=0.0)
    cash_residual_pct: float = Field(
        description="1.0 - total_deployed_pct. Negative if positions sum > 1 (over-allocation)."
    )
    cash_residual_usd_m: float
    gini_coefficient: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Inequality of position weights. 0 = perfectly equal allocation; "
            "1 = all weight on one asset. A useful concentration metric for "
            "barbell-style portfolios."
        ),
    )
    expected_value_rnpv_usd_m: float = Field(
        description=(
            "Sum over positions of (final_weight × asset.pos × "
            "rnpv.base_case + (1-pos) × downside). The portfolio's "
            "probability-weighted expected payoff in $M."
        )
    )
    n_recommended: int
    n_below_floor: int
    n_above_cap: int
    n_negative_kelly: int
