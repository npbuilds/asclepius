"""Comparables request/response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ...domain import AssetInput, ComparablesResult, RnpvInputs


class ComparablesRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    rnpv_inputs: RnpvInputs | None = None
    cohort_ids: list[str] | None = None  # optional explicit cohort


class ComparablesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    comparables: ComparablesResult
