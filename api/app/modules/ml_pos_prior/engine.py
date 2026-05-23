"""ML PoS Prior — inference engine (rule-smoothed logistic surrogate).

Loads the pickled artifact lazily on first call. Inference is ~1ms per
record. The artifact includes a feature-schema sidecar (n_features +
phase/TA/modality/capital_position enum-value lists at training time);
this is validated against the runtime encoder so a sklearn or domain-
enum change cannot silently produce a wrong feature mapping.

If the artifact is missing or fails schema validation, the engine raises
HTTPException(503) — not a raw 500 — so the route surface is graceful.

The uncertainty band is a fixed heuristic (±1 in logit space), not a
statistical CI. Field names in the schema were renamed in v1.5.1.1 to
reflect this — see schemas.py for the discussion.
"""

from __future__ import annotations

import logging
import math
from functools import lru_cache
from pathlib import Path

import joblib
from fastapi import HTTPException

from ...domain import DiligenceRecord
from .features import (
    CAPITAL_POSITIONS,
    MODALITIES,
    N_FEATURES,
    PHASE_ORDER,
    THERAPEUTIC_AREAS,
    encode,
)
from .schemas import DisagreementLevel, MLPosPriorResult

log = logging.getLogger(__name__)

MODEL_PATH = Path(__file__).parent / "model.joblib"

# Epsilon clipping on predict_proba to avoid logit(0) / logit(1) issues
# when sklearn returns exact endpoints (model-artifact and version dependent).
PROBA_EPS = 1e-6

# Fixed-width heuristic uncertainty band (±SE_HEURISTIC in logit space).
# Replace with a proper coverage interval in v1.5.2.
SE_HEURISTIC = 0.30


@lru_cache(maxsize=1)
def _load_model():
    """Lazy load — keeps module import cheap until the engine first runs."""
    if not MODEL_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "ML PoS Prior model artifact not present on this deploy. "
                "Run `python -m app.modules.ml_pos_prior.train` to fit it."
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

    # Feature-schema validation: the artifact records the enum value-lists
    # active at training time. If the runtime encoder doesn't match, the
    # learned coefficients map to the wrong features — fail loud.
    schema = artifact.get("feature_schema")
    if schema is None or schema.get("n_features") != N_FEATURES:
        raise HTTPException(
            status_code=503,
            detail=(
                "ML PoS Prior artifact feature schema does not match the "
                "runtime encoder. Re-train via "
                "`python -m app.modules.ml_pos_prior.train`."
            ),
        )
    if (
        schema.get("phase_order") != [p.value for p in PHASE_ORDER]
        or schema.get("therapeutic_areas") != [t.value for t in THERAPEUTIC_AREAS]
        or schema.get("modalities") != [m.value for m in MODALITIES]
        or schema.get("capital_positions") != [c.value for c in CAPITAL_POSITIONS]
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
    """Public accessor for the /model_info route — surfaces training metrics
    without exposing model weights."""
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
    # Guarantee enclosure: rounding/eps clipping shouldn't violate the
    # invariant the schema validator checks.
    return min(lo, p), max(hi, p)


def compute(record: DiligenceRecord) -> MLPosPriorResult:
    """Required entrypoint."""
    model, metrics = _load_model()
    x = encode(record.asset).reshape(1, -1)
    assert x.shape == (1, N_FEATURES), f"feature shape mismatch: {x.shape}"

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
        n_features=N_FEATURES,
    )
