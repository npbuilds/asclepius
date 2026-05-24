// API client — thin wrappers around the backend module endpoints.
//
// All paths are relative ("/api/...") because next.config.js proxies them to
// the FastAPI service. That keeps the client free of base-URL knowledge and
// lets prod / staging / local use the same code.

import type {
  AdversaryOutput,
  AgentManifest,
  AssetCalibrationContext,
  AssetInput,
  AssetSizingInput,
  AutoDiligenceOutput,
  CalibrationReport,
  ComparablesResult,
  FundParameters,
  MLPosPriorResult,
  PortfolioRecommendation,
  MemoOutput,
  ModuleManifest,
  PoSResult,
  PredictionLogEntry,
  RnpvInputs,
  RnpvResult,
  ScorecardInput,
  ScorecardResult,
} from "./types";

export interface AgentError {
  status: number;
  message: string;
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${path} ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function listModules(): Promise<ModuleManifest[]> {
  const data = await jsonFetch<{ modules: ModuleManifest[] }>("/api/modules");
  return data.modules;
}

export async function runPoS(asset: AssetInput): Promise<PoSResult> {
  const data = await jsonFetch<{ pos: PoSResult }>("/api/modules/pos", {
    method: "POST",
    body: JSON.stringify({ asset }),
  });
  return data.pos;
}

export async function runRnpv(
  asset: AssetInput,
  pos: PoSResult,
  rnpv_inputs: RnpvInputs,
): Promise<RnpvResult> {
  const data = await jsonFetch<{ rnpv: RnpvResult }>("/api/modules/rnpv", {
    method: "POST",
    body: JSON.stringify({ asset, pos, rnpv_inputs }),
  });
  return data.rnpv;
}

export async function runMLPosPrior(
  asset: AssetInput,
  pos: PoSResult,
  opts?: { criteria_text?: string | null; nct_id?: string | null },
): Promise<MLPosPriorResult> {
  // v1.5.2: the backend's ML path needs eligibility-criteria text whenever
  // the feature-fingerprint cache misses. The cached path (e.g. canonical
  // adagrasib) ignores both fields. Send them through verbatim — the
  // backend handles precedence (`criteria_text` wins over `nct_id`).
  const body: Record<string, unknown> = { asset, pos };
  if (opts?.criteria_text) body.criteria_text = opts.criteria_text;
  if (opts?.nct_id) body.nct_id = opts.nct_id;
  return jsonFetch<MLPosPriorResult>("/api/modules/ml_pos_prior", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function runScorecard(
  asset: AssetInput,
  scorecard_input: ScorecardInput,
): Promise<ScorecardResult> {
  const data = await jsonFetch<{ scorecard: ScorecardResult }>(
    "/api/modules/scorecard",
    {
      method: "POST",
      body: JSON.stringify({ asset, scorecard_input }),
    },
  );
  return data.scorecard;
}

// ---- Agents (v1.1) -------------------------------------------------------

export async function listAgents(): Promise<AgentManifest[]> {
  const data = await jsonFetch<{ agents: AgentManifest[] }>("/api/agents");
  return data.agents;
}

// The agent endpoint differs from modules: it expects the full DiligenceRecord
// shape, not the {asset, pos, …} envelope each module uses. We accept a record
// shape from the caller and forward it verbatim.
export async function runAgent<T>(
  agentId: string,
  record: Record<string, unknown>,
): Promise<T> {
  const res = await fetch(`/api/agents/${agentId}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify(record),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // body wasn't JSON; keep statusText
    }
    const err: AgentError = { status: res.status, message: detail };
    throw err;
  }
  return res.json() as Promise<T>;
}

export async function runMemoWriter(
  record: Record<string, unknown>,
): Promise<MemoOutput> {
  return runAgent<MemoOutput>("memo_writer", record);
}

export async function runGameTheoryAdversary(
  record: Record<string, unknown>,
): Promise<AdversaryOutput> {
  return runAgent<AdversaryOutput>("game_theory_adversary", record);
}

export async function runAutoDiligence(
  record: Record<string, unknown>,
): Promise<AutoDiligenceOutput> {
  return runAgent<AutoDiligenceOutput>("auto_diligence", record);
}

// --- Portfolio Sizing (v2.0) ----------------------------------------------

export async function runPortfolioSizing(
  assets: AssetSizingInput[],
  fund: FundParameters,
): Promise<PortfolioRecommendation> {
  return jsonFetch<PortfolioRecommendation>(
    "/api/modules/portfolio_sizing/portfolio",
    {
      method: "POST",
      body: JSON.stringify({ assets, fund }),
    },
  );
}

// --- Calibration module ---------------------------------------------------

export async function runCalibration(
  asset: AssetInput,
): Promise<AssetCalibrationContext> {
  return jsonFetch<AssetCalibrationContext>("/api/modules/calibration", {
    method: "POST",
    body: JSON.stringify({ asset }),
  });
}

export async function getCalibrationReport(): Promise<CalibrationReport> {
  return jsonFetch<CalibrationReport>("/api/modules/calibration/report");
}

export async function listPredictions(): Promise<PredictionLogEntry[]> {
  return jsonFetch<PredictionLogEntry[]>(
    "/api/modules/calibration/predictions",
  );
}

export async function runComparables(
  asset: AssetInput,
  rnpv_inputs?: RnpvInputs,
  cohort_ids?: string[],
): Promise<ComparablesResult> {
  const data = await jsonFetch<{ comparables: ComparablesResult }>(
    "/api/modules/comparables",
    {
      method: "POST",
      body: JSON.stringify({ asset, rnpv_inputs, cohort_ids }),
    },
  );
  return data.comparables;
}
