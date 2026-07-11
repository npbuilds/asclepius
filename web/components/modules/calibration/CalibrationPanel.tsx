"use client";

// Segment calibration reference. Shows, for THIS asset's segment (therapeutic
// area · modality · capital tier), how the framework's estimates have compared
// to observed outcomes in a historical reference cohort. This is per-asset
// analysis context — NOT a forecasting track record (the aggregate Brier
// dashboard and the public prediction log were cut in the R2 rescope). The
// reference cohort is small and survivorship-flavored; the panel says so.

import { useEffect, useState } from "react";

import { runCalibration } from "@/lib/api-client";
import { emitModuleLoad, type ModulePanelProps } from "@/lib/module-registry";
import type { AssetCalibrationContext } from "@/lib/types";

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtBrier(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toFixed(3);
}

// Brier score color heuristic. Lower = better calibration.
function brierColor(v: number | null | undefined): string {
  if (v == null) return "text-text-dim";
  if (v < 0.1) return "text-green-bright";
  if (v < 0.25) return "text-amber-bright";
  return "text-red-bright";
}

export default function CalibrationPanel({ record }: ModulePanelProps) {
  const [ctx, setCtx] = useState<AssetCalibrationContext | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    emitModuleLoad("calibration", "start");
    runCalibration(record.asset)
      .then((c) => {
        if (cancelled) return;
        setCtx(c);
        emitModuleLoad("calibration", "done");
      })
      .catch((e) => {
        if (cancelled) return;
        setError(String(e));
        emitModuleLoad("calibration", "error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(record.asset)]);

  if (error) {
    return (
      <section className="rounded border border-red-bright/30 bg-red-bright/10 p-3 text-sm text-red-bright">
        Calibration reference unavailable: {error}
      </section>
    );
  }

  if (!ctx) {
    return (
      <section className="rounded border border-border-dim bg-bg-panel p-3">
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
            Segment reference
            <span className="ml-2 font-mono text-[9px] font-normal uppercase tracking-[0.15em] text-text-dim">
              · computing
            </span>
          </h2>
          <div className="h-2 w-32 animate-pulse rounded bg-bg-panel-hover" />
        </div>
        <div className="rounded border border-border-dim bg-bg-deep p-2.5">
          <div className="h-2 w-32 animate-pulse rounded bg-bg-panel-hover" />
          <div className="mt-2 grid grid-cols-3 gap-2">
            {[0, 1, 2].map((i) => (
              <div key={i}>
                <div className="h-1.5 w-12 animate-pulse rounded bg-bg-panel-hover" />
                <div className="mt-1 h-3 w-12 animate-pulse rounded bg-bg-panel-hover" />
              </div>
            ))}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
          Segment reference
        </h2>
        <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
          n={ctx.segment_n_resolved} in segment · {ctx.overall_n_resolved} total
        </span>
      </div>

      <div className="rounded border border-magenta-bright/30 bg-magenta-bright/5 p-2.5">
        <div className="font-mono text-[9px] uppercase tracking-[0.15em] text-magenta-bright">
          ● this asset&apos;s segment vs the reference cohort
        </div>
        <div className="mt-0.5 font-mono text-[11px] text-text-bright">
          {ctx.asset_segment_label}
        </div>
        <div className="mt-2 grid grid-cols-3 gap-2 font-mono tabular-nums">
          <div>
            <div className="text-[9px] uppercase tracking-[0.1em] text-text-dim">
              Brier
            </div>
            <div className={`text-sm font-bold ${brierColor(ctx.segment_brier)}`}>
              {fmtBrier(ctx.segment_brier)}
            </div>
          </div>
          <div>
            <div className="text-[9px] uppercase tracking-[0.1em] text-text-dim">
              Mean pred
            </div>
            <div className="text-sm text-text-bright">
              {fmtPct(ctx.segment_mean_predicted)}
            </div>
          </div>
          <div>
            <div className="text-[9px] uppercase tracking-[0.1em] text-text-dim">
              Mean obs
            </div>
            <div className="text-sm text-text-bright">
              {fmtPct(ctx.segment_mean_observed)}
            </div>
          </div>
        </div>
      </div>

      <details className="mt-2 rounded border border-amber-bright/30 bg-amber-bright/5 p-2">
        <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.15em] text-amber-bright">
          ● reference-cohort caveat
        </summary>
        <p className="mt-1.5 font-prose text-[11px] leading-snug text-text-primary">
          {ctx.sample_size_disclaimer} The reference cohort is small and
          survivorship-flavored (weighted toward known approvals), so treat the
          segment figures as directional context, not a calibrated claim. This
          is analysis context — the framework&apos;s value is its reasoning
          structure, not a forecasting record.
        </p>
      </details>
    </section>
  );
}
