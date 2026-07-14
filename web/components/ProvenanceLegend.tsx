// Provenance system — makes the framework's honesty stance scannable.
//
// Every number the framework produces ships a `source` string. Those sources
// fall into two honestly-distinguished tiers:
//   • cited      — an external dataset / study / named deal (BIO/Informa, Wong
//                  2019, FDA, a specific M&A comparable).
//   • estimate   — the tool's OWN reasoned magnitude, explicitly self-labeled
//                  ("Asclepius estimate, no BIO/Informa cohort", a framework
//                  thesis, a practitioner heuristic). The framework never
//                  borrows a citation it isn't entitled to; where no data
//                  exists it says so.
//
// This is the tool's strongest differentiator (auditable, honest provenance),
// so we surface the distinction with a badge per source + a one-line legend.

export type ProvenanceTier = "cited" | "estimate";

// Classify a source string. A source is a framework ESTIMATE when it
// self-identifies as the tool's own judgment; otherwise it CITES an external
// source. The frontier-modality multipliers and the two path-dependency theses
// deliberately fall in the estimate tier — that honesty is the point.
export function provenanceTier(source: string | null | undefined): ProvenanceTier {
  const s = (source ?? "").toLowerCase();
  const selfLabeledEstimate =
    s.includes("asclepius") ||
    s.includes("practitioner") ||
    s.includes("framework estimate") ||
    s.includes("reasoned estimate") ||
    s.includes("no bio") ||
    s.includes("no cohort");
  return selfLabeledEstimate ? "estimate" : "cited";
}

export function ProvenanceBadge({ source }: { source: string | null | undefined }) {
  const tier = provenanceTier(source);
  const cls =
    tier === "estimate"
      ? "border-amber-bright/40 text-amber-bright"
      : "border-cyan-bright/40 text-cyan-bright";
  return (
    <span
      className={`inline-block rounded border px-1 py-px font-mono text-[8px] uppercase tracking-wider ${cls}`}
      title={
        tier === "estimate"
          ? "Framework estimate — the tool's own reasoned magnitude, honestly labeled (no external cohort)."
          : "Cited — anchored to an external dataset, study, or named deal."
      }
    >
      {tier === "estimate" ? "◇ estimate" : "● cited"}
    </span>
  );
}

export function ProvenanceLegend({ className = "" }: { className?: string }) {
  return (
    <div
      className={`flex flex-wrap items-center gap-x-3 gap-y-1 font-prose text-[10px] leading-snug text-text-dim ${className}`}
    >
      <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
        provenance
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="rounded border border-cyan-bright/40 px-1 py-px font-mono text-[8px] uppercase tracking-wider text-cyan-bright">
          ● cited
        </span>
        external dataset / study / named deal
      </span>
      <span className="inline-flex items-center gap-1">
        <span className="rounded border border-amber-bright/40 px-1 py-px font-mono text-[8px] uppercase tracking-wider text-amber-bright">
          ◇ estimate
        </span>
        the tool&apos;s own reasoned magnitude, honestly labeled — never a borrowed citation
      </span>
    </div>
  );
}
