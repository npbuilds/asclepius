"""Calibration module engine.

compute(record) returns the segment-specific calibration context for the
asset on the diligence page — Brier score and mean predicted/observed for
the asset's therapeutic_area / modality / capital_position triple, plus the
overall aggregate. The frontend renders this next to the PoS waterfall.
"""

from __future__ import annotations

from ...domain import DiligenceRecord
from . import db
from .schemas import AssetCalibrationContext


def compute(record: DiligenceRecord) -> AssetCalibrationContext:
    """Required module entrypoint."""
    asset = record.asset
    return db.get_asset_context(
        therapeutic_area=asset.therapeutic_area.value,
        modality=asset.modality.value,
        capital_position=asset.capital_position.value,
    )
