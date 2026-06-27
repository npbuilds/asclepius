"""DiligenceRecord — the single source of truth for every module.

Every analysis module reads from and writes to a slice of this record. No module
holds state outside of it. This is the contract that makes the registry pattern work:
new modules compose by extending the record's typed sub-models, not by inventing
parallel state.

Schema version is explicit so future migrations are unambiguous.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enums — categorical fields use enums so typos fail at validation, not at runtime
# ---------------------------------------------------------------------------


class Phase(str, Enum):
    PRECLINICAL = "preclinical"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    NDA = "nda"
    APPROVED = "approved"


class TherapeuticArea(str, Enum):
    ONCOLOGY = "oncology"
    RARE_ORPHAN = "rare_orphan"
    CNS = "cns"
    METABOLIC = "metabolic"
    INFECTIOUS = "infectious"
    CARDIOVASCULAR = "cardiovascular"
    AUTOIMMUNE = "autoimmune"
    OPHTHALMOLOGY = "ophthalmology"
    HEMATOLOGY = "hematology"
    RESPIRATORY = "respiratory"
    OTHER = "other"


class Modality(str, Enum):
    SMALL_MOLECULE = "small_molecule"
    MAB = "monoclonal_antibody"
    ADC = "antibody_drug_conjugate"
    GENE_THERAPY = "gene_therapy"
    CELL_THERAPY_AUTO = "cell_therapy_autologous"
    CELL_THERAPY_ALLO = "cell_therapy_allogeneic"
    MRNA = "mrna"
    PROTEIN = "protein"
    OLIGONUCLEOTIDE = "oligonucleotide"
    PEPTIDE = "peptide"
    # v1.10 frontier modalities (dogfood-driven): the 2023-2025 classes a
    # biotech investor actually tracks, which the 2021-era taxonomy lacked.
    TARGETED_PROTEIN_DEGRADER = "targeted_protein_degrader"  # PROTAC / molecular glue
    RADIOPHARMACEUTICAL = "radiopharmaceutical"  # radioligand therapy (incl. Ac-225 alpha)
    EPIGENETIC_EDITING = "epigenetic_editing"  # epigenetic silencing/activation
    OTHER = "other"


class CapitalPosition(str, Enum):
    """Reflexivity tier. Drives the reflexivity adjustment in pos engine."""

    WELL_CAPITALIZED = "well_capitalized"  # >24mo cash, no near-term raise pressure
    ADEQUATE = "adequate"                  # 12-24mo cash
    CONSTRAINED = "constrained"            # 6-12mo cash, raise dependency
    DISTRESSED = "distressed"              # <6mo cash, going concern overhang


class SupplyConstraint(str, Enum):
    """Supply / manufacturing constraint tier — a second path-dependency.

    Like reflexivity (which keys PoS off sponsor capital), supply constraint is a
    structural overlay: scarce raw materials / isotopes / manufacturing capacity
    add trial-execution risk (PoS) AND cap achievable peak sales (rNPV). Drives the
    supply adjustment in the pos engine and the peak-sales ceiling in the rnpv engine.
    """

    UNCONSTRAINED = "unconstrained"  # standard manufacturing scales with demand
    MODERATE = "moderate"            # complex but scalable (cell therapy, bispecifics)
    SEVERE = "severe"                # binding raw-material/isotope/capacity constraint


class RegulatoryDesignation(str, Enum):
    BTD = "breakthrough_therapy"
    ORPHAN = "orphan_drug"
    FAST_TRACK = "fast_track"
    ACCELERATED_APPROVAL = "accelerated_approval"
    RMAT = "rmat"
    PRIME = "prime_ema"


# ---------------------------------------------------------------------------
# Asset input (the user-provided / autofilled side of the record)
# ---------------------------------------------------------------------------


class AssetInput(BaseModel):
    """User-supplied or auto-diligence-extracted asset definition."""

    model_config = ConfigDict(extra="forbid")

    asset_name: str
    sponsor: str | None = None
    phase: Phase
    therapeutic_area: TherapeuticArea
    modality: Modality
    capital_position: CapitalPosition = CapitalPosition.ADEQUATE
    # Supply-constraint tier. Defaults to UNCONSTRAINED so every existing
    # AssetInput(...) call and staged-asset literal keeps working unchanged —
    # the second path-dependency is opt-in, never a silent behavior change.
    supply_constraint: SupplyConstraint = SupplyConstraint.UNCONSTRAINED
    mechanism: str | None = Field(
        default=None, description="Free-text mechanism of action (e.g. 'KRAS G12C inhibitor')."
    )
    target: str | None = None
    indication: str | None = None
    regulatory_designations: list[RegulatoryDesignation] = Field(default_factory=list)
    num_competitors: int = Field(default=0, ge=0)
    target_validated: bool = Field(
        default=False,
        description="True if the target has prior clinical validation in this indication.",
    )
    biomarker_enrichment: bool = Field(
        default=False,
        description="True if the trial uses a predictive biomarker to enrich the population.",
    )


# ---------------------------------------------------------------------------
# PoS outputs
# ---------------------------------------------------------------------------


class PoSAdjustment(BaseModel):
    """One row of the PoS audit trail. Every adjustment must justify itself."""

    model_config = ConfigDict(extra="forbid")

    name: str
    multiplier: float = Field(description="Multiplicative factor applied to running PoS.")
    rationale: str
    source: str = Field(description="Citation, e.g. 'BIO 2021 Table 5' or 'Wong 2019 §4.2'.")


class PoSResult(BaseModel):
    """Output of the PoS module. Written onto DiligenceRecord.pos."""

    model_config = ConfigDict(extra="forbid")

    base_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Phase-to-approval base rate from BIO/Informa for this TA + phase.",
    )
    adjustments: list[PoSAdjustment]
    final_loa: float = Field(
        ge=0.0,
        le=1.0,
        description="Final cumulative likelihood of approval after all adjustments.",
    )
    confidence_low: float = Field(ge=0.0, le=1.0)
    confidence_high: float = Field(ge=0.0, le=1.0)
    phase_transitions: dict[str, float] = Field(
        default_factory=dict,
        description="Per-phase transition probabilities (e.g. {'p2_to_p3': 0.29}).",
    )


# ---------------------------------------------------------------------------
# rNPV outputs
# ---------------------------------------------------------------------------


class RnpvInputs(BaseModel):
    """User-supplied (or autofilled) commercial/economic assumptions."""

    model_config = ConfigDict(extra="forbid")

    peak_sales_usd_m: float = Field(gt=0, description="Peak annual sales in $M.")
    years_to_peak: int = Field(default=5, ge=1, le=15)
    years_of_exclusivity: int = Field(default=12, ge=1, le=20)
    cogs_pct: float = Field(default=0.20, ge=0.0, le=0.95)
    wacc: float = Field(default=0.12, ge=0.0, le=0.30)
    dev_cost_phase_1_usd_m: float = Field(default=25.0, ge=0)
    dev_cost_phase_2_usd_m: float = Field(default=75.0, ge=0)
    dev_cost_phase_3_usd_m: float = Field(default=250.0, ge=0)
    launch_cost_usd_m: float = Field(default=150.0, ge=0)
    years_per_phase: dict[str, float] = Field(
        default_factory=lambda: {"phase_1": 1.5, "phase_2": 2.5, "phase_3": 3.0, "regulatory": 1.0}
    )


class RnpvResult(BaseModel):
    """Output of the rNPV module."""

    model_config = ConfigDict(extra="forbid")

    base_case_usd_m: float
    low_case_usd_m: float | None = None
    high_case_usd_m: float | None = None
    # Supply-constraint ceiling on peak sales (the distinctive second-path effect).
    # `supply_peak_ceiling_pct` is the multiplier applied to the user's nominal peak
    # (1.0 when unconstrained); `supply_adjusted_peak_usd_m` is the effective peak the
    # revenue model actually used. Surfaced so the haircut is inspectable, not hidden.
    supply_peak_ceiling_pct: float | None = None
    supply_adjusted_peak_usd_m: float | None = None
    downside_failed_p3_usd_m: float | None = Field(
        default=None,
        description="Terminal value if asset fails Phase 3 (residual cash + IP).",
    )
    tornado: list["TornadoBar"] = Field(default_factory=list)
    monte_carlo_paths: int = 0
    monte_carlo_p25_usd_m: float | None = None
    monte_carlo_p50_usd_m: float | None = None
    monte_carlo_p75_usd_m: float | None = None


class TornadoBar(BaseModel):
    """One bar of the tornado chart.

    Note on orientation: `low_value_usd_m` is the rNPV *when the input variable
    is at the low end of its swing*. For inversely-correlated variables like
    WACC, that produces a *higher* rNPV than `high_value_usd_m`. The frontend
    plots whichever is larger as the right bar; the magnitude is in `swing_usd_m`.
    """

    model_config = ConfigDict(extra="forbid")

    variable: str
    low_value_usd_m: float
    high_value_usd_m: float
    swing_usd_m: float


# ---------------------------------------------------------------------------
# Scorecard outputs
# ---------------------------------------------------------------------------


class PillarScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    weight: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=1.0, le=10.0)
    rationale: str | None = None


class ScorecardResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pillars: list[PillarScore]
    aggregate_score: float = Field(ge=1.0, le=10.0)
    recommendation: Literal[
        "strong_buy", "buy", "hold", "cautious", "avoid"
    ]
    red_flags: list[str] = Field(default_factory=list)
    green_flags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Comparable transactions
# ---------------------------------------------------------------------------


class Comparable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_name: str
    acquirer: str | None = None
    deal_value_usd_m: float | None = None
    deal_date: date | None = None
    peak_sales_estimate_usd_m: float | None = None
    ev_to_peak_sales: float | None = None
    notes: str | None = None
    source: str | None = Field(
        default=None,
        description=(
            "Citation of the deal-value and peak-sales estimates. The tool's "
            "headline provenance discipline relies on this propagating from "
            "the JSON to the API response and into the rendered cohort table."
        ),
    )


class ComparablesResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cohort: list[Comparable]
    median_ev_to_peak_sales: float | None = None
    implied_value_usd_m: float | None = None
    # v1.6: human-readable description of which curated cohort matched —
    # e.g. "Oncology · small molecule (kinase-TKI)" or "CNS · small molecule"
    # or "Fallback: kinase-TKI (no asset-matched cohort for X)". The UI
    # uses this to render an honest disclosure when the cohort isn't
    # asset-matched, and to omit the disclosure when it IS.
    cohort_label: str | None = None
    cohort_matched: bool = True


# ---------------------------------------------------------------------------
# The record itself
# ---------------------------------------------------------------------------


class DiligenceRecord(BaseModel):
    """The single source of truth that every module reads from and writes to.

    Modules update specific fields; they do not invent parallel state. The schema
    version is explicit so any future migration is a deliberate operation, not a
    silent drift.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    asset: AssetInput

    pos: PoSResult | None = None
    rnpv_inputs: RnpvInputs | None = None
    rnpv: RnpvResult | None = None
    scorecard: ScorecardResult | None = None
    comparables: ComparablesResult | None = None


# Resolve forward refs (RnpvResult references TornadoBar declared after it)
RnpvResult.model_rebuild()
