// API client — thin wrappers around the backend module endpoints.
//
// All paths are relative ("/api/...") because next.config.js proxies them to
// the FastAPI service. That keeps the client free of base-URL knowledge and
// lets prod / staging / local use the same code.

import type {
  AdversaryOutput,
  AgentManifest,
  AnalysisDetail,
  AnalysisSummary,
  AssetCalibrationContext,
  AssetInput,
  AssetSizingInput,
  AutoDiligenceOutput,
  ComparablesResult,
  FundParameters,
  MLPosPriorResult,
  PortfolioRecommendation,
  MemoOutput,
  ModuleManifest,
  PoSResult,
  RnpvInputs,
  RnpvResult,
  ScorecardInput,
  ScorecardResult,
} from "./types";

export interface AgentError {
  status: number;
  message: string;
}

// v1.9.1 access gate (agent routes only). The backend gates the three
// money-spending agents behind a shared passphrase (ASCLEPIUS_ACCESS_PASSPHRASE
// Fly secret); see api/app/agents/routes.py. The owner shares a link of the
// form `…/?access=<passphrase>`; we read that token once, persist it to
// localStorage, and attach it as the `X-Asclepius-Access` header on agent
// calls. No token / wrong token → the backend 403s (only when the gate is
// active; it's inert until the secret is set). Deterministic module calls
// never send this header — they're public.
const ACCESS_STORAGE_KEY = "asclepius_access";

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const fromUrl = new URL(window.location.href).searchParams.get("access");
    if (fromUrl) {
      // Persist so the token survives navigation away from the ?access= link.
      window.localStorage.setItem(ACCESS_STORAGE_KEY, fromUrl);
      return fromUrl;
    }
    return window.localStorage.getItem(ACCESS_STORAGE_KEY);
  } catch {
    return null;
  }
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

// v1.8.0 Phase 5: getMLPosPriorModelInfo() hits the /model_info endpoint
// that's been live since v1.5.3.1 and exposes the full artifact metadata
// (AUC, Brier, conformal coverage, bootstrap band width, n_features, etc.).
// QuantBanner + ModelInfoRawCard both consume this — typed as a permissive
// Record so the live JSON can evolve without breaking the types.
export async function getMLPosPriorModelInfo(): Promise<Record<string, unknown>> {
  return jsonFetch<Record<string, unknown>>("/api/modules/ml_pos_prior/model_info");
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

// Fields ClientDiligenceRecord carries that the canonical pydantic
// DiligenceRecord doesn't accept. These are UI-state and module-input
// holders; the backend's strict (extra="forbid") schema 422s if any
// reach the route. Strip them before POSTing to the agent endpoint.
const CLIENT_ONLY_RECORD_FIELDS = [
  "rnpv_inputs",        // user-editable rNPV input bundle (lives in record on the client)
  "ml_pos",             // ml prior output cached on the client for HeroBanner
  "ml_pos_nct_id",      // NCT ID for the on-demand criteria fetch
  "ml_pos_criteria_text", // raw criteria text override
] as const;

function stripClientOnlyFields(
  record: Record<string, unknown>,
): Record<string, unknown> {
  const out = { ...record };
  for (const field of CLIENT_ONLY_RECORD_FIELDS) {
    delete out[field];
  }
  return out;
}

// FastAPI's 422 returns `detail: Array<{loc: [...], msg: "...", type: "..."}>`,
// not a string. The previous implementation read it as a string and the
// UI rendered `"[object Object],[object Object],…"`. Format it readably:
// "field msg; field msg; …" so the surfaced error is actionable.
function formatErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        if (typeof d === "string") return d;
        const obj = d as { loc?: unknown[]; msg?: string; type?: string };
        const loc = Array.isArray(obj.loc)
          ? obj.loc.filter((x) => x !== "body").join(".")
          : "";
        const msg = obj.msg ?? "validation error";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join("; ");
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return String(detail);
  }
}

// The agent endpoint differs from modules: it expects the full DiligenceRecord
// shape, not the {asset, pos, …} envelope each module uses. We accept a record
// shape from the caller, strip the client-only fields, and POST the result.
export async function runAgent<T>(
  agentId: string,
  record: Record<string, unknown>,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const accessToken = getAccessToken();
  if (accessToken) headers["X-Asclepius-Access"] = accessToken;
  const res = await fetch(`/api/agents/${agentId}/run`, {
    method: "POST",
    headers,
    cache: "no-store",
    body: JSON.stringify(stripClientOnlyFields(record)),
  });
  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body.detail !== undefined) detail = formatErrorDetail(body.detail);
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

// --- Saved analyses (persistence) -----------------------------------------
// The /api/analyses routes are gated behind the same shared passphrase as the
// agents, so these calls attach the X-Asclepius-Access header (read from the
// ?access= link / localStorage, exactly like runAgent).

// Save persists the canonical DiligenceRecord. Unlike agent calls we KEEP
// rnpv_inputs (a real DiligenceRecord field the reload needs to restore the
// economic assumptions) and strip only the pure UI-state fields.
const UI_ONLY_RECORD_FIELDS = [
  "ml_pos",
  "ml_pos_nct_id",
  "ml_pos_criteria_text",
] as const;

function stripUiOnlyFields(
  record: Record<string, unknown>,
): Record<string, unknown> {
  const out = { ...record };
  for (const field of UI_ONLY_RECORD_FIELDS) delete out[field];
  return out;
}

async function accessFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const accessToken = getAccessToken();
  if (accessToken) headers["X-Asclepius-Access"] = accessToken;
  const res = await fetch(path, { cache: "no-store", ...init, headers });
  if (!res.ok) {
    let detail: string = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (body.detail !== undefined) detail = formatErrorDetail(body.detail);
    } catch {
      // not JSON; keep statusText
    }
    const err: AgentError = { status: res.status, message: detail };
    throw err;
  }
  return res.json() as Promise<T>;
}

export async function saveAnalysis(
  record: Record<string, unknown>,
  label?: string | null,
): Promise<{ id: string }> {
  return accessFetch<{ id: string }>("/api/analyses", {
    method: "POST",
    body: JSON.stringify({
      record: stripUiOnlyFields(record),
      label: label ?? null,
    }),
  });
}

export async function listAnalyses(): Promise<AnalysisSummary[]> {
  const data = await accessFetch<{ analyses: AnalysisSummary[] }>("/api/analyses");
  return data.analyses;
}

export async function getAnalysis(id: string): Promise<AnalysisDetail> {
  return accessFetch<AnalysisDetail>(`/api/analyses/${id}`);
}

export async function deleteAnalysis(id: string): Promise<{ deleted: boolean }> {
  return accessFetch<{ deleted: boolean }>(`/api/analyses/${id}`, {
    method: "DELETE",
  });
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
