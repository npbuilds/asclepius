"""HTTP surface for Portfolio Sizing.

Two endpoints:
- POST /api/modules/portfolio_sizing      — single-asset Kelly (registry standard)
- POST /api/modules/portfolio_sizing/portfolio — multi-asset allocator (v2 surface)
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, DiligenceRecord, PoSResult, RnpvResult
from . import engine
from .schemas import (
    AssetKellyResult,
    PortfolioRecommendation,
    PortfolioRequest,
)

router = APIRouter(prefix="/api/modules/portfolio_sizing", tags=["portfolio_sizing"])


class SingleAssetSizingRequest(BaseModel):
    """Single-asset sizing input. The standard POST takes this shape."""

    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    pos: PoSResult | None = None
    rnpv: RnpvResult | None = None


@router.post("", response_model=AssetKellyResult)
def compute_single_asset_sizing(req: SingleAssetSizingRequest) -> AssetKellyResult:
    """Standard module entry — single-asset Kelly under default fund params.
    Useful for showing 'if this were your only asset, sizing would say X%'
    on a single-asset diligence flow."""
    record = DiligenceRecord(asset=req.asset, pos=req.pos, rnpv=req.rnpv)
    return engine.compute(record)


@router.post("/portfolio", response_model=PortfolioRecommendation)
def compute_portfolio_sizing(req: PortfolioRequest) -> PortfolioRecommendation:
    """Multi-asset portfolio allocator — Kelly + fractional + conviction +
    barbell across a list of computed assets. Returns the recommended
    position weights with full rationale per asset."""
    return engine.recommend_portfolio(req)
