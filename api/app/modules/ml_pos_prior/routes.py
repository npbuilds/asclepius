"""HTTP surface for the ML PoS Prior module.

v1.5.2: the request schema now accepts an optional `criteria_text`
(verbatim eligibility-criteria text for the BERT embedding step) and
an optional `nct_id` (ClinicalTrials.gov ID; the engine fetches the
criteria text server-side when this is supplied and no explicit text
is given). At least one of the two must be present for the live ML
path; cached responses are served without text input.

Phase.APPROVED is rejected at the route level because the classifier
was trained on pre-approval transitions — accepting APPROVED would
silently extrapolate outside the training distribution.

The /model_info route uses the public `get_model_metrics()` accessor
on the engine, so failure modes propagate as HTTPException(503)
rather than raw 500s.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from ...domain import AssetInput, DiligenceRecord, Phase, PoSResult
from . import engine
from .schemas import MLPosPriorResult

router = APIRouter(prefix="/api/modules/ml_pos_prior", tags=["ml_pos_prior"])


class MLPosPriorRequest(BaseModel):
    """v1.5.2 request shape — adds optional criteria_text + nct_id.

    Backwards-compatible: callers that only send `asset` (+ optional `pos`)
    still work but get HTTPException(422) on the live path because the
    v1.5.2 ML model requires eligibility-criteria text. The cached path
    (adagrasib) returns without needing either field.
    """

    model_config = ConfigDict(extra="forbid")

    asset: AssetInput
    pos: PoSResult | None = None

    criteria_text: str | None = Field(
        default=None,
        description=(
            "Verbatim eligibility-criteria text for the BERT embedding "
            "step. Optional — if absent but nct_id is supplied, the "
            "engine fetches the criteria from ClinicalTrials.gov v2."
        ),
    )
    nct_id: str | None = Field(
        default=None,
        description=(
            "ClinicalTrials.gov NCT ID. Optional — used to fetch "
            "criteria text server-side when criteria_text isn't supplied."
        ),
    )


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
    try:
        return engine.compute(
            record,
            criteria_text=req.criteria_text,
            nct_id=req.nct_id,
        )
    except ValueError as exc:
        # Engine raises ValueError for in-process callers that bypass the
        # Phase.APPROVED route check (F6 from Codex review of v1.6).
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/model_info")
def model_info() -> dict:
    """Exposes the trained model's metadata via the engine's public accessor.
    Errors (missing/corrupt artifact) propagate as HTTPException(503), not 500."""
    return engine.get_model_metrics()
