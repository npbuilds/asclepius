"use client";

// HeroBanner — the "30-second read" surface introduced in v1.7.0.
//
// Stat grid + recommendation chip + next-catalyst row, mounted directly
// under the page header on /diligence/[asset]. Reads from the lifted
// ClientDiligenceRecord (no own fetches), so it progressively populates
// as the underlying modules settle (PoS first, then rNPV, then scorecard
// for the recommendation, then ML PoS for the LOA microsplit).
//
// Visual target — a terminal/CLI-style stat block in mono-typography,
// dense, aligned to the weathered-cyberpunk theme's existing tokens:
//
//   ● HOLD (price-conditioned)            adagrasib · Mirati · Phase 2 · NSCLC
//
//   rNPV base / P25-P75       $570M    [$440-680M]
//   LOA final                 13.2%    BIO 7.9% → Reflexivity 13.2% → ML 23.6%
//   Reflexivity tier          ADEQUATE ×1.00
//   Next catalyst             KRYSTAL-12 Ph3 readout — post-cutoff for backtest
//
// See docs/ia-redesign-notes.md for the research that informed this
// surface and methodology/00-product-thesis.md for the public summary.

import {
  catalystLine,
  loaDisplay,
  recommendationChip,
  reflexivityDisplay,
  rnpvDisplay,
  subtitleLine,
  type RecommendationChip,
} from "@/lib/banner-stats";
import type { ClientDiligenceRecord } from "@/lib/module-registry";

interface HeroBannerProps {
  record: ClientDiligenceRecord;
}

const TONE_CLASSES: Record<RecommendationChip["tone"], string> = {
  positive: "bg-green-bright/15 text-green-bright border-green-bright/40",
  neutral: "bg-cyan-bright/15 text-cyan-bright border-cyan-bright/40",
  cautious: "bg-amber-bright/15 text-amber-bright border-amber-bright/40",
  negative: "bg-red-bright/15 text-red-bright border-red-bright/40",
  pending: "bg-bg-panel-hover text-text-dim border-border-dim",
};

export default function HeroBanner({ record }: HeroBannerProps) {
  const chip = recommendationChip(record);
  const rnpv = rnpvDisplay(record);
  const loa = loaDisplay(record);
  const reflex = reflexivityDisplay(record);
  const catalyst = catalystLine(record);
  const subtitle = subtitleLine(record);

  return (
    <section
      aria-label="Diligence summary"
      className="mb-4 rounded border border-border-dim bg-bg-panel p-3"
    >
      {/* Top row — recommendation chip + asset identity subtitle */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-[11px] font-bold uppercase tracking-[0.12em] ${TONE_CLASSES[chip.tone]}`}
        >
          <span className="leading-none">●</span>
          <span>{chip.label}</span>
          {chip.qualifier ? (
            <span className="font-normal tracking-normal opacity-80">
              ({chip.qualifier})
            </span>
          ) : null}
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
          {subtitle}
        </span>
      </div>

      {/* Stat grid — 4 rows, mono-typography, terminal feel */}
      <div className="grid gap-y-1 font-mono text-[12px]">
        <StatRow
          label="rNPV base / P25-P75"
          primary={rnpv.base}
          secondary={rnpv.range}
          isPending={rnpv.isPending}
        />
        <StatRow
          label="LOA final"
          primary={loa.final}
          secondary={loa.microsplit}
          isPending={loa.isPending}
        />
        <StatRow
          label="Reflexivity tier"
          primary={reflex.tier}
          secondary={reflex.multiplier}
        />
        <StatRow
          label="Next catalyst"
          primary={catalyst}
          secondary={null}
          // Catalyst is always-populated (per-asset map fallback)
          mono={false}
        />
      </div>
    </section>
  );
}

interface StatRowProps {
  label: string;
  primary: string;
  secondary: string | null;
  isPending?: boolean;
  // primary defaults to mono+bold (numeric); set false for prose-style values
  // like the catalyst line so it doesn't read as a code value.
  mono?: boolean;
}

function StatRow({
  label,
  primary,
  secondary,
  isPending,
  mono = true,
}: StatRowProps) {
  return (
    <div className="grid grid-cols-[160px_minmax(0,1fr)] items-baseline gap-3 sm:grid-cols-[180px_minmax(0,1fr)]">
      <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
        {label}
      </span>
      <span className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
        <span
          className={
            mono
              ? `font-mono ${isPending ? "text-text-dim" : "font-bold text-text-bright"} tabular-nums`
              : `font-prose ${isPending ? "text-text-dim" : "text-text-primary"}`
          }
        >
          {primary}
        </span>
        {secondary ? (
          <span
            className={`font-mono text-[11px] ${isPending ? "text-text-dim/60" : "text-text-dim"} tabular-nums`}
          >
            {secondary}
          </span>
        ) : null}
      </span>
    </div>
  );
}
