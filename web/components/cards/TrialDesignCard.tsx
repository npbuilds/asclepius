"use client";

// TrialDesignCard — v1.8.0 Phase 4.
//
// Renders inside the Science section (Scientific Reviewer persona only).
// Surfaces the trial-protocol context that informs the ML PoS Prior's
// supervised signal — the same eligibility-criteria text the backend
// embedded with PubMedBERT, plus contextual flags from the asset record.
//
// Why this is a separate card: the science reviewer reading the page
// wants to verify the model is being asked to predict outcomes for the
// RIGHT trial — not just see a number. The NCT ID + link makes the
// underlying study auditable; the biomarker / target-validation flags
// surface the assumptions the model is leaning on; the rationale lines
// connect protocol design back to the framework's signaling thesis.
//
// Data sources:
//   - record.ml_pos_nct_id: per-asset NCT ID (e.g. NCT04685135 for
//     adagrasib's KRYSTAL-1 registrational trial). Pre-populated for
//     pre-staged assets; null for user-typed ones.
//   - record.asset.{biomarker_enrichment, target_validated, target,
//     mechanism, indication}: structured flags already in the record
//
// What this card does NOT do: render the full criteria text inline.
// That lives server-side (the backend fetches CT.gov v2 on cache-miss
// for ML PoS Prior) and isn't surfaced to the frontend record. A
// future enhancement could pass it through; for v1.8.0 we link out.

import { ExternalLink } from "lucide-react";

import type { ClientDiligenceRecord } from "@/lib/module-registry";

interface TrialDesignCardProps {
  record: ClientDiligenceRecord;
}

export default function TrialDesignCard({ record }: TrialDesignCardProps) {
  const asset = record.asset;
  const nctId = record.ml_pos_nct_id;
  const ctGovUrl = nctId
    ? `https://clinicaltrials.gov/study/${nctId}`
    : null;
  // v1.8.0-rc3.1 (Codex MINOR #4): blank-asset proxy. Treat unset
  // indication as "the user hasn't filled this in yet" and render
  // target_validated / biomarker_enrichment as neutral "unknown"
  // instead of misleading amber-toned warnings on a fresh record.
  const assetIsBlank = asset.indication === null;

  return (
    <section
      aria-label="Trial design"
      className="rounded border border-cyan-bright/30 bg-cyan-bright/5 p-3"
    >
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h3 className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-bright">
          Trial design
        </h3>
        {ctGovUrl ? (
          <a
            href={ctGovUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-cyan-bright hover:underline"
          >
            {nctId}
            <ExternalLink size={10} />
          </a>
        ) : (
          <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
            No NCT ID configured
          </span>
        )}
      </div>

      <ul className="space-y-1.5 font-prose text-[11px] leading-snug text-text-primary">
        <li>
          <span className="font-mono font-bold text-text-bright">Target.</span>{" "}
          {asset.target ?? "—"}
          {assetIsBlank ? (
            <span className="ml-1 text-text-dim">
              — target-validation status not yet recorded
            </span>
          ) : asset.target_validated ? (
            <span className="ml-1 text-green-bright">
              ✓ target-validated by prior approval in the same indication
            </span>
          ) : (
            <span className="ml-1 text-amber-bright">
              ✗ target NOT clinically validated — additional biological risk
            </span>
          )}
        </li>
        <li>
          <span className="font-mono font-bold text-text-bright">
            Mechanism.
          </span>{" "}
          {asset.mechanism ?? "—"}
        </li>
        <li>
          <span className="font-mono font-bold text-text-bright">
            Indication.
          </span>{" "}
          {asset.indication ?? "—"}
        </li>
        <li>
          <span className="font-mono font-bold text-text-bright">
            Enrichment.
          </span>{" "}
          {assetIsBlank ? (
            <span className="text-text-dim">
              — biomarker-enrichment status not yet recorded
            </span>
          ) : asset.biomarker_enrichment ? (
            <>
              Biomarker-enriched enrollment.{" "}
              <span className="text-green-bright">
                ✓ enrolls responders directly — Spence-style costly signal
              </span>
            </>
          ) : (
            <>
              All-comers enrollment.{" "}
              <span className="text-amber-bright">
                ✗ no biomarker pre-selection — efficacy diluted by non-responders
              </span>
            </>
          )}
        </li>
        {nctId ? (
          <li className="font-mono text-[10px] text-text-dim">
            The ML PoS Prior embeds this trial&rsquo;s eligibility-criteria text
            via PubMedBERT and feeds it into the 804-dim feature vector. The
            band displayed in the ML PoS panel below reflects bootstrap
            disagreement across 10 LightGBM models. See{" "}
            <a
              href="/methodology/09-ml-pos-prior"
              className="text-cyan-bright hover:underline"
            >
              methodology/09-ml-pos-prior
            </a>{" "}
            for the full discipline.
          </li>
        ) : null}
      </ul>
    </section>
  );
}
