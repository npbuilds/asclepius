"use client";

// Calibration Dashboard panel. Renders below the four core analysis modules.
// Shows: (1) the asset's segment-specific Brier + calibration gap, (2) the
// full per-segment table, (3) the prediction log on demand.
//
// Designed to be intellectually honest: the survivorship-biased seed cohort
// surfaces a *high* Brier score, which the dashboard acknowledges directly.
// "We're shipping the discipline; v1.6+ accumulates the unbiased sample."

import { useEffect, useState } from "react";

import {
  getCalibrationReport,
  listPredictions,
  runCalibration,
} from "@/lib/api-client";
import type { ModulePanelProps } from "@/lib/module-registry";
import type {
  AssetCalibrationContext,
  CalibrationReport,
  CalibrationSegmentStats,
  PredictionLogEntry,
} from "@/lib/types";

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function fmtBrier(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toFixed(3);
}

// Brier score color heuristic. Lower = better calibration.
// 0.00-0.10 = green (well-calibrated); 0.10-0.25 = amber; >0.25 = red (high error).
// 0.25 is the benchmark for a 50/50 coin flip.
function brierColor(v: number | null | undefined): string {
  if (v == null) return "text-text-dim";
  if (v < 0.1) return "text-green-bright";
  if (v < 0.25) return "text-amber-bright";
  return "text-red-bright";
}

export default function CalibrationPanel({ record }: ModulePanelProps) {
  const [ctx, setCtx] = useState<AssetCalibrationContext | null>(null);
  const [report, setReport] = useState<CalibrationReport | null>(null);
  const [log, setLog] = useState<PredictionLogEntry[] | null>(null);
  const [showLog, setShowLog] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    Promise.all([runCalibration(record.asset), getCalibrationReport()])
      .then(([c, r]) => {
        if (cancelled) return;
        setCtx(c);
        setReport(r);
      })
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(record.asset)]);

  async function toggleLog() {
    if (showLog) {
      setShowLog(false);
      return;
    }
    if (!log) {
      try {
        const data = await listPredictions();
        setLog(data);
      } catch (e) {
        setError(String(e));
        return;
      }
    }
    setShowLog(true);
  }

  if (error) {
    return (
      <section className="rounded border border-red-bright/30 bg-red-bright/10 p-3 text-sm text-red-bright">
        Calibration unavailable: {error}
      </section>
    );
  }

  if (!ctx || !report) {
    return (
      <section className="rounded border border-border-dim bg-bg-panel p-3">
        <h2 className="mb-2.5 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
          Calibration Dashboard
        </h2>
        <div className="h-24 animate-pulse rounded bg-bg-panel-hover" />
      </section>
    );
  }

  return (
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
          Calibration Dashboard
        </h2>
        <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
          n={report.n_resolved} resolved · {report.n_total_predictions - report.n_resolved} pending
        </span>
      </div>

      <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {/* Asset segment card */}
        <div className="rounded border border-magenta-bright/30 bg-magenta-bright/5 p-2.5">
          <div className="font-mono text-[9px] uppercase tracking-[0.15em] text-magenta-bright">
            ● this asset's segment
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
          <div className="mt-1 font-mono text-[9px] uppercase tracking-wider text-text-dim">
            n={ctx.segment_n_resolved} resolved in segment
          </div>
        </div>

        {/* Overall card */}
        <div className="rounded border border-border-dim bg-bg-deep p-2.5">
          <div className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
            ● framework overall
          </div>
          <div className="mt-0.5 font-mono text-[11px] text-text-bright">
            all resolved predictions
          </div>
          <div className="mt-2 grid grid-cols-3 gap-2 font-mono tabular-nums">
            <div>
              <div className="text-[9px] uppercase tracking-[0.1em] text-text-dim">
                Brier
              </div>
              <div className={`text-sm font-bold ${brierColor(report.overall.brier_score)}`}>
                {fmtBrier(report.overall.brier_score)}
              </div>
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-[0.1em] text-text-dim">
                Mean pred
              </div>
              <div className="text-sm text-text-bright">
                {fmtPct(report.overall.mean_predicted)}
              </div>
            </div>
            <div>
              <div className="text-[9px] uppercase tracking-[0.1em] text-text-dim">
                Mean obs
              </div>
              <div className="text-sm text-text-bright">
                {fmtPct(report.overall.mean_observed)}
              </div>
            </div>
          </div>
          <div className="mt-1 font-mono text-[9px] uppercase tracking-wider text-text-dim">
            calibration gap{" "}
            {report.overall.calibration_gap != null
              ? `${(report.overall.calibration_gap * 100).toFixed(1)}pp`
              : "—"}{" "}
            (pred − obs)
          </div>
        </div>
      </div>

      {/* Per-capital-position breakdown — this is the one the reflexivity adjustment hinges on */}
      <div className="mb-3">
        <div className="mb-1 font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
          ── by capital position (reflexivity tiers) ──
        </div>
        <table className="w-full font-mono text-[11px] tabular-nums">
          <thead>
            <tr className="text-left text-[9px] uppercase tracking-wider text-text-dim">
              <th className="py-0.5">Tier</th>
              <th className="py-0.5 text-right">n</th>
              <th className="py-0.5 text-right">Brier</th>
              <th className="py-0.5 text-right">Pred</th>
              <th className="py-0.5 text-right">Obs</th>
              <th className="py-0.5 text-right">Gap</th>
            </tr>
          </thead>
          <tbody>
            {report.by_capital_position.map((s) => (
              <SegmentRow key={s.segment_value} s={s} />
            ))}
          </tbody>
        </table>
      </div>

      <details className="rounded border border-amber-bright/30 bg-amber-bright/5 p-2">
        <summary className="cursor-pointer font-mono text-[10px] uppercase tracking-[0.15em] text-amber-bright">
          ● sample-size disclaimer
        </summary>
        <p className="mt-1.5 font-prose text-[11px] leading-snug text-text-primary">
          {report.sample_size_disclaimer} The v1.5 seed cohort is also
          survivorship-biased toward known approvals (kinase-inhibitor M&A
          comps) — observed-success rate of {fmtPct(report.overall.mean_observed)}{" "}
          is much higher than the population prior. The dashboard is shipping
          the discipline, not yet a calibrated claim.
        </p>
      </details>

      <div className="mt-2 flex justify-end">
        <button
          type="button"
          onClick={toggleLog}
          className="rounded border border-cyan-bright/30 bg-cyan-bright/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
        >
          {showLog ? "[ hide log ]" : "[ view prediction log ]"}
        </button>
      </div>

      {showLog && log ? (
        <div className="mt-2 overflow-x-auto rounded border border-border-dim bg-bg-deep p-2">
          <table className="w-full font-mono text-[10px] tabular-nums">
            <thead>
              <tr className="text-left text-[9px] uppercase tracking-wider text-text-dim">
                <th className="py-0.5 pr-2">Date</th>
                <th className="py-0.5 pr-2">Asset</th>
                <th className="py-0.5 pr-2">Tier</th>
                <th className="py-0.5 pr-2 text-right">Pred</th>
                <th className="py-0.5 pr-2">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {log.map((p) => (
                <tr key={p.id} className="border-t border-border-dim/30">
                  <td className="py-0.5 pr-2 text-text-dim">
                    {p.prediction_date}
                  </td>
                  <td className="py-0.5 pr-2 text-text-bright">{p.asset_name}</td>
                  <td className="py-0.5 pr-2 text-text-dim">
                    {p.capital_position}
                  </td>
                  <td className="py-0.5 pr-2 text-right text-text-bright">
                    {(p.predicted_pos * 100).toFixed(1)}%
                  </td>
                  <td className="py-0.5 pr-2">
                    {p.outcome === 1 ? (
                      <span className="text-green-bright">● approved</span>
                    ) : p.outcome === 0 ? (
                      <span className="text-red-bright">● failed</span>
                    ) : (
                      <span className="text-text-dim">○ pending</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

function SegmentRow({ s }: { s: CalibrationSegmentStats }) {
  return (
    <tr className="border-t border-border-dim/30">
      <td className="py-0.5 text-text-bright">{s.segment_value}</td>
      <td className="py-0.5 text-right text-text-dim">{s.n_resolved}</td>
      <td className={`py-0.5 text-right font-bold ${brierColor(s.brier_score)}`}>
        {fmtBrier(s.brier_score)}
      </td>
      <td className="py-0.5 text-right text-text-bright">
        {fmtPct(s.mean_predicted)}
      </td>
      <td className="py-0.5 text-right text-text-bright">
        {fmtPct(s.mean_observed)}
      </td>
      <td className="py-0.5 text-right text-text-dim">
        {s.calibration_gap != null
          ? `${(s.calibration_gap * 100).toFixed(1)}pp`
          : "—"}
      </td>
    </tr>
  );
}
