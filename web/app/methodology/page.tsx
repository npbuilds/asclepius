import Link from "next/link";

import { METHODOLOGY_ENTRIES } from "@/lib/methodology-content";

export const metadata = {
  title: "Methodology — Asclepius",
  description:
    "The full methodology folder. Seven writeups, ~20,000 words, every empirical claim cited.",
};

export default function MethodologyIndexPage() {
  // The 00 entry is the product thesis — surface it as the "read this first" lede.
  const lede = METHODOLOGY_ENTRIES.find((e) => e.slug === "00-product-thesis");
  const technical = METHODOLOGY_ENTRIES.filter((e) => e.slug !== "00-product-thesis");

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <header className="mb-12">
        <h1 className="font-serif text-4xl text-ink-900">Methodology</h1>
        <p className="mt-3 max-w-2xl text-ink-600">
          The framework's intellectual foundation. Seven writeups,{" "}
          {METHODOLOGY_ENTRIES.reduce(
            (acc, e) => acc + e.body.split(/\s+/).length,
            0,
          ).toLocaleString()}{" "}
          words, every empirical claim cited.
        </p>
        <p className="mt-2 max-w-2xl text-sm text-ink-400">
          Each writeup is also a standalone document; cross-links between them
          stay within the methodology folder. A senior reader can land on any
          file and follow the citations from there.
        </p>
      </header>

      {lede ? (
        <section className="mb-12">
          <div className="text-xs uppercase tracking-wider text-accent-700">
            Read this first
          </div>
          <Link
            href={`/methodology/${lede.slug}`}
            className="block rounded-lg border-2 border-accent-600/20 bg-gradient-to-br from-accent-50 to-white p-6 hover:border-accent-600/40"
          >
            <h2 className="font-serif text-2xl text-ink-900">{lede.title}</h2>
            <p className="mt-3 text-ink-600">{lede.summary}</p>
            <div className="mt-3 text-sm font-medium text-accent-700">
              Read the product thesis →
            </div>
          </Link>
        </section>
      ) : null}

      <section>
        <div className="mb-4 text-xs uppercase tracking-wider text-ink-400">
          Technical writeups
        </div>
        <div className="space-y-4">
          {technical.map((entry) => (
            <Link
              key={entry.slug}
              href={`/methodology/${entry.slug}`}
              className="block rounded-lg border border-ink-200 bg-white p-5 hover:border-ink-400"
            >
              <div className="flex items-baseline justify-between gap-4">
                <h3 className="font-serif text-lg text-ink-900">
                  {entry.title}
                </h3>
                <div className="shrink-0 text-xs tabular-nums text-ink-400">
                  {entry.body.split(/\s+/).length.toLocaleString()} words
                </div>
              </div>
              <p className="mt-2 text-sm text-ink-600">{entry.summary}</p>
              {entry.primary_sources.length > 0 ? (
                <div className="mt-2 text-xs text-ink-400">
                  {entry.primary_sources.length} primary{" "}
                  {entry.primary_sources.length === 1 ? "source" : "sources"} cited
                </div>
              ) : null}
            </Link>
          ))}
        </div>
      </section>

      <section className="mt-12 rounded-lg border border-ink-200 bg-white p-5 text-sm text-ink-600">
        <h2 className="font-medium text-ink-900">How to read the methodology folder</h2>
        <ul className="mt-3 space-y-2 list-disc pl-5">
          <li>
            <strong>For framework intuition:</strong> read{" "}
            <Link
              href="/methodology/02-reflexivity-thesis"
              className="text-accent-700 underline"
            >
              02-reflexivity-thesis
            </Link>{" "}
            and then{" "}
            <Link
              href="/methodology/05-worked-example-adagrasib"
              className="text-accent-700 underline"
            >
              05-worked-example-adagrasib
            </Link>
            . Together ~4,400 words; together they tell the full story of what
            the tool is.
          </li>
          <li>
            <strong>For the formal foundation:</strong> read{" "}
            <Link
              href="/methodology/06-signaling-equilibrium"
              className="text-accent-700 underline"
            >
              06-signaling-equilibrium
            </Link>{" "}
            for Spence/Akerlof grounding and{" "}
            <Link
              href="/methodology/01-pos-framework"
              className="text-accent-700 underline"
            >
              01-pos-framework
            </Link>{" "}
            for the full PoS chain reference.
          </li>
          <li>
            <strong>For the engine mechanics:</strong> read{" "}
            <Link
              href="/methodology/03-rnpv-monte-carlo"
              className="text-accent-700 underline"
            >
              03-rnpv-monte-carlo
            </Link>{" "}
            and{" "}
            <Link
              href="/methodology/04-scorecard-pillars"
              className="text-accent-700 underline"
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
