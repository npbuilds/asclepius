import Link from "next/link";

import { SystemStatus } from "@/components/SystemStatus";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="font-display text-4xl font-black uppercase leading-none tracking-[0.06em] text-text-bright sm:text-5xl">
        Asclepius
      </h1>

      <p className="mt-3 font-mono text-[11px] uppercase tracking-[0.15em] text-text-dim">
        Biotech venture valuation · reflexivity-adjusted PoS · phase-gated rNPV
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        <Link
          href="/diligence/adagrasib"
          className="rounded border border-cyan-bright bg-cyan-bright/10 px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
        >
          [ Launch workbench → ]
        </Link>
        <Link
          href="/methodology"
          className="rounded border border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-text-primary hover:border-magenta-bright hover:text-magenta-bright"
        >
          [ Methodology → ]
        </Link>
      </div>

      <div className="mt-8 rounded border border-border-dim bg-bg-panel p-3">
        <SystemStatus />
      </div>
    </div>
  );
}
