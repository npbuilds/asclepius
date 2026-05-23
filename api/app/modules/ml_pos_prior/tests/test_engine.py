"""ML PoS Prior tests — feature encoding, inference, disagreement bucketing."""

from __future__ import annotations

import numpy as np

from app.domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    PoSAdjustment,
    PoSResult,
    RegulatoryDesignation,
    TherapeuticArea,
)
from app.modules.ml_pos_prior import engine
from app.modules.ml_pos_prior.engine import _disagreement_level
from app.modules.ml_pos_prior.features import N_FEATURES, encode
from app.modules.ml_pos_prior.schemas import MLPosPriorResult


def _record(
    *,
    phase: Phase = Phase.PHASE_2,
    ta: TherapeuticArea = TherapeuticArea.ONCOLOGY,
    modality: Modality = Modality.SMALL_MOLECULE,
    capital: CapitalPosition = CapitalPosition.ADEQUATE,
    pos_loa: float | None = 0.161,
) -> DiligenceRecord:
    asset = AssetInput(
        asset_name="test_asset",
        phase=phase,
        therapeutic_area=ta,
        modality=modality,
        capital_position=capital,
        regulatory_designations=[RegulatoryDesignation.BTD],
        biomarker_enrichment=True,
        target_validated=True,
        num_competitors=1,
    )
    pos = None
    if pos_loa is not None:
        pos = PoSResult(
            base_rate=0.106,
            final_loa=pos_loa,
            confidence_low=pos_loa * 0.7,
            confidence_high=min(pos_loa * 1.3, 1.0),
            adjustments=[
                PoSAdjustment(
                    name="test", multiplier=1.0, rationale="test", source="test"
                )
            ],
        )
    return DiligenceRecord(asset=asset, pos=pos)


def test_encoded_vector_has_correct_length():
    vec = encode(_record().asset)
    assert vec.shape == (N_FEATURES,)
    assert vec.dtype == np.float32


def test_encoded_vector_uses_one_hot_for_categoricals():
    """Exactly one TA, one modality, one capital should be 1.0; rest 0.0."""
    vec = encode(_record().asset)
    # TA one-hot block is indices 1..11 inclusive
    ta_block = vec[1 : 1 + 11]
    assert ta_block.sum() == 1.0
    # Modality block follows
    mod_block = vec[12 : 12 + 11]
    assert mod_block.sum() == 1.0


def test_inference_returns_valid_probability():
    out = engine.compute(_record())
    assert isinstance(out, MLPosPriorResult)
    assert 0.0 <= out.predicted_pos <= 1.0
    assert 0.0 <= out.confidence_low <= out.predicted_pos
    assert out.predicted_pos <= out.confidence_high <= 1.0


def test_disagreement_pp_computed_against_rule_based():
    out = engine.compute(_record(pos_loa=0.10))
    # ML prediction is some float; gap_pp = (predicted - 0.10) * 100
    assert out.rule_based_pos == 0.10
    expected_gap = round((out.predicted_pos - 0.10) * 100, 2)
    assert out.disagreement_pp == expected_gap


def test_disagreement_level_buckets_correctly():
    assert _disagreement_level(2.5) == "aligned"
    assert _disagreement_level(-2.0) == "aligned"
    assert _disagreement_level(5.0) == "moderate"
    assert _disagreement_level(-6.5) == "moderate"
    assert _disagreement_level(8.0) == "divergent"
    assert _disagreement_level(-12.0) == "divergent"


def test_inference_without_pos_returns_zero_rule_based():
    out = engine.compute(_record(pos_loa=None))
    assert out.rule_based_pos == 0.0
    # Disagreement is large because rule_based defaulted to 0
    assert abs(out.disagreement_pp) > 0


def test_inference_for_well_capitalized_brings_predicted_higher():
    """Well-capitalized sponsors should get a higher ML prediction than
    constrained ones, all else equal. Direct test of the reflexivity tier
    influence on the trained model."""
    out_well = engine.compute(_record(capital=CapitalPosition.WELL_CAPITALIZED))
    out_constrained = engine.compute(
        _record(capital=CapitalPosition.CONSTRAINED)
    )
    assert out_well.predicted_pos > out_constrained.predicted_pos
