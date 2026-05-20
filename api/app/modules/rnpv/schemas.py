"""HTTP request/response schemas for rNPV."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, PoSResult, RnpvInputs, RnpvResult


class RnpvRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    pos: PoSResult
    rnpv_inputs: RnpvInputs


class RnpvResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rnpv: RnpvResult
