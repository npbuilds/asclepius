import Link from "next/link";

import { SystemStatus } from "@/components/SystemStatus";
import { TryYourOwnAsset } from "@/components/TryYourOwnAsset";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="font-display text-4xl font-black uppercase leading-none tracking-[0.06em] text-text-bright sm:text-5xl">
        Asclepius
      </h1>

      <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.15em] text-text-dim">
        Biotech venture valuation · reflexivity-adjusted PoS · phase-gated rNPV
      </p>

      {/* v1.6 onboarding block: three exploration modes laid out as
          discrete cards rather than a single "Launch workbench" button.
          The motivation is that a generalist VC visitor needs to see —
          before clicking anything — that the tool has both (a) a worked
          example to understand what it does, and (b) a way to evaluate
          their own asset. Without this surface, the only obvious path
          was adagrasib, which led to "the tool is hard-coded to one
          asset" misperception. */}
      <div className="mt-8">
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-text-dim">
          ── three modes ──
        </p>
        <div className="space-y-3">
          {/* Mode 1: retrospective backtest */}
          <Link
            href="/diligence/adagrasib"
            className="group block rounded border border-border-dim bg-bg-panel p-3 transition hover:border-cyan-bright"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-[12px] font-semibold uppercase tracking-wider text-text-bright group-hover:text-cyan-bright">
                Retrospective backtest
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-bright">
                adagrasib →
              </span>
            </div>
            <p className="mt-1.5 font-prose text-[12px] leading-snug text-text-dim">
              Mirati → BMS, Oct 2022, $4.8B deal. Inputs locked to a
              June 2022 cutoff; framework brackets the deal value within ~2%.
              Drag the reflexivity slider for the headline demo.
            </p>
          </Link>

          {/* Mode 2: live forward prediction */}
          <Link
            href="/diligence/divarasib"
            className="group block rounded border border-border-dim bg-bg-panel p-3 transition hover:border-magenta-bright"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-display text-[12px] font-semibold uppercase tracking-wider text-text-bright group-hover:text-magenta-bright">
                Live forward prediction
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider text-magenta-bright">
                divarasib →
              </span>
            </div>
            <p className="mt-1.5 font-prose text-[12px] leading-snug text-text-dim">
              Roche Phase 3 head-to-head vs sotorasib/adagrasib. PoS 59.3%,
              rNPV $948M base case &mdash;{" "}
              <strong className="text-text-primary">pre-registered before any outcome was known</strong>.
              Resolution catalyst: 2027-09-30.
            </p>
          </Link>

          {/* Mode 3: any custom asset */}
          <div className="rounded border border-border-dim bg-bg-panel p-3">
            <div className="mb-2 flex items-baseline justify-between gap-2">
              <span className="font-display text-[12px] font-semibold uppercase tracking-wider text-text-bright">
                Your own asset
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider text-text-dim">
                auto-diligence →
              </span>
            </div>
            <p className="mb-2.5 font-prose text-[12px] leading-snug text-text-dim">
              Type a pre-approval asset name; the page opens with an empty
              form and an{" "}
              <strong className="text-text-primary">Auto-Diligence</strong>{" "}
              button that populates inputs from public sources (CT.gov, FDA,
              EDGAR, top journals) in ~30 seconds.
            </p>
            <TryYourOwnAsset />
          </div>
        </div>
      </div>

      {/* Methodology + the parity-linted writeup count is a credibility
          signal worth surfacing inline rather than buried behind a tab. */}
      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/methodology"
          className="rounded border border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-text-primary hover:border-magenta-bright hover:text-magenta-bright"
        >
          [ Methodology · 18 writeups → ]
        </Link>
      </div>

      <div className="mt-8 rounded border border-border-dim bg-bg-panel p-3">
        <SystemStatus />
      </div>
    </div>
  );
}
