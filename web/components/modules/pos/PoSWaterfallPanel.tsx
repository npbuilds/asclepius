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

      <details className="mt-4 rounded border border-ink-200 bg-ink-50 p-3 text-xs text-ink-600">
        <summary className="cursor-pointer font-medium text-ink-900">
          Audit trail ({result.adjustments.length} adjustments)
        </summary>
        <ol className="mt-2 space-y-2">
          {result.adjustments.map((a, i) => (
            <li key={i}>
              <div className="flex justify-between font-medium text-ink-900">
                <span>{a.name}</span>
                <span className="font-mono tabular-nums">
                  ×{a.multiplier.toFixed(3)}
                </span>
              </div>
              <div className="mt-0.5">{a.rationale}</div>
              <div className="mt-0.5 italic text-ink-400">{a.source}</div>
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
            ? "bg-ink-400"
            : s.kind === "final"
              ? "bg-accent-600"
              : "bg-ink-600";
        return (
          <div key={i} className="grid grid-cols-[1fr_auto] items-center gap-3">
            <div className="truncate text-ink-600">{s.label}</div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-32 rounded bg-ink-100">
                <div className={`h-full rounded ${fill}`} style={{ width }} />
              </div>
              <span className="w-12 text-right font-mono tabular-nums text-ink-900">
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
    <section className="rounded-lg border border-ink-200 bg-white p-5">
      <h2 className="mb-4 font-serif text-lg text-ink-900">{title}</h2>
      {loading ? <div className="h-32 animate-pulse rounded bg-ink-100" /> : null}
      {error ? (
        <div className="rounded border border-bad-500/30 bg-bad-500/10 p-3 text-sm text-bad-500">
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
      <div className="text-[10px] uppercase tracking-wide text-ink-400">{label}</div>
      <div
        className={`mt-0.5 font-medium ${accent ? "text-accent-700" : "text-ink-900"}`}
      >
        {value}
      </div>
    </div>
  );
}
