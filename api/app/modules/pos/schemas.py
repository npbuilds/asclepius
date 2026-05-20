"""Request/response schemas for the PoS HTTP surface.

The module's core compute() takes a DiligenceRecord and writes pos: PoSResult onto
it. These schemas are for the HTTP request/response wrapping that.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, PoSResult


class PoSRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput


class PoSResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pos: PoSResult
