"use client";

// ML PoS Prior panel — the rule-smoothed logistic-surrogate path alongside
// the deterministic PoS chain. Renders immediately below the PoS waterfall.
//
// Three-way readout: BIO base rate | Rule-based final LOA | ML surrogate.
// Disagreement chip surfaces composition-rule sensitivity (multiplicative
// vs. additive log-odds) — NOT independent clinical evidence. See
// methodology/09-ml-pos-prior.md for the honest framing.

import { useEffect, useState } from "react";

import { runMLPosPrior } from "@/lib/api-client";
import type { ModulePanelProps } from "@/lib/module-registry";
import type { DisagreementLevel, MLPosPriorResult } from "@/lib/types";

const DISAGREEMENT_COLOR: Record<DisagreementLevel, string> = {
  aligned: "bg-green-bright/15 text-green-bright border-green-bright/30",
  moderate: "bg-amber-bright/15 text-amber-bright border-amber-bright/30",
  divergent: "bg-red-bright/15 text-red-bright border-red-bright/30",
};

const DISAGREEMENT_LABEL: Record<DisagreementLevel, string> = {
  aligned: "aligned",
  moderate: "moderate",
  divergent: "divergent",
};

function pct(v: number): string {
  return `${(v * 100).toFixed(1)}%`;
}

export default function MLPosPriorPanel({ record }: ModulePanelProps) {
  const [result, setResult] = useState<MLPosPriorResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    if (!record.pos) {
      // Wait for PoS module to populate first
      return () => {
        cancelled = true;
      };
    }
    runMLPosPrior(record.asset, record.pos, {
      criteria_text: record.ml_pos_criteria_text ?? null,
      nct_id: record.ml_pos_nct_id ?? null,
    })
      .then((r) => !cancelled && setResult(r))
      .catch((e) => !cancelled && setError(String(e)));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    JSON.stringify(record.asset),
    record.pos?.final_loa,
    record.ml_pos_criteria_text,
    record.ml_pos_nct_id,
  ]);

  if (!record.pos) {
    return (
      <section className="rounded border border-border-dim bg-bg-panel p-3">
        <h2 className="mb-2 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
          ML PoS Prior · rule-smoothed surrogate
        </h2>
        <p className="font-mono text-[11px] uppercase tracking-wider text-text-dim">
          Waiting for the rule-based PoS chain…
        </p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded border border-red-bright/30 bg-red-bright/10 p-3 text-sm text-red-bright">
        ML PoS Prior unavailable: {error}
      </section>
    );
  }

  if (!result) {
    return (
      <section className="rounded border border-border-dim bg-bg-panel p-3">
        <h2 className="mb-2 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
          ML PoS Prior · rule-smoothed surrogate
        </h2>
        <div className="h-20 animate-pulse rounded bg-bg-panel-hover" />
      </section>
    );
  }

  const base = record.pos.base_rate;
  const ruleBased = result.rule_based_pos;
  const ml = result.predicted_pos;
  // For the visual bar, normalize against the maximum of the three so all
  // three are visible regardless of magnitude.
  const maxVal = Math.max(base, ruleBased, ml, 0.01);

  return (
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
          ML PoS Prior · rule-smoothed surrogate
        </h2>
        <span className="font-mono text-[9px] uppercase tracking-wider text-text-dim">
          {result.model_kind} · {result.n_features} features
        </span>
      </div>

      <div className="space-y-1 text-xs">
        <ReadoutRow label="BIO base rate" value={base} max={maxVal} color="bg-text-dim" />
        <ReadoutRow
          label="Rule-based final LOA"
          value={ruleBased}
          max={maxVal}
          color="bg-cyan-faded"
        />
        <ReadoutRow
          label="ML prior (PubMedBERT + LGBM, HINT)"
          value={ml}
          max={maxVal}
          color="bg-magenta-bright"
          band={[result.uncertainty_low, result.uncertainty_high]}
        />
      </div>

      <div className="mt-3 flex items-center gap-2">
        <span
          className={`rounded border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider ${DISAGREEMENT_COLOR[result.disagreement_level]}`}
        >
          ● {DISAGREEMENT_LABEL[result.disagreement_level]}
        </span>
        <span className="font-mono text-[10px] tabular-nums text-text-dim">
          ML − rule-based: {result.disagreement_pp > 0 ? "+" : ""}
          {result.disagreement_pp.toFixed(1)}pp
        </span>
      </div>

      <p className="mt-2 font-prose text-[11px] leading-snug text-text-dim">
        v1.5.3: PubMedBERT-pooled eligibility-criteria embeddings concatenated
        with 36-dim structured features (804-dim total), supervised on real
        Phase-2/3 outcomes from the HINT clinical-trial corpus (Fu 2022).
        Uncertainty band = 90% bootstrap-percentile interval across 10 LGBMs
        trained on independent bootstrap resamples; the band tightens where
        the ensemble agrees and widens where it doesn’t. A complementary
        Mondrian split-conformal coverage check (91.5% marginal on test)
        lives in the methodology page — see methodology/09-ml-pos-prior.md.
      </p>
    </section>
  );
}

function ReadoutRow({
  label,
  value,
  max,
  color,
  band,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
  // Bootstrap 90% band.
  band?: [number, number];
}) {
  const width = `${(value / max) * 100}%`;
  const bandLeft = band ? `${(band[0] / max) * 100}%` : null;
  const bandWidth = band ? `${((band[1] - band[0]) / max) * 100}%` : null;
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-3">
      <div className="truncate text-text-primary">{label}</div>
      <div className="flex items-center gap-2">
        <div className="relative h-3 w-40 rounded bg-bg-panel-hover">
          {/* Bootstrap 90% band */}
          {band ? (
            <div
              className="absolute h-full rounded bg-magenta-bright/20"
              style={{ left: bandLeft!, width: bandWidth! }}
              title={`Bootstrap 90% band: ${(band[0] * 100).toFixed(1)}-${(band[1] * 100).toFixed(1)}%`}
            />
          ) : null}
          <div className={`h-full rounded ${color}`} style={{ width }} />
        </div>
        <span className="w-12 text-right font-mono font-bold tabular-nums text-text-bright">
          {pct(value)}
        </span>
      </div>
    </div>
  );
}
