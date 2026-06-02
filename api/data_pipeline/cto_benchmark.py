"""CT Open benchmark — held-out evaluation of the v1.5.x ML PoS Prior.

Stage 6 of the pipeline. Runs AFTER:
  - Stage 3: api/data/cto/metadata_cache.jsonl (CT.gov fetches)
  - Stage 4: api/data/cto/cto_embeddings.npy + cto_embeddings_nctid.txt
             (PubMedBERT embeddings from the Colab notebook)
  - The current shipping artifact at
    api/app/modules/ml_pos_prior/model.joblib (or model_v152.joblib)

Computes:
  - Overall AUC + Brier on the uncontaminated 2,429-trial held-out set
  - Per-phase AUC + Brier (phase_1, phase_2, phase_3)
  - Comparison to internal HINT-test AUC (typically 0.7030) and to
    Doane 2025 baseline (0.7404)
  - Calibration: predicted probability vs observed success rate, binned

Output: prints summary to stdout + writes
api/data/cto/benchmark_results.json with structured metrics.

Run with:
  cd api && python -m data_pipeline.cto_benchmark
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np

# Make app/ importable for the structured-feature encoder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.ml_pos_prior.features import (  # noqa: E402
    N_FEATURES as N_STRUCT_FEATURES,
    encode,
)
from sklearn.metrics import brier_score_loss, roc_auc_score  # noqa: E402

from .cto_acquire import load_uncontaminated_test_set
from .cto_derive_features import derive_from_cto_row
from .cto_fetch_metadata import CtGovMetadata

log = logging.getLogger(__name__)

API_DIR = Path(__file__).resolve().parent.parent
CTO_DIR = API_DIR / "data" / "cto"
METADATA_CACHE = CTO_DIR / "metadata_cache.jsonl"
EMBEDDINGS_NPY = CTO_DIR / "cto_embeddings.npy"
EMBEDDINGS_NCTIDS = CTO_DIR / "cto_embeddings_nctid.txt"
MODEL_ARTIFACT = API_DIR / "app" / "modules" / "ml_pos_prior" / "model.joblib"
RESULTS_OUT = CTO_DIR / "benchmark_results.json"

EMBEDDING_DIM = 768
COMBINED_DIM = EMBEDDING_DIM + N_STRUCT_FEATURES  # 768 + 36 = 804


def _load_metadata_cache(path: Path) -> dict[str, CtGovMetadata]:
    """Read the JSONL cache produced by cto_fetch_batch.py back into a
    dict keyed by NCT ID. Reconstructs a partial CtGovMetadata (without
    the raw field, which the runner didn't persist for size reasons)."""
    if not path.exists():
        raise FileNotFoundError(
            f"Stage 3 output not found at {path}. "
            f"Run `python -m data_pipeline.cto_fetch_batch` first."
        )
    out: dict[str, CtGovMetadata] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            out[record["nct_id"].upper()] = CtGovMetadata(
                nct_id=record["nct_id"],
                eligibility_criteria=record.get("eligibility_criteria"),
                conditions=record.get("conditions", []),
                intervention_types=record.get("intervention_types", []),
                intervention_names=record.get("intervention_names", []),
                mesh_terms=record.get("mesh_terms", []),
                enrollment_count=record.get("enrollment_count"),
                raw={},
            )
    log.info("loaded %d cached metadata records", len(out))
    return out


def _load_embeddings(npy: Path, nctids: Path) -> dict[str, np.ndarray]:
    """Load Colab-produced embeddings + sidecar, return dict keyed by
    NCT ID. Both files must be the Stage 4 output downloaded from the
    PubMedBERT Colab notebook."""
    if not npy.exists() or not nctids.exists():
        raise FileNotFoundError(
            f"Stage 4 outputs not found. Expected:\n"
            f"  {npy}\n  {nctids}\n"
            f"Run api/data_pipeline/notebooks/cto_pubmedbert_embed_colab.ipynb "
            f"on Colab and drop the outputs in api/data/cto/."
        )
    arr = np.load(npy)
    if arr.shape[1] != EMBEDDING_DIM:
        raise ValueError(
            f"embeddings shape mismatch: got {arr.shape}, "
            f"expected (*, {EMBEDDING_DIM})"
        )
    ids = nctids.read_text(encoding="utf-8").strip().split("\n")
    if len(ids) != arr.shape[0]:
        raise ValueError(
            f"NCT ID count {len(ids)} != embeddings row count {arr.shape[0]}"
        )
    return {ids[i].upper(): arr[i] for i in range(len(ids))}


def _load_model() -> tuple[object, dict, dict]:
    """Load the current v1.5.x artifact. Returns (model, metrics,
    feature_schema). The benchmark script reads model_kind +
    embedding_model_id from `metrics` (NOT `feature_schema`) — that's
    where the trainer's save_artifact actually writes them. Returning
    both dicts here lets the caller pull from whichever is appropriate."""
    if not MODEL_ARTIFACT.exists():
        raise FileNotFoundError(f"model artifact not found at {MODEL_ARTIFACT}")
    artifact = joblib.load(MODEL_ARTIFACT)
    return (
        artifact["model"],
        artifact.get("metrics", {}),
        artifact.get("feature_schema", {}),
    )


def _build_feature_vector(
    embedding: np.ndarray,
    structured: np.ndarray,
) -> np.ndarray:
    """Concatenate PubMedBERT embedding + structured features into the
    804-dim vector the LightGBM expects."""
    if embedding.shape != (EMBEDDING_DIM,):
        raise ValueError(f"embedding shape {embedding.shape}")
    if structured.shape != (N_STRUCT_FEATURES,):
        raise ValueError(f"structured shape {structured.shape}")
    return np.concatenate([embedding, structured])


def _per_phase_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    phases: np.ndarray,
) -> dict[str, dict[str, float | int]]:
    """Group AUC + Brier by phase."""
    out: dict[str, dict[str, float | int]] = {}
    for phase in ("phase_1", "phase_2", "phase_3"):
        mask = phases == phase
        n = int(mask.sum())
        if n < 10 or len(np.unique(y_true[mask])) < 2:
            out[phase] = {"n": n, "auc": None, "brier": None}
            continue
        out[phase] = {
            "n": n,
            "auc": float(roc_auc_score(y_true[mask], y_pred[mask])),
            "brier": float(brier_score_loss(y_true[mask], y_pred[mask])),
            "base_rate": float(y_true[mask].mean()),
        }
    return out


def run() -> dict:
    """Top-level benchmark runner. Returns a stats dict."""
    log.info("loading uncontaminated CTO test set…")
    acquired = load_uncontaminated_test_set()
    test_df = acquired.uncontaminated.copy()
    test_df["nct_id"] = test_df["nct_id"].str.upper()
    log.info("uncontaminated test set: %d trials", len(test_df))

    log.info("loading Stage 3 metadata cache…")
    metadata = _load_metadata_cache(METADATA_CACHE)

    log.info("loading Stage 4 embeddings…")
    embeddings = _load_embeddings(EMBEDDINGS_NPY, EMBEDDINGS_NCTIDS)

    log.info("loading model artifact…")
    model, metrics, schema = _load_model()
    log.info(
        "model_kind: %s, embedding_model_id: %s",
        metrics.get("model_kind", "unknown"),
        schema.get("embedding_model_id", "unknown"),
    )

    # Build feature matrix; skip trials missing metadata or embeddings
    rows: list[tuple[str, str, int, float]] = []
    skipped = {"no_metadata": 0, "no_embedding": 0, "derivation_failed": 0}

    for _, row in test_df.iterrows():
        nct = row["nct_id"]
        meta = metadata.get(nct)
        if meta is None:
            skipped["no_metadata"] += 1
            continue
        emb = embeddings.get(nct)
        if emb is None:
            skipped["no_embedding"] += 1
            continue
        derivation = derive_from_cto_row(row.to_dict(), meta)
        if derivation is None:
            skipped["derivation_failed"] += 1
            continue
        struct = encode(derivation.asset)
        x = _build_feature_vector(emb, struct).reshape(1, -1).astype(np.float32)
        proba = float(model.predict_proba(x)[0, 1])
        rows.append((nct, row["phase_normalized"], derivation.label, proba))

    log.info("scored %d trials; skipped %s", len(rows), skipped)
    if not rows:
        raise RuntimeError("no trials scored — check Stage 3 + 4 outputs")

    phase_arr = np.array([r[1] for r in rows])
    y_true = np.array([r[2] for r in rows], dtype=float)
    y_pred = np.array([r[3] for r in rows], dtype=float)

    overall_auc = float(roc_auc_score(y_true, y_pred))
    overall_brier = float(brier_score_loss(y_true, y_pred))
    per_phase = _per_phase_metrics(y_true, y_pred, phase_arr)

    results = {
        "model_kind": metrics.get("model_kind", "unknown"),
        "embedding_model_id": schema.get(
            "embedding_model_id", "microsoft/BiomedNLP-PubMedBERT-..."
        ),
        "test_set": "CTO human_labels_2020_2024, phase_1/2/3, "
        "completion_year >= 2023, not in HINT (uncontaminated)",
        "n_scored": len(rows),
        "skipped": skipped,
        "overall": {
            "n": len(rows),
            "auc": overall_auc,
            "brier": overall_brier,
            "base_rate": float(y_true.mean()),
        },
        "per_phase": per_phase,
        "reference": {
            "hint_internal_test_auc": 0.7030,
            "doane_2025_baseline_auc": 0.7404,
        },
    }

    log.info("=== Benchmark results ===")
    log.info("Overall AUC: %.4f  Brier: %.4f  (n=%d, base=%.3f)",
             overall_auc, overall_brier, len(rows), y_true.mean())
    for phase, m in per_phase.items():
        if m.get("auc") is None:
            log.info("  %s: n=%d (skipped — too few or one-class)", phase, m["n"])
        else:
            log.info("  %s: AUC=%.4f Brier=%.4f n=%d base=%.3f",
                     phase, m["auc"], m["brier"], m["n"], m["base_rate"])
    log.info("Reference: HINT-internal-test AUC 0.7030, Doane 2025 baseline AUC 0.7404")

    RESULTS_OUT.write_text(json.dumps(results, indent=2))
    log.info("wrote results to %s", RESULTS_OUT)
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    run()
