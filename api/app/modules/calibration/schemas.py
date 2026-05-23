"""Schemas for the Calibration Dashboard module.

The module's compute() runs when the diligence page loads — returns
segment-level Brier stats for the current asset's TA/modality/capital tier.
Separate endpoints handle the write-side (log_prediction, resolve_prediction)
and the aggregate read-side (report).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PredictionLogEntry(BaseModel):
    """One row of the predictions table. `outcome` is None until resolved."""

    model_config = ConfigDict(extra="forbid")

    id: str
    asset_name: str
    phase: str
    therapeutic_area: str
    modality: str
    capital_position: str
    predicted_pos: float = Field(ge=0.0, le=1.0)
    reflexivity_multiplier: float = Field(gt=0.0)
    prediction_date: date
    outcome: Literal[0, 1] | None = None
    outcome_date: date | None = None
    outcome_source: str | None = None


class LogPredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_name: str
    phase: str
    therapeutic_area: str
    modality: str
    capital_position: str
    predicted_pos: float = Field(ge=0.0, le=1.0)
    reflexivity_multiplier: float = Field(gt=0.0)
    prediction_date: date | None = None  # defaults to today


class ResolvePredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: str
    outcome: Literal[0, 1]
    outcome_date: date | None = None  # defaults to today
    outcome_source: str | None = None


class SegmentStats(BaseModel):
    """Aggregated Brier-score stats for one segment (TA / modality / capital).
    Brier score = mean((predicted - actual)^2). Lower is better. 0.25 is the
    benchmark for an uninformative 50/50 classifier; 0.0 is perfect."""

    segment_kind: Literal["therapeutic_area", "modality", "capital_position", "overall"]
    segment_value: str
    n_resolved: int
    n_unresolved: int
    brier_score: float | None = None  # None if n_resolved == 0
    mean_predicted: float | None = None
    mean_observed: float | None = None  # = fraction of successes among resolved
    calibration_gap: float | None = None  # mean_predicted - mean_observed


class CalibrationReport(BaseModel):
    """Aggregated dashboard. Returned by GET /report."""

    n_total_predictions: int
    n_resolved: int
    overall: SegmentStats
    by_therapeutic_area: list[SegmentStats]
    by_modality: list[SegmentStats]
    by_capital_position: list[SegmentStats]
    last_updated: datetime
    sample_size_disclaimer: str = Field(
        default=(
            "Brier scores below n=20 are directional only — variance is too high "
            "to attribute calibration quality to the methodology vs. noise. "
            "v1.6+ accumulates the sample through quarterly prediction logging."
        )
    )


class AssetCalibrationContext(BaseModel):
    """What the diligence page renders next to the current asset.
    Returned by compute() — pulls the stats for the asset's segment."""

    asset_segment_label: str  # e.g. "oncology / small_molecule / adequate"
    segment_n_resolved: int
    segment_brier: float | None = None
    segment_mean_predicted: float | None = None
    segment_mean_observed: float | None = None
    overall_n_resolved: int
    overall_brier: float | None = None
    sample_size_disclaimer: str
