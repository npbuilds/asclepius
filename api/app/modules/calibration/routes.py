"""Calibration module HTTP surface.

The standard module pattern is `POST /api/modules/<id>` returning the
module's compute() output. Calibration extends it with three extra routes:
  - POST /log_prediction  (write side)
  - POST /resolve_prediction  (write side)
  - GET /report  (read side — aggregate dashboard)
  - GET /predictions  (read side — full log table)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, DiligenceRecord
from . import db, engine
from .schemas import (
    AssetCalibrationContext,
    CalibrationReport,
    LogPredictionRequest,
    PredictionLogEntry,
    ResolvePredictionRequest,
)

router = APIRouter(prefix="/api/modules/calibration", tags=["calibration"])


class CalibrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput


@router.post("", response_model=AssetCalibrationContext)
def compute_calibration(req: CalibrationRequest) -> AssetCalibrationContext:
    """Standard module entry — returns context for the current asset."""
    record = DiligenceRecord(asset=req.asset)
    return engine.compute(record)


@router.post("/log_prediction")
def log_prediction(req: LogPredictionRequest) -> dict[str, str]:
    pid = db.log_prediction(
        asset_name=req.asset_name,
        phase=req.phase,
        therapeutic_area=req.therapeutic_area,
        modality=req.modality,
        capital_position=req.capital_position,
        predicted_pos=req.predicted_pos,
        reflexivity_multiplier=req.reflexivity_multiplier,
        prediction_date=req.prediction_date,
    )
    return {"id": pid}


@router.post("/resolve_prediction")
def resolve_prediction(req: ResolvePredictionRequest) -> dict[str, bool]:
    ok = db.resolve_prediction(
        prediction_id=req.prediction_id,
        outcome=req.outcome,
        outcome_date=req.outcome_date,
        outcome_source=req.outcome_source,
    )
    if not ok:
        raise HTTPException(
            status_code=404, detail=f"prediction {req.prediction_id} not found"
        )
    return {"updated": True}


@router.get("/report", response_model=CalibrationReport)
def get_report() -> CalibrationReport:
    return db.get_calibration_report()


@router.get("/predictions", response_model=list[PredictionLogEntry])
def list_predictions() -> list[PredictionLogEntry]:
    return db.list_predictions()
