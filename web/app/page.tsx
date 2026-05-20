import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="font-display text-4xl font-bold uppercase leading-tight tracking-wide text-text-bright sm:text-5xl">
        Pricing the path-dependency between a sponsor's balance sheet and
        their trial's probability of success.
      </h1>
      <p className="mt-6 text-lg text-text-primary">
        Asclepius is the first open rNPV tool that models the reflexivity
        between sponsor capital position and clinical-trial quality.
        Capital-constrained sponsors run worse trials; well-capitalized
        sponsors enable adaptive designs and stronger regulatory engagement.
        We make that explicit and quantifiable — with citations on every
        number.
      </p>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
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

      <div className="mt-10 flex flex-wrap gap-4">
        <Link
          href="/diligence/adagrasib"
          className="rounded border border-cyan-bright bg-cyan-bright/10 px-6 py-3 font-display text-sm font-semibold uppercase tracking-wider text-cyan-bright hover:bg-cyan-bright/20"
        >
          Run the adagrasib worked example →
        </Link>
        <Link
          href="/methodology"
          className="rounded border border-border-dim bg-bg-panel px-6 py-3 font-display text-sm font-semibold uppercase tracking-wider text-text-primary hover:border-cyan-bright hover:text-cyan-bright"
        >
          Read the methodology
        </Link>
      </div>

      <div className="mt-16 rounded border border-border-dim bg-bg-panel p-6">
        <h2 className="font-display text-xs font-semibold uppercase tracking-[0.2em] text-text-dim">
          Worked example
        </h2>
        <p className="mt-3 text-sm text-text-primary">
          Adagrasib (Mirati → BMS, October 2022). Framework applied to public
          information available before the KRYSTAL-12 Phase 3 readout:
        </p>
        <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat label="Pre-readout rNPV" value="$516M" />
          <Stat label="MC P25 – P75" value="$290 – $700M" />
          <Stat label="Post-readout (at NDA)" value="$4,581M" />
          <Stat label="Actual BMS deal" value="$4,800M" />
        </dl>
        <p className="mt-5 text-sm text-text-primary">
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
    <div className="rounded border border-border-dim bg-bg-panel p-5">
      <h3 className="font-display text-sm font-semibold uppercase tracking-wider text-text-bright">
        {title}
      </h3>
      <p className="mt-2 text-sm text-text-primary">{detail}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-display text-[10px] uppercase tracking-[0.2em] text-text-dim">
        {label}
      </div>
      <div className="mt-1 font-mono text-lg tabular-nums text-text-bright">
        {value}
      </div>
    </div>
  );
}
