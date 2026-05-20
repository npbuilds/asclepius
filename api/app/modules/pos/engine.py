"""PoS computation with explicit audit trail.

Core idea: `final_loa = base_rate * Π(multipliers)` where each multiplier is logged
with its name, value, rationale, and source. The waterfall the frontend renders is
literally this list of adjustments.

The reflexivity multiplier is applied LAST in the chain (it's a sponsor-level
structural overlay), not because the order changes the math but because the
methodology positions it as such: base rate is population, modality is technology,
mechanism is data, reflexivity is sponsor.
"""

from __future__ import annotations

from ...domain import (
    AssetInput,
    DiligenceRecord,
    PoSAdjustment,
    PoSResult,
    RegulatoryDesignation,
)
from ...registry import get_registry


# ---- Mechanism-level modifiers ----
# These come from established biotech investor practice; each is documented inline.

_BIOMARKER_ENRICHMENT_BOOST = 0.20   # +20% LOA when trial uses predictive biomarker
_TARGET_VALIDATED_BOOST = 0.15       # +15% when target has prior clinical validation
_HIGH_COMPETITION_PENALTY = -0.10    # -10% when ≥3 direct competitors in same indication

_BTD_BOOST = 0.10                    # +10% for Breakthrough Therapy Designation
_ORPHAN_BOOST = 0.05                 # +5% for Orphan Drug
_FAST_TRACK_BOOST = 0.03             # +3% for Fast Track


def compute(record: DiligenceRecord) -> PoSResult:
    """The required entrypoint for the registry."""
    return _compute_for_asset(record.asset)


def _compute_for_asset(asset: AssetInput) -> PoSResult:
    # Approved assets: no remaining development risk. Bypass adjustments so the
    # audit trail doesn't list modifiers that have no analytical meaning.
    from ...domain import Phase as _Phase

    if asset.phase == _Phase.APPROVED:
        return PoSResult(
            base_rate=1.0,
            adjustments=[],
            final_loa=1.0,
            confidence_low=1.0,
            confidence_high=1.0,
            phase_transitions={},
        )

    reg = get_registry()
    bio = reg.data_sources["bio_base_rates"]
    modality = reg.data_sources["modality_multipliers"]
    reflexivity = reg.data_sources["reflexivity_adjustments"]

    # 1. Base rate from BIO/Informa for this TA + phase
    base = bio.fetch(
        {"therapeutic_area": asset.therapeutic_area.value, "phase": asset.phase.value}
    )
    base_rate: float = base["base_rate"]
    phase_transitions: dict[str, float] = base["phase_transitions"]

    adjustments: list[PoSAdjustment] = []
    running = base_rate

    # 2. Modality multiplier
    mod = modality.fetch({"modality": asset.modality.value})
    mod_mult: float = mod["modality_multiplier"]
    running *= mod_mult
    adjustments.append(
        PoSAdjustment(
            name=f"modality: {asset.modality.value}",
            multiplier=mod_mult,
            rationale=mod["rationale"],
            source=f"BIO/Informa 2021 modality cohort — {mod['source']}",
        )
    )

    # 3. Mechanism modifiers — applied as additive boosts to the multiplier
    if asset.biomarker_enrichment:
        running *= 1.0 + _BIOMARKER_ENRICHMENT_BOOST
        adjustments.append(
            PoSAdjustment(
                name="biomarker enrichment",
                multiplier=1.0 + _BIOMARKER_ENRICHMENT_BOOST,
                rationale="Trial enriches the population using a predictive biomarker, raising response rate and statistical power.",
                source="Wong 2019 §4.3 — biomarker-enriched trials show ~20% higher P2→P3 transition.",
            )
        )

    if asset.target_validated:
        running *= 1.0 + _TARGET_VALIDATED_BOOST
        adjustments.append(
            PoSAdjustment(
                name="target validated",
                multiplier=1.0 + _TARGET_VALIDATED_BOOST,
                rationale="Target has prior clinical validation in this indication (e.g., a prior approved drug against the same target).",
                source="Practitioner heuristic; consistent with Wong 2019 prior-target-validation analysis.",
            )
        )

    if asset.num_competitors >= 3:
        running *= 1.0 + _HIGH_COMPETITION_PENALTY
        adjustments.append(
            PoSAdjustment(
                name=f"competitive density ({asset.num_competitors} competitors)",
                multiplier=1.0 + _HIGH_COMPETITION_PENALTY,
                rationale="Three or more direct competitors in the same indication raise the commercial bar required for approval and reduce enrollment speed.",
                source="Practitioner heuristic; downstream demand effects.",
            )
        )

    # 4. Regulatory designations — additive boosts
    designations = set(asset.regulatory_designations)
    if RegulatoryDesignation.BTD in designations:
        running *= 1.0 + _BTD_BOOST
        adjustments.append(
            PoSAdjustment(
                name="Breakthrough Therapy Designation",
                multiplier=1.0 + _BTD_BOOST,
                rationale="BTD signals FDA agreement on preliminary clinical evidence and unlocks more intensive guidance.",
                source="FDA BTD program; practitioner-observed PoS uplift.",
            )
        )
    if RegulatoryDesignation.ORPHAN in designations:
        running *= 1.0 + _ORPHAN_BOOST
        adjustments.append(
            PoSAdjustment(
                name="Orphan Drug Designation",
                multiplier=1.0 + _ORPHAN_BOOST,
                rationale="Orphan status confers regulatory flexibility, extended exclusivity, and (per BIO) historically higher LOA.",
                source="BIO 2021 — rare/orphan LOA ~16% vs ~8% all-indications.",
            )
        )
    if RegulatoryDesignation.FAST_TRACK in designations:
        running *= 1.0 + _FAST_TRACK_BOOST
        adjustments.append(
            PoSAdjustment(
                name="Fast Track Designation",
                multiplier=1.0 + _FAST_TRACK_BOOST,
                rationale="Fast Track enables rolling review and more frequent FDA interaction.",
                source="FDA Fast Track program; practitioner-observed PoS uplift.",
            )
        )

    # 5. Reflexivity (sponsor capital position) — applied LAST per methodology framing
    refl = reflexivity.fetch({"capital_position": asset.capital_position.value})
    refl_mult: float = refl["reflexivity_multiplier"]
    running *= refl_mult
    adjustments.append(
        PoSAdjustment(
            name=f"reflexivity: {asset.capital_position.value}",
            multiplier=refl_mult,
            rationale=refl["reflexivity_rationale"],
            source="Asclepius methodology/02-reflexivity-thesis.md (Spence-style signaling equilibrium; empirical backing from Ma et al. 2025 trial-accrual model AUC 0.74).",
        )
    )

    final_loa = max(0.0, min(1.0, running))

    # 6. Confidence range — propagate modality and reflexivity range widths
    mod_range = mod["modality_range"]
    refl_range = refl["reflexivity_range"]
    low_factor = (mod_range[0] / mod_mult) * (refl_range[0] / refl_mult)
    high_factor = (mod_range[1] / mod_mult) * (refl_range[1] / refl_mult)
    conf_low = max(0.0, min(1.0, final_loa * low_factor))
    conf_high = max(0.0, min(1.0, final_loa * high_factor))

    return PoSResult(
        base_rate=base_rate,
        adjustments=adjustments,
        final_loa=final_loa,
        confidence_low=conf_low,
        confidence_high=conf_high,
        phase_transitions=phase_transitions,
    )
