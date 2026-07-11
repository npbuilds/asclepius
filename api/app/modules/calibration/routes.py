"""Calibration module HTTP surface.

Per-asset calibration CONTEXT only: for a given asset's segment (TA · modality ·
capital tier), how the framework's estimates compare to observed outcomes in a
historical reference cohort. This is analysis context, not a forecasting track
record — the aggregate Brier dashboard, the public prediction log, and the
log/resolve write endpoints were removed in the R2 rescope.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, DiligenceRecord
from . import engine
from .schemas import AssetCalibrationContext

router = APIRouter(prefix="/api/modules/calibration", tags=["calibration"])


class CalibrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput


@router.post("", response_model=AssetCalibrationContext)
def compute_calibration(req: CalibrationRequest) -> AssetCalibrationContext:
    """Standard module entry — returns the per-asset segment reference context."""
    record = DiligenceRecord(asset=req.asset)
    return engine.compute(record)
