import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="font-display text-3xl font-bold uppercase leading-[1.1] tracking-[0.04em] text-text-bright sm:text-4xl">
        Pricing the path-dependency between a sponsor's balance sheet and
        their trial's probability of success.
      </h1>
      <p className="mt-5 font-prose text-base leading-relaxed text-text-primary">
        Asclepius is the first open rNPV tool that models the reflexivity
        between sponsor capital position and clinical-trial quality.
        Capital-constrained sponsors run worse trials; well-capitalized
        sponsors enable adaptive designs and stronger regulatory engagement.
        We make that explicit and quantifiable — with citations on every
        number.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Card
          title="Probability of Success"
          detail="BIO/Informa base rates × modality × mechanism × reflexivity. Audit trail on every adjustment."
        />
        <Card
          title="Risk-Adjusted NPV"
          detail="Phase-gated cash flows, 10K-path Monte Carlo, tornado sensitivity, downside scenarios."
        />
        <Card
          title="8-Pillar Scorecard"
          detail="Clinical / regulatory / competitive / manufacturing / IP / financial / team — plus a novel computational-infrastructure pillar."
        />
        <Card
          title="Cited Deal Comparables"
          detail="Each comp ships its source. Implied value from cohort median × target peak sales."
        />
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/diligence/adagrasib"
          className="rounded border border-cyan-bright bg-cyan-bright/10 px-5 py-2 font-display text-xs font-semibold uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
        >
          Run the adagrasib worked example →
        </Link>
        <Link
          href="/methodology"
          className="rounded border border-border-dim bg-bg-panel px-5 py-2 font-display text-xs font-semibold uppercase tracking-wider text-text-primary hover:border-magenta-bright hover:text-magenta-bright"
        >
          Read the methodology
        </Link>
      </div>

      <div className="mt-12 rounded border border-border-dim bg-bg-panel p-4">
        <h2 className="font-display text-[11px] font-semibold uppercase tracking-[0.2em] text-text-dim">
          Worked example
        </h2>
        <p className="mt-2 font-prose text-sm text-text-primary">
          Adagrasib (Mirati → BMS, October 2022). Framework applied to public
          information available before the KRYSTAL-12 Phase 3 readout:
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Pre-readout rNPV" value="$516M" />
          <Stat label="MC P25 – P75" value="$290 – $700M" />
          <Stat label="Post-readout (at NDA)" value="$4,581M" />
          <Stat label="Actual BMS deal" value="$4,800M" accent="green" />
        </dl>
        <p className="mt-4 font-prose text-sm text-text-primary">
          Framework brackets the deal price within ~5%. The story: pre-readout,
          you'd pay up to ~$700M; post-readout, the deal price is exactly
          defensible. Winner's-curse adjustment to ~$4.4–4.6B implies BMS's
          premium reflects strategic KRAS-franchise value, not financial fair
          value.
        </p>
      </div>
    </div>
  );
}

function Card({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded border border-border-dim bg-bg-panel p-4">
      <h3 className="font-display text-xs font-semibold uppercase tracking-wider text-text-bright">
        {title}
      </h3>
      <p className="mt-1.5 font-prose text-sm text-text-primary">{detail}</p>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "green";
}) {
  return (
    <div>
      <div className="font-display text-[10px] uppercase tracking-[0.2em] text-text-dim">
        {label}
      </div>
      <div
        className={`mt-1 font-mono text-base font-bold tabular-nums ${
          accent === "green" ? "text-green-bright" : "text-text-bright"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
