"""v1.5.9 — per-phase isotonic calibrators for the shipped ML PoS Prior.

Discovery from the Phase-2 error analysis (methodology/17): the v1.5.6
shipped model systematically over-predicts success on held-out CTO by
+12-15pp across all three phases. Root cause: training set is
HINT-dominated (5489 of 6179 Phase-2 rows, success rate 49%) but the
CTO held-out distribution is 23%. The model learned the HINT prior.

Post-hoc isotonic regression on the CTO valid split (the only data the
model never trained on AND which matches the modern post-2023 trial
distribution) corrects this without retraining. Isotonic is monotonic,
so the existing bootstrap-percentile bands transform endpoint-for-
endpoint and retain their coverage guarantee.

What this script does:
  1. Load the shipped model.joblib
  2. For each phase ∈ {phase_1, phase_2, phase_3}:
       - Pull raw model predictions on that phase's CTO valid rows
       - Fit IsotonicRegression(out_of_bounds='clip') mapping raw → truth
       - Record train+valid Brier before/after to confirm improvement
  3. Append `calibrators: {phase_x: IsotonicRegression}` to the model
     artifact and rewrite it.

The engine's _load_model picks up the new key on next start (it's optional;
absent → legacy raw-prediction path, fully backward-compatible).

Run with:
    python scripts/fit_isotonic_calibrators.py            # writes back to live artifact
    python scripts/fit_isotonic_calibrators.py --dry-run  # show diagnostics, don't write
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

# Make app/ importable without changing CWD
REPO_ROOT = Path(__file__).resolve().parent.parent
API_DIR = REPO_ROOT / "api"
sys.path.insert(0, str(API_DIR))

from sklearn.isotonic import IsotonicRegression  # noqa: E402
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402

warnings.filterwarnings("ignore")

MODEL_PATH = API_DIR / "app" / "modules" / "ml_pos_prior" / "model.joblib"
HINT_PARQUET = API_DIR / "data" / "training" / "training_dataset.parquet"
CTO_PARQUET = API_DIR / "data" / "training" / "cto_training_dataset.parquet"
CTO_EMB_NPY = API_DIR / "data" / "cto" / "cto_embeddings.npy"
CTO_EMB_IDS = API_DIR / "data" / "cto" / "cto_embeddings_nctid.txt"

PHASES = ("phase_1", "phase_2", "phase_3")


def _build_x(df: pd.DataFrame, emb: np.ndarray, lookup: dict[str, int]) -> np.ndarray:
    e = np.array([emb[lookup[n.upper()]] for n in df["nctid"]])
    s = np.array(df["feature_vector"].tolist(), dtype=np.float32)
    return np.concatenate([e, s], axis=1).astype(np.float32)


def fit_calibrators(*, dry_run: bool = False) -> dict[str, IsotonicRegression]:
    """Fit per-phase isotonic calibrators on the CTO valid split.

    Returns the dict {phase: IsotonicRegression} so the caller can also
    inspect / test the fit (the dry-run flag short-circuits the artifact
    rewrite step but still returns the fitted objects).
    """
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"model artifact not found at {MODEL_PATH}")

    artifact = joblib.load(MODEL_PATH)
    phase_models = artifact.get("phase_models") or {}
    if not phase_models:
        raise RuntimeError(
            "shipped model has no phase_models — isotonic-per-phase requires "
            "the v1.5.6+ phase-stratified architecture",
        )

    print(f"loaded {artifact['metrics'].get('model_kind')}")
    print(f"  phase models: {sorted(phase_models)}")

    cto = pd.read_parquet(CTO_PARQUET)
    emb = np.load(CTO_EMB_NPY)
    ids = CTO_EMB_IDS.read_text().strip().split()
    lk = {n.upper(): i for i, n in enumerate(ids)}

    calibrators: dict[str, IsotonicRegression] = {}
    print()
    print(
        f'{"phase":<10}{"n_valid":>9}{"raw_mean":>10}{"actual":>9}'
        f'{"raw_Brier":>11}{"cal_Brier":>11}{"raw_AUC":>10}{"cal_AUC":>10}'
    )
    print("-" * 80)

    for ph in PHASES:
        valid = cto[(cto["phase"] == ph) & (cto["split"] == "valid")].reset_index(drop=True)
        test = cto[(cto["phase"] == ph) & (cto["split"] == "test")].reset_index(drop=True)
        if len(valid) < 30:
            print(f"  {ph}: only {len(valid)} valid rows — skipping (< 30 minimum)")
            continue

        Xv = _build_x(valid, emb, lk)
        Xt = _build_x(test, emb, lk)
        yv = valid["label"].to_numpy(dtype=float)
        yt = test["label"].to_numpy(dtype=float)

        pm = phase_models[ph]
        raw_v = pm.predict_proba(Xv)[:, 1]
        raw_t = pm.predict_proba(Xt)[:, 1]

        # Fit isotonic on valid (the only CTO data the LightGBM never saw)
        iso = IsotonicRegression(out_of_bounds="clip").fit(raw_v, yv)
        cal_v = iso.predict(raw_v)
        cal_t = iso.predict(raw_t)

        # Report on the test split — the held-out external measure
        br_raw = brier_score_loss(yt, raw_t)
        br_cal = brier_score_loss(yt, cal_t)
        try:
            auc_raw = roc_auc_score(yt, raw_t)
            auc_cal = roc_auc_score(yt, cal_t)
        except ValueError:
            auc_raw = float("nan")
            auc_cal = float("nan")

        print(
            f"{ph:<10}{len(valid):>9}{raw_t.mean():>10.3f}{yt.mean():>9.3f}"
            f"{br_raw:>11.4f}{br_cal:>11.4f}{auc_raw:>10.3f}{auc_cal:>10.3f}"
        )
        calibrators[ph] = iso

    if dry_run:
        print("\n(dry-run) — not writing artifact")
        return calibrators

    # Write back to the artifact. Use a temp file + rename for atomicity.
    artifact["calibrators"] = calibrators
    # Mark the calibration metadata so the engine can log + the methodology
    # writeup can be reproduced.
    artifact_calib_meta = {
        "method": "isotonic_regression",
        "fit_on": "cto_valid_per_phase",
        "out_of_bounds": "clip",
        "n_fit_per_phase": {
            ph: int(((cto["phase"] == ph) & (cto["split"] == "valid")).sum())
            for ph in PHASES
        },
    }
    artifact["calibration_meta"] = artifact_calib_meta

    tmp = MODEL_PATH.with_suffix(".joblib.tmp")
    joblib.dump(artifact, tmp)
    tmp.replace(MODEL_PATH)
    print(f"\nwrote calibrators back to {MODEL_PATH}")
    print(f"new artifact size: {MODEL_PATH.stat().st_size / 1e6:.2f} MB")
    return calibrators


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="Fit + show metrics, but don't write the artifact.")
    args = ap.parse_args(argv)
    fit_calibrators(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
