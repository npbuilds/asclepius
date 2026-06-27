"use client";

import Link from "next/link";
import { useState } from "react";

import { SystemStatus, type HealthStatus } from "@/components/SystemStatus";
import { TryYourOwnAsset } from "@/components/TryYourOwnAsset";
import { STAGED_ASSETS, type StagedAsset } from "@/lib/staged-assets";

/**
 * v1.6 friend-test landing — asset library + "your own asset" tile.
 *
 * The showcase cards iterate the canonical pre-staged registry in
 * lib/staged-assets.ts (the same source the diligence + compare views use).
 * To add a new showcase: add one entry to STAGED_ASSETS, then add its
 * framing paragraph in app/diligence/[asset]/page.tsx — both surfaces here
 * update automatically. The accent color on each card differentiates the
 * mode — cyan = retrospective backtest, magenta = forward prediction,
 * amber = contested/atypical case.
 *
 * Layout: single column on mobile, two columns on sm+ so a generalist
 * VC visitor sees the breadth-of-coverage in one screen-height. The
 * "your own asset" tile sits last so it reads as a fallback after the
 * curated options, not as the primary call to action.
 */

const MODE_LABEL: Record<StagedAsset["mode"], string> = {
  retrospective: "retrospective →",
  forward: "live forward prediction →",
  contested: "contested case →",
};

const MODE_ACCENT: Record<StagedAsset["mode"], string> = {
  retrospective: "hover:border-cyan-bright group-hover:text-cyan-bright",
  forward: "hover:border-magenta-bright group-hover:text-magenta-bright",
  contested: "hover:border-amber-bright group-hover:text-amber-bright",
};

const MODE_LABEL_COLOR: Record<StagedAsset["mode"], string> = {
  retrospective: "text-cyan-bright",
  forward: "text-magenta-bright",
  contested: "text-amber-bright",
};

export default function LandingPage() {
  // Lifted from <SystemStatus> via its onStatusChange callback so we can
  // render a degraded-mode banner above the showcase grid. We only surface
  // the banner once the ping has *resolved* offline — during the initial
  // "checking" window we stay silent to avoid a flash on every page load.
  const [apiStatus, setApiStatus] = useState<HealthStatus>("checking");
  const apiOffline = apiStatus === "offline";

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="font-display text-4xl font-black uppercase leading-none tracking-[0.06em] text-text-bright sm:text-5xl">
        Asclepius
      </h1>

      <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.15em] text-text-dim">
        Biotech venture valuation · reflexivity-adjusted PoS · phase-gated rNPV
      </p>

      {/* Featured: the narrated case study. The get-hired centerpiece — makes
          the differentiated thinking legible without the reader having to
          construct the triggering asset. Placed above the fold, prominent. */}
      <Link
        href="/showcase"
        className="mt-6 block rounded border border-cyan-bright/50 bg-cyan-bright/[0.06] p-3 transition hover:bg-cyan-bright/[0.12]"
      >
        <div className="flex items-baseline justify-between gap-2">
          <span className="font-display text-[13px] font-semibold uppercase tracking-wider text-cyan-bright">
            How the tool thinks — a worked case
          </span>
          <span className="font-mono text-[9px] uppercase tracking-wider text-cyan-bright">
            Ac-225 case study →
          </span>
        </div>
        <p className="mt-1 font-prose text-[12px] leading-snug text-text-dim">
          A frontier asset read end to end — the reflexivity and
          supply-constraint theses in action, where a generic DCF stops at a
          single number.
        </p>
      </Link>

      {apiOffline ? (
        <div
          role="status"
          aria-live="polite"
          className="mt-6 rounded border border-amber-bright/60 bg-amber-bright/[0.08] p-3"
        >
          <div className="flex items-start gap-2">
            <span className="mt-0.5 font-mono text-[11px] leading-none text-amber-bright">
              ●
            </span>
            <div className="flex-1">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-amber-bright">
                ── degraded mode · live API offline ──
              </p>
              <p className="mt-1.5 font-prose text-[12px] leading-snug text-text-primary">
                The framework&apos;s live API is offline. Pre-staged assets load
                from cache; the compare and methodology pages still work. Live
                computation (Auto-Diligence, custom assets) will return 503
                until the API recovers.
              </p>
            </div>
          </div>
        </div>
      ) : null}

      <div className="mt-8">
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-text-dim">
          ── pre-staged assets ──
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          {STAGED_ASSETS.map((asset) => (
            <Link
              key={asset.slug}
              href={`/diligence/${asset.slug}`}
              className={`group block rounded border border-border-dim bg-bg-panel p-3 transition ${MODE_ACCENT[asset.mode]}`}
            >
              <div className="mb-1 flex items-baseline justify-between gap-2">
                <span className="font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
                  {asset.name}
                </span>
                <span className={`font-mono text-[9px] uppercase tracking-wider ${MODE_LABEL_COLOR[asset.mode]}`}>
                  {MODE_LABEL[asset.mode]}
                </span>
              </div>
              <p className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-text-dim">
                {asset.sponsor} · {asset.context}
              </p>
              <p className="font-prose text-[12px] leading-snug text-text-dim">
                {asset.story}
              </p>
            </Link>
          ))}

          {/* "Your own asset" tile in the grid — placed last so it reads as
              the fallback after the curated showcases, not the primary CTA. */}
          <div className="rounded border border-border-dim bg-bg-panel p-3 sm:col-span-2">
            <div className="mb-1 flex items-baseline justify-between gap-2">
              <span className="font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
                Your own asset
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider text-text-dim">
                auto-diligence →
              </span>
            </div>
            <p className="mb-2.5 font-prose text-[12px] leading-snug text-text-dim">
              Type a pre-approval asset name; the page opens with an empty form
              and an{" "}
              <strong className="text-text-primary">Auto-Diligence</strong>{" "}
              button that populates inputs from public sources (CT.gov, FDA,
              EDGAR, top journals) in ~30 seconds. Works on any biotech asset
              with sponsor-public information.
            </p>
            <TryYourOwnAsset />
          </div>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/compare"
          className="rounded border border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-text-primary hover:border-cyan-bright hover:text-cyan-bright"
        >
          [ Compare assets side-by-side → ]
        </Link>
        <Link
          href="/predictions"
          className="rounded border border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-text-primary hover:border-magenta-bright hover:text-magenta-bright"
        >
          [ Public predictions · track record → ]
        </Link>
        <Link
          href="/methodology"
          className="rounded border border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-text-primary hover:border-magenta-bright hover:text-magenta-bright"
        >
          [ Methodology · 21 writeups → ]
        </Link>
      </div>

      <div className="mt-8 rounded border border-border-dim bg-bg-panel p-3">
        <SystemStatus onStatusChange={setApiStatus} />
      </div>
    </div>
  );
}
