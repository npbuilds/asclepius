"use client";

// ActionSection — v1.7.0 Phase 6 footer.
//
// Frames the active controls (Auto-Diligence, Memo Writer, methodology
// link, PDF export stub) as "what you DO with the diligence," visually
// separated from the report content above. Per the v1.7.0 reading-order
// research, this is the "the action read" surface — the reader has
// finished consuming the framework's analysis and now decides what to do.
//
// Pre-v1.7.0 these controls were scattered: AutoDiligence at the top of
// the right column (suggesting it was analysis), MemoPanel at the bottom
// (correctly positioned, no framing), methodology accessible only via
// the global header link. Consolidating into one section with an
// ASCII-rule header that matches the pattern of THESIS / VALUATION /
// OPERATIONAL / RISK puts actions in the same visual register as
// content — a named beat, the last one in the journey.
//
// Sub-components keep their existing card internals; this wrapper is
// layout + sub-action strip only.

import Link from "next/link";

import { AutoDiligencePanel } from "@/components/agents/AutoDiligencePanel";
import { MemoPanel } from "@/components/agents/MemoPanel";
import type {
  ClientDiligenceRecord,
  ModulePanelProps,
} from "@/lib/module-registry";

interface ActionSectionProps {
  record: ClientDiligenceRecord;
  setRecord: ModulePanelProps["setRecord"];
}

export default function ActionSection({ record, setRecord }: ActionSectionProps) {
  return (
    <div className="space-y-3">
      <div className="border-b border-border-dim/60 pb-1">
        <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
          ── Take action ─────────────────────────
        </div>
        <p className="mt-1 font-prose text-[11px] italic leading-snug text-text-dim">
          Q: what do you do with this diligence?
        </p>
      </div>

      <AutoDiligencePanel record={record} setRecord={setRecord} />
      <MemoPanel record={record} />

      {/* Other actions — methodology link + future PDF export. Kept small
          and visually subordinate to the agent cards above. */}
      <section className="rounded border border-border-dim bg-bg-panel p-3">
        <h2 className="mb-2 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-text-dim">
          Other
        </h2>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/methodology"
            className="rounded border border-cyan-bright/40 bg-cyan-bright/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
          >
            [ read methodology → ]
          </Link>
          <button
            type="button"
            disabled
            title="Export PDF — v1.8.0+"
            aria-label="Export PDF — coming in v1.8.0 or later"
            className="cursor-not-allowed rounded border border-border-dim bg-bg-panel-hover px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-text-dim opacity-60"
          >
            [ export pdf · v1.8+ ]
          </button>
          <span className="ml-auto font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
            ● {record.asset.asset_name}
          </span>
        </div>
      </section>
    </div>
  );
}
