// API client — thin wrappers around the backend module endpoints.
//
// All paths are relative ("/api/...") because next.config.js proxies them to
// the FastAPI service. That keeps the client free of base-URL knowledge and
// lets prod / staging / local use the same code.

import type {
  AssetInput,
  ComparablesResult,
  ModuleManifest,
  PoSResult,
  RnpvInputs,
  RnpvResult,
  ScorecardInput,
  ScorecardResult,
} from "./types";

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
