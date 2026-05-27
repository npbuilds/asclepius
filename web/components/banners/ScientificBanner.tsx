"use client";

// ScientificBanner — v1.8.0 Phase 4.
//
// Banner variant for the Scientific Reviewer persona (KOL / clinical
// reviewer / scientific advisor reading the diligence). The reviewer's
// first questions are about the science, NOT the valuation:
//
//   1. "Is the target real?" → target + target_validated
//   2. "Is the mechanism defensible?" → mechanism
//   3. "Is the indication clinically coherent?" → indication
//   4. "Is the trial design biomarker-enriched / enriching for responders?"
//      → biomarker_enrichment
//   5. "What does the protocol-text signal say?" → ml_pos_prior
//      (the supervised model whose features include eligibility-criteria
//      embeddings)
//
// rNPV, deal comparables, and even the recommendation chip are
// deliberately absent — they answer the VC's questions, not the
// reviewer's. The persona-config already drops the rnpv + comparables
// modules from the rendered page; this banner removes the chip from
// the headline surface.
//
// Below the banner the page renders the persona-config-defined
// Science → Operational sections.

import {
  catalystLine,
  loaDisplay,
  subtitleLine,
} from "@/lib/banner-stats";
import type { ClientDiligenceRecord } from "@/lib/module-registry";

interface ScientificBannerProps {
  record: ClientDiligenceRecord;
}

export default function ScientificBanner({ record }: ScientificBannerProps) {
  const asset = record.asset;
  const loa = loaDisplay(record);
  const subtitle = subtitleLine(record);
  const catalyst = catalystLine(record);
  const ml = record.ml_pos;

  return (
    <section
      aria-label="Scientific reviewer summary"
      className="mb-4 rounded border border-border-dim bg-bg-panel p-3"
    >
      {/* Top row — asset identity + headline LOA / ML pairing */}
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
          {subtitle}
        </span>
        <div className="flex items-baseline gap-4 font-mono">
          <Stat
            label="Rule LOA"
            value={loa.final}
            secondary={record.pos ? `BIO ${(record.pos.base_rate * 100).toFixed(1)}%` : null}
          />
          <Stat
            label="ML prior"
            value={ml ? `${(ml.predicted_pos * 100).toFixed(1)}%` : "—%"}
            secondary={
              ml
                ? `${(ml.uncertainty_low * 100).toFixed(0)}–${(ml.uncertainty_high * 100).toFixed(0)}%`
                : "loading…"
            }
          />
        </div>
      </div>

      {/* Middle — structured science fields in two columns */}
      <div className="grid gap-x-4 gap-y-1.5 border-t border-border-dim/60 pt-3 md:grid-cols-2">
        <Field label="Target" value={asset.target ?? "—"} />
        <Field label="Indication" value={asset.indication ?? "—"} />
        <Field label="Mechanism" value={asset.mechanism ?? "—"} mono={false} />
        <Field
          label="Modality"
          value={asset.modality.replace(/_/g, " ")}
        />
        <Field
          label="Biomarker enrichment"
          value={asset.biomarker_enrichment ? "✓ enriched" : "✗ all-comers"}
          tone={asset.biomarker_enrichment ? "good" : "warn"}
        />
        <Field
          label="Target validated"
          value={asset.target_validated ? "✓ prior approval" : "✗ unvalidated"}
          tone={asset.target_validated ? "good" : "warn"}
        />
        <Field
          label="In-class competitors"
          value={`${asset.num_competitors} drug${asset.num_competitors === 1 ? "" : "s"}`}
        />
        <Field label="Phase" value={asset.phase.replace(/_/g, " ")} />
      </div>

      {/* Bottom — clinical catalyst */}
      <div className="mt-3 border-t border-border-dim/60 pt-2">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
            Next clinical catalyst
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

interface FieldProps {
  label: string;
  value: string;
  secondary?: string | null;
  tone?: "good" | "warn" | null;
  mono?: boolean;
}

function Field({ label, value, secondary, tone, mono = true }: FieldProps) {
  const valueColor =
    tone === "good"
      ? "text-green-bright"
      : tone === "warn"
        ? "text-amber-bright"
        : "text-text-bright";
  return (
    <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-x-2 text-[11px]">
      <span className="font-mono uppercase tracking-[0.15em] text-text-dim">
        {label}
      </span>
      <span>
        <span className={mono ? `font-mono font-bold ${valueColor}` : `font-prose ${valueColor}`}>
          {value}
        </span>
        {secondary ? (
          <span className="ml-2 font-mono text-[10px] text-text-dim">
            {secondary}
          </span>
        ) : null}
      </span>
    </div>
  );
}
