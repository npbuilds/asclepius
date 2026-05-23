"""HTTP surface for the ML PoS Prior module.

The standard module POST takes the asset + (optional) pos result and runs
the trained classifier. Phase.APPROVED is rejected at the route level
because the classifier was trained on pre-approval transitions — accepting
APPROVED would silently extrapolate outside the training distribution.

The /model_info route uses the public `get_model_metrics()` accessor on
the engine, so failure modes propagate as HTTPException(503) rather than
raw 500s.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, DiligenceRecord, Phase, PoSResult
from . import engine
from .schemas import MLPosPriorResult

router = APIRouter(prefix="/api/modules/ml_pos_prior", tags=["ml_pos_prior"])


class MLPosPriorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    pos: PoSResult | None = None


@router.post("", response_model=MLPosPriorResult)
def compute_ml_pos_prior(req: MLPosPriorRequest) -> MLPosPriorResult:
    if req.asset.phase == Phase.APPROVED:
        raise HTTPException(
            status_code=422,
            detail=(
                "ML PoS Prior is fit on pre-approval transitions only; "
                "Phase.APPROVED assets are out of the training distribution. "
                "For already-approved assets, the rule-based chain returns "
                "the deterministic LOA directly."
            ),
        )
    record = DiligenceRecord(asset=req.asset, pos=req.pos)
    return engine.compute(record)


@router.get("/model_info")
def model_info() -> dict:
    """Exposes the trained model's metadata via the engine's public accessor.
    Errors (missing/corrupt artifact) propagate as HTTPException(503), not 500."""
    return engine.get_model_metrics()
