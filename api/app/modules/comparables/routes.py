"""HTTP surface for the comparables module."""

from __future__ import annotations

from fastapi import APIRouter

from ...domain import DiligenceRecord
from .engine import compute
from .schemas import ComparablesRequest, ComparablesResponse

router = APIRouter(prefix="/api/modules/comparables", tags=["comparables"])


@router.post("", response_model=ComparablesResponse)
def run_comparables(req: ComparablesRequest) -> ComparablesResponse:
    record = DiligenceRecord(asset=req.asset, rnpv_inputs=req.rnpv_inputs)
    comparables = compute(record, cohort_ids=req.cohort_ids)
    return ComparablesResponse(comparables=comparables)
