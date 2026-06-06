import Link from "next/link";

import { SystemStatus } from "@/components/SystemStatus";
import { TryYourOwnAsset } from "@/components/TryYourOwnAsset";

/**
 * v1.6 friend-test landing — asset library + "your own asset" tile.
 *
 * Each showcase card is one of the pre-staged assets wired in
 * app/diligence/[asset]/page.tsx (search for "isStaged" to see the list).
 * To add a new showcase, add an entry here AND wire it in the diligence
 * page (define const, add to the isName branching, add the framing
 * paragraph). The accent color on each card differentiates the mode
 * — cyan = retrospective backtest, magenta = forward prediction,
 * amber = contested/atypical case.
 *
 * Layout: single column on mobile, two columns on sm+ so a generalist
 * VC visitor sees the breadth-of-coverage in one screen-height. The
 * "your own asset" tile sits last so it reads as a fallback after the
 * curated options, not as the primary call to action.
 */

interface ShowcaseAsset {
  slug: string;
  name: string;
  sponsor: string;
  mode: "retrospective" | "forward" | "contested";
  context: string; // phase · TA · modality, compact form
  story: string; // 1-2 line "why this asset" hook
}

const SHOWCASE_ASSETS: ShowcaseAsset[] = [
  {
    slug: "adagrasib",
    name: "adagrasib",
    sponsor: "Mirati → BMS",
    mode: "retrospective",
    context: "Phase 2 · oncology · small molecule",
    story:
      "Worked example. June 2022 cutoff; framework brackets the BMS $4.8B deal within ~2%. Drag the reflexivity slider for the headline demo.",
  },
  {
    slug: "divarasib",
    name: "divarasib",
    sponsor: "Roche",
    mode: "forward",
    context: "Phase 3 · oncology · small molecule",
    story:
      "Live forward prediction. Head-to-head vs sotorasib/adagrasib. PoS 59.3%, rNPV $948M committed to git before any outcome was known. Resolution 2027-09-30.",
  },
  {
    slug: "lifileucel",
    name: "lifileucel",
    sponsor: "Iovance",
    mode: "retrospective",
    context: "Phase 3 · oncology · autologous cell therapy",
    story:
      "Cell therapy retrospective. January 2024 cutoff (BLA filed); framework on autologous TIL economics — 38% COGS, constrained sponsor, $300M launch costs. FDA approved Feb 2024 as Amtagvi.",
  },
  {
    slug: "tulisokibart",
    name: "tulisokibart",
    sponsor: "Merck (ex-Prometheus)",
    mode: "forward",
    context: "Phase 3 · autoimmune · monoclonal antibody",
    story:
      "Autoimmune forward prediction. Anti-TL1A novel target (no anti-TL1A approved yet). Phase 3 ATLAS-UC + ATLAS-CD ongoing. Tests the new autoimmune-biologic cohort.",
  },
  {
    slug: "aducanumab",
    name: "aducanumab",
    sponsor: "Biogen / Eisai",
    mode: "contested",
    context: "Phase 3 · CNS · monoclonal antibody",
    story:
      "Contested-approval retrospective. March 2019 cutoff, immediately post-ENGAGE/EMERGE futility failure. FDA later approved over a 10-0 AdCom reject — a political process the framework can't predict.",
  },
];

const MODE_LABEL: Record<ShowcaseAsset["mode"], string> = {
  retrospective: "retrospective →",
  forward: "live forward prediction →",
  contested: "contested case →",
};

const MODE_ACCENT: Record<ShowcaseAsset["mode"], string> = {
  retrospective: "hover:border-cyan-bright group-hover:text-cyan-bright",
  forward: "hover:border-magenta-bright group-hover:text-magenta-bright",
  contested: "hover:border-amber-bright group-hover:text-amber-bright",
};

const MODE_LABEL_COLOR: Record<ShowcaseAsset["mode"], string> = {
  retrospective: "text-cyan-bright",
  forward: "text-magenta-bright",
  contested: "text-amber-bright",
};

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="font-display text-4xl font-black uppercase leading-none tracking-[0.06em] text-text-bright sm:text-5xl">
        Asclepius
      </h1>

      <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.15em] text-text-dim">
        Biotech venture valuation · reflexivity-adjusted PoS · phase-gated rNPV
      </p>

      <div className="mt-8">
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-text-dim">
          ── pre-staged assets ──
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          {SHOWCASE_ASSETS.map((asset) => (
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
