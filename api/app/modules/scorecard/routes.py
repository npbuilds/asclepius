"""HTTP surface for the scorecard module."""

from __future__ import annotations

from fastapi import APIRouter

from ...domain import DiligenceRecord
from .engine import compute
from .schemas import ScorecardRequest, ScorecardResponse

router = APIRouter(prefix="/api/modules/scorecard", tags=["scorecard"])


@router.post("", response_model=ScorecardResponse)
def run_scorecard(req: ScorecardRequest) -> ScorecardResponse:
    record = DiligenceRecord(asset=req.asset)
    scorecard = compute(record, scorecard_input=req.scorecard_input)
    return ScorecardResponse(scorecard=scorecard)
