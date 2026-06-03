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

import json
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


def _valid_conformal() -> dict:
    return {
        "method": "split_conformal_mondrian",
        "alpha": 0.10,
        "radii": {"phase_1": 0.70, "phase_2": 0.72, "phase_3": 0.74},
        "overall_radius": 0.73,
        "test_coverage": {
            "phase_1": 0.90,
            "phase_2": 0.91,
            "phase_3": 0.92,
            "overall": 0.91,
        },
    }


def _training_meta() -> dict:
    return {
        "sklearn_version": "test",
        "lightgbm_version": "test",
        "trained_at": "2026-05-25T00:00:00+00:00",
        "random_seed": 42,
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
            "training_meta": _training_meta(),
            "conformal": _valid_conformal(),
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
    assert metrics["conformal"] == _valid_conformal()


# ---------------------------------------------------------------------------
# v1.5.3 — bootstrap ensemble path
# ---------------------------------------------------------------------------


class _FakeBootstrapModel:
    """LightGBM-shaped stub that always returns a fixed prediction. Useful
    for building an ensemble with controlled disagreement."""

    def __init__(self, predicted_p: float):
        self._p = predicted_p

    def predict_proba(self, X):
        n = X.shape[0]
        return np.tile([1 - self._p, self._p], (n, 1))


def _write_artifact_with_bootstrap(
    path: Path,
    *,
    main_p: float = 0.40,
    ensemble_ps: list[float] | None = None,
) -> None:
    """Variant of _write_fake_artifact that includes a `bootstrap_models`
    list — exercises the v1.5.3 inference path."""
    if ensemble_ps is None:
        # Default ensemble with deliberate spread: bracketing main_p
        ensemble_ps = [0.30, 0.32, 0.35, 0.38, 0.40, 0.42, 0.45, 0.48, 0.50, 0.52]
    schema = _valid_schema_sidecar()
    joblib.dump(
        {
            "model": _FakeModel(main_p),
            "metrics": {
                "model_kind": "lightgbm_pubmedbert_v0.2.0_42",
                "test_auc": 0.703,
                "bootstrap_n_models": len(ensemble_ps),
            },
            "feature_schema": schema,
            "training_meta": _training_meta(),
            "conformal": _valid_conformal(),
            "bootstrap_models": [_FakeBootstrapModel(p) for p in ensemble_ps],
        },
        path,
    )


def test_bootstrap_band_widens_with_ensemble_disagreement(
    tmp_path: Path, monkeypatch, stub_bert_embed,
):
    """When the bootstrap ensemble disagrees, the displayed band widens.
    Verifies that the v1.5.3 path actually consults the ensemble rather
    than silently falling back to the logit heuristic."""
    tight = [0.39, 0.395, 0.40, 0.40, 0.40, 0.40, 0.40, 0.405, 0.41, 0.41]
    wide = [0.20, 0.25, 0.30, 0.35, 0.40, 0.40, 0.45, 0.50, 0.55, 0.60]

    artifact_tight = tmp_path / "tight.joblib"
    _write_artifact_with_bootstrap(artifact_tight, main_p=0.40, ensemble_ps=tight)
    monkeypatch.setattr(engine, "MODEL_PATH", artifact_tight)
    engine._load_model.cache_clear()
    out_tight = engine.compute(_record(), criteria_text="dummy criteria")

    artifact_wide = tmp_path / "wide.joblib"
    _write_artifact_with_bootstrap(artifact_wide, main_p=0.40, ensemble_ps=wide)
    monkeypatch.setattr(engine, "MODEL_PATH", artifact_wide)
    engine._load_model.cache_clear()
    out_wide = engine.compute(_record(), criteria_text="dummy criteria")

    width_tight = out_tight.uncertainty_high - out_tight.uncertainty_low
    width_wide = out_wide.uncertainty_high - out_wide.uncertainty_low

    assert width_wide > width_tight, (
        f"Wide ensemble ({width_wide:.3f}) should give a wider band than "
        f"tight ensemble ({width_tight:.3f}); v1.5.3 bootstrap path may "
        f"have silently fallen back to the heuristic"
    )


def test_bootstrap_band_encloses_point_estimate(
    tmp_path: Path, monkeypatch, stub_bert_embed,
):
    """Even when the main model is an outlier vs the ensemble (rare but
    possible because the main model is fit on the full train set, not a
    bootstrap), the band must still enclose predicted_pos so the pydantic
    validator accepts the result."""
    # Main model predicts 0.65; ensemble clustered at 0.20-0.35.
    ensemble = [0.20, 0.22, 0.25, 0.28, 0.30, 0.30, 0.32, 0.33, 0.34, 0.35]
    artifact = tmp_path / "outlier.joblib"
    _write_artifact_with_bootstrap(artifact, main_p=0.65, ensemble_ps=ensemble)
    monkeypatch.setattr(engine, "MODEL_PATH", artifact)
    engine._load_model.cache_clear()

    out = engine.compute(_record(), criteria_text="dummy criteria")
    assert out.uncertainty_low <= out.predicted_pos <= out.uncertainty_high


def test_legacy_artifact_without_bootstrap_uses_heuristic_band(
    tmp_path: Path, monkeypatch, stub_bert_embed,
):
    """Backward compat: artifacts without `bootstrap_models` must still
    work, falling back to the v1.5.2 logit heuristic band."""
    legacy = tmp_path / "legacy.joblib"
    _write_fake_artifact(legacy, predicted_p=0.40)  # no bootstrap_models key
    monkeypatch.setattr(engine, "MODEL_PATH", legacy)
    engine._load_model.cache_clear()

    out = engine.compute(_record(), criteria_text="dummy criteria")
    # Heuristic band: at p=0.40 with SE=0.30 in logit space, band is roughly
    # [0.32, 0.49]. Sanity check it lands somewhere reasonable.
    assert out.uncertainty_low < 0.40 < out.uncertainty_high
    assert 0.05 < (out.uncertainty_high - out.uncertainty_low) < 0.30


def test_bootstrap_band_bounds_inside_unit_interval(
    tmp_path: Path, monkeypatch, stub_bert_embed,
):
    """Empirical quantiles of probabilities are in [0,1] by construction,
    but defensive check that the v1.5.3 path never returns out-of-range."""
    ensemble = [0.01, 0.02, 0.05, 0.10, 0.50, 0.70, 0.85, 0.90, 0.95, 0.99]
    artifact = tmp_path / "spread.joblib"
    _write_artifact_with_bootstrap(artifact, main_p=0.50, ensemble_ps=ensemble)
    monkeypatch.setattr(engine, "MODEL_PATH", artifact)
    engine._load_model.cache_clear()

    out = engine.compute(_record(), criteria_text="dummy criteria")
    assert 0.0 <= out.uncertainty_low <= 1.0
    assert 0.0 <= out.uncertainty_high <= 1.0


def test_conformal_coverage_below_floor_rejected(tmp_path: Path, monkeypatch):
    bad = tmp_path / "bad_conformal.joblib"
    payload = {
        "model": _FakeModel(0.40),
        "metrics": {"model_kind": "lightgbm_pubmedbert_v0.2.0_42"},
        "feature_schema": _valid_schema_sidecar(),
        "training_meta": _training_meta(),
        "conformal": {
            **_valid_conformal(),
            "test_coverage": {
                "phase_1": 0.90,
                "phase_2": 0.84,
                "phase_3": 0.91,
                "overall": 0.90,
            },
        },
    }
    joblib.dump(payload, bad)
    monkeypatch.setattr(engine, "MODEL_PATH", bad)
    engine._load_model.cache_clear()

    with pytest.raises(HTTPException) as exc:
        engine._load_model()
    assert exc.value.status_code == 503
    assert "phase_2" in exc.value.detail


def test_cache_requires_matching_artifact_fingerprint(tmp_path: Path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    record = _record()
    cache_payload = {
        "predicted_pos": 0.40,
        "uncertainty_low": 0.30,
        "uncertainty_high": 0.50,
        "model_kind": "lightgbm_pubmedbert_v0.2.0_42",
        "n_features": EXPECTED_COMBINED_DIM,
        "feature_fingerprint": engine.compute_feature_fingerprint(record),
        "artifact_fingerprint": {
            "trained_at": "stale",
            "random_seed": 999,
        },
    }
    (cache_dir / "test_asset.json").write_text(json.dumps(cache_payload))
    monkeypatch.setattr(engine, "CACHE_DIR", cache_dir)

    assert engine._maybe_cached(record) is None


def test_real_lightgbm_bootstrap_artifact_round_trip(
    tmp_path: Path, monkeypatch, stub_bert_embed,
):
    import lightgbm as lgb

    rng = np.random.default_rng(7)
    X = rng.normal(size=(48, EXPECTED_COMBINED_DIM)).astype(np.float32)
    y = (X[:, 0] + X[:, -1] > 0).astype(int)

    def fit_model(seed: int) -> lgb.LGBMClassifier:
        model = lgb.LGBMClassifier(
            random_state=seed,
            verbose=-1,
            n_estimators=6,
            learning_rate=0.2,
            num_leaves=3,
            min_child_samples=1,
            min_data_in_bin=1,
        )
        model.fit(X, y)
        return model

    bootstrap_models = [fit_model(100 + i) for i in range(engine.MIN_BOOTSTRAP_MODELS)]
    artifact = tmp_path / "real_lgbm.joblib"
    joblib.dump(
        {
            "model": fit_model(1),
            "metrics": {
                "model_kind": "lightgbm_pubmedbert_v0.2.0_42",
                "test_auc": 0.75,
                "bootstrap_n_models": len(bootstrap_models),
            },
            "feature_schema": _valid_schema_sidecar(),
            "training_meta": _training_meta(),
            "conformal": _valid_conformal(),
            "bootstrap_models": bootstrap_models,
        },
        artifact,
    )
    monkeypatch.setattr(engine, "MODEL_PATH", artifact)
    engine._load_model.cache_clear()

    model, phase_models, metrics, ensemble, conformal, fingerprint, calibrators = (
        engine._load_model()
    )
    assert isinstance(model, lgb.LGBMClassifier)
    assert len(ensemble) == engine.MIN_BOOTSTRAP_MODELS
    assert conformal["radii"]["phase_2"] == pytest.approx(0.72)
    assert fingerprint == engine.artifact_fingerprint_from_meta(_training_meta())
    # v1.5.9: calibrators are an optional sidecar; this synthetic artifact
    # doesn't include them, so the load path returns an empty dict and the
    # compute() path silently falls through to the raw-prediction branch.
    assert calibrators == {}

    out = engine.compute(_record(), criteria_text="synthetic KRAS criteria")
    assert 0.0 <= out.predicted_pos <= 1.0
    assert out.uncertainty_low <= out.predicted_pos <= out.uncertainty_high
    assert metrics["bootstrap_n_models"] == engine.MIN_BOOTSTRAP_MODELS
