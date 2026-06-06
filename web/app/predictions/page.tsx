/**
 * v1.6 Session 2 — public prediction track record.
 *
 * Renders every JSON in predictions/ (synced into lib/predictions-content.ts
 * at build time) as a single scrollable feed: pending forward predictions
 * at the top (open commitments), resolved predictions below (the track
 * record). Each card shows the framework's predicted_pos, the
 * resolution status, and a link to the methodology writeup that
 * frames the prediction.
 *
 * Why this page exists: methodology/10-public-prediction-log describes
 * the *concept* of pre-registered predictions; this page renders the
 * actual receipts. A VC visitor reading the methodology layer wants to
 * see the predictions, not just the principle behind them. The page
 * also reads as a forecasting-accountability surface — rare in
 * valuation tools, valuable to a generalist VC evaluating the framework.
 */

import Link from "next/link";

import { PUBLIC_PREDICTIONS } from "@/lib/predictions-content";

interface PredictionResolution {
  date?: string | null;
  outcome?: number | null;
  source?: string | null;
  note?: string | null;
}

interface PredictionAsset {
  name?: string;
  sponsor?: string | null;
  phase?: string;
  therapeutic_area?: string;
  modality?: string;
}

interface PredictionFramework {
  predicted_pos?: number;
  predicted_pos_ci_low?: number | null;
  predicted_pos_ci_high?: number | null;
  reflexivity_multiplier?: number;
  rnpv_base_usd_m?: number | null;
}

interface PredictionTrial {
  nct_id?: string;
  primary_completion_date?: string;
  primary_endpoint?: string;
}

interface PredictionEntry {
  filename: string;
  prediction_id?: string;
  prediction_date?: string;
  asset?: PredictionAsset;
  framework?: PredictionFramework;
  trial?: PredictionTrial;
  resolution?: PredictionResolution;
  methodology_writeup?: string;
}

// The sync script's `as const` widens the type into a giant tuple union
// at the type level; cast to a workable interface here.
const PREDICTIONS = PUBLIC_PREDICTIONS as readonly PredictionEntry[];

function formatPct(v: number | undefined | null, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

function formatYear(dateStr: string | undefined | null): string {
  if (!dateStr) return "—";
  return dateStr.slice(0, 4);
}

function outcomeText(outcome: number | null | undefined): string {
  if (outcome == null) return "pending";
  if (outcome === 1) return "outcome = 1 (positive)";
  if (outcome === 0) return "outcome = 0 (negative)";
  return `outcome = ${outcome} (partial / ambiguous)`;
}

function brierContribution(
  predicted: number | undefined,
  outcome: number | null | undefined,
): number | null {
  if (predicted == null || outcome == null) return null;
  return (predicted - outcome) ** 2;
}

export default function PredictionsPage() {
  const pending = PREDICTIONS.filter(
    (p) => p.resolution?.outcome == null,
  );
  const resolved = PREDICTIONS.filter(
    (p) => p.resolution?.outcome != null,
  );

  // Compute aggregate Brier score across resolved predictions
  const briers = resolved
    .map((p) => brierContribution(p.framework?.predicted_pos, p.resolution?.outcome))
    .filter((v): v is number => v != null);
  const meanBrier = briers.length
    ? briers.reduce((a, b) => a + b, 0) / briers.length
    : null;

  // How many of the resolved predictions were directionally correct
  // (predicted_pos > 0.5 ⟺ outcome=1)? Simple but useful.
  const directionalCorrect = resolved.filter((p) => {
    const pred = p.framework?.predicted_pos;
    const outcome = p.resolution?.outcome;
    if (pred == null || outcome == null) return false;
    return (pred >= 0.5 && outcome === 1) || (pred < 0.5 && outcome === 0);
  }).length;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <header className="mb-6">
        <h1 className="font-display text-xl font-black uppercase leading-tight tracking-wider text-text-bright sm:text-3xl">
          Public predictions
        </h1>
        <p className="mt-2 max-w-3xl font-prose text-[13px] leading-relaxed text-text-primary">
          Every prediction the framework has made on a public asset, as
          immutable JSON in git. Pending forward predictions are open
          commitments — they resolve at the catalyst date. Resolved
          predictions are the track record. See{" "}
          <Link
            href="/methodology/10-public-prediction-log"
            className="text-cyan-bright underline hover:text-cyan-bright"
          >
            methodology/10
          </Link>{" "}
          for the design.
        </p>
      </header>

      {/* Top-line stats */}
      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat
          label="total"
          value={PREDICTIONS.length.toString()}
          detail="all predictions in the log"
        />
        <Stat
          label="pending"
          value={pending.length.toString()}
          detail="forward / awaiting catalyst"
          accent="magenta"
        />
        <Stat
          label="resolved"
          value={resolved.length.toString()}
          detail="track record"
          accent="cyan"
        />
        <Stat
          label="mean Brier"
          value={meanBrier == null ? "—" : meanBrier.toFixed(3)}
          detail={
            meanBrier == null
              ? "(no resolved yet)"
              : `${directionalCorrect}/${resolved.length} directionally right`
          }
        />
      </div>

      {/* Pending forward predictions */}
      {pending.length > 0 ? (
        <section className="mb-10">
          <h2 className="mb-3 font-display text-[13px] font-semibold uppercase tracking-wider text-magenta-bright">
            ── pending · {pending.length} open commitment{pending.length === 1 ? "" : "s"} ──
          </h2>
          <div className="space-y-3">
            {pending.map((p) => (
              <PredictionCard key={p.prediction_id ?? p.filename} prediction={p} />
            ))}
          </div>
        </section>
      ) : null}

      {/* Resolved track record */}
      <section className="mb-10">
        <h2 className="mb-3 font-display text-[13px] font-semibold uppercase tracking-wider text-cyan-bright">
          ── resolved · track record ──
        </h2>
        <div className="space-y-3">
          {resolved.map((p) => (
            <PredictionCard key={p.prediction_id ?? p.filename} prediction={p} />
          ))}
        </div>
      </section>
    </div>
  );
}

interface StatProps {
  label: string;
  value: string;
  detail: string;
  accent?: "cyan" | "magenta";
}

function Stat({ label, value, detail, accent }: StatProps) {
  const accentClass =
    accent === "magenta"
      ? "text-magenta-bright"
      : accent === "cyan"
        ? "text-cyan-bright"
        : "text-text-bright";
  return (
    <div className="rounded border border-border-dim bg-bg-panel p-3">
      <div className="font-mono text-[9px] uppercase tracking-wider text-text-dim">
        {label}
      </div>
      <div className={`mt-1 font-display text-xl font-bold tabular-nums ${accentClass}`}>
        {value}
      </div>
      <div className="mt-0.5 font-mono text-[10px] text-text-dim">{detail}</div>
    </div>
  );
}

function PredictionCard({ prediction }: { prediction: PredictionEntry }) {
  const { asset, framework, resolution, trial } = prediction;
  const isPending = resolution?.outcome == null;
  const brier = brierContribution(framework?.predicted_pos, resolution?.outcome);
  const directionalRight =
    resolution?.outcome != null && framework?.predicted_pos != null
      ? (framework.predicted_pos >= 0.5 && resolution.outcome === 1) ||
        (framework.predicted_pos < 0.5 && resolution.outcome === 0)
      : null;

  const borderClass = isPending
    ? "border-magenta-bright/30 bg-magenta-bright/5"
    : resolution?.outcome === 1
      ? "border-green-bright/30 bg-green-bright/5"
      : "border-red-bright/30 bg-red-bright/5";

  return (
    <div className={`rounded border ${borderClass} p-3`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 min-w-0">
          <h3 className="font-display text-[14px] font-semibold uppercase tracking-wider text-text-bright break-words">
            {asset?.name ?? prediction.prediction_id ?? prediction.filename}
          </h3>
          {asset?.sponsor ? (
            <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim break-words">
              {asset.sponsor}
            </span>
          ) : null}
        </div>
        <span
          className={`font-mono text-[10px] uppercase tracking-wider ${
            isPending
              ? "text-magenta-bright"
              : resolution?.outcome === 1
                ? "text-green-bright"
                : "text-red-bright"
          }`}
        >
          {outcomeText(resolution?.outcome)}
        </span>
      </div>

      <div className="mt-1.5 font-mono text-[10px] uppercase tracking-wider text-text-dim">
        {asset?.phase} · {asset?.therapeutic_area} · {asset?.modality?.replace(/_/g, " ")} ·
        predicted {formatYear(prediction.prediction_date)}
        {isPending ? ` · catalyst ${formatYear(trial?.primary_completion_date)}` : null}
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Mini label="predicted PoS" value={formatPct(framework?.predicted_pos)} />
        {framework?.rnpv_base_usd_m != null ? (
          <Mini
            label="rNPV base"
            value={`$${framework.rnpv_base_usd_m.toFixed(0)}M`}
          />
        ) : null}
        {!isPending ? (
          <>
            <Mini
              label="Brier"
              value={brier == null ? "—" : brier.toFixed(3)}
            />
            <Mini
              label="directional"
              value={directionalRight == null ? "—" : directionalRight ? "✓" : "✗"}
              accent={directionalRight ? "green" : "red"}
            />
          </>
        ) : (
          <Mini
            label="reflexivity"
            value={
              framework?.reflexivity_multiplier != null
                ? `×${framework.reflexivity_multiplier.toFixed(2)}`
                : "—"
            }
          />
        )}
      </div>

      {resolution?.note || resolution?.source ? (
        <p className="mt-2 font-prose text-[11px] leading-snug text-text-dim">
          {resolution.note ?? resolution.source}
        </p>
      ) : null}

      {prediction.methodology_writeup ? (
        <p className="mt-2 font-mono text-[10px] uppercase tracking-wider">
          <Link
            href={`/${prediction.methodology_writeup.replace(/\.md$/, "").replace(/^methodology\//, "methodology/")}`}
            className="text-cyan-bright hover:underline"
          >
            see {prediction.methodology_writeup} →
          </Link>
        </p>
      ) : null}
    </div>
  );
}

interface MiniProps {
  label: string;
  value: string;
  accent?: "green" | "red";
}

function Mini({ label, value, accent }: MiniProps) {
  const accentClass =
    accent === "green"
      ? "text-green-bright"
      : accent === "red"
        ? "text-red-bright"
        : "text-text-primary";
  return (
    <div>
      <div className="font-mono text-[9px] uppercase tracking-wider text-text-dim">
        {label}
      </div>
      <div className={`font-mono text-[13px] font-bold tabular-nums ${accentClass}`}>
        {value}
      </div>
    </div>
  );
}
