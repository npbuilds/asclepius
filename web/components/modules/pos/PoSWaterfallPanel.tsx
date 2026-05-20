"use client";

import { useEffect, useState } from "react";

import { runPoS } from "@/lib/api-client";
import type { ModulePanelProps } from "@/lib/module-registry";
import type { PoSResult } from "@/lib/types";

export default function PoSWaterfallPanel({ record, setRecord }: ModulePanelProps) {
  const asset = record.asset;
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    runPoS(asset)
      .then((pos) => !cancelled && setRecord({ pos }))
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(asset)]);

  const result = record.pos;

  if (loading && !result) return <PanelShell title="Probability of Success" loading />;
  if (error) return <PanelShell title="Probability of Success" error={error} />;
  if (!result) return null;

  const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

  return (
    <PanelShell title="Probability of Success">
      <div className="mb-4 grid grid-cols-3 gap-3 text-sm tabular-nums">
        <Stat label="Base rate" value={pct(result.base_rate)} />
        <Stat label="Final LOA" value={pct(result.final_loa)} accent />
        <Stat
          label="Confidence range"
          value={`${pct(result.confidence_low)} – ${pct(result.confidence_high)}`}
        />
      </div>

      <Waterfall
        baseRate={result.base_rate}
        adjustments={result.adjustments}
        finalLoa={result.final_loa}
      />

      <details className="mt-4 rounded border border-border-dim bg-bg-deep p-3 text-xs text-text-primary">
        <summary className="cursor-pointer font-medium text-text-bright">
          Audit trail ({result.adjustments.length} adjustments)
        </summary>
        <ol className="mt-2 space-y-2">
          {result.adjustments.map((a, i) => (
            <li key={i}>
              <div className="flex justify-between font-medium text-text-bright">
                <span>{a.name}</span>
                <span className="font-mono tabular-nums">
                  ×{a.multiplier.toFixed(3)}
                </span>
              </div>
              <div className="mt-0.5">{a.rationale}</div>
              <div className="mt-0.5 italic text-text-dim">{a.source}</div>
            </li>
          ))}
        </ol>
      </details>
    </PanelShell>
  );
}

function Waterfall({
  baseRate,
  adjustments,
  finalLoa,
}: {
  baseRate: number;
  adjustments: PoSResult["adjustments"];
  finalLoa: number;
}) {
  type Step = { label: string; value: number; kind: "base" | "step" | "final" };
  let running = baseRate;
  const steps: Step[] = [{ label: "BIO base rate", value: baseRate, kind: "base" }];
  for (const adj of adjustments) {
    running *= adj.multiplier;
    steps.push({ label: adj.name, value: Math.min(running, 1), kind: "step" });
  }
  steps.push({ label: "Final LOA", value: finalLoa, kind: "final" });

  const max = Math.max(...steps.map((s) => s.value));

  return (
    <div className="space-y-1 text-xs">
      {steps.map((s, i) => {
        const width = `${(s.value / max) * 100}%`;
        const fill =
          s.kind === "base"
            ? "bg-text-dim"
            : s.kind === "final"
              ? "bg-cyan-bright"
              : "bg-cyan-faded";
        return (
          <div key={i} className="grid grid-cols-[1fr_auto] items-center gap-3">
            <div className="truncate text-text-primary">{s.label}</div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-32 rounded bg-bg-panel-hover">
                <div className={`h-full rounded ${fill}`} style={{ width }} />
              </div>
              <span className="w-12 text-right font-mono tabular-nums text-text-bright">
                {(s.value * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PanelShell({
  title,
  children,
  loading,
  error,
}: {
  title: string;
  children?: React.ReactNode;
  loading?: boolean;
  error?: string;
}) {
  return (
    <section className="rounded border border-border-dim bg-bg-panel p-5">
      <h2 className="mb-4 font-display text-lg text-text-bright">{title}</h2>
      {loading ? <div className="h-32 animate-pulse rounded bg-bg-panel-hover" /> : null}
      {error ? (
        <div className="rounded border border-red-bright/30 bg-red-bright/10 p-3 text-sm text-red-bright">
          {error}
        </div>
      ) : null}
      {children}
    </section>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-text-dim">{label}</div>
      <div
        className={`mt-0.5 font-medium ${accent ? "text-cyan-bright" : "text-text-bright"}`}
      >
        {value}
      </div>
    </div>
  );
}
