"use client";

// UnresearchedAssetHero — focused empty-state for the "try your own asset" path.
//
// The diligence workbench computes PoS / rNPV / scorecard against whatever
// AssetInput is in the record. For an unstaged custom asset (the friend
// types "tarlatamab" or "pelabresib" on the landing TryYourOwnAsset tile)
// the record starts with blankAsset() — phase_2, oncology, small_molecule,
// adequate capital, no sponsor, no mechanism, no indication. Rendering the
// full workbench against those defaults produces a screen of *real-looking
// but meaningless* numbers — the framework computing a PoS based on
// "oncology · phase_2 · small_molecule · adequate" defaults, which is
// neither this asset's actual class nor the analyst's intended input.
//
// Pre-this-component the page handled that with a small cyan banner saying
// "Start here → scroll to the bottom action strip and click Auto-Diligence,"
// plus the full workbench rendering below. Two problems:
//   1. The friend has to scroll past four+ panels of meaningless analysis
//      to find the action that produces real analysis.
//   2. The meaningless analysis renders as if it were real — there's no
//      visual signal that the numbers are computed against defaults.
//
// This component replaces the entire workbench for unresearched custom
// assets. Auto-Diligence is the page's centerpiece, not a footer action.
// Once Auto-Diligence applies (or the analyst manually populates sponsor
// + mechanism via the form below), the parent's `isUnresearched` flag
// flips false and the full workbench renders.
//
// Detection contract (in DiligencePage): `isUnresearched =
//   !isStaged && !record.asset.sponsor && !record.asset.mechanism`.
// Same predicate that previously gated the "Start here →" banner, so
// the behavior is consistent.

import { Fragment, useState } from "react";

import { AssetForm } from "@/components/AssetForm";
import { AutoDiligencePanel } from "@/components/agents/AutoDiligencePanel";
import type {
  ClientDiligenceRecord,
  ModulePanelProps,
} from "@/lib/module-registry";
import { STAGED_ASSETS } from "@/lib/staged-assets";
import type { AssetInput } from "@/lib/types";

// Terse one-line descriptors for the "not sure where to start?" footer
// link list. The SET of assets comes from the canonical STAGED_ASSETS
// registry (so a newly-added staged asset auto-appears in this footer);
// only this short per-slug prose is local. Falls back to the registry
// `mode` for any slug without an entry here.
const FOOTER_BLURB: Record<string, string> = {
  adagrasib: "retrospective backtest",
  divarasib: "live forward prediction",
  lifileucel: "cell therapy retrospective",
  tulisokibart: "autoimmune forward",
  aducanumab: "contested approval",
};

interface UnresearchedAssetHeroProps {
  record: ClientDiligenceRecord;
  setRecord: ModulePanelProps["setRecord"];
  onAssetChange: (asset: AssetInput) => void;
}

export default function UnresearchedAssetHero({
  record,
  setRecord,
  onAssetChange,
}: UnresearchedAssetHeroProps) {
  // Manual form starts collapsed — the primary path is Auto-Diligence.
  // The friend who *wants* to enter values by hand can click "[ enter
  // manually ]" to expand. Collapsed by default because we want the
  // research-from-web button to be the unambiguous primary affordance.
  const [manualFormOpen, setManualFormOpen] = useState(false);

  return (
    <div className="space-y-4">
      {/* Lead card: the explanatory framing + the agent action.
          AutoDiligencePanel is rendered inside but presents itself with
          its own magenta-bordered card — that's intentional, it gives
          the agent action its own visual register inside the broader
          unresearched-asset hero. */}
      <div className="rounded border border-border-dim bg-bg-panel p-4">
        <div className="mb-3 border-b border-border-dim/60 pb-2">
          <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
            ── Unresearched asset ─────────────────────────
          </div>
          <p className="mt-1.5 font-prose text-[12px] leading-snug text-text-primary">
            Asclepius computes against a structured{" "}
            <code className="font-mono text-[11px] text-text-bright">
              AssetInput
            </code>{" "}
            (phase, sponsor, modality, capital position, mechanism, target,
            indication, designations, competitors, target-validation and
            biomarker-enrichment flags). Pick one of two paths to populate
            it for{" "}
            <strong className="text-text-bright">
              {record.asset.asset_name}
            </strong>{" "}
            — then the workbench loads with the framework&apos;s actual
            analysis. The default values you see in the form below are{" "}
            <em className="text-amber-bright">not</em> this asset&apos;s real
            values; they&apos;re the field schema&apos;s defaults.
          </p>
        </div>

        <AutoDiligencePanel record={record} setRecord={setRecord} />
      </div>

      {/* Manual entry — collapsed by default, expand if the friend wants
          to enter values without the agent. Asset form is the same one
          the staged workbench uses; once she edits sponsor or mechanism
          to anything truthy, the parent re-renders into full workbench. */}
      <details
        open={manualFormOpen}
        onToggle={(e) => setManualFormOpen(e.currentTarget.open)}
        className="group rounded border border-border-dim bg-bg-panel"
      >
        <summary className="flex cursor-pointer flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-3 py-3 [&::-webkit-details-marker]:hidden">
          <span className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-dim">
              Or enter manually ▸
            </span>
            <span className="font-prose text-[11px] italic text-text-dim">
              skip the agent, populate fields by hand
            </span>
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-text-dim">
            {manualFormOpen ? "[ collapse ]" : "[ enter manually ]"}
          </span>
        </summary>
        <div className="border-t border-border-dim/60 p-3">
          <AssetForm value={record.asset} onChange={onAssetChange} />
          <p className="mt-3 font-prose text-[11px] italic leading-snug text-text-dim">
            Save fields as you edit — once <strong>sponsor</strong> and{" "}
            <strong>mechanism</strong> are both populated, the full workbench
            loads automatically with the framework&apos;s analysis.
          </p>
        </div>
      </details>

      {/* Footer tip — keeps the friend from feeling stuck if the live
          agent isn't available on this deploy. The 503 fallback is also
          handled inside AutoDiligencePanel; this is a pre-emptive escape
          hatch so she knows the alternative without having to click first. */}
      <div className="rounded border border-cyan-bright/30 bg-cyan-bright/5 p-3 font-prose text-[12px] leading-snug text-text-primary">
        <strong className="font-display text-[10px] uppercase tracking-[0.15em] text-cyan-bright">
          ● not sure where to start?
        </strong>{" "}
        Try one of the pre-staged assets — they showcase the framework
        on different modalities, phases, and outcomes:{" "}
        {STAGED_ASSETS.map((a, i) => {
          const prefix =
            i === 0 ? "" : i === STAGED_ASSETS.length - 1 ? ", or " : ", ";
          return (
            <Fragment key={a.slug}>
              {prefix}
              <a
                href={`/diligence/${a.slug}`}
                className="text-cyan-bright underline hover:text-cyan-bright"
              >
                {a.name}
              </a>{" "}
              ({FOOTER_BLURB[a.slug] ?? a.mode})
            </Fragment>
          );
        })}
        .
      </div>
    </div>
  );
}
