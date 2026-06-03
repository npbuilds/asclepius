"""v1.5.6 — Phase-stratified LightGBM training on HINT ∪ CTO.

Why phase-stratified models:
  The v1.5.5 external benchmark exposed a diagnostic failure: Phase-2 AUC
  collapsed to 0.543 (barely above random) on the CTO held-out set. A single
  global model shares one decision boundary across three wildly different base
  rates (CTO: Ph1=12%, Ph2=23%, Ph3=44%). Phase-stratified training allocates
  a separate LGBM per phase — each specialising on its own base rate, feature
  patterns, and eligibility-criteria style (dose-finding vs. indication-
  specific vs. registration-pivotal).

Why HINT ∪ CTO:
  The 2,429 CTO benchmark trials (v1.5.5) are now in training. The honest
  external validation (AUC 0.600) is permanently recorded in
  methodology/13-ct-open-benchmark.md. Retraining on labelled data is the
  natural next step per standard ML practice. A new held-out test evaluation
  uses the CTO test split (20%, ~486 trials) + HINT test split in combination.

Inputs:
  api/data/training/training_dataset.parquet           HINT (11,552 rows)
  api/data/training/embeddings_pubmedbert.npy          HINT embeddings
  api/data/training/embeddings_pubmedbert_nctid.txt    HINT nctid sidecar
  api/data/training/cto_training_dataset.parquet       CTO (2,429 rows)
  api/data/cto/cto_embeddings.npy                      CTO embeddings
  api/data/cto/cto_embeddings_nctid.txt                CTO nctid sidecar

Output:
  api/data/training/model_v156.joblib   → copy to model.joblib to ship

Artifact format (backward-compatible):
  {
    "model":          <overall LGBM — fallback for non-Ph1/2/3>,
    "phase_models":   {"phase_1": <LGBM>, "phase_2": <LGBM>, "phase_3": <LGBM>},
    "metrics":        {overall + per-phase AUC/Brier on test splits},
    "conformal":      {radii per phase + overall, test coverage},
    "bootstrap_models": [<10 LGBM resamples on full train corpus>],
    "feature_schema": {...},
    "training_meta":  {...},
  }

The engine.py v1.5.6 routes to phase_models[asset.phase] when available,
falls back to model for edge cases (preclinical, NDA).

Run with:
  cd api && python -m data_pipeline.train_gbt_v156

Optional flags:
  --seed N              random seed (default 42)
  --early-stop-frac F   fraction of train carved for early stopping (default 0.15)
  --n-bootstrap N       bootstrap ensemble size (default 10)
  --skip-bootstrap      skip bootstrap to save time; uncertainty band is disabled
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import brier_score_loss, roc_auc_score

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

HINT_PARQUET = TRAINING_DIR / "training_dataset.parquet"
HINT_EMB_NPY = TRAINING_DIR / "embeddings_pubmedbert.npy"
HINT_EMB_IDS = TRAINING_DIR / "embeddings_pubmedbert_nctid.txt"

CTO_PARQUET = TRAINING_DIR / "cto_training_dataset.parquet"
CTO_EMB_NPY = API_DIR / "data" / "cto" / "cto_embeddings.npy"
CTO_EMB_IDS = API_DIR / "data" / "cto" / "cto_embeddings_nctid.txt"

MODEL_OUT = TRAINING_DIR / "model_v156.joblib"
MODEL_SHIP = API_DIR / "app" / "modules" / "ml_pos_prior" / "model.joblib"

EMBEDDING_DIM = 768
COMBINED_DIM = EMBEDDING_DIM + N_STRUCT_FEATURES   # 768 + 36 = 804
EMBEDDING_MODEL_ID = "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext"

RANDOM_SEED = 42
EARLY_STOP_FRAC = 0.15
N_BOOTSTRAP_MODELS = 10
CONFORMAL_ALPHA = 0.10
CONFORMAL_PHASES = ("phase_1", "phase_2", "phase_3")

# Ship floor — same decision criteria as v1.5.2
SHIP_THRESHOLD = 0.70

# v1.5.6 LGBM hyperparams — same base as v1.5.2 but increased estimators for
# the larger combined training set (HINT 11k + CTO 1.6k = ~13k train rows).
LGBM_PARAMS = dict(
    verbose=-1,
    n_estimators=800,    # increased from 500 (larger dataset; early stopping governs)
    learning_rate=0.04,  # slightly lower to compensate for more estimators
    num_leaves=31,
    reg_alpha=0.5,
    reg_lambda=0.5,
    min_child_samples=25,  # slightly lower (smaller per-phase subsets in Ph1)
)


# ---------------------------------------------------------------------------
# Data loading + alignment
# ---------------------------------------------------------------------------


def _load_hint(
    parquet: Path = HINT_PARQUET,
    emb_npy: Path = HINT_EMB_NPY,
    emb_ids: Path = HINT_EMB_IDS,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Load HINT parquet + embeddings, return (df, embeddings) aligned by nctid."""
    if not parquet.exists():
        raise FileNotFoundError(
            f"HINT parquet not found: {parquet}\n"
            "Run: python -m data_pipeline.build_training_dataset"
        )
    for p in (emb_npy, emb_ids):
        if not p.exists():
            raise FileNotFoundError(f"HINT embeddings not found: {p}")

    df = pd.read_parquet(parquet)
    emb = np.load(emb_npy)
    ids = emb_ids.read_text().strip().split("\n")

    if len(df) != len(ids) or len(df) != emb.shape[0]:
        raise ValueError(
            f"HINT alignment mismatch: parquet={len(df)}, "
            f"embeddings={emb.shape[0]}, sidecar={len(ids)}"
        )
    if list(df["nctid"]) != ids:
        raise ValueError("HINT parquet ↔ embeddings nctid order mismatch")

    if "source_domain" not in df.columns:
        df = df.copy()
        df["source_domain"] = "hint"

    log.info("HINT: %d rows loaded (train=%d val=%d test=%d)",
             len(df), (df["split"] == "train").sum(),
             (df["split"] == "valid").sum(), (df["split"] == "test").sum())
    return df, emb.astype(np.float32)


def _load_cto(
    parquet: Path = CTO_PARQUET,
    emb_npy: Path = CTO_EMB_NPY,
    emb_ids: Path = CTO_EMB_IDS,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Load CTO training parquet + embeddings, align by nctid."""
    if not parquet.exists():
        raise FileNotFoundError(
            f"CTO training parquet not found: {parquet}\n"
            "Run: python -m data_pipeline.build_cto_training_dataset"
        )
    for p in (emb_npy, emb_ids):
        if not p.exists():
            raise FileNotFoundError(f"CTO embeddings not found: {p}")

    df = pd.read_parquet(parquet)
    emb_arr = np.load(emb_npy)
    emb_nctids = emb_ids.read_text().strip().split("\n")
    emb_lookup = {nid.upper(): i for i, nid in enumerate(emb_nctids)}

    # Align CTO embeddings to parquet row order (parquet rows may differ from
    # sidecar order — the CTO benchmark script aligns on-the-fly).
    indices = []
    missing = 0
    for nid in df["nctid"]:
        idx = emb_lookup.get(nid.upper())
        if idx is None:
            missing += 1
            indices.append(None)
        else:
            indices.append(idx)

    if missing > 0:
        log.warning("%d CTO parquet rows have no embedding — dropping", missing)
        keep = [i for i, idx in enumerate(indices) if idx is not None]
        df = df.iloc[keep].reset_index(drop=True)
        indices = [idx for idx in indices if idx is not None]

    aligned_emb = emb_arr[indices].astype(np.float32)

    if "source_domain" not in df.columns:
        df = df.copy()
        df["source_domain"] = "cto"

    log.info("CTO: %d rows loaded (train=%d val=%d test=%d)",
             len(df), (df["split"] == "train").sum(),
             (df["split"] == "valid").sum(), (df["split"] == "test").sum())
    return df, aligned_emb


def build_feature_matrix(df: pd.DataFrame, emb: np.ndarray) -> np.ndarray:
    """[PubMedBERT 768] ++ [structured 36] per row → 804-dim matrix."""
    struct = np.array(df["feature_vector"].tolist(), dtype=np.float32)
    assert struct.shape == (len(df), N_STRUCT_FEATURES), struct.shape
    X = np.concatenate([emb, struct], axis=1).astype(np.float32)
    assert X.shape == (len(df), COMBINED_DIM)
    return X


def load_union(
) -> tuple[pd.DataFrame, np.ndarray]:
    """Return (union_df, union_X). union_df has columns nctid, phase, label,
    split, source_domain. union_X is the 804-dim feature matrix aligned
    row-by-row to union_df."""
    hint_df, hint_emb = _load_hint()
    cto_df, cto_emb = _load_cto()

    hint_X = build_feature_matrix(hint_df, hint_emb)
    cto_X = build_feature_matrix(cto_df, cto_emb)

    union_df = pd.concat([hint_df, cto_df], ignore_index=True)
    union_X = np.concatenate([hint_X, cto_X], axis=0)

    log.info(
        "union: %d rows, %d train, %d valid, %d test",
        len(union_df),
        (union_df["split"] == "train").sum(),
        (union_df["split"] == "valid").sum(),
        (union_df["split"] == "test").sum(),
    )
    return union_df, union_X


# ---------------------------------------------------------------------------
# Training helpers (ported from train_gbt.py with phase-stratified additions)
# ---------------------------------------------------------------------------


def _train_early_stop_masks(
    splits: np.ndarray, y: np.ndarray, *, frac: float, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Carve a deterministic early-stop holdout from train rows (per v1.5.3.1)."""
    train_idx = np.flatnonzero(splits == "train")
    rng = np.random.default_rng(seed)
    early_parts = []
    y_train = y[train_idx]
    for label in np.unique(y_train):
        label_idx = train_idx[y_train == label]
        shuffled = rng.permutation(label_idx)
        n = max(1, int(np.ceil(len(shuffled) * frac)))
        n = min(n, len(shuffled) - 1)
        early_parts.append(shuffled[:n])
    early_idx = np.concatenate(early_parts)
    early_mask = np.zeros(len(splits), dtype=bool)
    early_mask[early_idx] = True
    fit_mask = splits == "train"
    fit_mask[early_mask] = False
    return fit_mask, early_mask


def _fit_lgbm(
    X_fit: np.ndarray,
    y_fit: np.ndarray,
    X_early: np.ndarray,
    y_early: np.ndarray,
    *,
    seed: int,
    tag: str = "",
) -> lgb.LGBMClassifier:
    """Fit one LGBMClassifier with early stopping. tag is for logging."""
    model = lgb.LGBMClassifier(random_state=seed, **LGBM_PARAMS)
    model.fit(
        X_fit, y_fit,
        eval_set=[(X_early, y_early)],
        callbacks=[lgb.early_stopping(25, verbose=False)],
    )
    log.info("  %s: fit done (%d iterations)", tag or "overall", model.best_iteration_)
    return model


def train_overall(
    X: np.ndarray,
    y: np.ndarray,
    splits: np.ndarray,
    *,
    seed: int,
    frac: float,
) -> tuple[lgb.LGBMClassifier, dict]:
    """Train the single overall fallback model on all phases combined."""
    fit_mask, early_mask = _train_early_stop_masks(splits, y, frac=frac, seed=seed)
    model = _fit_lgbm(
        X[fit_mask], y[fit_mask],
        X[early_mask], y[early_mask],
        seed=seed, tag="overall",
    )
    test_mask = splits == "test"
    y_pred = model.predict_proba(X[test_mask])[:, 1]
    auc = float(roc_auc_score(y[test_mask], y_pred))
    brier = float(brier_score_loss(y[test_mask], y_pred))
    log.info("overall → test AUC=%.4f Brier=%.4f", auc, brier)
    return model, {"overall_test_auc": auc, "overall_test_brier": brier}


def train_phase_models(
    X: np.ndarray,
    y: np.ndarray,
    phases: np.ndarray,
    splits: np.ndarray,
    *,
    seed: int,
    frac: float,
) -> tuple[dict[str, lgb.LGBMClassifier], dict[str, dict]]:
    """Train one LGBM per phase. Returns (models_dict, per_phase_metrics)."""
    phase_models: dict[str, lgb.LGBMClassifier] = {}
    phase_metrics: dict[str, dict] = {}

    for phase in CONFORMAL_PHASES:
        phase_mask = phases == phase
        n_phase = int(phase_mask.sum())
        if n_phase < 50:
            log.warning("phase %s: only %d rows — skipping phase model", phase, n_phase)
            continue

        Xp = X[phase_mask]
        yp = y[phase_mask]
        sp = splits[phase_mask]

        n_train = int((sp == "train").sum())
        n_val = int((sp == "valid").sum())
        n_test = int((sp == "test").sum())
        log.info(
            "phase %s: n=%d (train=%d val=%d test=%d) base_rate=%.3f",
            phase, n_phase, n_train, n_val, n_test, float(yp.mean()),
        )

        if n_train < 10 or len(np.unique(yp[sp == "train"])) < 2:
            log.warning("phase %s: train too small or one-class — skipping", phase)
            continue

        fit_mask_p, early_mask_p = _train_early_stop_masks(
            sp, yp, frac=frac, seed=seed,
        )
        pm = _fit_lgbm(
            Xp[fit_mask_p], yp[fit_mask_p],
            Xp[early_mask_p], yp[early_mask_p],
            seed=seed + hash(phase) % 1000, tag=phase,
        )
        phase_models[phase] = pm

        test_mask_p = sp == "test"
        if test_mask_p.sum() >= 2 and len(np.unique(yp[test_mask_p])) >= 2:
            yp_pred = pm.predict_proba(Xp[test_mask_p])[:, 1]
            auc = float(roc_auc_score(yp[test_mask_p], yp_pred))
            brier = float(brier_score_loss(yp[test_mask_p], yp_pred))
            log.info("  %s test: AUC=%.4f Brier=%.4f", phase, auc, brier)
            phase_metrics[phase] = {
                "n_train": n_train, "n_val": n_val, "n_test": n_test,
                "test_auc": auc, "test_brier": brier,
                "test_base_rate": float(yp[test_mask_p].mean()),
                "train_base_rate": float(yp[sp == "train"].mean()),
            }
        else:
            phase_metrics[phase] = {
                "n_train": n_train, "n_val": n_val, "n_test": n_test,
                "test_auc": None, "test_brier": None,
            }

    return phase_models, phase_metrics


# ---------------------------------------------------------------------------
# Conformal calibration (Mondrian, from train_gbt.py v1.5.3.1)
# ---------------------------------------------------------------------------


def _conformal_quantile(residuals: np.ndarray, alpha: float) -> float:
    n = len(residuals)
    if n == 0:
        raise ValueError("empty residual set")
    k = min(max(int(np.ceil((n + 1) * (1 - alpha))), 1), n)
    return float(np.sort(np.abs(residuals))[k - 1])


def compute_mondrian_radii(
    model_for_phase: lgb.LGBMClassifier,
    X_val: np.ndarray,
    y_val: np.ndarray,
    phases_val: np.ndarray,
    *,
    alpha: float = CONFORMAL_ALPHA,
    phase: str | None = None,
) -> tuple[dict[str, float], dict[str, int], float]:
    """Compute Mondrian conformal radii on the validation set.

    If `phase` is given, only that phase's residuals are used (for
    phase-specific models where all rows are the same phase, the
    'overall' radius is the only meaningful output).
    """
    pred = model_for_phase.predict_proba(X_val)[:, 1]
    residuals_all = np.abs(y_val.astype(float) - pred)
    radii: dict[str, float] = {}
    n_by_phase: dict[str, int] = {}

    phases_to_check = [phase] if phase else list(CONFORMAL_PHASES)
    for ph in phases_to_check:
        mask = phases_val == ph
        n = int(mask.sum())
        n_by_phase[ph] = n
        if n < 15:
            continue
        radii[ph] = _conformal_quantile(residuals_all[mask], alpha)

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
    pred = model.predict_proba(X_test)[:, 1]
    coverage: dict[str, float] = {}
    for ph in CONFORMAL_PHASES:
        mask = phases_test == ph
        if not mask.any():
            continue
        r = radii.get(ph, overall_radius)
        in_band = np.abs(y_test[mask].astype(float) - pred[mask]) <= r
        coverage[ph] = float(in_band.mean())
    in_band_all = [
        abs(float(y_test[i]) - pred[i]) <= radii.get(phases_test[i], overall_radius)
        for i in range(len(y_test))
    ]
    coverage["overall"] = float(np.mean(in_band_all))
    return coverage


# ---------------------------------------------------------------------------
# Bootstrap ensemble
# ---------------------------------------------------------------------------


def train_bootstrap(
    X: np.ndarray,
    y: np.ndarray,
    splits: np.ndarray,
    *,
    n: int,
    seed: int,
    frac: float,
) -> list[lgb.LGBMClassifier]:
    """Train n LGBM models on bootstrap resamples of train rows (on the full
    union corpus — same as v1.5.3 but on the larger dataset)."""
    fit_mask, early_mask = _train_early_stop_masks(splits, y, frac=frac, seed=seed)
    Xf, yf = X[fit_mask], y[fit_mask]
    Xe, ye = X[early_mask], y[early_mask]
    n_train = len(Xf)
    rng = np.random.default_rng(seed)
    models = []
    for i in range(n):
        idx = rng.integers(0, n_train, size=n_train)
        m = lgb.LGBMClassifier(random_state=seed + i + 1, **LGBM_PARAMS)
        m.fit(Xf[idx], yf[idx], eval_set=[(Xe, ye)],
              callbacks=[lgb.early_stopping(25, verbose=False)])
        log.info("  bootstrap %d/%d (n_iter=%d)", i + 1, n, m.best_iteration_)
        models.append(m)
    return models


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    parser.add_argument("--early-stop-frac", type=float, default=EARLY_STOP_FRAC)
    parser.add_argument("--n-bootstrap", type=int, default=N_BOOTSTRAP_MODELS)
    parser.add_argument("--skip-bootstrap", action="store_true")
    parser.add_argument(
        "--ship", action="store_true",
        help="After training, copy artifact to model.joblib (the live inference path)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    log.info("=== v1.5.6 Phase-stratified training on HINT ∪ CTO ===")
    union_df, union_X = load_union()

    y = union_df["label"].to_numpy(dtype=float)
    splits = union_df["split"].to_numpy()
    phases = union_df["phase"].to_numpy()

    log.info(
        "union: X=%s, train=%d val=%d test=%d label_rate=%.3f",
        union_X.shape, (splits == "train").sum(),
        (splits == "valid").sum(), (splits == "test").sum(), y.mean(),
    )

    # ---- 1. Overall fallback model ----------------------------------------
    log.info("\n[1/4] Training overall (fallback) model on all phases…")
    overall_model, overall_metrics = train_overall(
        union_X, y, splits, seed=args.seed, frac=args.early_stop_frac,
    )

    # ---- 2. Phase-stratified models ----------------------------------------
    log.info("\n[2/4] Training phase-stratified models (Ph1 / Ph2 / Ph3)…")
    phase_models, phase_metrics = train_phase_models(
        union_X, y, phases, splits,
        seed=args.seed, frac=args.early_stop_frac,
    )

    # ---- 3. Mondrian conformal (overall model on union val) -----------------
    log.info("\n[3/4] Computing Mondrian conformal radii on union val split…")
    val_mask = splits == "valid"
    test_mask = splits == "test"

    # Use the overall model for the global conformal calibration (most data;
    # phase models can use their own phase-specific val rows for finer radii).
    radii, n_cal, overall_radius = compute_mondrian_radii(
        overall_model, union_X[val_mask], y[val_mask], phases[val_mask],
        alpha=CONFORMAL_ALPHA,
    )
    coverage = compute_test_coverage(
        overall_model, union_X[test_mask], y[test_mask], phases[test_mask],
        radii, overall_radius,
    )
    log.info("conformal radii: %s", radii)
    log.info("conformal test coverage: %s", coverage)

    # Also compute per-phase conformal using phase-specific models on their
    # own val rows — this is the tighter, more principled estimate.
    phase_radii: dict[str, dict] = {}
    for ph, pm in phase_models.items():
        ph_mask = phases == ph
        ph_val = ph_mask & (splits == "valid")
        ph_test = ph_mask & (splits == "test")
        if ph_val.sum() < 5:
            continue
        r_ph, n_ph, r_ph_overall = compute_mondrian_radii(
            pm, union_X[ph_val], y[ph_val], phases[ph_val],
            alpha=CONFORMAL_ALPHA, phase=ph,
        )
        cov_ph = compute_test_coverage(
            pm, union_X[ph_test], y[ph_test], phases[ph_test],
            r_ph, r_ph_overall,
        ) if ph_test.sum() >= 2 else {}
        phase_radii[ph] = {
            "radius": r_ph.get(ph, r_ph_overall),
            "overall_radius": r_ph_overall,
            "n_calibration": n_ph,
            "test_coverage": cov_ph,
        }
        log.info("  phase %s conformal radius: %.4f (cov: %s)", ph,
                 phase_radii[ph]["radius"], cov_ph)

    # ---- 4. Bootstrap ensemble (overall model) ------------------------------
    boot_models: list[lgb.LGBMClassifier] = []
    avg_width: float | None = None
    if not args.skip_bootstrap:
        log.info("\n[4/4] Training %d bootstrap models (overall corpus)…", args.n_bootstrap)
        boot_models = train_bootstrap(
            union_X, y, splits,
            n=args.n_bootstrap, seed=args.seed, frac=args.early_stop_frac,
        )
        boot_preds = np.stack(
            [m.predict_proba(union_X[test_mask])[:, 1] for m in boot_models]
        )
        ql = np.quantile(boot_preds, 0.05, axis=0)
        qh = np.quantile(boot_preds, 0.95, axis=0)
        avg_width = float(np.mean(qh - ql))
        log.info("bootstrap avg band width on test: %.4f", avg_width)
    else:
        log.info("\n[4/4] Skipping bootstrap (--skip-bootstrap)")

    # ---- Compose final metrics dict ----------------------------------------
    test_auc = overall_metrics["overall_test_auc"]
    metrics = {
        "model_version": "v1.5.6",
        "model_kind": f"lightgbm_pubmedbert_phase_stratified_v1.5.6_{args.seed}",
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "feature_dim": int(union_X.shape[1]),
        "embedding_dim": EMBEDDING_DIM,
        "structured_dim": N_STRUCT_FEATURES,
        "n_train_hint": int((union_df["source_domain"] == "hint").sum()),
        "n_train_cto": int((union_df["source_domain"] == "cto").sum()),
        "n_union": len(union_df),
        "test_auc": test_auc,
        "test_brier": overall_metrics["overall_test_brier"],
        "conformal_test_coverage": coverage,
        "per_phase_metrics": phase_metrics,
    }
    if avg_width is not None:
        metrics["bootstrap_avg_band_width_test"] = avg_width
        metrics["bootstrap_n_models"] = args.n_bootstrap

    conformal_payload = {
        "alpha": CONFORMAL_ALPHA,
        "method": "split_conformal_mondrian_v156",
        "radii": radii,
        "overall_radius": overall_radius,
        "n_calibration": n_cal,
        "test_coverage": coverage,
        "calibration_split": "valid",
        "phase_radii": phase_radii,
    }

    feature_schema = {
        "n_features": COMBINED_DIM,
        "embedding_dim": EMBEDDING_DIM,
        "structured_dim": N_STRUCT_FEATURES,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "max_length": 512,
        "pool_method": "mean",
        "lightgbm_version_major": lgb.__version__.split(".")[0],
        "phase_order": [p.value for p in PHASE_ORDER],
        "therapeutic_areas": [t.value for t in THERAPEUTIC_AREAS],
        "modalities": [m.value for m in MODALITIES],
        "capital_positions": [c.value for c in CAPITAL_POSITIONS],
        "designation_flags": [d.value for d in DESIGNATION_FLAGS],
    }

    training_meta = {
        "sklearn_version": sklearn.__version__,
        "lightgbm_version": lgb.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": args.seed,
        "training_label_source": (
            "HINT (Fu et al. 2022) + CT Open v1.5.5 benchmark set (Gao et al. 2024). "
            "HINT: 11,552 rows. CTO: 2,429 rows (the trials that achieved external "
            "AUC 0.600 in v1.5.5 — now used for training per standard ML practice; "
            "the honest benchmark is permanently recorded in methodology/13). "
            "Architecture: one LGBM per phase (Ph1/Ph2/Ph3) + one global fallback."
        ),
        "phase_models": list(phase_models.keys()),
    }

    TRAINING_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "model": overall_model,
        "phase_models": phase_models,
        "metrics": metrics,
        "feature_schema": feature_schema,
        "conformal": conformal_payload,
        "training_meta": training_meta,
    }
    if boot_models:
        payload["bootstrap_models"] = boot_models

    joblib.dump(payload, MODEL_OUT)
    size_mb = MODEL_OUT.stat().st_size / 1e6
    log.info("\nArtifact written → %s (%.2f MB)", MODEL_OUT, size_mb)

    # ---- Per-phase test summary ----------------------------------------
    print("\n=== PER-PHASE TEST METRICS ===")
    for ph, m in phase_metrics.items():
        auc_str = f"{m['test_auc']:.4f}" if m["test_auc"] is not None else "N/A"
        print(
            f"  {ph}: AUC={auc_str}  n_test={m['n_test']}"
            f"  base_rate={m.get('test_base_rate', '?')}"
        )

    print("\n=== FINAL METRICS ===")
    for k, v in metrics.items():
        if isinstance(v, (dict, list)):
            continue
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    print(f"\nDoane 2025 HINT baseline AUC: 0.7404")
    print(f"v1.5.5 external CTO AUC:      0.6000 (benchmark, immutable)")
    if test_auc >= 0.80:
        print(f"✓ Overall test AUC {test_auc:.4f} >= 0.80 — credible improvement. SHIP.")
    elif test_auc >= 0.74:
        print(f"✓ Overall test AUC {test_auc:.4f} >= 0.74 — matches Doane baseline. SHIP.")
    elif test_auc >= SHIP_THRESHOLD:
        print(f"~ Overall test AUC {test_auc:.4f} in 0.70-0.74 — BORDERLINE SHIP.")
    else:
        print(f"⚠ Overall test AUC {test_auc:.4f} < {SHIP_THRESHOLD} — DO NOT SHIP.")

    if args.ship:
        import shutil
        shutil.copy(MODEL_OUT, MODEL_SHIP)
        log.info("Shipped → %s", MODEL_SHIP)
        print(f"\n✓ Shipped to {MODEL_SHIP}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
