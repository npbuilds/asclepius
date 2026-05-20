import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <h1 className="font-serif text-4xl leading-tight text-ink-900 sm:text-5xl">
        Pricing the path-dependency between a sponsor's balance sheet and
        their trial's probability of success.
      </h1>
      <p className="mt-6 text-lg text-ink-600">
        Asclepius is the first open rNPV tool that models the reflexivity
        between sponsor capital position and clinical-trial quality.
        Capital-constrained sponsors run worse trials; well-capitalized
        sponsors enable adaptive designs and stronger regulatory engagement.
        We make that explicit and quantifiable — with citations on every
        number.
      </p>

      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card title="Probability of Success" detail="BIO/Informa base rates × modality × mechanism × reflexivity. Audit trail on every adjustment." />
        <Card title="Risk-Adjusted NPV" detail="Phase-gated cash flows, 10K-path Monte Carlo, tornado sensitivity, downside scenarios." />
        <Card title="8-Pillar Scorecard" detail="Clinical / regulatory / competitive / manufacturing / IP / financial / team — plus a novel computational-infrastructure pillar." />
        <Card title="Cited Deal Comparables" detail="Each comp ships its source. Implied value from cohort median × target peak sales." />
      </div>

      <div className="mt-10 flex flex-wrap gap-4">
        <Link
          href="/diligence/adagrasib"
          className="rounded-md bg-ink-900 px-6 py-3 text-white shadow-sm hover:bg-ink-800"
        >
          Run the adagrasib worked example →
        </Link>
        <Link
          href="/methodology"
          className="rounded-md border border-ink-200 bg-white px-6 py-3 text-ink-900 hover:bg-ink-50"
        >
          Read the methodology
        </Link>
      </div>

      <div className="mt-16 rounded-lg border border-ink-200 bg-white p-6">
        <h2 className="font-serif text-xl text-ink-900">Worked example</h2>
        <p className="mt-2 text-sm text-ink-600">
          Adagrasib (Mirati → BMS, October 2022). Framework applied to public
          information available before the KRYSTAL-12 Phase 3 readout:
        </p>
        <dl className="mt-4 grid grid-cols-2 gap-4 text-sm tabular-nums sm:grid-cols-4">
          <Stat label="Pre-readout rNPV" value="≈ $530M" />
          <Stat label="MC P25 – P75" value="$290 – $700M" />
          <Stat label="Post-readout (at NDA)" value="≈ $4.9B" />
          <Stat label="Actual BMS deal" value="$4.8B" />
        </dl>
        <p className="mt-4 text-sm text-ink-600">
          Framework brackets the deal price within 2%. The story: pre-readout,
          you'd pay up to ~$550M; post-readout, the deal price is exactly
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
    <div className="rounded-lg border border-ink-200 bg-white p-5">
      <h3 className="font-medium text-ink-900">{title}</h3>
      <p className="mt-2 text-sm text-ink-600">{detail}</p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-ink-400">{label}</div>
      <div className="mt-1 text-lg font-medium text-ink-900">{value}</div>
    </div>
  );
}
