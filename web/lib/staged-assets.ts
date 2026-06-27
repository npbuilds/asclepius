/**
 * Single source of truth for pre-staged showcase assets.
 *
 * Originally these constants lived inline in `app/diligence/[asset]/page.tsx`.
 * v1.6 Session 2 lifts them here so:
 *   - the landing (`app/page.tsx`) reads the same registry the diligence
 *     page uses,
 *   - the new compare view (`app/compare/page.tsx`) can iterate over them
 *     to populate the multi-asset comparison table,
 *   - adding a new pre-staged asset is one entry in `STAGED_ASSETS` plus
 *     a framing-paragraph branch in the diligence page (the only place
 *     where rich per-asset prose lives).
 *
 * Modes (drives accent color on the landing + the framing-paragraph
 * shape on the diligence page):
 *   - retrospective: information-cutoff backtest against a known outcome
 *   - forward: pre-registered prediction with a future catalyst date
 *   - contested: controversial / unusual outcome the framework can't
 *     and shouldn't try to predict — useful for testing edges
 */

import type { AssetInput, RnpvInputs } from "@/lib/types";

export type StagedAssetMode = "retrospective" | "forward" | "contested";

export interface StagedAsset {
  slug: string;
  name: string;
  sponsor: string;
  mode: StagedAssetMode;
  /** Compact one-line "phase · TA · modality" — purely display. */
  context: string;
  /** 1-2 line "why this asset" hook for the landing tile. */
  story: string;
  asset: AssetInput;
  rnpv: RnpvInputs;
  /** NCT ID for the MLPosPriorPanel criteria-fetch path. Null for assets
   *  whose lead trial isn't on CT.gov in a useful form. */
  ml_pos_nct_id: string | null;
  /** Loadable by slug but excluded from the landing grid. Used for
   *  showcase-only exemplars (e.g. the Ac-225 case study asset) that the
   *  /showcase CTA deep-links into but that aren't real named backtests/
   *  predictions belonging in the curated "pre-staged assets" grid. */
  hidden?: boolean;
}

// ---------------------------------------------------------------------------
// Asset definitions — verbatim from the original page.tsx constants so
// the registry preserves the existing semantics exactly.
// ---------------------------------------------------------------------------

const ADAGRASIB: AssetInput = {
  asset_name: "adagrasib",
  sponsor: "Mirati Therapeutics",
  phase: "phase_2",
  therapeutic_area: "oncology",
  modality: "small_molecule",
  capital_position: "adequate",
  mechanism: "KRAS G12C inhibitor",
  target: "KRAS G12C",
  indication: "NSCLC (2L+, G12C-mutant)",
  regulatory_designations: ["breakthrough_therapy"],
  num_competitors: 1,
  target_validated: true,
  biomarker_enrichment: true,
};

const ADAGRASIB_RNPV: RnpvInputs = {
  peak_sales_usd_m: 1200,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.18,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 3, regulatory: 1 },
};

const DIVARASIB: AssetInput = {
  asset_name: "divarasib",
  sponsor: "Hoffmann-La Roche",
  phase: "phase_3",
  therapeutic_area: "oncology",
  modality: "small_molecule",
  capital_position: "well_capitalized",
  mechanism: "KRAS G12C inhibitor (covalent, second-generation)",
  target: "KRAS G12C",
  indication: "Previously treated KRAS G12C+ advanced/metastatic NSCLC",
  regulatory_designations: [],
  num_competitors: 3,
  target_validated: true,
  biomarker_enrichment: true,
};

const DIVARASIB_RNPV: RnpvInputs = {
  peak_sales_usd_m: 700,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.20,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 1.5, regulatory: 1 },
};

const ADUCANUMAB: AssetInput = {
  asset_name: "aducanumab",
  sponsor: "Biogen / Eisai",
  phase: "phase_3",
  therapeutic_area: "cns",
  modality: "monoclonal_antibody",
  capital_position: "well_capitalized",
  mechanism: "anti-amyloid-beta monoclonal antibody",
  target: "amyloid beta (Aβ) aggregates",
  indication: "Alzheimer's disease (mild cognitive impairment)",
  regulatory_designations: ["fast_track"],
  num_competitors: 2,
  target_validated: false,
  biomarker_enrichment: false,
};

const ADUCANUMAB_RNPV: RnpvInputs = {
  peak_sales_usd_m: 4500,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.15,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 200,
  launch_cost_usd_m: 200,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 2, regulatory: 1 },
};

const LIFILEUCEL: AssetInput = {
  asset_name: "lifileucel",
  sponsor: "Iovance Biotherapeutics",
  phase: "phase_3",
  therapeutic_area: "oncology",
  modality: "cell_therapy_autologous",
  capital_position: "constrained",
  mechanism: "autologous tumor-infiltrating lymphocyte (TIL) therapy",
  target: "patient-specific tumor neoantigens",
  indication: "Advanced/metastatic melanoma post-anti-PD1 + BRAF/MEK (if BRAF+)",
  regulatory_designations: ["breakthrough_therapy", "orphan_drug", "fast_track"],
  num_competitors: 0,
  target_validated: true,
  biomarker_enrichment: false,
};

const LIFILEUCEL_RNPV: RnpvInputs = {
  peak_sales_usd_m: 1100,
  years_to_peak: 6,
  years_of_exclusivity: 12,
  cogs_pct: 0.38,
  wacc: 0.12,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 150,
  launch_cost_usd_m: 300,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 1, regulatory: 1 },
};

const TULISOKIBART: AssetInput = {
  asset_name: "tulisokibart",
  sponsor: "Merck & Co. (acquired from Prometheus)",
  phase: "phase_3",
  therapeutic_area: "autoimmune",
  modality: "monoclonal_antibody",
  capital_position: "well_capitalized",
  mechanism: "anti-TL1A (TNFSF15) monoclonal antibody",
  target: "TL1A (TNFSF15)",
  indication: "Ulcerative colitis (Phase 3 ATLAS-UC) and Crohn's disease (Phase 3 ATLAS-CD)",
  regulatory_designations: [],
  num_competitors: 2,
  target_validated: false,
  biomarker_enrichment: false,
};

const TULISOKIBART_RNPV: RnpvInputs = {
  peak_sales_usd_m: 5000,
  years_to_peak: 6,
  years_of_exclusivity: 12,
  cogs_pct: 0.22,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 400,
  launch_cost_usd_m: 200,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 3, regulatory: 1 },
};

// Ac-225 — the /showcase case-study asset. An illustrative frontier exemplar
// (not a specific company's drug), kept `hidden` so it loads at
// /diligence/ac-225 with these exact inputs (the showcase CTA's deep-link
// target) but doesn't appear in the curated landing grid of real assets.
// rNPV inputs mirror the engine defaults + peak $1,500M so the live workbench
// reproduces the numbers shown on the showcase page verbatim.
const AC225: AssetInput = {
  asset_name: "Ac-225 alpha-emitter (radioligand therapy)",
  sponsor: "Illustrative frontier exemplar",
  phase: "phase_1",
  therapeutic_area: "oncology",
  modality: "radiopharmaceutical",
  capital_position: "constrained",
  supply_constraint: "severe",
  mechanism: "Actinium-225 targeted alpha therapy",
  target: "tumor-associated antigen (e.g. PSMA / SSTR)",
  indication: "Advanced solid tumor (biomarker-selected)",
  regulatory_designations: ["orphan_drug", "fast_track"],
  num_competitors: 2,
  target_validated: true,
  biomarker_enrichment: true,
};

const AC225_RNPV: RnpvInputs = {
  peak_sales_usd_m: 1500,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.20,
  wacc: 0.12,
  dev_cost_phase_1_usd_m: 25,
  dev_cost_phase_2_usd_m: 75,
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 1.5, phase_2: 2.5, phase_3: 3, regulatory: 1 },
};

// ---------------------------------------------------------------------------
// Registry — ordered for narrative flow (oncology workhorse → forward
// prediction → cell therapy → autoimmune → contested). The landing tile
// grid uses this order; the compare view defaults to the first two
// entries when no `?assets=` query is supplied.
// ---------------------------------------------------------------------------

export const STAGED_ASSETS: StagedAsset[] = [
  {
    slug: "adagrasib",
    name: "adagrasib",
    sponsor: "Mirati → BMS",
    mode: "retrospective",
    context: "Phase 2 · oncology · small molecule",
    story:
      "Worked example. June 2022 cutoff; framework brackets the BMS $4.8B deal within ~2%. Drag the reflexivity slider for the headline demo.",
    asset: ADAGRASIB,
    rnpv: ADAGRASIB_RNPV,
    ml_pos_nct_id: "NCT04685135",
  },
  {
    slug: "divarasib",
    name: "divarasib",
    sponsor: "Roche",
    mode: "forward",
    context: "Phase 3 · oncology · small molecule",
    story:
      "Live forward prediction. Head-to-head vs sotorasib/adagrasib. PoS 59.3%, rNPV $948M committed to git before any outcome was known. Resolution 2027-09-30.",
    asset: DIVARASIB,
    rnpv: DIVARASIB_RNPV,
    ml_pos_nct_id: "NCT06497556",
  },
  {
    slug: "lifileucel",
    name: "lifileucel",
    sponsor: "Iovance",
    mode: "retrospective",
    context: "Phase 3 · oncology · autologous cell therapy",
    story:
      "Cell therapy retrospective. January 2024 cutoff (BLA filed); framework on autologous TIL economics — 38% COGS, constrained sponsor, $300M launch costs. FDA approved Feb 2024 as Amtagvi.",
    asset: LIFILEUCEL,
    rnpv: LIFILEUCEL_RNPV,
    ml_pos_nct_id: "NCT02360579",
  },
  {
    slug: "tulisokibart",
    name: "tulisokibart",
    sponsor: "Merck (ex-Prometheus)",
    mode: "forward",
    context: "Phase 3 · autoimmune · monoclonal antibody",
    story:
      "Autoimmune forward prediction. Anti-TL1A novel target (no anti-TL1A approved yet). Phase 3 ATLAS-UC + ATLAS-CD ongoing. Tests the new autoimmune-biologic cohort.",
    asset: TULISOKIBART,
    rnpv: TULISOKIBART_RNPV,
    ml_pos_nct_id: "NCT06430879",
  },
  {
    slug: "aducanumab",
    name: "aducanumab",
    sponsor: "Biogen / Eisai",
    mode: "contested",
    context: "Phase 3 · CNS · monoclonal antibody",
    story:
      "Contested-approval retrospective. March 2019 cutoff, immediately post-ENGAGE/EMERGE futility failure. FDA later approved over a 10-0 AdCom reject — a political process the framework can't predict.",
    asset: ADUCANUMAB,
    rnpv: ADUCANUMAB_RNPV,
    ml_pos_nct_id: "NCT02484547",
  },
  {
    slug: "ac-225",
    name: "Ac-225 radioligand",
    sponsor: "Illustrative frontier exemplar",
    mode: "forward",
    context: "Phase 1 · oncology · radiopharmaceutical",
    story:
      "Showcase case-study asset (see /showcase). Severe isotope supply + a capital-constrained sponsor light up both path-dependencies at once.",
    asset: AC225,
    rnpv: AC225_RNPV,
    ml_pos_nct_id: null,
    hidden: true,
  },
];

/**
 * Lookup by URL slug. Returns null for unknown slugs so callers can
 * decide whether to render a blank-asset form vs. show a 404 vs. handle
 * the case differently (e.g. /compare ignores unknown slugs silently).
 */
export function findStagedAsset(slug: string): StagedAsset | null {
  const lower = slug.toLowerCase();
  return STAGED_ASSETS.find((a) => a.slug === lower) ?? null;
}

/** Default rNPV inputs for unstaged assets — same shape as the
 *  per-asset constants. Lives here so it travels with the registry. */
export const DEFAULT_RNPV: RnpvInputs = {
  peak_sales_usd_m: 1000,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.20,
  wacc: 0.12,
  dev_cost_phase_1_usd_m: 25,
  dev_cost_phase_2_usd_m: 75,
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 1.5, phase_2: 2.5, phase_3: 3, regulatory: 1 },
};
