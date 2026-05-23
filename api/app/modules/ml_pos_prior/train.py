"""Training script for the ML PoS Prior — a rule-smoothed logistic surrogate.

Run with:
    python -m app.modules.ml_pos_prior.train

What this trains, honestly:
    Samples N=10_000 synthetic AssetInputs uniformly over feature combinations,
    computes the rule-based PoS engine's final_loa for each, then Bernoulli-
    samples a binary outcome from that probability. Fits sklearn
    LogisticRegression(L2) on the encoded features and pickles to model.joblib.

What this is NOT:
    An independent second opinion. The labels are derived from the rule-based
    chain. The trained classifier is a logistic-regression surrogate — useful
    for surfacing where the chain's multiplicative composition disagrees with
    an additive log-odds approximation, but NOT new evidence about the world.
    True independent evidence requires real outcome data (HINT / CTOP / CT
    Open), which is the v1.5.2 path documented in methodology/09-ml-pos-prior.md.

What's persisted in the artifact:
    {
      "model": <fitted LogisticRegression>,
      "metrics": {... test_auc, test_brier, ...},
      "feature_schema": {... runtime-encoder-invariants the engine validates},
      "training_meta": {... sklearn version, fitting date, random seed},
    }
    The schema sidecar lets engine._load_model() reject artifacts whose feature
    space has drifted from the runtime encoder.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import cast

from datetime import datetime, timezone

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from ...domain import (
    AssetInput,
    CapitalPosition,
    DiligenceRecord,
    Modality,
    Phase,
    TherapeuticArea,
)
from ..pos.engine import compute as compute_pos
from .features import (
    CAPITAL_POSITIONS,
    DESIGNATION_FLAGS,
    MODALITIES,
    N_FEATURES,
    PHASE_ORDER,
    THERAPEUTIC_AREAS,
    encode,
)

log = logging.getLogger(__name__)

N_SAMPLES = 10_000
RANDOM_SEED = 42
MODEL_OUT = Path(__file__).parent / "model.joblib"


def _sample_asset(rng: np.random.Generator) -> AssetInput:
    """Sample one AssetInput uniformly over its feature combinations."""
    # Skip APPROVED phase — has no transition to predict
    phases = [p for p in PHASE_ORDER if p != Phase.APPROVED]
    return AssetInput(
        asset_name=f"synth_{rng.integers(0, 1_000_000_000):010d}",
        phase=cast(Phase, phases[rng.integers(0, len(phases))]),
        therapeutic_area=cast(
            TherapeuticArea,
            THERAPEUTIC_AREAS[rng.integers(0, len(THERAPEUTIC_AREAS))],
        ),
        modality=cast(Modality, MODALITIES[rng.integers(0, len(MODALITIES))]),
        capital_position=cast(
            CapitalPosition,
            CAPITAL_POSITIONS[rng.integers(0, len(CAPITAL_POSITIONS))],
        ),
        regulatory_designations=[
            d for d in DESIGNATION_FLAGS if rng.random() < 0.15
        ],
        biomarker_enrichment=bool(rng.random() < 0.30),
        target_validated=bool(rng.random() < 0.50),
        num_competitors=int(rng.integers(0, 8)),
    )


def _compute_true_pos(asset: AssetInput) -> float:
    """Get the rule-based chain's final_loa for this asset."""
    record = DiligenceRecord(asset=asset)
    result = compute_pos(record)
    return result.final_loa


def generate_dataset(
    n: int = N_SAMPLES, seed: int = RANDOM_SEED
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (X, y, true_pos) — features, sampled binary outcomes, mean P."""
    rng = np.random.default_rng(seed)
    X = []
    y = []
    true_p = []
    for _ in range(n):
        asset = _sample_asset(rng)
        true_pos = _compute_true_pos(asset)
        outcome = int(rng.random() < true_pos)
        X.append(encode(asset))
        y.append(outcome)
        true_p.append(true_pos)
    return np.stack(X), np.array(y, dtype=int), np.array(true_p, dtype=float)


def train() -> dict:
    """Train the model and write model.joblib. Returns metrics."""
    log.info("generating %d synthetic samples", N_SAMPLES)
    X, y, _true_p = generate_dataset()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    log.info("fitting logistic regression on %d train samples", len(X_train))
    model = LogisticRegression(
        max_iter=2000,
        C=1.0,
        random_state=RANDOM_SEED,
    )
    model.fit(X_train, y_train)

    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    brier = brier_score_loss(y_test, y_pred_proba)
    base_rate = float(y_test.mean())

    metrics = {
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "test_auc": float(auc),
        "test_brier": float(brier),
        "test_base_rate": base_rate,
        "model_kind": "logistic_regression_v0.1.1",
    }

    # Schema sidecar — engine._load_model() validates these against runtime
    # encoder. Any change in feature count or category order forces a re-train,
    # which is what we want (silent feature drift would invalidate every
    # prediction).
    feature_schema = {
        "n_features": N_FEATURES,
        "phase_order": [p.value for p in PHASE_ORDER],
        "therapeutic_areas": [t.value for t in THERAPEUTIC_AREAS],
        "modalities": [m.value for m in MODALITIES],
        "capital_positions": [c.value for c in CAPITAL_POSITIONS],
        "designation_flags": [d.value for d in DESIGNATION_FLAGS],
    }

    training_meta = {
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "training_label_source": (
            "rule-based PoS engine final_loa, Bernoulli-sampled — "
            "rule-distillation, not independent evidence"
        ),
    }

    joblib.dump(
        {
            "model": model,
            "metrics": metrics,
            "feature_schema": feature_schema,
            "training_meta": training_meta,
        },
        MODEL_OUT,
    )
    log.info("model written to %s", MODEL_OUT)
    log.info("metrics: %s", metrics)
    log.info("training_meta: %s", training_meta)
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    metrics = train()
    print()
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
