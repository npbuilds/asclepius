"""HTTP surface for the rNPV module."""

from __future__ import annotations

from fastapi import APIRouter

from ...domain import DiligenceRecord
from .engine import compute
from .schemas import RnpvRequest, RnpvResponse

router = APIRouter(prefix="/api/modules/rnpv", tags=["rnpv"])


@router.post("", response_model=RnpvResponse)
def run_rnpv(req: RnpvRequest) -> RnpvResponse:
    record = DiligenceRecord(
        asset=req.asset, pos=req.pos, rnpv_inputs=req.rnpv_inputs
    )
    rnpv = compute(record)
    return RnpvResponse(rnpv=rnpv)
