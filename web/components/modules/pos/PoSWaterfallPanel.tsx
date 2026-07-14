"use client";

import { useEffect, useState } from "react";

import { ProvenanceBadge, ProvenanceLegend } from "@/components/ProvenanceLegend";
import { runPoS } from "@/lib/api-client";
import { emitModuleLoad, type ModulePanelProps } from "@/lib/module-registry";
import type { PoSResult } from "@/lib/types";

export default function PoSWaterfallPanel({ record, setRecord }: ModulePanelProps) {
  const asset = record.asset;
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    emitModuleLoad("pos", "start");
    runPoS(asset)
      .then((pos) => {
        if (cancelled) return;
        setRecord({ pos });
        emitModuleLoad("pos", "done");
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
        emitModuleLoad("pos", "error");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(asset)]);

  const result = record.pos;

  if (loading && !result) return <PoSSkeleton />;
  if (error) return <PanelShell title="Probability of Success" error={error} />;
  if (!result) return <PoSSkeleton />;

  const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

  return (
    <PanelShell title="Probability of Success">
      <div className="mb-2.5 grid grid-cols-3 gap-2.5 tabular-nums">
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

      <details className="mt-3 rounded border border-border-dim bg-bg-deep p-2.5 text-xs text-text-primary">
        <summary className="cursor-pointer font-display text-[11px] font-semibold uppercase tracking-[0.15em] text-text-bright">
          Audit trail · {result.adjustments.length} adjustments
        </summary>
        <ol className="mt-2 space-y-2">
          {result.adjustments.map((a, i) => {
            const isReflexivity = a.name.toLowerCase().startsWith("reflexivity");
            return (
              <li
                key={i}
                className={
                  isReflexivity
                    ? "rounded border-l-2 border-magenta-bright bg-magenta-bright/5 pl-2"
                    : ""
                }
              >
                <div className="flex justify-between">
                  <span
                    className={
                      isReflexivity
                        ? "font-bold text-magenta-bright"
                        : "font-medium text-text-bright"
                    }
                  >
                    {a.name}
                  </span>
                  <span
                    className={
                      isReflexivity
                        ? "font-mono font-bold tabular-nums text-magenta-bright"
                        : "font-mono tabular-nums text-text-bright"
                    }
                  >
                    ×{a.multiplier.toFixed(3)}
                  </span>
                </div>
                <div className="mt-0.5 font-prose">{a.rationale}</div>
                <div className="mt-0.5 flex items-start gap-1.5">
                  <ProvenanceBadge source={a.source} />
                  <span className="italic text-text-dim">{a.source}</span>
                </div>
              </li>
            );
          })}
        </ol>
        <ProvenanceLegend className="mt-2.5 border-t border-border-dim pt-2" />
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
  type Step = {
    label: string;
    value: number;
    kind: "base" | "step" | "reflexivity" | "final";
  };
  let running = baseRate;
  const steps: Step[] = [{ label: "BIO base rate", value: baseRate, kind: "base" }];
  for (const adj of adjustments) {
    running *= adj.multiplier;
    // Reflexivity row visually distinct — it's the framework's headline differentiator.
    const isReflexivity = adj.name.toLowerCase().startsWith("reflexivity");
    steps.push({
      label: adj.name,
      value: Math.min(running, 1),
      kind: isReflexivity ? "reflexivity" : "step",
    });
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
              : s.kind === "reflexivity"
                ? "bg-magenta-bright"
                : "bg-cyan-faded";
        const labelClass =
          s.kind === "reflexivity"
            ? "truncate font-semibold text-magenta-bright"
            : "truncate text-text-primary";
        const valueClass =
          s.kind === "reflexivity"
            ? "w-12 text-right font-mono font-bold tabular-nums text-magenta-bright"
            : "w-12 text-right font-mono tabular-nums text-text-bright";
        return (
          <div key={i} className="grid grid-cols-[1fr_auto] items-center gap-3">
            <div className={labelClass}>{s.label}</div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-32 rounded bg-bg-panel-hover">
                <div className={`h-full rounded ${fill}`} style={{ width }} />
              </div>
              <span className={valueClass}>{(s.value * 100).toFixed(1)}%</span>
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
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <h2 className="mb-2.5 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
        {title}
      </h2>
      {loading ? <div className="h-32 animate-pulse rounded bg-bg-panel-hover" /> : null}
      {error ? (
        <div className="rounded border border-red-bright/30 bg-red-bright/10 p-2.5 text-sm text-red-bright">
          {error}
        </div>
      ) : null}
      {children}
    </section>
  );
}

// Structured skeleton matching the panel's actual layout: 3 top stats + a
// 6-row waterfall + an audit-trail row. Renders to the same height as the
// loaded panel (~280px) so the page below doesn't shift when the fetch
// resolves. The shimmer signals "computing" without the disorienting blank
// of an animate-pulse rectangle.
function PoSSkeleton() {
  return (
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <h2 className="mb-2.5 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
        Probability of Success
        <span className="ml-2 font-mono text-[9px] font-normal uppercase tracking-[0.15em] text-text-dim">
          · computing
        </span>
      </h2>
      <div className="mb-2.5 grid grid-cols-3 gap-2.5">
        {[0, 1, 2].map((i) => (
          <div key={i}>
            <div className="h-2 w-16 animate-pulse rounded bg-bg-panel-hover" />
            <div className="mt-1.5 h-4 w-12 animate-pulse rounded bg-bg-panel-hover" />
          </div>
        ))}
      </div>
      <div className="space-y-1">
        {[60, 80, 70, 55, 45, 65].map((w, i) => (
          <div key={i} className="grid grid-cols-[1fr_auto] items-center gap-3">
            <div className="h-2 w-32 animate-pulse rounded bg-bg-panel-hover" />
            <div className="flex items-center gap-2">
              <div className="h-3 w-32 rounded bg-bg-panel-hover">
                <div
                  className="h-full animate-pulse rounded bg-cyan-faded/30"
                  style={{ width: `${w}%` }}
                />
              </div>
              <div className="h-2 w-10 animate-pulse rounded bg-bg-panel-hover" />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-3 h-7 animate-pulse rounded border border-border-dim bg-bg-deep" />
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
      <div className="font-display text-[9px] uppercase tracking-[0.15em] text-text-dim">
        {label}
      </div>
      <div
        className={`mt-0.5 font-mono text-sm font-bold tabular-nums ${
          accent ? "text-cyan-bright" : "text-text-bright"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
