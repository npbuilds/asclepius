"""Feature engineering for the ML PoS Prior classifier.

Same code is called by `train.py` (to generate the training set) and by
`engine.py` (to encode at inference). Keeping it in one module is the
only way to guarantee the model's feature space matches inference.

Feature vector layout — fixed-length, no model-side encoder needed:

  [0]      phase_ordinal              0=preclinical … 5=approved
  [1..11]  therapeutic_area one-hot   11 enum values, in domain.py order
  [12..22] modality one-hot           11 enum values
  [23..26] capital_position one-hot   4 enum values
  [27]     biomarker_enrichment       0/1
  [28]     target_validated           0/1
  [29]     has_btd                    0/1
  [30]     has_fast_track             0/1
  [31]     has_orphan                 0/1
  [32]     has_accelerated_approval   0/1
  [33]     has_rmat                   0/1
  [34]     has_prime                  0/1
  [35]     num_competitors_clipped    int 0-10

  Total: 36 features.
"""

from __future__ import annotations

import numpy as np

from ...domain import (
    AssetInput,
    CapitalPosition,
    Modality,
    Phase,
    RegulatoryDesignation,
    TherapeuticArea,
)

PHASE_ORDER = [
    Phase.PRECLINICAL,
    Phase.PHASE_1,
    Phase.PHASE_2,
    Phase.PHASE_3,
    Phase.NDA,
    Phase.APPROVED,
]
THERAPEUTIC_AREAS = list(TherapeuticArea)
MODALITIES = list(Modality)
CAPITAL_POSITIONS = list(CapitalPosition)

DESIGNATION_FLAGS = [
    RegulatoryDesignation.BTD,
    RegulatoryDesignation.FAST_TRACK,
    RegulatoryDesignation.ORPHAN,
    RegulatoryDesignation.ACCELERATED_APPROVAL,
    RegulatoryDesignation.RMAT,
    RegulatoryDesignation.PRIME,
]

N_FEATURES = (
    1
    + len(THERAPEUTIC_AREAS)
    + len(MODALITIES)
    + len(CAPITAL_POSITIONS)
    + 2  # biomarker_enrichment, target_validated
    + len(DESIGNATION_FLAGS)
    + 1  # num_competitors_clipped
)


def encode(asset: AssetInput) -> np.ndarray:
    """Encode one AssetInput to a fixed-length float vector."""
    vec = np.zeros(N_FEATURES, dtype=np.float32)
    idx = 0

    vec[idx] = float(PHASE_ORDER.index(asset.phase))
    idx += 1

    ta_idx = THERAPEUTIC_AREAS.index(asset.therapeutic_area)
    vec[idx + ta_idx] = 1.0
    idx += len(THERAPEUTIC_AREAS)

    mod_idx = MODALITIES.index(asset.modality)
    vec[idx + mod_idx] = 1.0
    idx += len(MODALITIES)

    cap_idx = CAPITAL_POSITIONS.index(asset.capital_position)
    vec[idx + cap_idx] = 1.0
    idx += len(CAPITAL_POSITIONS)

    vec[idx] = 1.0 if asset.biomarker_enrichment else 0.0
    idx += 1
    vec[idx] = 1.0 if asset.target_validated else 0.0
    idx += 1

    designations = set(asset.regulatory_designations or [])
    for d in DESIGNATION_FLAGS:
        vec[idx] = 1.0 if d in designations else 0.0
        idx += 1

    vec[idx] = float(min(max(asset.num_competitors or 0, 0), 10))
    idx += 1

    assert idx == N_FEATURES, f"feature index mismatch: {idx} vs {N_FEATURES}"
    return vec
