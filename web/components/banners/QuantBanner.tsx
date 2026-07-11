"use client";

// QuantBanner — v1.8.0 Phase 5.
//
// Banner variant for the Quant / Calibration-focused persona. Defining
// trait: this reader doesn't trust opaque recommendation chips and wants
// raw model honesty. The banner deliberately *omits* the recommendation
// chip (which depends on scorecard's qualitative pillar weights) and
// surfaces the inputs that let the reader synthesize their own view:
//
//   - test AUC + Brier (model accuracy on held-out HINT test set)
//   - per-phase conformal coverage (frequentist calibration check)
//   - bootstrap band width on test (epistemic uncertainty proxy)
//   - ML-vs-rule disagreement (the framework's two-axis read)
//
// Below the banner the Calibration section renders the calibration
// dashboard + ml_pos_prior modules (per QUANT_SECTIONS), with the
// ModelInfoRawCard as a leading element exposing the literal JSON.
//
// Where the data comes from: /api/modules/ml_pos_prior/model_info (the
// endpoint v1.5.3.1 added). Fetched once on mount, no record-state
// dependency, no refetch on persona changes.

import { useEffect, useState } from "react";

import { getMLPosPriorModelInfo } from "@/lib/api-client";
import {
  catalystLine,
  subtitleLine,
} from "@/lib/banner-stats";
import type { ClientDiligenceRecord } from "@/lib/module-registry";

interface QuantBannerProps {
  record: ClientDiligenceRecord;
}

function pct(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return "—%";
  return `${(value * 100).toFixed(digits)}%`;
}

function num(value: number | null | undefined, digits = 4): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toFixed(digits);
}

// Extract the fields we display from the model_info JSON. Permissive —
// the endpoint is the source of truth; if a field is absent or
// non-numeric, render as "—" / "—%". No type-check failures on JSON drift.
function unpack(info: Record<string, unknown> | null): {
  testAuc: number | null;
  testBrier: number | null;
  bootstrapBandWidth: number | null;
  bootstrapN: number | null;
  modelKind: string | null;
  coverage: Record<string, number | null>;
} {
  if (!info) {
    return {
      testAuc: null,
      testBrier: null,
      bootstrapBandWidth: null,
      bootstrapN: null,
      modelKind: null,
      coverage: { phase_1: null, phase_2: null, phase_3: null, overall: null },
    };
  }
  const asNum = (v: unknown): number | null =>
    typeof v === "number" && Number.isFinite(v) ? v : null;
  const cov = (info.conformal_test_coverage ?? {}) as Record<string, unknown>;
  return {
    testAuc: asNum(info.test_auc),
    testBrier: asNum(info.test_brier),
    bootstrapBandWidth: asNum(info.bootstrap_avg_band_width_test),
    bootstrapN: asNum(info.bootstrap_n_models),
    modelKind: typeof info.model_kind === "string" ? info.model_kind : null,
    coverage: {
      phase_1: asNum(cov.phase_1),
      phase_2: asNum(cov.phase_2),
      phase_3: asNum(cov.phase_3),
      overall: asNum(cov.overall),
    },
  };
}

export default function QuantBanner({ record }: QuantBannerProps) {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMLPosPriorModelInfo()
      .then((data) => {
        if (!cancelled) setInfo(data);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const subtitle = subtitleLine(record);
  const catalyst = catalystLine(record);
  const ml = record.ml_pos;
  const unpacked = unpack(info);

  return (
    <section
      aria-label="Quant calibration summary"
      className="mb-4 rounded border border-border-dim bg-bg-panel p-3"
    >
      {/* Top row — asset identity + model kind */}
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2 border-b border-border-dim/60 pb-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
          {subtitle}
        </span>
        <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
          {unpacked.modelKind ?? "model loading…"}
        </span>
      </div>

      {/* Accuracy stats — AUC + Brier + bootstrap band width */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2 md:grid-cols-4">
        <Stat
          label="Test AUC (union)"
          value={num(unpacked.testAuc, 4)}
          secondary="HINT∪CTO held-out"
        />
        <Stat
          label="Test Brier"
          value={num(unpacked.testBrier, 4)}
          secondary="lower is better"
        />
        <Stat
          label="Bootstrap band"
          value={pct(unpacked.bootstrapBandWidth, 1)}
          secondary={
            unpacked.bootstrapN != null
              ? `n=${unpacked.bootstrapN} LGBM resamples`
              : null
          }
        />
        <Stat
          label="ML − rule"
          value={
            ml ? `${ml.disagreement_pp > 0 ? "+" : ""}${ml.disagreement_pp.toFixed(1)}pp` : "—"
          }
          secondary={ml ? ml.disagreement_level : null}
        />
      </div>

      {/* Per-phase conformal coverage table */}
      <div className="mt-3 border-t border-border-dim/60 pt-2">
        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
          Mondrian split-conformal test coverage (target ≥90%)
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-2 font-mono text-[12px] tabular-nums sm:grid-cols-4">
          <CoverageCell label="phase_1" value={unpacked.coverage.phase_1} />
          <CoverageCell label="phase_2" value={unpacked.coverage.phase_2} />
          <CoverageCell label="phase_3" value={unpacked.coverage.phase_3} />
          <CoverageCell label="overall" value={unpacked.coverage.overall} />
        </div>

      </div>

      {/* Bottom — catalyst (terse for the quant reader) */}
      <div className="mt-3 border-t border-border-dim/60 pt-2">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
            Next catalyst
          </span>
          <span className="font-prose text-[11px] text-text-primary sm:text-right">
            {catalyst}
          </span>
        </div>
      </div>

      {error ? (
        <p className="mt-2 font-mono text-[10px] text-red-bright">
          /model_info unavailable: {error}
        </p>
      ) : null}
    </section>
  );
}

interface StatProps {
  label: string;
  value: string;
  secondary: string | null;
}

function Stat({ label, value, secondary }: StatProps) {
  return (
    <div className="flex flex-col">
      <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
        {label}
      </span>
      <span className="font-mono text-[16px] font-bold tabular-nums text-text-bright">
        {value}
      </span>
      {secondary ? (
        <span className="font-mono text-[10px] text-text-dim">
          {secondary}
        </span>
      ) : null}
    </div>
  );
}

interface CoverageCellProps {
  label: string;
  value: number | null;
}

function CoverageCell({ label, value }: CoverageCellProps) {
  // Color-code: green if ≥90%, amber 85-89.9%, red <85%.
  const color =
    value == null
      ? "text-text-dim"
      : value >= 0.9
        ? "text-green-bright"
        : value >= 0.85
          ? "text-amber-bright"
          : "text-red-bright";
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-[0.1em] text-text-dim">
        {label}
      </span>
      <span className={`font-bold ${color}`}>{pct(value, 1)}</span>
    </div>
  );
}

