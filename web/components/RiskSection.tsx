"use client";

// RiskSection — v1.7.0 Phase 5 consolidation.
//
// Wraps LimitationsPanel + AdversaryPanel under a single named section
// matching the Phase 2 ASCII-rule + "Q:" microcopy pattern. Per the
// healthcare-VC research (Spectup, Qubit Capital, IC-memo literature),
// risk-section depth is "the section that determines a yes/no vote" —
// it should read as visually co-equal with Valuation, not buried.
//
// Pre-v1.7.0 these two panels rendered as siblings in the main flow
// with no shared header, which fragmented "what could break this?"
// across two surfaces — easy to miss.
//
// The component itself is layout-only; both child panels keep their
// existing internal rendering, accents (amber for Limitations, magenta
// for Adversary), and state management.

import { AdversaryPanel } from "@/components/agents/AdversaryPanel";
import { LimitationsPanel } from "@/components/LimitationsPanel";
import type { ClientDiligenceRecord } from "@/lib/module-registry";

interface RiskSectionProps {
  record: ClientDiligenceRecord;
}

export default function RiskSection({ record }: RiskSectionProps) {
  return (
    <div className="space-y-3">
      <div className="border-b border-border-dim/60 pb-1">
        <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
          ── Risk &amp; limits ─────────────────────────
        </div>
        <p className="mt-1 font-prose text-[11px] italic leading-snug text-text-dim">
          Q: what could break this thesis?
        </p>
      </div>
      <LimitationsPanel />
      <AdversaryPanel record={record} />
    </div>
  );
}
