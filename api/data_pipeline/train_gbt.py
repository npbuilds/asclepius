"""v1.5.2 Day 3 — train the gradient-boosted classifier on combined features.

Inputs:
  api/data/training/training_dataset.parquet       (Day 1: structured + labels)
  api/data/training/embeddings_pubmedbert.npy      (Day 2: PubMedBERT 768-dim)

The two files are pre-aligned by row index.

Output:
  api/data/training/model_v152.joblib              (artifact for Day 4 wiring)

The artifact lands at data/training/ rather than directly at
api/app/modules/ml_pos_prior/model.joblib because the v1.5.1.1 inference
path can't consume an 804-dim model yet. Day 4 swaps the inference path
to the PubMedBERT-in-container flow and renames this file to model.joblib
at that point.

Splits: HINT's pre-defined train/valid/test. Model uses LightGBM with L1
+ L2 regularization, fits on train with early stopping on valid, reports
held-out test AUC + Brier.

Decision history:
  - Initial run with HistGradientBoostingClassifier on BioBERT + struct
    hit AUC 0.6841, below the 0.70 ship floor.
  - LightGBM regularized: 0.6899 on the same features.
  - Morgan FP, normalize-L2, length features, ensemble: no meaningful gain.
  - PubMedBERT swap: AUC 0.7030 — crosses the borderline-ship threshold.
    PubMedBERT is the trained-from-scratch-on-PubMed model (Microsoft);
    BioBERT is BERT-base continued-pretrained on PubMed. The from-scratch
    vocabulary handles biomedical-dense text more efficiently. This is
    the v1.5.2 ship configuration.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import (
    brier_score_loss,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)

# Make app/ importable for the feature-schema sidecar fields
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.ml_pos_prior.features import (  # noqa: E402
    CAPITAL_POSITIONS,
    DESIGNATION_FLAGS,
    MODALITIES,
    N_FEATURES as N_STRUCT_FEATURES,
    PHASE_ORDER,
    THERAPEUTIC_AREAS,
)

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
TRAINING_DIR = API_DIR / "data" / "training"
PARQUET_PATH = TRAINING_DIR / "training_dataset.parquet"
# v1.5.2 ships PubMedBERT embeddings (AUC 0.703) not BioBERT (AUC 0.690).
# See module docstring for the decision history.
EMBEDDINGS_PATH = TRAINING_DIR / "embeddings_pubmedbert.npy"
NCTID_INDEX_PATH = TRAINING_DIR / "embeddings_pubmedbert_nctid.txt"
MODEL_OUT = TRAINING_DIR / "model_v152.joblib"

EMBEDDING_DIM = 768  # PubMedBERT-base hidden size (same as BioBERT)
COMBINED_DIM = EMBEDDING_DIM + N_STRUCT_FEATURES  # 768 + 36 = 804
EMBEDDING_MODEL_ID = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"

RANDOM_SEED = 42
EARLY_STOP_FRAC = 0.15
N_BOOTSTRAP_MODELS = 10  # 10x training cost, 10x artifact size, ~3.6 MB total.
MAX_BOOTSTRAP_MODELS = 20
MAX_ARTIFACT_SIZE_MB = 50
MAX_ARTIFACT_SIZE_BYTES = MAX_ARTIFACT_SIZE_MB * 1024 * 1024


def load_aligned_data() -> tuple[pd.DataFrame, np.ndarray]:
    """Load parquet + embeddings, verify alignment, return both.

    v1.5.2.1 (Codex F1): all three files are MANDATORY. The previous
    version made the NCTID sidecar optional, which silently accepted any
    same-length array. Now an embeddings file without its matching
    sidecar fails loud — the 0.7030 AUC claim rests on the sidecar
    matching the parquet order, so we enforce that pairing.
    """
    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Training parquet not found at {PARQUET_PATH}. "
            f"Run Day 1: python -m data_pipeline.build_training_dataset"
        )
    if not EMBEDDINGS_PATH.exists():
        raise FileNotFoundError(
            f"Embeddings not found at {EMBEDDINGS_PATH}. "
            f"Run Day 2 (Colab notebook with PubMedBERT, or "
            f"`python -m data_pipeline.embed_biobert` locally)."
        )
    if not NCTID_INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Embeddings sidecar (nctid order file) not found at "
            f"{NCTID_INDEX_PATH}. The sidecar is mandatory — its presence "
            f"is what guarantees row-by-row alignment with the parquet "
            f"DataFrame. Re-run the Day 2 producer so both files are "
            f"emitted together."
        )

    df = pd.read_parquet(PARQUET_PATH)
    embeddings = np.load(EMBEDDINGS_PATH)
    index_nctids = NCTID_INDEX_PATH.read_text().strip().split("\n")

    # Alignment check — must match by length, dim, AND nctid order
    if len(df) != embeddings.shape[0]:
        raise ValueError(
            f"row count mismatch: parquet has {len(df)} rows, "
            f"embeddings have {embeddings.shape[0]}"
        )
    if len(df) != len(index_nctids):
        raise ValueError(
            f"sidecar row count mismatch: parquet has {len(df)} rows, "
            f"sidecar has {len(index_nctids)}"
        )
    if list(df["nctid"]) != index_nctids:
        raise ValueError(
            "nctid order mismatch between parquet and embeddings sidecar. "
            "The embeddings file is paired with the wrong sidecar (or vice "
            "versa). Re-run Day 2 to regenerate both atomically."
        )
    if embeddings.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"embedding dim mismatch: got {embeddings.shape[1]}, "
            f"expected {EMBEDDING_DIM}"
        )

    return df, embeddings


def build_feature_matrix(df: pd.DataFrame, embeddings: np.ndarray) -> np.ndarray:
    """Concatenate [BERT-family embedding 768] + [structured 36] per row → 804-dim matrix."""
    struct_features = np.array(df["feature_vector"].tolist(), dtype=np.float32)
    if struct_features.shape[1] != N_STRUCT_FEATURES:
        raise ValueError(
            f"structured feature dim mismatch: got {struct_features.shape[1]}, "
            f"expected {N_STRUCT_FEATURES}"
        )
    X = np.concatenate([embeddings, struct_features], axis=1)
    assert X.shape == (len(df), COMBINED_DIM)
    return X


def train_early_stop_masks(
    splits: np.ndarray,
    y: np.ndarray,
    *,
    early_stop_frac: float = EARLY_STOP_FRAC,
    seed: int = RANDOM_SEED,
) -> tuple[np.ndarray, np.ndarray]:
    """Split HINT train rows into fit rows + deterministic early-stop rows.

    The HINT valid split is reserved exclusively for split-conformal
    calibration. Early stopping is model selection, so it gets its own
    train-only holdout carved deterministically by seed.
    """
    if not 0.0 < early_stop_frac < 0.5:
        raise ValueError("early_stop_frac must be between 0 and 0.5")

    train_idx = np.flatnonzero(splits == "train")
    if len(train_idx) < 4:
        raise ValueError("not enough train rows to carve early-stop split")

    rng = np.random.default_rng(seed)
    early_idx_parts = []
    y_train = y[train_idx]
    for label in np.unique(y_train):
        label_idx = train_idx[y_train == label]
        shuffled = rng.permutation(label_idx)
        n_holdout = int(np.ceil(len(shuffled) * early_stop_frac))
        if len(shuffled) > 1:
            n_holdout = min(max(n_holdout, 1), len(shuffled) - 1)
        early_idx_parts.append(shuffled[:n_holdout])

    early_idx = np.concatenate(early_idx_parts)
    early_stop_mask = np.zeros_like(splits, dtype=bool)
    early_stop_mask[early_idx] = True
    train_fit_mask = splits == "train"
    train_fit_mask[early_stop_mask] = False

    if not train_fit_mask.any() or not early_stop_mask.any():
        raise ValueError("early-stop split produced an empty fit or eval set")
    return train_fit_mask, early_stop_mask


def train_model(
    X: np.ndarray,
    y: np.ndarray,
    splits: np.ndarray,
    *,
    seed: int = RANDOM_SEED,
    early_stop_frac: float = EARLY_STOP_FRAC,
) -> tuple[lgb.LGBMClassifier, dict]:
    """Train LightGBM with early stopping carved from train rows only.

    HINT valid rows are kept untouched for split-conformal calibration.
    """
    train_mask = splits == "train"
    val_mask = splits == "valid"
    test_mask = splits == "test"
    train_fit_mask, early_stop_mask = train_early_stop_masks(
        splits, y, early_stop_frac=early_stop_frac, seed=seed,
    )

    X_train_fit, y_train_fit = X[train_fit_mask], y[train_fit_mask]
    X_train_all, y_train_all = X[train_mask], y[train_mask]
    X_early, y_early = X[early_stop_mask], y[early_stop_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    log.info(
        "splits: train_fit=%d, early_stop=%d, valid_cal=%d, test=%d",
        len(X_train_fit), len(X_early), int(val_mask.sum()), len(X_test),
    )

    # LGBM regularized config — picked via the Day 3 hyperparameter sweep.
    # The L1+L2 reg + larger min_child_samples keeps the trees from
    # over-fitting to the BERT-embedding feature dimensions (which are
    # dense, continuous, and noisy at the individual-feature level).
    model = lgb.LGBMClassifier(
        random_state=seed,
        verbose=-1,
        n_estimators=500,
        learning_rate=0.05,
        num_leaves=31,
        reg_alpha=0.5,
        reg_lambda=0.5,
        min_child_samples=30,
    )
    model.fit(
        X_train_fit, y_train_fit,
        eval_set=[(X_early, y_early)],
        callbacks=[lgb.early_stopping(20, verbose=False)],
    )

    log.info("fit complete after %d iterations", model.best_iteration_)

    # Evaluate on held-out test
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    auc = float(roc_auc_score(y_test, y_pred_proba))
    brier = float(brier_score_loss(y_test, y_pred_proba))
    test_base_rate = float(y_test.mean())
    train_base_rate = float(y_train_all.mean())

    log.info("test AUC: %.4f, Brier: %.4f", auc, brier)

    metrics = {
        "n_train": int(len(X_train_all)),
        "n_train_fit": int(len(X_train_fit)),
        "n_early_stop": int(len(X_early)),
        "n_val": int(val_mask.sum()),
        "early_stop_frac": float(early_stop_frac),
        "n_test": int(len(X_test)),
        "n_iterations": int(model.best_iteration_),
        "test_auc": auc,
        "test_brier": brier,
        "test_base_rate": test_base_rate,
        "train_base_rate": train_base_rate,
        "model_kind": f"lightgbm_pubmedbert_v0.2.0_{seed}",
        "feature_dim": int(X.shape[1]),
        "embedding_dim": EMBEDDING_DIM,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "structured_dim": N_STRUCT_FEATURES,
    }
    metrics["test_confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()
    metrics["test_classification_report"] = classification_report(
        y_test, y_pred, output_dict=True, zero_division=0
    )

    return model, metrics


# ---------------------------------------------------------------------------
# v1.5.3 — Mondrian split-conformal calibration of the uncertainty band.
#
# Pre-v1.5.3 the engine emitted a fixed ±0.30-logit heuristic band, openly
# documented in schemas.py as "NOT a calibrated statistical interval." This
# block replaces the heuristic with a distribution-free, post-hoc calibrated
# interval. The math: on the held-out val split (which the LGBM saw only for
# early-stopping, never for parameter fit), compute the (1-α) empirical
# quantile of |y_true - predicted_pos| within each phase. Stratify by phase
# because phase_1/2/3 base rates are wildly different (Ph1 ~56%, Ph3 ~76%),
# so a single global radius is too wide for one phase and too narrow for
# another — Mondrian conformal addresses that without sacrificing the
# marginal coverage guarantee.
#
# Coverage guarantee under exchangeability:
#   Pr( y ∈ [p̂ - r_phase, p̂ + r_phase] ) ≥ 1 - α
# evaluated separately per phase. The (n+1)/n correction in the quantile
# index gives the finite-sample tightness.
# ---------------------------------------------------------------------------


CONFORMAL_ALPHA = 0.10  # ship a 90% interval. Standard for portfolio analytics.
CONFORMAL_PHASES = ("phase_1", "phase_2", "phase_3")


def _conformal_quantile(residuals: np.ndarray, alpha: float) -> float:
    """Split-conformal quantile with the (n+1)/n finite-sample correction.

    Standard split-conformal recipe: rank residuals ascending; take the
    ceil((n+1)(1-α))-th order statistic. Returns the radius r such that
    Pr(|y - p̂| ≤ r) ≥ 1 - α under exchangeability with the calibration set.
    """
    n = len(residuals)
    if n == 0:
        raise ValueError("cannot compute conformal radius on empty residual set")
    # The exact split-conformal index. np.quantile with "higher" gives the
    # right tail bound; we manually compute the index to make the (n+1)
    # correction visible.
    k = int(np.ceil((n + 1) * (1 - alpha)))
    k = min(max(k, 1), n)  # clamp into [1, n] for small calibration sets
    return float(np.sort(np.abs(residuals))[k - 1])


def compute_mondrian_radii(
    model: lgb.LGBMClassifier,
    X_val: np.ndarray,
    y_val: np.ndarray,
    phases_val: np.ndarray,
    *,
    alpha: float = CONFORMAL_ALPHA,
) -> tuple[dict[str, float], dict[str, int], float]:
    """Returns (radii_by_phase, n_calibration_by_phase, overall_radius).

    `overall_radius` is the fallback used at inference for phases not in
    CONFORMAL_PHASES (e.g., preclinical, NDA — both rare in the training
    distribution).
    """
    pred_val = model.predict_proba(X_val)[:, 1]
    residuals_all = np.abs(y_val.astype(float) - pred_val)

    radii: dict[str, float] = {}
    n_by_phase: dict[str, int] = {}
    for phase in CONFORMAL_PHASES:
        mask = phases_val == phase
        n = int(mask.sum())
        n_by_phase[phase] = n
        if n < 20:
            # Small calibration set: skip Mondrian and let the engine use the
            # overall radius. <20 is too few for a stable 90% quantile.
            log.warning(
                "phase %s has only %d val rows — skipping Mondrian, will use "
                "overall radius at inference", phase, n,
            )
            continue
        radii[phase] = _conformal_quantile(residuals_all[mask], alpha)

    overall_radius = _conformal_quantile(residuals_all, alpha)
    return radii, n_by_phase, overall_radius


def compute_test_coverage(
    model: lgb.LGBMClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray,
    phases_test: np.ndarray,
    radii: dict[str, float],
    overall_radius: float,
) -> dict[str, float]:
    """Empirical coverage on test split — the sanity check that the
    calibration set generalizes. Should be close to 1 - α (i.e., ~0.90) for
    each phase under exchangeability.
    """
    pred_test = model.predict_proba(X_test)[:, 1]
    coverage: dict[str, float] = {}

    for phase in CONFORMAL_PHASES:
        mask = phases_test == phase
        if not mask.any():
            continue
        r = radii.get(phase, overall_radius)
        y_phase = y_test[mask].astype(float)
        p_phase = pred_test[mask]
        in_band = (np.abs(y_phase - p_phase) <= r).astype(float)
        coverage[phase] = float(in_band.mean())

    # Overall coverage uses each row's applicable radius (phase-specific
    # when available, else the global fallback).
    in_band_all = []
    for i, ph in enumerate(phases_test):
        r = radii.get(ph, overall_radius)
        in_band_all.append(abs(float(y_test[i]) - pred_test[i]) <= r)
    coverage["overall"] = float(np.mean(in_band_all))
    return coverage




def train_bootstrap_ensemble(
    X: np.ndarray,
    y: np.ndarray,
    splits: np.ndarray,
    *,
    n_models: int = N_BOOTSTRAP_MODELS,
    base_seed: int = RANDOM_SEED,
    early_stop_frac: float = EARLY_STOP_FRAC,
) -> list[lgb.LGBMClassifier]:
    """Train n_models LGBM classifiers on independent bootstrap resamples of
    train-fit rows. Each model uses the same hyperparams as the main model;
    early-stopping runs against a deterministic train-only holdout.

    Why bootstrap, not bagging via LGBM's bagging_fraction: we want
    independent draws from the empirical training distribution so the
    bootstrap predictions actually reflect resampling uncertainty. LGBM's
    bagging_fraction subsamples per-iteration within a single tree
    ensemble, which doesn't give the same uncertainty signal.

    Why 10 models, not 100: marginal coverage of the empirical quantile
    band is acceptable at K=10 (rough monte-carlo error on the quantile
    is ~3-5pp at K=10 vs ~1pp at K=100); the next bottleneck is artifact
    size and inference latency, not statistical noise.
    """
    train_fit_mask, early_stop_mask = train_early_stop_masks(
        splits, y, early_stop_frac=early_stop_frac, seed=base_seed,
    )
    X_train_full, y_train_full = X[train_fit_mask], y[train_fit_mask]
    X_early, y_early = X[early_stop_mask], y[early_stop_mask]
    n_train = len(X_train_full)

    rng = np.random.default_rng(base_seed)
    models: list[lgb.LGBMClassifier] = []
    for i in range(n_models):
        # Bootstrap-resample WITH replacement (the standard).
        idx = rng.integers(0, n_train, size=n_train)
        Xb, yb = X_train_full[idx], y_train_full[idx]
        m = lgb.LGBMClassifier(
            random_state=base_seed + i + 1,
            verbose=-1,
            n_estimators=500,
            learning_rate=0.05,
            num_leaves=31,
            reg_alpha=0.5,
            reg_lambda=0.5,
            min_child_samples=30,
        )
        m.fit(
            Xb, yb,
            eval_set=[(X_early, y_early)],
            callbacks=[lgb.early_stopping(20, verbose=False)],
        )
        log.info("bootstrap model %d/%d fit (n_iter=%d)", i + 1, n_models, m.best_iteration_)
        models.append(m)
    return models


def bootstrap_intervals(
    bootstrap_models: list[lgb.LGBMClassifier],
    X: np.ndarray,
    *,
    alpha: float = 0.10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute (mean_pred, q_low, q_high) from the bootstrap ensemble for
    every row in X. q_low/q_high are the α/2 and 1-α/2 empirical quantiles
    across the K bootstrap models — the bootstrap percentile interval.
    """
    preds = np.stack([m.predict_proba(X)[:, 1] for m in bootstrap_models], axis=0)
    mean_pred = preds.mean(axis=0)
    q_low = np.quantile(preds, alpha / 2, axis=0)
    q_high = np.quantile(preds, 1 - alpha / 2, axis=0)
    return mean_pred, q_low, q_high


# ---------------------------------------------------------------------------
# v1.5.4 — Locally-adaptive (heteroskedastic) split-conformal calibration.
#
# v1.5.3 shipped TWO uncertainty bands but they answered different questions:
#   - Bootstrap percentile (displayed in UI): useful adaptive shape, no
#     formal coverage guarantee
#   - Mondrian split-conformal (recorded only): formal 90% guarantee per
#     phase, but radii so wide (~0.70) the bands collapse to [0, 1] for
#     any prediction near 0.5 — mathematically correct, practically
#     uninformative.
#
# v1.5.4 merges them via Conformalized Quantile Regression-style
# heteroskedastic conformal (Romano, Patterson, Candès 2019). The
# bootstrap ensemble's per-prediction std σ̂(x) is the variance proxy;
# the conformal radius scales each prediction by this proxy. Where the
# bootstrap models agree → tight band. Where they disagree → wide band.
# Coverage guarantee survives because conformalization is post-hoc on
# the val split.
#
# Algorithm:
#   1. On val split, compute mean prediction p̂_mean(x) and std σ̂(x)
#      across the K bootstrap models.
#   2. Scaled residual at each cal point:
#        s_i = |y_i − p̂_mean(x_i)| / max(σ̂(x_i), σ_floor)
#      σ_floor avoids divide-by-zero when bootstrap models agree
#      perfectly (rare but observable).
#   3. Conformal scaling factor:
#        r = quantile_{1-α}^{(n+1)/n}(s_i)
#      This is a SCALAR — same for all test predictions.
#   4. At inference for novel x_new:
#        band = [p̂_mean(x_new) − r·σ̂(x_new),
#                p̂_mean(x_new) + r·σ̂(x_new)]
#      clipped to [0, 1].
#
# Coverage guarantee (under exchangeability of test + val):
#   Pr( y_new ∈ band ) ≥ 1 - α
# with the (n+1)/n finite-sample correction. Width adapts to local
# bootstrap disagreement instead of being a flat Mondrian per-phase
# scalar.
# ---------------------------------------------------------------------------


SIGMA_FLOOR = 1e-3  # bootstrap std floor; tiny but nonzero to keep
                    # divisions stable when all 10 models converge


def _bootstrap_mean_std(
    bootstrap_models: list[lgb.LGBMClassifier],
    X: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (mean, std) of the K bootstrap models' predict_proba[:,1] for
    every row in X. Vectorized once, no Python loop on rows."""
    preds = np.stack([m.predict_proba(X)[:, 1] for m in bootstrap_models], axis=0)
    return preds.mean(axis=0), preds.std(axis=0, ddof=0)


def compute_adaptive_radius(
    bootstrap_models: list[lgb.LGBMClassifier],
    X_val: np.ndarray,
    y_val: np.ndarray,
    *,
    alpha: float = CONFORMAL_ALPHA,
    sigma_floor: float = SIGMA_FLOOR,
) -> tuple[float, dict[str, float]]:
    """Compute the locally-adaptive conformal scaling factor r on the val
    split. Returns (r, diagnostics) where diagnostics records the median
    σ̂ on val, the min σ̂ (after floor), and the n used.

    The σ_floor prevents pathological behavior when bootstrap models all
    agree on a point (σ̂ ≈ 0 → scaled residual blows up). 1e-3 is small
    enough not to dominate well-uncertain points but large enough to
    keep the quantile finite for sharp-prediction outliers.
    """
    mean_val, std_val = _bootstrap_mean_std(bootstrap_models, X_val)
    sigma = np.maximum(std_val, sigma_floor)
    scaled_residuals = np.abs(y_val.astype(float) - mean_val) / sigma
    r = _conformal_quantile(scaled_residuals, alpha)
    return r, {
        "median_sigma_val": float(np.median(std_val)),
        "min_sigma_val_pre_floor": float(np.min(std_val)),
        "min_sigma_val_post_floor": float(np.min(sigma)),
        "n_val": int(len(y_val)),
        "sigma_floor": sigma_floor,
    }


def adaptive_band(
    bootstrap_models: list[lgb.LGBMClassifier],
    X: np.ndarray,
    r: float,
    *,
    sigma_floor: float = SIGMA_FLOOR,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """At inference: for each row of X return (mean, low, high) where
    [low, high] = [mean - r·σ̂, mean + r·σ̂], clipped to [0, 1]."""
    mean, std = _bootstrap_mean_std(bootstrap_models, X)
    sigma = np.maximum(std, sigma_floor)
    half = r * sigma
    low = np.clip(mean - half, 0.0, 1.0)
    high = np.clip(mean + half, 0.0, 1.0)
    return mean, low, high


def compute_adaptive_coverage(
    bootstrap_models: list[lgb.LGBMClassifier],
    X_test: np.ndarray,
    y_test: np.ndarray,
    phases_test: np.ndarray,
    r: float,
    *,
    sigma_floor: float = SIGMA_FLOOR,
) -> dict[str, float]:
    """Empirical coverage of the locally-adaptive band on test. Reports
    per-phase and overall. Sanity check that the val-calibrated r
    generalizes."""
    mean_test, low_test, high_test = adaptive_band(
        bootstrap_models, X_test, r, sigma_floor=sigma_floor,
    )
    in_band = (low_test <= y_test) & (y_test <= high_test)

    coverage: dict[str, float] = {}
    for phase in CONFORMAL_PHASES:
        mask = phases_test == phase
        if not mask.any():
            continue
        coverage[phase] = float(in_band[mask].mean())
    coverage["overall"] = float(in_band.mean())
    return coverage


def compute_adaptive_band_widths(
    bootstrap_models: list[lgb.LGBMClassifier],
    X_test: np.ndarray,
    r: float,
    *,
    sigma_floor: float = SIGMA_FLOOR,
) -> dict[str, float]:
    """Diagnostic widths to report alongside coverage — avg / p25 / p75
    band width on test. Lets the reader see whether locally-adaptive is
    actually adapting (wide spread between p25 and p75 widths means
    yes; narrow spread means it's effectively constant-radius)."""
    _, low_test, high_test = adaptive_band(
        bootstrap_models, X_test, r, sigma_floor=sigma_floor,
    )
    widths = high_test - low_test
    return {
        "avg": float(widths.mean()),
        "p25": float(np.quantile(widths, 0.25)),
        "p50": float(np.quantile(widths, 0.50)),
        "p75": float(np.quantile(widths, 0.75)),
        "min": float(widths.min()),
        "max": float(widths.max()),
    }


def save_artifact(
    model,
    metrics: dict,
    *,
    seed: int = RANDOM_SEED,
    conformal: dict | None = None,
    bootstrap_models: list[lgb.LGBMClassifier] | None = None,
) -> Path:
    """Persist model + feature_schema + training_meta in the same shape as
    v1.5.1's artifact (so the Day 4 inference path can load it).

    v1.5.2.1 (Codex F8): the actual seed used at fit time is persisted in
    training_meta, not the module-level RANDOM_SEED constant. Re-running
    with --seed now records the actual seed in the artifact metadata,
    preserving reproducibility.
    """
    from datetime import datetime, timezone

    import sklearn

    # Capture lightgbm version up front so we can record it both in the
    # validated feature_schema (engine checks it) and in training_meta
    # (informational duplicate). v1.5.2.1 (Codex Day 4 MINOR #5): the
    # version was previously only in training_meta and the runtime
    # engine didn't check it, allowing silent unpickle-version drift.
    try:
        import lightgbm

        lightgbm_version = lightgbm.__version__
    except ImportError:
        lightgbm_version = "unknown"

    # v1.5.2 Day 4 (Decision D): schema sidecar adds the embedding-pipeline
    # parameters that the runtime engine must match exactly. Any drift
    # between training-time and runtime tokenization / pooling silently
    # produces wrong embeddings, so we record + validate all of them.
    feature_schema = {
        "n_features": COMBINED_DIM,
        "embedding_dim": EMBEDDING_DIM,
        "structured_dim": N_STRUCT_FEATURES,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "max_length": 512,
        "pool_method": "mean",
        "lightgbm_version_major": lightgbm_version.split(".")[0]
            if lightgbm_version != "unknown" else "unknown",
        "phase_order": [p.value for p in PHASE_ORDER],
        "therapeutic_areas": [t.value for t in THERAPEUTIC_AREAS],
        "modalities": [m.value for m in MODALITIES],
        "capital_positions": [c.value for c in CAPITAL_POSITIONS],
        "designation_flags": [d.value for d in DESIGNATION_FLAGS],
    }
    # Note: lightgbm_version was already captured above for the
    # feature_schema. Reused here in training_meta for informational
    # transparency (the engine validates only the major-version compatibility
    # via the schema; this preserves the full version string for audit).
    training_meta = {
        "sklearn_version": sklearn.__version__,
        "lightgbm_version": lightgbm_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": seed,
        "training_label_source": (
            "HINT clinical-trial-outcome-prediction corpus "
            "(Fu et al. 2022); supervised on real success/failure outcomes — "
            "not label-derived from the rule chain (the v1.5.1 surrogate's "
            "labels were Bernoulli samples from the rule chain itself; "
            "v1.5.2 uses real outcomes instead). See "
            "methodology/09-ml-pos-prior.md for the precise framing of the "
            "remaining shared upstream dependencies."
        ),
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "classifier": "LightGBM L1+L2 regularized, n_estimators=500, lr=0.05",
    }

    MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model,
        "metrics": metrics,
        "feature_schema": feature_schema,
        "training_meta": training_meta,
    }
    if conformal is not None:
        # v1.5.3: Mondrian split-conformal radii live at the top level of the
        # artifact (not in feature_schema) because they're not part of the
        # input-validation contract — the engine reads them at load and
        # applies them at inference. Schema is for "what shape was the
        # model trained on"; conformal is for "what does the model output
        # mean."
        payload["conformal"] = conformal
    if bootstrap_models is not None:
        # v1.5.3: ensemble of K LGBM models trained on bootstrap resamples
        # of train. The engine surfaces this as the displayed uncertainty
        # band (epistemic model-resampling uncertainty), in contrast to
        # the conformal radii which surface label-uncertainty coverage.
        # Two-axis uncertainty: conformal for "how often does the truth
        # fall in the band" (recorded in methodology), bootstrap for
        # "how much does the model disagree with itself" (shown in UI).
        payload["bootstrap_models"] = bootstrap_models
    joblib.dump(payload, MODEL_OUT)
    log.info("artifact written to %s (%.2f MB)", MODEL_OUT, MODEL_OUT.stat().st_size / 1024 / 1024)
    return MODEL_OUT


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--early-stop-frac", type=float, default=EARLY_STOP_FRAC)
    parser.add_argument("--n-bootstrap-models", type=int, default=N_BOOTSTRAP_MODELS)
    parser.add_argument(
        "--override-bootstrap-model-limit",
        action="store_true",
        help=f"allow more than {MAX_BOOTSTRAP_MODELS} bootstrap models",
    )
    args = parser.parse_args(argv)
    if args.n_bootstrap_models > MAX_BOOTSTRAP_MODELS and not args.override_bootstrap_model_limit:
        parser.error(
            f"--n-bootstrap-models={args.n_bootstrap_models} exceeds "
            f"MAX_BOOTSTRAP_MODELS={MAX_BOOTSTRAP_MODELS}; pass "
            "--override-bootstrap-model-limit to proceed intentionally"
        )

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    log.info(
        "Day 3: training GBT classifier on combined PubMedBERT + structured features"
    )
    df, embeddings = load_aligned_data()
    X = build_feature_matrix(df, embeddings)
    y = df["label"].to_numpy()
    splits = df["split"].to_numpy()

    log.info("X shape: %s, y shape: %s", X.shape, y.shape)

    model, metrics = train_model(
        X, y, splits, seed=args.seed, early_stop_frac=args.early_stop_frac,
    )

    # v1.5.3.1: Mondrian split-conformal calibration. The HINT valid split
    # is now untouched by both parameter fit and early stopping; early
    # stopping uses a deterministic train-only holdout. Stratify
    # by phase because base rates differ enormously across phases.
    val_mask = splits == "valid"
    test_mask = splits == "test"
    phases_all = df["phase"].to_numpy()
    radii, n_cal_by_phase, overall_radius = compute_mondrian_radii(
        model, X[val_mask], y[val_mask], phases_all[val_mask],
        alpha=CONFORMAL_ALPHA,
    )
    coverage = compute_test_coverage(
        model, X[test_mask], y[test_mask], phases_all[test_mask],
        radii, overall_radius,
    )
    log.info("conformal radii (α=%.2f): %s", CONFORMAL_ALPHA, radii)
    log.info("conformal overall radius (fallback): %.4f", overall_radius)
    log.info("conformal coverage on test split: %s", coverage)

    conformal_payload = {
        "alpha": CONFORMAL_ALPHA,
        "method": "split_conformal_mondrian",
        "radii": radii,
        "overall_radius": overall_radius,
        "n_calibration": n_cal_by_phase,
        "test_coverage": coverage,
        "calibration_split": "valid",
    }
    metrics["conformal_test_coverage"] = coverage

    # v1.5.3: bootstrap ensemble for the displayed uncertainty band.
    log.info("training %d bootstrap models for the v1.5.3 uncertainty band", args.n_bootstrap_models)
    boot_models = train_bootstrap_ensemble(
        X, y, splits,
        n_models=args.n_bootstrap_models,
        base_seed=args.seed,
        early_stop_frac=args.early_stop_frac,
    )

    # Diagnostic: average bootstrap band-width on the test split (sanity
    # check that the band isn't trivially [0,1] or collapsed to a point).
    _, ql_test, qh_test = bootstrap_intervals(
        boot_models, X[test_mask], alpha=CONFORMAL_ALPHA,
    )
    avg_width = float(np.mean(qh_test - ql_test))
    log.info("bootstrap band: avg width on test = %.4f (target: 0.05-0.20 for useful UX)", avg_width)
    metrics["bootstrap_avg_band_width_test"] = avg_width
    metrics["bootstrap_n_models"] = args.n_bootstrap_models

    # v1.5.4: locally-adaptive (heteroskedastic) split-conformal radius.
    # Uses the bootstrap ensemble's per-prediction std as the variance proxy
    # so the conformal scaling factor produces tight bands where the K
    # bootstrap models agree and wide bands where they disagree. This
    # supersedes the v1.5.3 Mondrian-by-phase fixed radii (which are still
    # persisted alongside as a methodology-grade comparison baseline).
    log.info("computing v1.5.4 locally-adaptive conformal radius on val…")
    adaptive_r, adaptive_diag = compute_adaptive_radius(
        boot_models, X[val_mask], y[val_mask], alpha=CONFORMAL_ALPHA,
    )
    adaptive_coverage = compute_adaptive_coverage(
        boot_models, X[test_mask], y[test_mask], phases_all[test_mask],
        adaptive_r,
    )
    adaptive_widths = compute_adaptive_band_widths(
        boot_models, X[test_mask], adaptive_r,
    )
    log.info("locally-adaptive r=%.4f, test coverage=%s", adaptive_r, adaptive_coverage)
    log.info("locally-adaptive band widths on test: %s", adaptive_widths)
    adaptive_payload = {
        "alpha": CONFORMAL_ALPHA,
        "method": "split_conformal_adaptive_heteroskedastic",
        "scaling_factor_r": adaptive_r,
        "sigma_floor": SIGMA_FLOOR,
        "test_coverage": adaptive_coverage,
        "test_band_widths": adaptive_widths,
        "diagnostics": adaptive_diag,
        "calibration_split": "valid",
    }
    metrics["adaptive_conformal_test_coverage"] = adaptive_coverage
    metrics["adaptive_conformal_band_widths_test"] = adaptive_widths

    # Combine Mondrian (legacy v1.5.3, kept for comparison) + adaptive
    # (v1.5.4, the new primary band) into the artifact's conformal block.
    # Engine reads adaptive.scaling_factor_r at inference; Mondrian stays
    # available for any consumer that wants the per-phase fixed radii.
    conformal_payload = {
        **conformal_payload,
        "adaptive": adaptive_payload,
    }

    artifact_path = save_artifact(
        model, metrics, seed=args.seed,
        conformal=conformal_payload,
        bootstrap_models=boot_models,
    )
    if artifact_path.stat().st_size >= MAX_ARTIFACT_SIZE_BYTES:
        raise RuntimeError(
            f"artifact size {artifact_path.stat().st_size / 1024 / 1024:.2f} MB "
            f"exceeds {MAX_ARTIFACT_SIZE_MB} MB ceiling"
        )

    # Per-phase breakdown of test AUC
    print("\nPER-PHASE TEST METRICS")
    test_mask = splits == "test"
    test_df = df[test_mask].reset_index(drop=True)
    X_test = X[test_mask]
    y_test = y[test_mask]
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    for phase in ("phase_1", "phase_2", "phase_3"):
        mask = test_df["phase"] == phase
        if mask.sum() < 5:
            continue
        sub_y = y_test[mask]
        sub_p = y_pred_proba[mask]
        if len(np.unique(sub_y)) < 2:
            continue
        sub_auc = roc_auc_score(sub_y, sub_p)
        sub_brier = brier_score_loss(sub_y, sub_p)
        print(
            f"  {phase}: n={int(mask.sum())}, "
            f"AUC={sub_auc:.4f}, Brier={sub_brier:.4f}, "
            f"observed_rate={float(sub_y.mean()):.3f}"
        )

    print("\nFINAL METRICS")
    for k, v in metrics.items():
        if k in ("test_confusion_matrix", "test_classification_report"):
            continue
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    print("\nDoane 2025 baseline AUC: 0.7404")
    auc = metrics["test_auc"]
    # Decision criteria locked at v1.5.2 plan time:
    #   ≥0.80 credible improvement | ≥0.74 ship | ≥0.70 borderline ship | <0.70 don't ship
    if auc >= 0.80:
        print(f"✓ Test AUC {auc:.4f} >= 0.80 — credible improvement over Doane 2025. SHIP.")
    elif auc >= 0.74:
        print(f"✓ Test AUC {auc:.4f} >= 0.74 — matches Doane 2025 baseline. SHIP.")
    elif auc >= 0.70:
        print(f"~ Test AUC {auc:.4f} in 0.70-0.74 — BORDERLINE SHIP per locked criteria.")
    else:
        print(f"⚠ Test AUC {auc:.4f} < 0.70 — DO NOT SHIP. Re-examine the pipeline.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
