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
  "scorecard",
  "comparables",
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
