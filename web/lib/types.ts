// TypeScript mirrors of the pydantic models in api/app/domain.py.
// Keep these aligned with domain.py — both reference the same DiligenceRecord
// schema_version, so any breaking change should bump both sides together.

export type Phase =
  | "preclinical"
  | "phase_1"
  | "phase_2"
  | "phase_3"
  | "nda"
  | "approved";

export type TherapeuticArea =
  | "oncology"
  | "rare_orphan"
  | "cns"
  | "metabolic"
  | "infectious"
  | "cardiovascular"
  | "autoimmune"
  | "ophthalmology"
  | "hematology"
  | "respiratory"
  | "other";

export type Modality =
  | "small_molecule"
  | "monoclonal_antibody"
  | "antibody_drug_conjugate"
  | "gene_therapy"
  | "cell_therapy_autologous"
  | "cell_therapy_allogeneic"
  | "mrna"
  | "protein"
  | "oligonucleotide"
  | "peptide"
  | "other";

export type CapitalPosition =
  | "well_capitalized"
  | "adequate"
  | "constrained"
  | "distressed";

export type RegulatoryDesignation =
  | "breakthrough_therapy"
  | "orphan_drug"
  | "fast_track"
  | "accelerated_approval"
  | "rmat"
  | "prime_ema";

export interface AssetInput {
  asset_name: string;
  sponsor?: string | null;
  phase: Phase;
  therapeutic_area: TherapeuticArea;
  modality: Modality;
  capital_position: CapitalPosition;
  mechanism?: string | null;
  target?: string | null;
  indication?: string | null;
  regulatory_designations: RegulatoryDesignation[];
  num_competitors: number;
  target_validated: boolean;
  biomarker_enrichment: boolean;
}

export interface PoSAdjustment {
  name: string;
  multiplier: number;
  rationale: string;
  source: string;
}

export interface PoSResult {
  base_rate: number;
  adjustments: PoSAdjustment[];
  final_loa: number;
  confidence_low: number;
  confidence_high: number;
  phase_transitions: Record<string, number>;
}

export interface RnpvInputs {
  peak_sales_usd_m: number;
  years_to_peak: number;
  years_of_exclusivity: number;
  cogs_pct: number;
  wacc: number;
  dev_cost_phase_1_usd_m: number;
  dev_cost_phase_2_usd_m: number;
  dev_cost_phase_3_usd_m: number;
  launch_cost_usd_m: number;
  years_per_phase: Record<string, number>;
}

export interface TornadoBar {
  variable: string;
  low_value_usd_m: number;
  high_value_usd_m: number;
  swing_usd_m: number;
}

export interface RnpvResult {
  base_case_usd_m: number;
  low_case_usd_m: number | null;
  high_case_usd_m: number | null;
  downside_failed_p3_usd_m: number | null;
  tornado: TornadoBar[];
  monte_carlo_paths: number;
  monte_carlo_p25_usd_m: number | null;
  monte_carlo_p50_usd_m: number | null;
  monte_carlo_p75_usd_m: number | null;
}

export interface PillarScore {
  name: string;
  weight: number;
  score: number;
  rationale: string | null;
}

export type Recommendation =
  | "strong_buy"
  | "buy"
  | "hold"
  | "cautious"
  | "avoid";

export interface ScorecardResult {
  pillars: PillarScore[];
  aggregate_score: number;
  recommendation: Recommendation;
  red_flags: string[];
  green_flags: string[];
}

export interface PillarInput {
  score: number;
  rationale?: string | null;
}

export interface ScorecardInput {
  clinical: PillarInput;
  regulatory: PillarInput;
  competitive: PillarInput;
  manufacturing: PillarInput;
  ip: PillarInput;
  financial: PillarInput;
  team: PillarInput;
  computational: PillarInput;
  red_flags: string[];
  green_flags: string[];
}

export interface Comparable {
  asset_name: string;
  acquirer: string | null;
  deal_value_usd_m: number | null;
  deal_date: string | null;
  peak_sales_estimate_usd_m: number | null;
  ev_to_peak_sales: number | null;
  notes: string | null;
  source: string | null;
}

export interface ComparablesResult {
  cohort: Comparable[];
  median_ev_to_peak_sales: number | null;
  implied_value_usd_m: number | null;
}

export interface ModuleManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  inputs: string[];
  outputs: string[];
  deps: string[];
}

// --- Agents (v1.1) ---------------------------------------------------------
// Recommendation is shared with ScorecardResult — declared once at line ~124.

export interface AgentManifest {
  id: string;
  name: string;
  version: string;
  description: string;
  methodology_refs: string[];
  trigger_label: string;
  input_fields: string[];
  output_fields: string[];
  model: string | null;
  cached_assets: string[];
}

export interface MemoOutput {
  body_markdown: string;
  executive_summary: string;
  recommendation: Recommendation;
  red_flags: string[];
  model_used: string;
  from_cache: boolean;
  generated_at: string;
}

export type AdversaryLens = "signaling" | "auction" | "persuasion";
export type AdversarySeverity = "minor" | "moderate" | "critical";
export type AdversaryVerdictShift = "upgrade" | "hold" | "downgrade";

export interface AdversarialFinding {
  lens: AdversaryLens;
  claim: string;
  severity: AdversarySeverity;
}

export interface AdversaryOutput {
  body_markdown: string;
  verdict_shift: AdversaryVerdictShift;
  recommendation_shift_to: Recommendation | null;
  findings: AdversarialFinding[];
  model_used: string;
  from_cache: boolean;
  generated_at: string;
}

export type FieldConfidence = "high" | "medium" | "low" | "missing";

export interface ExtractedAsset {
  asset_name: string | null;
  aliases?: string[];
  sponsor: string | null;
  phase: Phase | string | null;
  therapeutic_area: TherapeuticArea | string | null;
  modality: Modality | string | null;
  indication: string | null;
  target: string | null;
  mechanism: string | null;
  route_of_administration?: string | null;
  regulatory_designations?: string[];
  num_competitors?: number | null;
  named_competitors?: string[];
  target_validated?: boolean | null;
  biomarker_enrichment?: boolean | null;
  capital_position?: CapitalPosition | string | null;
}

export interface AutoDiligenceCitation {
  field: string;
  url: string;
  title: string | null;
  span: string;
}

export interface AutoDiligenceOutput {
  extracted: ExtractedAsset;
  citations: AutoDiligenceCitation[];
  field_confidence: Record<string, FieldConfidence>;
  web_searches_used: number;
  model_used: string;
  from_cache: boolean;
  generated_at: string;
}
