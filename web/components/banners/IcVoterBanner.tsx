"use client";

// IcVoterBanner — v1.8.0 Phase 3.
//
// 1-page summary surface for the IC Voter persona (senior partners reviewing
// an associate's diligence write-up). Designed for a ~2-minute scan:
//
//   recommendation chip          rNPV range          LOA + reflexivity
//   ──────────────────────────────────────────────────────────────────
//   TOP RISKS (red flags)              TOP REASONS (green flags)
//   1. ...                             1. ...
//   2. ...                             2. ...
//   3. ...                             3. ...
//   ──────────────────────────────────────────────────────────────────
//   Next catalyst: ...
//
// Per the healthcare-VC research (Qubit Capital, Spectup, VC Factory), IC
// voters scan for *risk awareness* first — what the analyst failed to
// think about, not what they emphasized. Surfacing top-3 risks immediately
// below the recommendation matches that scan pattern. Reasons are paired
// on the right so a voter can weigh signal against red flags at a glance.
//
// Data sources:
//   - record.scorecard.red_flags / green_flags: hand-curated by the
//     scorecard engine, primary source
//   - record.scorecard.pillars: fallback if flags arrays are empty —
//     derive risks from the lowest 3-scoring pillars (rationale field),
//     reasons from the highest 3
//
// Below the banner the page renders the persona-config-defined
// "Decision view" section containing pos + rnpv + scorecard at their
// full size. The ActionSection is suppressed per
// PersonaConfig.showActionSection: false.

import type { Recommendation } from "@/lib/types";
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

interface IcVoterBannerProps {
  record: ClientDiligenceRecord;
}

const TONE_CLASSES: Record<RecommendationChip["tone"], string> = {
  positive: "bg-green-bright/15 text-green-bright border-green-bright/40",
  neutral: "bg-cyan-bright/15 text-cyan-bright border-cyan-bright/40",
  cautious: "bg-amber-bright/15 text-amber-bright border-amber-bright/40",
  negative: "bg-red-bright/15 text-red-bright border-red-bright/40",
  pending: "bg-bg-panel-hover text-text-dim border-border-dim",
};

// Lowest 3-scoring pillars, taking rationale as the bullet text. Used as
// fallback when scorecard.red_flags is empty.
function fallbackRisks(record: ClientDiligenceRecord): string[] {
  if (!record.scorecard) return [];
  return record.scorecard.pillars
    .slice()
    .sort((a, b) => a.score - b.score)
    .slice(0, 3)
    .map((p) => p.rationale ?? `${p.name} pillar score: ${p.score.toFixed(1)}`);
}

function fallbackReasons(record: ClientDiligenceRecord): string[] {
  if (!record.scorecard) return [];
  return record.scorecard.pillars
    .slice()
    .sort((a, b) => b.score - a.score)
    .slice(0, 3)
    .map((p) => p.rationale ?? `${p.name} pillar score: ${p.score.toFixed(1)}`);
}

function topRisks(record: ClientDiligenceRecord): string[] {
  if (!record.scorecard) return [];
  const flagged = record.scorecard.red_flags ?? [];
  if (flagged.length >= 3) return flagged.slice(0, 3);
  // Pad with pillar-derived risks if flags array is short
  const fallback = fallbackRisks(record).filter((f) => !flagged.includes(f));
  return [...flagged, ...fallback].slice(0, 3);
}

function topReasons(record: ClientDiligenceRecord): string[] {
  if (!record.scorecard) return [];
  const flagged = record.scorecard.green_flags ?? [];
  if (flagged.length >= 3) return flagged.slice(0, 3);
  const fallback = fallbackReasons(record).filter((f) => !flagged.includes(f));
  return [...flagged, ...fallback].slice(0, 3);
}

// Pretty-print a recommendation for IC display. The chip itself uses a
// short label ("STRONG BUY"); this banner adds a one-line color sentence
// next to it so the partner doesn't have to mentally decode the chip.
const RECOMMENDATION_SENTENCE: Record<Recommendation, string> = {
  strong_buy: "Conviction position — recommend full allocation.",
  buy: "Recommend entry at the framework's central case or below.",
  hold: "Wait or enter only on a meaningful discount to central case.",
  cautious: "Wait — material risk not yet resolved.",
  avoid: "Pass. Risk-adjusted return does not clear the fund's hurdle.",
};

export default function IcVoterBanner({ record }: IcVoterBannerProps) {
  const chip = recommendationChip(record);
  const rnpv = rnpvDisplay(record);
  const loa = loaDisplay(record);
  const reflex = reflexivityDisplay(record);
  const catalyst = catalystLine(record);
  const subtitle = subtitleLine(record);
  const risks = topRisks(record);
  const reasons = topReasons(record);

  const sentence = record.scorecard
    ? RECOMMENDATION_SENTENCE[record.scorecard.recommendation]
    : "Awaiting scorecard...";

  return (
    <section
      aria-label="IC voter summary"
      className="mb-4 rounded border border-border-dim bg-bg-panel p-3"
    >
      {/* Top row — large recommendation chip + asset identity + headline numbers */}
      <div className="mb-3 grid gap-3 sm:grid-cols-[auto_1fr] sm:items-start">
        <div>
          <span
            className={`inline-flex items-center gap-2 rounded border px-3 py-1.5 font-mono text-[13px] font-bold uppercase tracking-[0.12em] ${TONE_CLASSES[chip.tone]}`}
          >
            <span className="leading-none">●</span>
            <span>{chip.label}</span>
          </span>
          <p className="mt-2 max-w-md font-prose text-[11px] leading-snug text-text-primary">
            {sentence}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2 text-right">
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
            {subtitle}
          </span>
          <div className="flex flex-wrap items-baseline justify-end gap-x-4 gap-y-1 font-mono">
            <Stat label="rNPV base" value={rnpv.base} secondary={rnpv.range} />
            <Stat label="LOA" value={loa.final} secondary={null} />
            <Stat
              label="Reflexivity"
              value={reflex.tier}
              secondary={reflex.multiplier}
            />
          </div>
        </div>
      </div>

      {/* Middle — top 3 risks + top 3 reasons, paired columns */}
      <div className="grid gap-3 border-t border-border-dim/60 pt-3 md:grid-cols-2">
        <FlagColumn
          label="Top risks"
          tone="red"
          items={risks}
          isPending={!record.scorecard}
        />
        <FlagColumn
          label="Top reasons"
          tone="green"
          items={reasons}
          isPending={!record.scorecard}
        />
      </div>

      {/* Bottom — catalyst */}
      <div className="mt-3 border-t border-border-dim/60 pt-2">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
            Next catalyst
          </span>
          <span className="font-prose text-[11px] text-text-primary">
            {catalyst}
          </span>
        </div>
      </div>
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
    <span className="flex flex-col items-end leading-tight">
      <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
        {label}
      </span>
      <span className="font-mono text-[14px] font-bold tabular-nums text-text-bright">
        {value}
      </span>
      {secondary ? (
        <span className="font-mono text-[10px] tabular-nums text-text-dim">
          {secondary}
        </span>
      ) : null}
    </span>
  );
}

interface FlagColumnProps {
  label: string;
  tone: "red" | "green";
  items: string[];
  isPending: boolean;
}

function FlagColumn({ label, tone, items, isPending }: FlagColumnProps) {
  const headerColor =
    tone === "red" ? "text-red-bright" : "text-green-bright";
  const bulletColor =
    tone === "red" ? "text-red-bright" : "text-green-bright";

  return (
    <div>
      <h3
        className={`mb-1.5 font-display text-[10px] font-semibold uppercase tracking-[0.2em] ${headerColor}`}
      >
        {label}
      </h3>
      {isPending ? (
        <p className="font-mono text-[11px] uppercase tracking-wider text-text-dim">
          Awaiting scorecard…
        </p>
      ) : items.length === 0 ? (
        <p className="font-prose text-[11px] italic text-text-dim">
          (no flags surfaced by the framework)
        </p>
      ) : (
        <ol className="space-y-1.5 font-prose text-[11px] leading-snug text-text-primary">
          {items.map((item, i) => (
            <li key={i} className="flex gap-1.5">
              <span className={`flex-none font-mono font-bold ${bulletColor}`}>
                {i + 1}.
              </span>
              <span className="min-w-0 break-words">{item}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
