"""HTTP surface for the PoS module."""

from __future__ import annotations

from fastapi import APIRouter

from ...domain import DiligenceRecord
from .engine import compute
from .schemas import PoSRequest, PoSResponse

router = APIRouter(prefix="/api/modules/pos", tags=["pos"])


@router.post("", response_model=PoSResponse)
def run_pos(req: PoSRequest) -> PoSResponse:
    record = DiligenceRecord(asset=req.asset)
    pos = compute(record)
    return PoSResponse(pos=pos)
