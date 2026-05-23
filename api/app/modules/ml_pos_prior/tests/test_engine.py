"""ML PoS Prior tests — feature encoding, inference, disagreement bucketing,
failure modes flagged by the Codex v1.5.1 review."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pytest
from fastapi import HTTPException

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
from app.modules.ml_pos_prior.engine import (
    PROBA_EPS,
    _disagreement_level,
    _logit_band,
)
from app.modules.ml_pos_prior.features import (
    CAPITAL_POSITIONS,
    MODALITIES,
    N_FEATURES,
    THERAPEUTIC_AREAS,
    encode,
)
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


# ---------------------------------------------------------------------------
# Feature encoding (preserved + tightened to use named constants per Codex nit)
# ---------------------------------------------------------------------------


def test_encoded_vector_has_correct_length():
    vec = encode(_record().asset)
    assert vec.shape == (N_FEATURES,)
    assert vec.dtype == np.float32


def test_encoded_vector_uses_one_hot_for_categoricals():
    """Exactly one TA, one modality, one capital should be 1.0; rest 0.0.
    Uses imported enum lengths (not hardcoded magic numbers) per the Codex nit."""
    vec = encode(_record().asset)
    ta_start = 1
    ta_end = ta_start + len(THERAPEUTIC_AREAS)
    assert vec[ta_start:ta_end].sum() == 1.0
    mod_start = ta_end
    mod_end = mod_start + len(MODALITIES)
    assert vec[mod_start:mod_end].sum() == 1.0
    cap_start = mod_end
    cap_end = cap_start + len(CAPITAL_POSITIONS)
    assert vec[cap_start:cap_end].sum() == 1.0


# ---------------------------------------------------------------------------
# Inference correctness
# ---------------------------------------------------------------------------


def test_inference_returns_valid_probability_with_band_enclosure():
    out = engine.compute(_record())
    assert isinstance(out, MLPosPriorResult)
    assert 0.0 <= out.predicted_pos <= 1.0
    # Pydantic validator (added in v1.5.1.1) guarantees the invariant
    assert out.uncertainty_low <= out.predicted_pos <= out.uncertainty_high


def test_disagreement_pp_computed_against_rule_based():
    out = engine.compute(_record(pos_loa=0.10))
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


def test_inference_for_well_capitalized_brings_predicted_higher():
    out_well = engine.compute(_record(capital=CapitalPosition.WELL_CAPITALIZED))
    out_constrained = engine.compute(
        _record(capital=CapitalPosition.CONSTRAINED)
    )
    assert out_well.predicted_pos > out_constrained.predicted_pos


# ---------------------------------------------------------------------------
# Edge cases flagged by Codex review (v1.5.1)
# ---------------------------------------------------------------------------


def test_logit_band_handles_exact_zero():
    """Codex finding #5: predict_proba == 0 should not produce a nonsensical
    50% logit center; the epsilon clip handles it."""
    lo, hi = _logit_band(0.0)
    assert lo == pytest.approx(0.0, abs=1e-3)
    assert hi < 0.05  # band stays tight near zero, not centered on 0.5


def test_logit_band_handles_exact_one():
    """Symmetric edge case at the upper endpoint."""
    lo, hi = _logit_band(1.0)
    assert lo > 0.95
    assert hi == pytest.approx(1.0, abs=1e-3)


def test_logit_band_encloses_point_estimate_always():
    """Property test — band must enclose the point estimate for any input."""
    for p in [0.0, 1e-9, 0.1, 0.5, 0.9, 1.0 - 1e-9, 1.0]:
        lo, hi = _logit_band(p)
        # Use a small epsilon for floating-point comparison
        assert lo <= p + 1e-9 and p - 1e-9 <= hi


def test_proba_eps_is_small_enough():
    """The epsilon must not materially shift the band for typical predictions."""
    p = 0.30
    lo, hi = _logit_band(p)
    # ±1 SE around 0.30 in logit space should be roughly [0.24, 0.37]
    assert 0.20 < lo < 0.30
    assert 0.30 < hi < 0.40
    # PROBA_EPS is small enough that it doesn't show up here
    assert PROBA_EPS < 1e-3


# ---------------------------------------------------------------------------
# Artifact-validation failures (Codex findings #6 + #7)
# ---------------------------------------------------------------------------


def test_missing_artifact_raises_503(tmp_path: Path, monkeypatch):
    """If model.joblib is gone, the engine raises HTTPException(503) instead
    of a raw RuntimeError / 500."""
    engine._load_model.cache_clear()
    fake_path = tmp_path / "nonexistent.joblib"
    monkeypatch.setattr(engine, "MODEL_PATH", fake_path)
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    engine._load_model.cache_clear()


def test_artifact_with_wrong_feature_count_rejected(tmp_path: Path, monkeypatch):
    """Schema validation rejects an artifact whose feature space doesn't match."""
    engine._load_model.cache_clear()
    bad_artifact_path = tmp_path / "bad.joblib"
    bad_artifact = {
        "model": object(),
        "metrics": {"model_kind": "test"},
        "feature_schema": {"n_features": 999},  # wrong
        "training_meta": {},
    }
    joblib.dump(bad_artifact, bad_artifact_path)
    monkeypatch.setattr(engine, "MODEL_PATH", bad_artifact_path)
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    assert "feature schema" in exc.value.detail.lower()
    engine._load_model.cache_clear()


def test_artifact_without_schema_sidecar_rejected(tmp_path: Path, monkeypatch):
    """Older artifacts without the feature_schema sidecar are rejected — keeps
    stale pre-v1.5.1.1 artifacts from being silently used."""
    engine._load_model.cache_clear()
    legacy_path = tmp_path / "legacy.joblib"
    joblib.dump({"model": object(), "metrics": {}}, legacy_path)
    monkeypatch.setattr(engine, "MODEL_PATH", legacy_path)
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    engine._load_model.cache_clear()


def test_get_model_metrics_public_accessor_works():
    """The /model_info route uses this. Verify it returns the new training
    metadata fields (sklearn version, trained_at)."""
    engine._load_model.cache_clear()
    metrics = engine.get_model_metrics()
    assert "model_kind" in metrics
    assert "test_auc" in metrics
    assert metrics["model_kind"] == "logistic_regression_v0.1.1"
