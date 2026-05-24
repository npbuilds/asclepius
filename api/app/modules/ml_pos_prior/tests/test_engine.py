"""ML PoS Prior v0.2.0 engine tests.

v0.2.0 changes the engine from a 36-dim structured-features-only path to
an 804-dim combined path (PubMedBERT 768 + structured 36). The test
fixtures correspondingly need:
  - 804-dim mock model
  - mock for bert_embed.embed_text (real PubMedBERT load is too heavy)
  - mock for ctgov_fetch.fetch_eligibility_criteria when nct_id path tested

The tests follow the same structure they did in v1.5.1.1 — every guard
the previous engine enforced is still enforced, plus the new ones.
"""

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
from app.modules.ml_pos_prior import bert_embed, engine
from app.modules.ml_pos_prior.engine import (
    EXPECTED_COMBINED_DIM,
    PROBA_EPS,
    _disagreement_level,
    _logit_band,
)
from app.modules.ml_pos_prior.features import (
    CAPITAL_POSITIONS,
    DESIGNATION_FLAGS,
    MODALITIES,
    N_FEATURES,
    PHASE_ORDER,
    THERAPEUTIC_AREAS,
)
from app.modules.ml_pos_prior.schemas import MLPosPriorResult


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


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
                PoSAdjustment(name="t", multiplier=1.0, rationale="r", source="s")
            ],
        )
    return DiligenceRecord(asset=asset, pos=pos)


def _valid_schema_sidecar() -> dict:
    """v0.2.0 feature_schema that the engine will accept."""
    return {
        "n_features": EXPECTED_COMBINED_DIM,
        "embedding_dim": bert_embed.EMBEDDING_DIM,
        "structured_dim": N_FEATURES,
        "embedding_model_id": bert_embed.MODEL_ID,
        "max_length": bert_embed.MAX_LENGTH,
        "pool_method": bert_embed.POOL_METHOD,
        "phase_order": [p.value for p in PHASE_ORDER],
        "therapeutic_areas": [t.value for t in THERAPEUTIC_AREAS],
        "modalities": [m.value for m in MODALITIES],
        "capital_positions": [c.value for c in CAPITAL_POSITIONS],
        "designation_flags": [d.value for d in DESIGNATION_FLAGS],
    }


class _FakeModel:
    """Stand-in for LightGBM that returns a deterministic prediction."""

    def __init__(self, predicted_p: float = 0.45):
        self._p = predicted_p

    def predict_proba(self, X):
        n = X.shape[0]
        # Return [P(0), P(1)] columns
        return np.tile([1 - self._p, self._p], (n, 1))


def _write_fake_artifact(path: Path, *, predicted_p: float = 0.45, overrides: dict | None = None) -> None:
    """Write a v0.2.0-shaped joblib artifact at `path`."""
    schema = _valid_schema_sidecar()
    if overrides:
        schema.update(overrides)
    joblib.dump(
        {
            "model": _FakeModel(predicted_p),
            "metrics": {"model_kind": "lightgbm_pubmedbert_v0.2.0_42", "test_auc": 0.703},
            "feature_schema": schema,
            "training_meta": {"sklearn_version": "test", "lightgbm_version": "test"},
        },
        path,
    )


@pytest.fixture(autouse=True)
def _isolate_engine_state(tmp_path: Path, monkeypatch):
    """Each test gets a fresh fake artifact at a per-test MODEL_PATH and
    a cleared LRU cache so prior tests' artifacts don't leak in."""
    artifact_path = tmp_path / "model.joblib"
    _write_fake_artifact(artifact_path)
    monkeypatch.setattr(engine, "MODEL_PATH", artifact_path)
    engine._load_model.cache_clear()
    yield
    engine._load_model.cache_clear()


@pytest.fixture
def stub_bert_embed(monkeypatch):
    """Replace bert_embed.embed_text with a fast stub that returns a
    fixed 768-dim vector. Avoids loading PubMedBERT in unit tests."""

    def fake_embed(text: str) -> np.ndarray:
        if not text or not text.strip():
            raise ValueError("empty text")
        return np.ones(bert_embed.EMBEDDING_DIM, dtype=np.float32) * 0.1

    monkeypatch.setattr(bert_embed, "embed_text", fake_embed)
    return fake_embed


# ---------------------------------------------------------------------------
# Helpers / pure functions
# ---------------------------------------------------------------------------


def test_disagreement_level_buckets_correctly():
    assert _disagreement_level(2.5) == "aligned"
    assert _disagreement_level(-2.0) == "aligned"
    assert _disagreement_level(5.0) == "moderate"
    assert _disagreement_level(-6.5) == "moderate"
    assert _disagreement_level(8.0) == "divergent"
    assert _disagreement_level(-12.0) == "divergent"


def test_logit_band_handles_exact_endpoints():
    """Codex finding from v1.5.1.1 review — preserved in v0.2.0."""
    lo, hi = _logit_band(0.0)
    assert lo == pytest.approx(0.0, abs=1e-3)
    assert hi < 0.05
    lo, hi = _logit_band(1.0)
    assert lo > 0.95
    assert hi == pytest.approx(1.0, abs=1e-3)


def test_logit_band_encloses_point_estimate():
    for p in [0.0, 1e-9, 0.1, 0.5, 0.9, 1.0 - 1e-9, 1.0]:
        lo, hi = _logit_band(p)
        assert lo <= p + 1e-9 and p - 1e-9 <= hi


def test_proba_eps_is_small_enough():
    p = 0.30
    lo, hi = _logit_band(p)
    assert 0.20 < lo < 0.30
    assert 0.30 < hi < 0.40
    assert PROBA_EPS < 1e-3


# ---------------------------------------------------------------------------
# Inference success path
# ---------------------------------------------------------------------------


def test_inference_with_explicit_criteria_text(stub_bert_embed):
    """Cache-miss + explicit criteria_text → embed → predict."""
    out = engine.compute(
        _record(),
        criteria_text="Inclusion: NSCLC patients with KRAS G12C mutation.",
    )
    assert isinstance(out, MLPosPriorResult)
    assert 0.0 <= out.predicted_pos <= 1.0
    assert out.uncertainty_low <= out.predicted_pos <= out.uncertainty_high
    assert out.n_features == EXPECTED_COMBINED_DIM
    assert "pubmedbert" in out.model_kind.lower()


def test_inference_with_nct_id_fetches_ctgov(monkeypatch, stub_bert_embed):
    """If criteria_text is absent but nct_id is supplied, fetch from ct.gov."""
    fetched = []

    def fake_fetch(nct_id: str) -> str:
        fetched.append(nct_id)
        return "Inclusion: pretend ct.gov returned this."

    monkeypatch.setattr(
        "app.modules.ml_pos_prior.engine.fetch_eligibility_criteria",
        fake_fetch,
    )
    out = engine.compute(_record(), nct_id="NCT04685135")
    assert fetched == ["NCT04685135"]
    assert 0.0 <= out.predicted_pos <= 1.0


def test_inference_explicit_text_takes_priority_over_nct_id(monkeypatch, stub_bert_embed):
    """If both supplied, explicit text wins; ct.gov fetch isn't invoked."""
    fetched = []

    def fake_fetch(nct_id: str) -> str:
        fetched.append(nct_id)
        return "should not be used"

    monkeypatch.setattr(
        "app.modules.ml_pos_prior.engine.fetch_eligibility_criteria",
        fake_fetch,
    )
    engine.compute(
        _record(),
        criteria_text="Inclusion: KRAS G12C cohort.",
        nct_id="NCT04685135",
    )
    assert fetched == [], "ct.gov should not be called when criteria_text is supplied"


def test_inference_disagreement_pp_computed_against_rule_based(stub_bert_embed):
    out = engine.compute(_record(pos_loa=0.30), criteria_text="x")
    assert out.rule_based_pos == 0.30
    expected_gap = round((out.predicted_pos - 0.30) * 100, 2)
    assert out.disagreement_pp == expected_gap


def test_inference_without_pos_returns_zero_rule_based(stub_bert_embed):
    out = engine.compute(_record(pos_loa=None), criteria_text="x")
    assert out.rule_based_pos == 0.0


# ---------------------------------------------------------------------------
# Error paths (text + nct_id resolution)
# ---------------------------------------------------------------------------


def test_inference_without_text_or_nct_id_raises_value_error(stub_bert_embed):
    """v1.5.2: ML path requires criteria text. Engine raises ValueError;
    route translates to HTTPException(422)."""
    with pytest.raises(ValueError) as exc:
        engine.compute(_record())  # no criteria_text, no nct_id
    assert "criteria-text" in str(exc.value).lower() or "criteria_text" in str(exc.value)


def test_empty_criteria_text_treated_as_missing(stub_bert_embed):
    """Whitespace-only or empty text falls through to the missing-text error."""
    with pytest.raises(ValueError):
        engine.compute(_record(), criteria_text="   ")


def test_ctgov_fetch_failure_raises_503(monkeypatch, stub_bert_embed):
    """If nct_id fetch fails, engine raises HTTPException(503) — not 422
    (the request itself was well-formed; the external dependency failed)."""
    from app.modules.ml_pos_prior.ctgov_fetch import CtGovFetchError

    def fake_fetch(nct_id: str) -> str:
        raise CtGovFetchError("simulated network failure")

    monkeypatch.setattr(
        "app.modules.ml_pos_prior.engine.fetch_eligibility_criteria",
        fake_fetch,
    )
    with pytest.raises(HTTPException) as exc:
        engine.compute(_record(), nct_id="NCT04685135")
    assert exc.value.status_code == 503
    assert "ClinicalTrials.gov" in exc.value.detail or "ct.gov" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# Phase.APPROVED defense in depth
# ---------------------------------------------------------------------------


def test_phase_approved_rejected_at_engine_layer(stub_bert_embed):
    with pytest.raises(ValueError) as exc:
        engine.compute(_record(phase=Phase.APPROVED), criteria_text="x")
    assert "approved" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# Artifact / schema validation
# ---------------------------------------------------------------------------


def test_missing_artifact_raises_503(tmp_path: Path, monkeypatch):
    fake = tmp_path / "missing.joblib"
    monkeypatch.setattr(engine, "MODEL_PATH", fake)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503


def test_artifact_with_wrong_n_features_rejected(tmp_path: Path, monkeypatch):
    """v0.1.x model.joblib (n_features=36) must be rejected by the v0.2.0
    engine (expects n_features=804). This is the clean-cut migration."""
    bad = tmp_path / "bad.joblib"
    _write_fake_artifact(bad, overrides={"n_features": 36})
    monkeypatch.setattr(engine, "MODEL_PATH", bad)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    assert "n_features" in exc.value.detail


def test_artifact_with_wrong_embedding_model_id_rejected(tmp_path: Path, monkeypatch):
    bad = tmp_path / "bad.joblib"
    _write_fake_artifact(bad, overrides={"embedding_model_id": "some/other-bert"})
    monkeypatch.setattr(engine, "MODEL_PATH", bad)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    assert "embedding_model_id" in exc.value.detail


def test_artifact_with_wrong_max_length_rejected(tmp_path: Path, monkeypatch):
    bad = tmp_path / "bad.joblib"
    _write_fake_artifact(bad, overrides={"max_length": 256})
    monkeypatch.setattr(engine, "MODEL_PATH", bad)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    assert "max_length" in exc.value.detail


def test_artifact_with_wrong_pool_method_rejected(tmp_path: Path, monkeypatch):
    bad = tmp_path / "bad.joblib"
    _write_fake_artifact(bad, overrides={"pool_method": "cls"})
    monkeypatch.setattr(engine, "MODEL_PATH", bad)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    assert "pool_method" in exc.value.detail


def test_artifact_with_wrong_designation_flags_rejected(tmp_path: Path, monkeypatch):
    """Regression check from Codex v1.6 review (F1): designation_flags
    drift must still fail loud."""
    bad = tmp_path / "bad.joblib"
    _write_fake_artifact(
        bad,
        overrides={
            "designation_flags": list(reversed([d.value for d in DESIGNATION_FLAGS])),
        },
    )
    monkeypatch.setattr(engine, "MODEL_PATH", bad)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503


def test_artifact_missing_required_keys_rejected(tmp_path: Path, monkeypatch):
    """Codex v1.5.1.1 F5 regression check — KeyError must be wrapped 503."""
    incomplete = tmp_path / "incomplete.joblib"
    joblib.dump(
        {"metrics": {"model_kind": "x"}, "feature_schema": _valid_schema_sidecar()},
        incomplete,
    )
    monkeypatch.setattr(engine, "MODEL_PATH", incomplete)
    engine._load_model.cache_clear()
    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503


# ---------------------------------------------------------------------------
# Cache-clear discipline (the engine uses lru_cache on _load_model)
# ---------------------------------------------------------------------------


def test_get_model_metrics_returns_artifact_metrics(stub_bert_embed):
    metrics = engine.get_model_metrics()
    assert metrics["model_kind"] == "lightgbm_pubmedbert_v0.2.0_42"
    assert "test_auc" in metrics
