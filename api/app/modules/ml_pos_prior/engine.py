"""ML PoS Prior — v1.5.2 inference engine.

The v1.5.1.1 inference path was structured-features-only (36-dim).
v1.5.2 adds PubMedBERT pooled embeddings of the eligibility-criteria
text → concatenated with the 36-dim structured features → 804-dim
combined → LightGBM classifier (trained on real HINT outcomes).

Engine responsibilities:
  - Load the v0.2.0 model artifact lazily; validate its feature_schema
    against runtime encoder + tokenizer + pool method.
  - For each request, resolve criteria text via:
      (1) explicit `criteria_text` field, or
      (2) fetch from ClinicalTrials.gov v2 if `nct_id` was supplied, or
      (3) raise ValueError → translated to HTTPException(422) by the route.
  - Embed criteria text via PubMedBERT (in-container; see bert_embed.py).
  - Concatenate with 36-dim structured features.
  - Predict via LightGBM; return MLPosPriorResult.

Cached predictions are served by the agent caches, NOT by this engine —
the engine runs only on live requests. (See app/agents/* for the cache
serving pattern.) That means cache regeneration (Day 4 Phase 4C) is
what materializes v1.5.2 predictions for known assets; this engine
handles only the "novel input from the UI" path.

Schema validation is unchanged in spirit from v1.5.1.1 but now includes
v0.2.0-specific fields:
  - n_features == 804 (was 36)
  - embedding_model_id matches bert_embed.MODEL_ID
  - max_length matches bert_embed.MAX_LENGTH
  - pool_method matches bert_embed.POOL_METHOD
  - lightgbm_version matches the runtime lightgbm import (best-effort
    string compare; minor-version mismatches log warning but proceed)
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
from fastapi import HTTPException

from ...domain import DiligenceRecord, Phase
from . import bert_embed
from .ctgov_fetch import CtGovFetchError, fetch_eligibility_criteria
from .features import (
    CAPITAL_POSITIONS,
    DESIGNATION_FLAGS,
    MODALITIES,
    N_FEATURES as N_STRUCT_FEATURES,
    PHASE_ORDER,
    THERAPEUTIC_AREAS,
    encode,
)
from .schemas import DisagreementLevel, MLPosPriorResult

log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "model.joblib"
CACHE_DIR = Path(__file__).parent / "cache"

# v1.5.2 Day 4 (Phase 4C / Codex remediation): the engine serves cached
# predictions for known assets without running PubMedBERT inference,
# mirroring the agent-cache pattern. v1.5.2.1 (this commit) fixes two
# Codex review findings:
#   1. Cache discovery is now filesystem-based (any `cache/<slug>.json`
#      present is a valid cache; no hardcoded frozenset). Simpler;
#      adding a new cached asset is a drop-in JSON file.
#   2. Cache hits verify a feature_fingerprint hash before returning,
#      so a request with a modified asset (e.g., user dragged a slider)
#      falls through to live inference instead of silently serving a
#      stale precomputed prediction.

# v1.5.2: combined dim = 768 (PubMedBERT) + 36 (structured)
EXPECTED_COMBINED_DIM = bert_embed.EMBEDDING_DIM + N_STRUCT_FEATURES

# Epsilon clipping on predict_proba to avoid logit(0)/logit(1) edge cases
PROBA_EPS = 1e-6

# Fixed-width heuristic uncertainty band (±SE_HEURISTIC in logit space).
# Replace with bootstrap or x'Cov(beta)x in v1.5.3.
SE_HEURISTIC = 0.30


@lru_cache(maxsize=1)
def _load_model():
    """Lazy load + validate. Returns (model, metrics)."""
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "ML PoS Prior model artifact not present on this deploy. "
                "Run the v1.5.2 training pipeline (api/data_pipeline/) "
                "and copy data/training/model_v152.joblib here."
            ),
        )
    try:
        artifact = joblib.load(MODEL_PATH)
    except Exception as exc:
        log.exception("failed to load ml_pos_prior model artifact")
        raise HTTPException(
            status_code=503,
            detail=f"ML PoS Prior artifact unreadable: {exc}",
        ) from exc

    if "model" not in artifact or "metrics" not in artifact:
        raise HTTPException(
            status_code=503,
            detail=(
                "ML PoS Prior artifact is missing required keys "
                "('model', 'metrics'). Re-train via the data_pipeline."
            ),
        )

    # v0.2.0 schema validation — the trained model's feature space must
    # match the runtime encoder + embedder exactly.
    schema = artifact.get("feature_schema") or {}

    if schema.get("n_features") != EXPECTED_COMBINED_DIM:
        raise HTTPException(
            status_code=503,
            detail=(
                f"ML PoS Prior artifact n_features "
                f"{schema.get('n_features')} != expected "
                f"{EXPECTED_COMBINED_DIM} (768 PubMedBERT + 36 structured). "
                f"Re-train against the v1.5.2 pipeline."
            ),
        )
    if schema.get("embedding_model_id") != bert_embed.MODEL_ID:
        raise HTTPException(
            status_code=503,
            detail=(
                f"ML PoS Prior artifact embedding_model_id "
                f"{schema.get('embedding_model_id')!r} != runtime "
                f"{bert_embed.MODEL_ID!r}. Re-train with the matching "
                f"embedding model or update bert_embed.MODEL_ID."
            ),
        )
    if schema.get("max_length") != bert_embed.MAX_LENGTH:
        raise HTTPException(
            status_code=503,
            detail=(
                f"ML PoS Prior artifact max_length "
                f"{schema.get('max_length')!r} != runtime "
                f"{bert_embed.MAX_LENGTH!r} — tokenization mismatch."
            ),
        )
    if schema.get("pool_method") != bert_embed.POOL_METHOD:
        raise HTTPException(
            status_code=503,
            detail=(
                f"ML PoS Prior artifact pool_method "
                f"{schema.get('pool_method')!r} != runtime "
                f"{bert_embed.POOL_METHOD!r}."
            ),
        )
    # v1.5.2.1 (Codex Day 4 MINOR #5): validate the lightgbm major version
    # matches between training and runtime. joblib pickle compatibility
    # across LightGBM major versions is not guaranteed; minor-version drift
    # is fine. Missing field is permitted for backward compat with
    # artifacts trained before this check was added.
    schema_lgbm_major = schema.get("lightgbm_version_major")
    if schema_lgbm_major and schema_lgbm_major != "unknown":
        try:
            import lightgbm as _lgb

            runtime_major = _lgb.__version__.split(".")[0]
            if runtime_major != schema_lgbm_major:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"ML PoS Prior artifact trained on LightGBM major "
                        f"{schema_lgbm_major}, runtime has major "
                        f"{runtime_major}. Re-train against the runtime "
                        f"LightGBM version."
                    ),
                )
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="ML PoS Prior runtime missing lightgbm dependency.",
            ) from None

    # Structured-feature categorical schema must still match runtime enums
    if (
        schema.get("phase_order") != [p.value for p in PHASE_ORDER]
        or schema.get("therapeutic_areas") != [t.value for t in THERAPEUTIC_AREAS]
        or schema.get("modalities") != [m.value for m in MODALITIES]
        or schema.get("capital_positions") != [c.value for c in CAPITAL_POSITIONS]
        or schema.get("designation_flags") != [d.value for d in DESIGNATION_FLAGS]
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "ML PoS Prior artifact's categorical schema does not match "
                "the runtime domain enums. Re-train to regenerate the "
                "model and feature schema."
            ),
        )

    return artifact["model"], artifact["metrics"]


def get_model_metrics() -> dict:
    """Public accessor for the /model_info route."""
    _, metrics = _load_model()
    return metrics


def _disagreement_level(gap_pp: float) -> DisagreementLevel:
    absgap = abs(gap_pp)
    if absgap < 3.0:
        return "aligned"
    if absgap < 7.0:
        return "moderate"
    return "divergent"


def _logit_band(p: float, se: float = SE_HEURISTIC) -> tuple[float, float]:
    """Map a point estimate to a fixed-width heuristic band in logit space."""
    p_clipped = min(max(p, PROBA_EPS), 1.0 - PROBA_EPS)
    logit = math.log(p_clipped / (1.0 - p_clipped))
    lo = 1.0 / (1.0 + math.exp(-(logit - se)))
    hi = 1.0 / (1.0 + math.exp(-(logit + se)))
    return min(lo, p), max(hi, p)


def _resolve_criteria_text(
    *, criteria_text: str | None, nct_id: str | None
) -> str:
    """Pick the source of criteria text for the BERT embedding step.

    Order:
      1. Explicit `criteria_text` (most direct; what the cached path uses)
      2. Fetch from ClinicalTrials.gov v2 via `nct_id`
      3. Raise ValueError → route translates to HTTPException(422)
    """
    if criteria_text and criteria_text.strip():
        return criteria_text.strip()

    if nct_id and nct_id.strip():
        try:
            return fetch_eligibility_criteria(nct_id.strip())
        except CtGovFetchError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"could not fetch criteria from ClinicalTrials.gov: {exc}",
            ) from exc

    raise ValueError(
        "ML PoS Prior requires eligibility-criteria text to embed. "
        "Supply `criteria_text` directly, or `nct_id` to fetch from "
        "ClinicalTrials.gov v2."
    )


def _slugify_asset_name(name: str) -> str:
    """Mirrors the agent-cache slug rule (app/utils/text.py:slugify_asset_name)."""
    cleaned = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
    return cleaned or "unnamed"


def compute_feature_fingerprint(record: DiligenceRecord) -> str:
    """Hash of the structured-feature encoding of the asset.

    A cached prediction is only valid for a request whose AssetInput
    encodes to the same 36-dim structured vector that was used at
    cache-gen time. If the user dragged a slider, changed phase, etc.,
    the fingerprint mismatches and the engine falls through to the
    live path (Codex Day 4 MAJOR finding #2).

    Uses SHA-256 truncated to 16 hex chars (64-bit collision resistance —
    overkill for the cache-key use, but cheap).
    """
    try:
        x = encode(record.asset)
    except Exception:
        # If the runtime encoder can't encode the asset, there's no way
        # a cache entry would be valid. Return a sentinel that can't
        # match any cache fingerprint.
        return "uncomputable"
    return hashlib.sha256(x.tobytes()).hexdigest()[:16]


def _list_cached_slugs() -> set[str]:
    """Discover cached assets from the filesystem. Any `cache/<slug>.json`
    present is treated as cached; no hardcoded frozenset (Codex Day 4
    NIT finding #7)."""
    if not CACHE_DIR.is_dir():
        return set()
    return {p.stem for p in CACHE_DIR.glob("*.json")}


def _maybe_cached(record: DiligenceRecord) -> MLPosPriorResult | None:
    """Cache-first read. Returns None if:
      - no cache file for this asset's slug exists, OR
      - the cache file is unreadable / malformed, OR
      - the cache file's feature_fingerprint doesn't match the request

    In all three cases the caller falls through to the live ML path.
    """
    slug = _slugify_asset_name(record.asset.asset_name)
    if slug not in _list_cached_slugs():
        return None
    cache_path = CACHE_DIR / f"{slug}.json"
    try:
        payload = json.loads(cache_path.read_text())
    except Exception as exc:
        log.warning("ml_pos_prior cache unreadable for %s: %s", slug, exc)
        return None

    # Verify the request's structured features match what was cached.
    # Codex Day 4 MAJOR #2: cache by slug alone could serve stale predictions
    # when the user changed any asset field. Requiring a fingerprint match
    # makes the cache safe to drag-slider-and-watch-it-update.
    cached_fp = payload.get("feature_fingerprint")
    runtime_fp = compute_feature_fingerprint(record)
    if cached_fp is None:
        log.warning(
            "ml_pos_prior cache for %s missing feature_fingerprint — "
            "treating as stale and falling through to live path", slug,
        )
        return None
    if cached_fp != runtime_fp:
        log.info(
            "ml_pos_prior cache miss for %s: fingerprint %s != cache %s "
            "(asset fields changed since cache-gen)",
            slug, runtime_fp, cached_fp,
        )
        return None

    try:
        # The cache stores model outputs; re-derive `rule_based_pos` and
        # `disagreement_pp` against the live PoS so the panel's
        # disagreement chip updates as the user drags the PoS slider.
        ml_pred = float(payload["predicted_pos"])
        rule_based = record.pos.final_loa if record.pos else 0.0
        gap_pp = (ml_pred - rule_based) * 100.0
        return MLPosPriorResult(
            predicted_pos=ml_pred,
            uncertainty_low=float(payload["uncertainty_low"]),
            uncertainty_high=float(payload["uncertainty_high"]),
            rule_based_pos=rule_based,
            disagreement_pp=round(gap_pp, 2),
            disagreement_level=_disagreement_level(gap_pp),
            model_kind=payload["model_kind"],
            n_features=int(payload["n_features"]),
        )
    except (KeyError, ValueError) as exc:
        log.warning("ml_pos_prior cache payload malformed for %s: %s", slug, exc)
        return None


def compute(
    record: DiligenceRecord,
    *,
    criteria_text: str | None = None,
    nct_id: str | None = None,
) -> MLPosPriorResult:
    """Required entrypoint. v1.5.2 signature: takes optional criteria_text
    + nct_id; one of them must resolve to non-empty text for the live
    ML path. Cache-first: if record.asset.asset_name is in the cached set
    AND its JSON file exists + parses, return the cached prediction
    re-keyed to the current PoS for an up-to-date disagreement-pp.

    Defense-in-depth: Phase.APPROVED rejected here (engine layer) AND at
    the route layer (Codex F6 from v1.6 review)."""
    if record.asset.phase == Phase.APPROVED:
        raise ValueError(
            "ML PoS Prior is fit on pre-approval transitions only; "
            "Phase.APPROVED assets are out of the training distribution."
        )

    cached = _maybe_cached(record)
    if cached is not None:
        return cached

    model, metrics = _load_model()

    # Build combined feature vector: [PubMedBERT 768] + [structured 36] = 804
    text = _resolve_criteria_text(criteria_text=criteria_text, nct_id=nct_id)
    embedding = bert_embed.embed_text(text)
    structured = encode(record.asset)
    x = np.concatenate([embedding, structured]).reshape(1, -1).astype(np.float32)

    if x.shape != (1, EXPECTED_COMBINED_DIM):
        # Should be unreachable given the schema validation in _load_model,
        # but assert defensively rather than silently feeding the wrong
        # shape into LightGBM
        raise HTTPException(
            status_code=503,
            detail=(
                f"feature vector shape {x.shape} != expected "
                f"(1, {EXPECTED_COMBINED_DIM}); refusing to predict on "
                f"misaligned input"
            ),
        )

    predicted = float(model.predict_proba(x)[0, 1])
    p_lo, p_hi = _logit_band(predicted)

    rule_based = record.pos.final_loa if record.pos else 0.0
    gap_pp = (predicted - rule_based) * 100.0

    return MLPosPriorResult(
        predicted_pos=predicted,
        uncertainty_low=p_lo,
        uncertainty_high=p_hi,
        rule_based_pos=rule_based,
        disagreement_pp=round(gap_pp, 2),
        disagreement_level=_disagreement_level(gap_pp),
        model_kind=metrics["model_kind"],
        n_features=EXPECTED_COMBINED_DIM,
    )
