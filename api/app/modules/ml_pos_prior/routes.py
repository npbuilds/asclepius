"""HTTP surface for the ML PoS Prior module.

The standard module POST takes the asset + (optional) pos result and runs
the trained classifier. If `pos` is not supplied, the route synthesizes a
zero-value rule_based for the comparison field (frontend handles).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, DiligenceRecord, PoSResult
from . import engine
from .schemas import MLPosPriorResult

router = APIRouter(prefix="/api/modules/ml_pos_prior", tags=["ml_pos_prior"])


class MLPosPriorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    pos: PoSResult | None = None


@router.post("", response_model=MLPosPriorResult)
def compute_ml_pos_prior(req: MLPosPriorRequest) -> MLPosPriorResult:
    record = DiligenceRecord(asset=req.asset, pos=req.pos)
    return engine.compute(record)


@router.get("/model_info")
def model_info() -> dict:
    """Exposes the trained model's metadata — useful for the methodology page
    and recruiter-facing transparency. No model weights are exposed."""
    _, metrics = engine._load_model()
    return metrics
