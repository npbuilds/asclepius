import Link from "next/link";

import { METHODOLOGY_ENTRIES } from "@/lib/methodology-content";

export const metadata = {
  title: "Methodology — Asclepius",
  description:
    "The full methodology folder. Seven writeups, ~20,000 words, every empirical claim cited.",
};

export default function MethodologyIndexPage() {
  const lede = METHODOLOGY_ENTRIES.find((e) => e.slug === "00-product-thesis");
  const technical = METHODOLOGY_ENTRIES.filter(
    (e) => e.slug !== "00-product-thesis",
  );

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <header className="mb-8">
        <div className="font-display text-[10px] uppercase tracking-[0.2em] text-text-dim">
          /methodology
        </div>
        <h1 className="mt-2 font-display text-3xl font-bold uppercase leading-[1.1] tracking-[0.04em] text-text-bright">
          Methodology
        </h1>
        <p className="mt-3 max-w-2xl font-prose text-base text-text-primary">
          The framework's intellectual foundation. Seven writeups, every
          empirical claim cited.
        </p>
        <p className="mt-2 max-w-2xl font-prose text-sm text-text-dim">
          Each writeup is also a standalone document; cross-links between them
          stay within the methodology folder. A senior reader can land on any
          file and follow the citations from there.
        </p>
      </header>

      {lede ? (
        <section className="mb-8">
          <div className="font-display text-[10px] uppercase tracking-[0.2em] text-magenta-bright">
            Read this first
          </div>
          <Link
            href={`/methodology/${lede.slug}`}
            className="mt-2 block rounded border-2 border-magenta-bright/40 bg-magenta-bright/5 p-4 hover:border-magenta-bright/80"
          >
            <h2 className="font-display text-lg font-bold uppercase tracking-wider text-text-bright">
              {lede.title}
            </h2>
            <p className="mt-2 font-prose text-sm text-text-primary">
              {lede.summary}
            </p>
            <div className="mt-3 font-display text-xs font-semibold uppercase tracking-wider text-magenta-bright">
              Read the product thesis →
            </div>
          </Link>
        </section>
      ) : null}

      <section>
        <div className="mb-3 font-display text-[10px] uppercase tracking-[0.2em] text-text-dim">
          Technical writeups
        </div>
        <div className="space-y-3">
          {technical.map((entry) => (
            <Link
              key={entry.slug}
              href={`/methodology/${entry.slug}`}
              className="block rounded border border-border-dim bg-bg-panel p-4 hover:border-cyan-bright"
            >
              <h3 className="font-display text-base font-semibold uppercase tracking-wider text-text-bright">
                {entry.title}
              </h3>
              <p className="mt-1.5 font-prose text-sm text-text-primary">
                {entry.summary}
              </p>
              {entry.primary_sources.length > 0 ? (
                <div className="mt-2 font-mono text-[10px] uppercase tracking-wider text-amber-bright">
                  {entry.primary_sources.length} primary{" "}
                  {entry.primary_sources.length === 1 ? "source" : "sources"}{" "}
                  cited
                </div>
              ) : null}
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-8 rounded border border-border-dim bg-bg-panel p-4 text-sm text-text-primary">
        <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-bright">
          How to read the methodology folder
        </h2>
        <ul className="mt-3 list-disc space-y-2 pl-5 font-prose">
          <li>
            <strong className="text-text-bright">
              For framework intuition:
            </strong>{" "}
            read{" "}
            <Link
              href="/methodology/02-reflexivity-thesis"
              className="text-cyan-bright underline-offset-2 hover:underline"
            >
              02-reflexivity-thesis
            </Link>{" "}
            and then{" "}
            <Link
              href="/methodology/05-worked-example-adagrasib"
              className="text-cyan-bright underline-offset-2 hover:underline"
            >
              05-worked-example-adagrasib
            </Link>
            . Together they tell the full story of what the tool is.
          </li>
          <li>
            <strong className="text-text-bright">
              For the formal foundation:
            </strong>{" "}
            read{" "}
            <Link
              href="/methodology/06-signaling-equilibrium"
              className="text-cyan-bright underline-offset-2 hover:underline"
            >
              06-signaling-equilibrium
            </Link>{" "}
            for Spence/Akerlof grounding and{" "}
            <Link
              href="/methodology/01-pos-framework"
              className="text-cyan-bright underline-offset-2 hover:underline"
            >
              01-pos-framework
            </Link>{" "}
            for the full PoS chain reference.
          </li>
          <li>
            <strong className="text-text-bright">For the engine mechanics:</strong>{" "}
            read{" "}
            <Link
              href="/methodology/03-rnpv-monte-carlo"
              className="text-cyan-bright underline-offset-2 hover:underline"
            >
              03-rnpv-monte-carlo
            </Link>{" "}
            and{" "}
            <Link
              href="/methodology/04-scorecard-pillars"
              className="text-cyan-bright underline-offset-2 hover:underline"
            >
              04-scorecard-pillars
            </Link>
            . The latter consolidates the framework's Known Limitations.
          </li>
        </ul>
      </section>
    </div>
  );
}
