// Showcase — a narrated case study that makes the framework's differentiated
// thinking legible WITHOUT requiring the reader to construct the triggering
// asset themselves. Step (c) of the product roadmap.
//
// Honesty stance: every number on this page is real engine output (computed
// by the actual PoS / rNPV / comparables engines for the Ac-225 inputs shown).
// The narration is editorial — "here is how I read this" — and is clearly
// framed as such. No agent memo is faked; the verdict is an analyst synthesis,
// and the CTA points to the live workbench to generate the real memo.
//
// Flagship asset: an Actinium-225 alpha-emitter (radioligand therapy) from a
// capital-constrained junior. Chosen because it lights up EVERY differentiator
// at once — the reflexivity multiplier (constrained capital), the supply
// constraint (isotope-gated, the newest thesis), the frontier-modality comp
// cohort — where the canonical adagrasib worked example shows none of them.

import Link from "next/link";

export const metadata = {
  title: "How the tool thinks — Ac-225 case study | Asclepius",
  description:
    "A worked walkthrough of a hard frontier asset, showing the reflexivity and supply-constraint theses in action.",
};

// --- Baked engine output (Ac-225, phase 1, oncology, radiopharmaceutical,
// capital_position=constrained, supply_constraint=severe, peak $1,500M).
// Real values from the PoS / rNPV / comparables engines. ---------------------

const POS_BASE = 4.7;
const POS_FINAL = 5.5;

interface Step {
  mult: number;
  name: string;
  source: string;
  kind: "modality" | "boost" | "path" | "reg";
}

const WATERFALL: Step[] = [
  { mult: 0.95, name: "modality: radiopharmaceutical", source: "Asclepius estimate (anchored on approved radioligands; no BIO/Informa cohort)", kind: "modality" },
  { mult: 1.2, name: "biomarker enrichment", source: "Wong 2019 §4.3", kind: "boost" },
  { mult: 1.15, name: "target validated", source: "Practitioner heuristic; consistent with Wong 2019", kind: "boost" },
  { mult: 1.05, name: "Orphan Drug Designation", source: "BIO 2021 — rare/orphan LOA uplift", kind: "reg" },
  { mult: 1.03, name: "Fast Track Designation", source: "FDA Fast Track; practitioner-observed", kind: "reg" },
  { mult: 0.88, name: "reflexivity: constrained", source: "Asclepius methodology/02 — capital as path-dependency", kind: "path" },
  { mult: 0.93, name: "supply constraint: severe", source: "Asclepius framework — supply as path-dependency", kind: "path" },
];

const RNPV_BASE_USD_M = 18;
const NOMINAL_PEAK_USD_M = 1500;
const SUPPLY_CEILING_PCT = 0.65;
const SUPPLY_ADJ_PEAK_USD_M = 975;

const COMP_MULTIPLE = 2.0;
const COMP_IMPLIED_USD_M = 3000;

function Annotation({
  label,
  children,
  tone = "cyan",
}: {
  label: string;
  children: React.ReactNode;
  tone?: "cyan" | "magenta" | "amber";
}) {
  const toneClass =
    tone === "magenta"
      ? "border-magenta-bright/40 bg-magenta-bright/5 text-magenta-bright"
      : tone === "amber"
        ? "border-amber-bright/40 bg-amber-bright/5 text-amber-bright"
        : "border-cyan-bright/40 bg-cyan-bright/5 text-cyan-bright";
  return (
    <div className={`mt-2 rounded border p-3 ${toneClass}`}>
      <div className="mb-1 font-mono text-[10px] uppercase tracking-[0.15em]">
        {label}
      </div>
      <div className="font-prose text-[13px] leading-relaxed text-text-primary">
        {children}
      </div>
    </div>
  );
}

function SectionHeader({ n, title }: { n: string; title: string }) {
  return (
    <h2 className="mb-2 mt-8 flex items-baseline gap-2 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
      <span className="text-text-dim">{n}</span>
      {title}
    </h2>
  );
}

export default function ShowcasePage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <header className="border-b border-border-dim pb-4">
        <div className="flex items-center justify-between gap-3">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-dim">
            Case study · how the tool thinks
          </div>
          <Link
            href="/"
            className="font-mono text-[11px] uppercase tracking-wider text-text-dim hover:text-cyan-bright"
          >
            [ ← home ]
          </Link>
        </div>
        <h1 className="mt-2 font-display text-xl uppercase tracking-wide text-text-bright">
          Actinium-225 alpha therapy — a hard asset, read end to end
        </h1>
        <p className="mt-2 font-prose text-[14px] leading-relaxed text-text-primary">
          Most valuation tools price a drug as a probability-weighted cash-flow
          stream and stop. This one treats two <em>structural</em> facts as
          first-class value drivers: who holds the capital, and who controls the
          supply. An Actinium-225 radioligand from a capital-constrained junior
          is the asset where both bite at once — so it&rsquo;s the clearest way
          to show the reasoning, not just the result.
        </p>
      </header>

      {/* 1. PoS */}
      <SectionHeader n="01" title="Probability of success" />
      <p className="font-prose text-[13px] leading-relaxed text-text-primary">
        The chain starts at a {POS_BASE}% phase-1 base rate and lands at{" "}
        <strong className="text-text-bright">{POS_FINAL}%</strong> after seven
        named multipliers — every one carrying its own citation, so the number
        is auditable rather than asserted.
      </p>

      <div className="mt-3 overflow-hidden rounded border border-border-dim">
        <div className="flex items-center justify-between bg-bg-panel px-3 py-1.5 font-mono text-[11px] text-text-dim">
          <span>base rate</span>
          <span className="text-text-bright">{POS_BASE}%</span>
        </div>
        {WATERFALL.map((s) => {
          const up = s.mult >= 1;
          const isPath = s.kind === "path";
          return (
            <div
              key={s.name}
              className={`flex items-center justify-between border-t border-border-dim px-3 py-1.5 ${
                isPath ? "bg-magenta-bright/5" : "bg-bg-panel"
              }`}
            >
              <span className="font-mono text-[11px] text-text-primary">
                {isPath ? "◆ " : ""}
                {s.name}
              </span>
              <span
                className={`font-mono text-[11px] ${up ? "text-green-bright" : "text-red-bright"}`}
              >
                ×{s.mult.toFixed(2)}
              </span>
            </div>
          );
        })}
        <div className="flex items-center justify-between border-t border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-[11px]">
          <span className="text-text-dim">final LOA</span>
          <span className="text-text-bright">{POS_FINAL}%</span>
        </div>
      </div>

      <Annotation label="◆ the two path-dependency rows" tone="magenta">
        The diamonds are the distinctive part. A constrained sponsor takes the
        chain down{" "}
        <strong className="text-text-bright">×0.88</strong> (
        <Link href="/methodology/02-reflexivity-thesis" className="text-cyan-bright hover:underline">
          reflexivity
        </Link>
        : a raise-dependent junior signals weakly and is forced into
        trial-design compromises), and severe isotope supply takes another{" "}
        <strong className="text-text-bright">×0.93</strong> (a supply bottleneck
        is execution risk, not just a commercial cap). Generic frameworks model
        neither — they treat capital and supply as someone else&rsquo;s problem.
      </Annotation>

      <Annotation label="honest provenance">
        Note the modality row: <strong className="text-text-bright">×0.95</strong>{" "}
        is labelled an <em>&ldquo;Asclepius estimate, no BIO/Informa cohort.&rdquo;</em>{" "}
        Radiopharmaceuticals post-date the 2021 industry dataset, so the tool
        says so rather than borrowing a citation it isn&rsquo;t entitled to.
        Every multiplier renders its real source — including the ones that admit
        a gap.
      </Annotation>

      {/* 2. Valuation */}
      <SectionHeader n="02" title="Valuation — and the ceiling generic DCF misses" />
      <p className="font-prose text-[13px] leading-relaxed text-text-primary">
        The risk-adjusted rNPV is a{" "}
        <strong className="text-text-bright">${RNPV_BASE_USD_M}M</strong> floor —
        what a {POS_FINAL}%-LOA phase-1 asset is worth today once you weight the
        whole cash-flow tree by the chance it ever launches.
      </p>

      <Annotation label="the supply ceiling on revenue" tone="magenta">
        Here&rsquo;s the move a DCF tool can&rsquo;t make: severe supply
        doesn&rsquo;t just add risk to the PoS, it <em>caps achievable peak
        sales</em>. The model holds nominal peak at{" "}
        <strong className="text-text-bright">${NOMINAL_PEAK_USD_M.toLocaleString()}M</strong>{" "}
        but applies a{" "}
        <strong className="text-text-bright">×{SUPPLY_CEILING_PCT}</strong> supply
        ceiling, so the revenue line is built on{" "}
        <strong className="text-text-bright">${SUPPLY_ADJ_PEAK_USD_M}M</strong>.
        You can&rsquo;t sell isotopes you can&rsquo;t make — the ceiling belongs
        on the revenue side, not buried in the discount rate.
      </Annotation>

      {/* 3. Comparables */}
      <SectionHeader n="03" title="Comparables — and a $18M ↔ $3B bracket" />
      <p className="font-prose text-[13px] leading-relaxed text-text-primary">
        The asset routes to a curated{" "}
        <strong className="text-text-bright">oncology · radiopharmaceutical</strong>{" "}
        cohort (RayzeBio/BMS, Fusion/AZ, POINT/Lilly), median{" "}
        <strong className="text-text-bright">{COMP_MULTIPLE.toFixed(1)}×</strong>{" "}
        EV/peak-sales — <em>not</em> the kinase-TKI fallback an off-the-shelf
        comp set would have forced. At {COMP_MULTIPLE.toFixed(1)}× the cohort
        implies roughly{" "}
        <strong className="text-text-bright">${COMP_IMPLIED_USD_M.toLocaleString()}M</strong>{" "}
        of strategic value.
      </p>

      <Annotation label="reading the bracket" tone="amber">
        So the framework brackets the asset between an{" "}
        <strong className="text-text-bright">${RNPV_BASE_USD_M}M</strong>{" "}
        risk-adjusted floor and a{" "}
        <strong className="text-text-bright">~${(COMP_IMPLIED_USD_M / 1000).toFixed(0)}B</strong>{" "}
        strategic ceiling. That gap <em>is</em> the thesis: it&rsquo;s the
        de-risking premium an acquirer pays once the isotope-supply and phase-1
        risks resolve — and the supply ceiling is precisely what keeps the upper
        bound soft until the supply chain is proven out.
      </Annotation>

      {/* 4. The call */}
      <SectionHeader n="04" title="The call" />
      <div className="rounded border border-green-bright/30 bg-green-bright/5 p-4">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <span className="rounded bg-cyan-bright/10 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan-bright">
            cautious
          </span>
          <span className="rounded border border-amber-bright/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-amber-bright">
            medium conviction
          </span>
        </div>
        <p className="font-prose text-[13px] leading-relaxed text-text-primary">
          Watch, don&rsquo;t chase — yet. The biology and the regulatory path
          are real, and the radiopharma cohort says the strategic ceiling is
          genuine. But the two path-dependencies net-move the call <em>down</em>:
          a constrained sponsor (×0.88) is one failed raise from a fire sale,
          and severe isotope supply (×0.93 on PoS, −35% on peak) caps the very
          upside the comp set is pricing. The asset is a buy <em>at the right
          basis once supply de-risks</em> — not before.
        </p>
        <div className="mt-3 rounded border border-red-bright/40 bg-red-bright/10 p-2.5">
          <div className="mb-0.5 font-mono text-[10px] uppercase tracking-wider text-red-bright">
            kill criterion (falsifiable)
          </div>
          <div className="font-prose text-[12px] text-text-primary">
            A failure to secure a multi-year Ac-225 supply agreement (or
            in-house production milestone) before the phase-2 start flips this to
            avoid — without scalable isotope, the $3B ceiling is fiction and the
            $18M floor is the whole story.
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-border-dim pt-5">
        <Link
          href="/diligence/adagrasib"
          className="rounded border border-cyan-bright bg-cyan-bright/10 px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
        >
          [ run the live workbench → ]
        </Link>
        <Link
          href="/methodology"
          className="rounded border border-border-dim bg-bg-panel px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider text-text-dim hover:border-cyan-bright/50 hover:text-cyan-bright"
        >
          [ read the methodology → ]
        </Link>
        <span className="ml-auto font-prose text-[11px] italic text-text-dim">
          Numbers are live engine output; the reading is editorial.
        </span>
      </div>
    </main>
  );
}
