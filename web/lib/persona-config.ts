// Persona configuration — declarative spec for what each persona shows/hides
// on the /diligence/[asset] page. The page-level orchestrator reads from this
// map (via the current persona from lib/persona.ts) to decide module ordering,
// hidden modules, banner variant, and compactness.
//
// v1.8.0 (this commit): config shape frozen with all four personas declared.
// The diligence page does NOT yet consume the persona-specific fields — every
// persona renders the v1.7.0 VC-Associate layout until Phases 3-5 wire the
// per-persona variations. Shipping the config early lets the contract
// stabilize before behavior depends on it.
//
// Adding a new persona = (1) extend PersonaId in lib/persona.ts + VALID_PERSONAS,
// (2) add a PersonaConfig entry here, (3) any persona-specific cards/banners
// added in components/banners or components/cards, (4) any conditional
// rendering in diligence/[asset]/page.tsx. The config is the API surface;
// everything downstream reads from it.

import type { PersonaId } from "./persona";

// ---------------------------------------------------------------------------
// Banner variants
// ---------------------------------------------------------------------------

// Which banner component renders for this persona. The default "vc" is the
// existing HeroBanner from v1.7.0. The other variants are introduced as
// dedicated components in Phases 3-5 (banners/IcVoterBanner, banners/
// ScientificBanner, banners/QuantBanner).
export type BannerVariant = "vc" | "ic_voter" | "scientific" | "quant";

// ---------------------------------------------------------------------------
// Section grouping per persona
// ---------------------------------------------------------------------------

// Each persona can re-define the section grouping. By default this mirrors
// the v1.7.0 MODULE_SECTIONS (thesis → valuation → operational). IC voter
// compacts into one "decision" section; scientific reviewer reorders to
// put science first; quant elevates calibration.
//
// PersonaSection.moduleIds lists modules to render IN ORDER inside the
// section. Modules in moduleIds but absent from the backend's discovered
// manifests are silently skipped (matches existing group behavior).

export interface PersonaSection {
  id: string;
  label: string;
  question: string;
  moduleIds: string[];
}

// ---------------------------------------------------------------------------
// PersonaConfig — the per-persona contract
// ---------------------------------------------------------------------------

export interface PersonaConfig {
  id: PersonaId;
  label: string;          // shown in the dropdown
  description: string;    // shown in the dropdown's tooltip / aria-description
  bannerVariant: BannerVariant;
  // Modules entirely filtered out of the manifests list. Used to drop rNPV +
  // Comparables for Scientific Reviewer (the science-focused read), or to
  // drop the recommendation chip's source for Quant (raw numbers only).
  hiddenModules: string[];
  // Section grouping override. If empty, the page uses the default
  // MODULE_SECTIONS from module-registry.ts (the v1.7.0 layout).
  sections: PersonaSection[];
  // IC Voter mode: single-screen target. Panels collapse tornado/MC details,
  // recommendation chip is enlarged, action strip is hidden in favor of
  // a "decision rationale" card. Other personas leave this false.
  compactMode: boolean;
  // Whether to render the v1.7.0 ActionSection (Auto-Diligence + Memo Writer
  // + methodology link + PDF stub) as a final beat. IC Voter hides it
  // (one-page target); others show it.
  showActionSection: boolean;
}

// ---------------------------------------------------------------------------
// The four persona configs
// ---------------------------------------------------------------------------

const VC_ASSOCIATE_SECTIONS: PersonaSection[] = [
  // Empty == use the default MODULE_SECTIONS from module-registry.ts.
  // The VC Associate persona IS the v1.7.0 baseline; no overrides.
];

const IC_VOTER_SECTIONS: PersonaSection[] = [
  {
    id: "decision",
    label: "Decision view",
    question: "should we vote yes — and what's the partner-killer risk?",
    moduleIds: ["pos", "rnpv", "scorecard"],
  },
];

const SCIENTIFIC_REVIEWER_SECTIONS: PersonaSection[] = [
  {
    id: "science",
    label: "Science",
    question: "is the mechanism + trial design defensible?",
    moduleIds: ["ml_pos_prior", "pos"],
  },
  {
    id: "operational",
    label: "Operational diligence",
    question: "what's qualitatively true beyond the math?",
    moduleIds: ["scorecard"],
  },
];

const QUANT_SECTIONS: PersonaSection[] = [
  {
    id: "calibration",
    label: "Calibration",
    question: "is the model honest about its own coverage?",
    moduleIds: ["calibration", "ml_pos_prior"],
  },
  {
    id: "math",
    label: "Math",
    question: "what's the raw rule-chain + valuation output?",
    moduleIds: ["pos", "rnpv", "comparables"],
  },
  {
    id: "operational",
    label: "Operational diligence",
    question: "what's the qualitative scoreboard?",
    moduleIds: ["scorecard"],
  },
];

export const PERSONA_CONFIGS: Record<PersonaId, PersonaConfig> = {
  vc_associate: {
    id: "vc_associate",
    label: "VC Associate",
    description:
      "Default reader-journey layout. Recommendation + rNPV + LOA + reflexivity + catalyst above the fold; thesis → valuation → operational → risk → action below.",
    bannerVariant: "vc",
    hiddenModules: [],
    sections: VC_ASSOCIATE_SECTIONS,
    compactMode: false,
    showActionSection: true,
  },
  ic_voter: {
    id: "ic_voter",
    label: "IC Voter",
    description:
      "1-page summary mode for senior partners. Recommendation + top-3 risks + top-3 reasons + catalyst — no tornado, no MC histogram, no methodology footnotes. ~2 minute read.",
    bannerVariant: "ic_voter",
    hiddenModules: ["calibration"],
    sections: IC_VOTER_SECTIONS,
    compactMode: true,
    showActionSection: false,
  },
  scientific_reviewer: {
    id: "scientific_reviewer",
    label: "Scientific Reviewer",
    description:
      "Mechanism + target + trial design focus. Elevates the ML PoS Prior (the protocol-embedding signal). Hides rNPV + deal comparables — not the science reviewer's question.",
    bannerVariant: "scientific",
    hiddenModules: ["rnpv", "comparables"],
    sections: SCIENTIFIC_REVIEWER_SECTIONS,
    compactMode: false,
    showActionSection: true,
  },
  quant: {
    id: "quant",
    label: "Quant",
    description:
      "Calibration-elevated raw-numbers mode. AUC + Brier + per-phase coverage + ML-vs-rule disagreement upfront; no recommendation chip (suspicious of opaque rec). Raw /model_info JSON exposed in a collapsible card.",
    bannerVariant: "quant",
    hiddenModules: [],
    sections: QUANT_SECTIONS,
    compactMode: false,
    showActionSection: true,
  },
};

// Convenience accessor for the page-level orchestrator (Phases 3-5 will
// use this).
export function getPersonaConfig(id: PersonaId): PersonaConfig {
  return PERSONA_CONFIGS[id];
}
