"use client";

// Auto-Diligence panel — takes record.asset.asset_name and runs the agent
// (web-search-enabled Opus 4.7) to extract structured AssetInput fields with
// citations from a high-signal allowlist (CT.gov, SEC EDGAR, FDA, EMA, top
// journals, newswires). User can then "Apply" the result to overwrite the
// diligence record's asset field, after which the four module panels
// recompute against the new values.
//
// Architectural grounding: Bioptic (arXiv 2508.16571v4) single-pass
// extractor. Validator pass is deferred to v1.1.4 — for v1.1.2 the model is
// trusted on its own citation discipline.

import { useState } from "react";

import { type AgentError, runAutoDiligence } from "@/lib/api-client";
import type { ClientDiligenceRecord } from "@/lib/module-registry";
import type {
  AssetInput,
  AutoDiligenceCitation,
  AutoDiligenceOutput,
  CapitalPosition,
  FieldConfidence,
  Modality,
  Phase,
  TherapeuticArea,
} from "@/lib/types";

const CONFIDENCE_COLOR: Record<FieldConfidence, string> = {
  high: "text-green-bright",
  medium: "text-amber-bright",
  low: "text-red-bright",
  missing: "text-text-dim",
};

// Fields rendered in the extracted-summary list, in display order.
const FIELD_ORDER: { key: string; label: string }[] = [
  { key: "asset_name", label: "Asset" },
  { key: "sponsor", label: "Sponsor" },
  { key: "phase", label: "Phase" },
  { key: "modality", label: "Modality" },
  { key: "therapeutic_area", label: "TA" },
  { key: "indication", label: "Indication" },
  { key: "target", label: "Target" },
  { key: "mechanism", label: "Mechanism" },
  { key: "route_of_administration", label: "Route" },
  { key: "regulatory_designations", label: "Designations" },
  { key: "biomarker_enrichment", label: "Biomarker enr." },
  { key: "target_validated", label: "Target validated" },
  { key: "num_competitors", label: "# competitors" },
  { key: "named_competitors", label: "Competitors" },
  { key: "capital_position", label: "Capital" },
];

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "—";
  if (typeof v === "boolean") return v ? "yes" : "no";
  return String(v);
}

export function AutoDiligencePanel({
  record,
  setRecord,
}: {
  record: ClientDiligenceRecord;
  setRecord: (
    update:
      | Partial<ClientDiligenceRecord>
      | ((prev: ClientDiligenceRecord) => ClientDiligenceRecord),
  ) => void;
}) {
  const [result, setResult] = useState<AutoDiligenceOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AgentError | null>(null);

  async function research() {
    setLoading(true);
    setError(null);
    try {
      const out = await runAutoDiligence(record as unknown as Record<string, unknown>);
      setResult(out);
    } catch (e) {
      setError(e as AgentError);
    } finally {
      setLoading(false);
    }
  }

  // v1.6 (custom-asset path): Auto-Diligence returns NCT IDs as URLs in the
  // citations array (e.g., "https://clinicaltrials.gov/study/NCT06119581"),
  // not as a structured field. Extract the first one so MLPosPriorPanel can
  // embed the trial's eligibility criteria for a custom asset. Without this,
  // the ML PoS Prior would fall back to its no-NCT path on every custom
  // asset — leaving the Quant persona's most load-bearing surface blank.
  function extractNctFromCitations(): string | null {
    const re = /NCT\d{8}/;
    for (const c of result?.citations || []) {
      const url = c.url ?? "";
      const m = url.match(re);
      if (m) return m[0];
    }
    return null;
  }

  function applyToRecord() {
    if (!result) return;
    const e = result.extracted;
    const merged: AssetInput = {
      ...record.asset,
      asset_name: e.asset_name || record.asset.asset_name,
      sponsor: e.sponsor ?? record.asset.sponsor,
      phase: (e.phase as Phase) || record.asset.phase,
      therapeutic_area:
        (e.therapeutic_area as TherapeuticArea) || record.asset.therapeutic_area,
      modality: (e.modality as Modality) || record.asset.modality,
      indication: e.indication ?? record.asset.indication,
      target: e.target ?? record.asset.target,
      mechanism: e.mechanism ?? record.asset.mechanism,
      regulatory_designations:
        (e.regulatory_designations as AssetInput["regulatory_designations"]) ??
        record.asset.regulatory_designations,
      num_competitors:
        typeof e.num_competitors === "number"
          ? e.num_competitors
          : record.asset.num_competitors,
      target_validated:
        typeof e.target_validated === "boolean"
          ? e.target_validated
          : record.asset.target_validated,
      biomarker_enrichment:
        typeof e.biomarker_enrichment === "boolean"
          ? e.biomarker_enrichment
          : record.asset.biomarker_enrichment,
      capital_position:
        (e.capital_position as CapitalPosition) || record.asset.capital_position,
    };
    // Preserve any user-supplied NCT ID that's already on the record (e.g.
    // analyst typed it explicitly); only auto-fill from citations when the
    // current value is empty.
    const nctFromCitations = extractNctFromCitations();
    const ml_pos_nct_id = record.ml_pos_nct_id || nctFromCitations || null;
    setRecord({ asset: merged, ml_pos_nct_id });
  }

  // Group citations by field for easy lookup
  const citationsByField: Record<string, AutoDiligenceCitation[]> = {};
  for (const c of result?.citations || []) {
    const k = c.field || "_unfielded";
    if (!citationsByField[k]) citationsByField[k] = [];
    citationsByField[k].push(c);
  }

  return (
    <section className="rounded border border-magenta-bright/30 bg-magenta-bright/5 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-magenta-bright">
          Auto-Diligence · agent
        </h2>
        <button
          type="button"
          onClick={research}
          disabled={loading}
          className="rounded border border-magenta-bright bg-magenta-bright/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-magenta-bright hover:bg-magenta-bright/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading
            ? "[ researching… ]"
            : result
              ? "[ re-research ]"
              : "[ research from web → ]"}
        </button>
      </div>

      <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-text-dim">
        Web search restricted to CT.gov · SEC EDGAR · FDA · EMA · NEJM · Nature · Cell · newswires
      </p>

      {error ? (
        <div className="rounded border border-red-bright/30 bg-red-bright/10 p-2.5 font-mono text-[11px] text-red-bright">
          {error.status === 503
            ? "● No live agent key configured on this deploy. Adagrasib is cached; other assets need ANTHROPIC_API_KEY."
            : `● Agent error (${error.status}): ${error.message}`}
        </div>
      ) : null}

      {result ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-text-dim">
            <span>
              {result.from_cache
                ? "● cached"
                : `● ${result.model_used} · ${result.web_searches_used} search${result.web_searches_used === 1 ? "" : "es"}`}
            </span>
            <span className="ml-auto">
              {new Date(result.generated_at).toISOString().slice(0, 10)}
            </span>
            <button
              type="button"
              onClick={applyToRecord}
              className="rounded border border-green-bright bg-green-bright/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-green-bright hover:bg-green-bright/20"
            >
              [ apply → record ]
            </button>
          </div>

          <dl className="space-y-1 font-mono text-[11px]">
            {FIELD_ORDER.map(({ key, label }) => {
              const value = (result.extracted as unknown as Record<string, unknown>)[key];
              const conf = result.field_confidence[key] || "missing";
              const cites = citationsByField[key] || [];
              return (
                <div
                  key={key}
                  className="grid grid-cols-[110px_auto_1fr_auto] items-baseline gap-2"
                >
                  <span className="uppercase tracking-wider text-text-dim">
                    {label}
                  </span>
                  <span className={`uppercase tracking-wider ${CONFIDENCE_COLOR[conf]}`}>
                    ●
                  </span>
                  <span className="font-prose text-[12px] normal-case tracking-normal text-text-primary">
                    {formatValue(value)}
                  </span>
                  <span className="flex gap-1">
                    {cites.slice(0, 3).map((c, i) => (
                      <a
                        key={i}
                        href={c.url}
                        target="_blank"
                        rel="noreferrer"
                        title={c.span}
                        className="rounded border border-cyan-bright/30 bg-cyan-bright/10 px-1 text-[9px] uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
                      >
                        {new URL(c.url).hostname.replace(/^www\./, "").split(".")[0]}
                      </a>
                    ))}
                  </span>
                </div>
              );
            })}
          </dl>

          {citationsByField["_unfielded"]?.length ? (
            <details className="rounded border border-border-dim bg-bg-panel p-2 font-mono text-[10px]">
              <summary className="cursor-pointer uppercase tracking-wider text-text-dim">
                {citationsByField["_unfielded"].length} additional source
                {citationsByField["_unfielded"].length === 1 ? "" : "s"} consulted
              </summary>
              <ul className="mt-1 space-y-0.5">
                {citationsByField["_unfielded"].map((c, i) => (
                  <li key={i} className="truncate text-text-primary">
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-cyan-bright hover:underline"
                    >
                      {c.title || c.url}
                    </a>
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
