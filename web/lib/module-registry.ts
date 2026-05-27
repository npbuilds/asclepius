// Client-side mirror of the backend's /api/modules registry.
//
// All panels share a uniform prop shape: they receive the current diligence
// record + a setter, then read the slices they need and publish their results
// back. This is the analog of the backend's "every module reads/writes
// DiligenceRecord" contract — same single source of truth, JS side.

import dynamic from "next/dynamic";
import type { ComponentType } from "react";

import type {
  AssetInput,
  ComparablesResult,
  MLPosPriorResult,
  ModuleManifest,
  PoSResult,
  RnpvInputs,
  RnpvResult,
  ScorecardResult,
} from "./types";

export interface ClientDiligenceRecord {
  asset: AssetInput;
  pos: PoSResult | null;
  rnpv_inputs: RnpvInputs;
  rnpv: RnpvResult | null;
  scorecard: ScorecardResult | null;
  comparables: ComparablesResult | null;
  // v1.7.0 (HeroBanner): the ML PoS Prior result is lifted to the page
  // so both the banner (headline LOA stat) and the MLPosPriorPanel can
  // read from a single source. Pre-v1.7.0, MLPosPriorPanel self-fetched
  // — that worked for the panel alone but meant the banner couldn't
  // surface the ML number without a double-fetch. Single source of
  // truth in ClientDiligenceRecord matches the project's broader
  // "DiligenceRecord is the contract every module reads/writes" pattern.
  ml_pos: MLPosPriorResult | null;
  // v1.5.2: optional trial-protocol bindings for the ML PoS Prior module.
  // When the engine's feature-fingerprint cache misses (i.e. the user has
  // edited any asset field away from a pre-cached canonical record), the
  // live PubMedBERT path needs eligibility-criteria text. Either field
  // can supply it: `ml_pos_criteria_text` is sent verbatim; `ml_pos_nct_id`
  // triggers a server-side fetch from ClinicalTrials.gov v2. For the
  // adagrasib retrospective, we pre-populate `ml_pos_nct_id` so the live
  // path resolves even after manual edits. Neither is required for the
  // cached path.
  ml_pos_criteria_text?: string | null;
  ml_pos_nct_id?: string | null;
}

export interface ModulePanelProps {
  record: ClientDiligenceRecord;
  setRecord: (
    update: Partial<ClientDiligenceRecord> | ((prev: ClientDiligenceRecord) => ClientDiligenceRecord),
  ) => void;
}

type LoadablePanel = ComponentType<ModulePanelProps>;

const panelByModuleId: Record<string, LoadablePanel> = {
  pos: dynamic(() => import("@/components/modules/pos/PoSWaterfallPanel"), {
    ssr: false,
  }),
  ml_pos_prior: dynamic(
    () => import("@/components/modules/ml_pos_prior/MLPosPriorPanel"),
    { ssr: false },
  ),
  rnpv: dynamic(() => import("@/components/modules/rnpv/RnpvPanel"), {
    ssr: false,
  }),
  scorecard: dynamic(
    () => import("@/components/modules/scorecard/ScorecardRadarPanel"),
    { ssr: false },
  ),
  comparables: dynamic(
    () => import("@/components/modules/comparables/ComparablesPanel"),
    { ssr: false },
  ),
  calibration: dynamic(
    () => import("@/components/modules/calibration/CalibrationPanel"),
    { ssr: false },
  ),
};

export function getPanelFor(manifest: ModuleManifest): LoadablePanel | null {
  return panelByModuleId[manifest.id] ?? null;
}

const DISPLAY_ORDER: string[] = [
  "pos",
  "ml_pos_prior",
  "rnpv",
  "comparables",
  "scorecard",
  "calibration",
];

export function orderModules(manifests: ModuleManifest[]): ModuleManifest[] {
  return [...manifests].sort((a, b) => {
    const ai = DISPLAY_ORDER.indexOf(a.id);
    const bi = DISPLAY_ORDER.indexOf(b.id);
    if (ai === -1 && bi === -1) return a.id.localeCompare(b.id);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}

// ---------------------------------------------------------------------------
// v1.7.0 — Reader-journey section grouping
//
// Each section maps to ONE question the reader is trying to answer at that
// point in their read. Order locked to equity-research / IC-memo
// convention: thesis (the edge) → valuation (the number) → operational
// (the qualitative). Risk + action surfaces live outside the module
// system (LimitationsPanel/AdversaryPanel/MemoPanel/AutoDiligencePanel).
//
// Adding a new module = either claim it into a section's moduleIds OR
// let it fall into the "Additional analysis" catch-all (the uncategorized
// fallback in groupModulesBySection). The grouping is configuration, not
// a registry contract — backend manifests are still the source of truth
// for what exists.
// ---------------------------------------------------------------------------

export interface ModuleSection {
  id: string;
  label: string;
  question: string; // shown as one-line "Q:" microcopy under the section heading
  moduleIds: string[];
}

export const MODULE_SECTIONS: ModuleSection[] = [
  {
    id: "thesis",
    label: "Thesis",
    question: "what's the framework's edge on this asset?",
    moduleIds: ["pos", "ml_pos_prior"],
  },
  {
    id: "valuation",
    label: "Valuation",
    question: "what's the number, and is the comp set consistent?",
    moduleIds: ["rnpv", "comparables"],
  },
  {
    id: "operational",
    label: "Operational diligence",
    question: "what's qualitatively true beyond the math?",
    moduleIds: ["scorecard", "calibration"],
  },
];

export interface SectionWithManifests {
  section: ModuleSection;
  manifests: ModuleManifest[];
}

export function groupModulesBySection(
  manifests: ModuleManifest[],
): SectionWithManifests[] {
  const byId = new Map(manifests.map((m) => [m.id, m]));
  const claimedIds = new Set<string>();
  const grouped: SectionWithManifests[] = MODULE_SECTIONS.map((section) => {
    const sectionManifests: ModuleManifest[] = [];
    for (const id of section.moduleIds) {
      const m = byId.get(id);
      if (m) {
        sectionManifests.push(m);
        claimedIds.add(id);
      }
    }
    return { section, manifests: sectionManifests };
  }).filter((g) => g.manifests.length > 0);

  // Orphan modules — discovered on backend but not claimed by any section.
  // Surface them under a generic header so a new backend module never
  // silently disappears from the page. Adding it to MODULE_SECTIONS is
  // the proper follow-up; this fallback just keeps the contract intact.
  const orphans = manifests.filter((m) => !claimedIds.has(m.id));
  if (orphans.length > 0) {
    grouped.push({
      section: {
        id: "uncategorized",
        label: "Additional analysis",
        question: "what else does the backend expose?",
        moduleIds: [],
      },
      manifests: orphans,
    });
  }
  return grouped;
}
