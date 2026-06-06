"use client";

// Game-Theory Adversary panel.
//
// v1.7.7 reframes the panel around structured *flags* — each flag is a card
// with severity-colored border, a framework-citation badge, the rationale,
// and a falsifiable test. The legacy findings list still renders below as a
// compact fallback for cached payloads that predate the flag format.
// Magenta-tinted to match the reflexivity/agent palette assignment (this
// agent operationalizes the same Spence/Akerlof framework behind the
// reflexivity adjustment).

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { type AgentError, runGameTheoryAdversary } from "@/lib/api-client";
import type { ClientDiligenceRecord } from "@/lib/module-registry";
import type {
  AdversaryOutput,
  AdversaryVerdictShift,
  AdversarySeverity,
  AdversaryLens,
} from "@/lib/types";

// --- v1.7.7 structured flag shape ----------------------------------------
// Inlined here (rather than added to web/lib/types.ts) so the change is
// scoped to this panel; the API parser tolerates payloads with or without
// the ``flags`` field.
type FlagType =
  | "signaling_equilibrium"
  | "winners_curse"
  | "bayesian_persuasion"
  | "cohort_base_rate_check"
  | "data_quality"
  | "regulatory_path";

type FlagSeverity = "high" | "medium" | "low";

interface AdversaryFlag {
  flag_type: FlagType;
  severity: FlagSeverity;
  title: string;
  rationale: string;
  test: string;
  cite: string[];
}

type AdversaryOutputWithFlags = AdversaryOutput & { flags?: AdversaryFlag[] };

const VERDICT_COLOR: Record<AdversaryVerdictShift, string> = {
  upgrade: "bg-green-bright/20 text-green-bright",
  hold: "bg-bg-panel-hover text-text-primary",
  downgrade: "bg-red-bright/20 text-red-bright",
};

const SEVERITY_COLOR: Record<AdversarySeverity, string> = {
  minor: "text-text-dim",
  moderate: "text-amber-bright",
  critical: "text-red-bright",
};

const LENS_LABEL: Record<AdversaryLens, string> = {
  signaling: "Signaling",
  auction: "Auction",
  persuasion: "Persuasion",
};

// Severity-driven border + label color for the new structured cards.
const FLAG_SEVERITY_BORDER: Record<FlagSeverity, string> = {
  high: "border-red-bright/60 bg-red-bright/5",
  medium: "border-amber-bright/60 bg-amber-bright/5",
  low: "border-text-dim/40 bg-bg-panel/40",
};

const FLAG_SEVERITY_LABEL: Record<FlagSeverity, string> = {
  high: "text-red-bright",
  medium: "text-amber-bright",
  low: "text-text-dim",
};

const FLAG_TYPE_LABEL: Record<FlagType, string> = {
  signaling_equilibrium: "Signaling equilibrium",
  winners_curse: "Winner's curse",
  bayesian_persuasion: "Bayesian persuasion",
  cohort_base_rate_check: "Cohort base-rate check",
  data_quality: "Data quality",
  regulatory_path: "Regulatory path",
};

export function AdversaryPanel({ record }: { record: ClientDiligenceRecord }) {
  const [adversary, setAdversary] =
    useState<AdversaryOutputWithFlags | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AgentError | null>(null);

  const ready =
    record.pos && record.rnpv && record.scorecard && record.comparables;

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const result = (await runGameTheoryAdversary(
        record as unknown as Record<string, unknown>,
      )) as AdversaryOutputWithFlags;
      setAdversary(result);
    } catch (e) {
      setError(e as AgentError);
    } finally {
      setLoading(false);
    }
  }

  const flags = adversary?.flags ?? [];

  return (
    <section className="rounded border border-magenta-bright/30 bg-magenta-bright/5 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-display text-[13px] font-semibold uppercase tracking-wider text-magenta-bright">
          Game-Theory Adversary · agent
        </h2>
        <button
          type="button"
          onClick={generate}
          disabled={!ready || loading}
          className="rounded border border-magenta-bright bg-magenta-bright/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-magenta-bright hover:bg-magenta-bright/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading
            ? "[ stress-testing… ]"
            : adversary
              ? "[ re-run ]"
              : "[ stress-test thesis → ]"}
        </button>
      </div>

      {!ready ? (
        <p className="font-mono text-[11px] uppercase tracking-wider text-text-dim">
          Waiting for PoS / rNPV / scorecard / comparables…
        </p>
      ) : null}

      {error ? (
        <div className="rounded border border-red-bright/30 bg-red-bright/10 p-2.5 font-mono text-[11px] text-red-bright">
          {error.status === 503
            ? "● No live agent key configured on this deploy. Adagrasib is cached; other assets need ANTHROPIC_API_KEY."
            : `● Agent error (${error.status}): ${error.message}`}
        </div>
      ) : null}

      {adversary ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-text-dim">
            <span
              className={`rounded px-1.5 py-0.5 ${VERDICT_COLOR[adversary.verdict_shift]}`}
            >
              ● verdict: {adversary.verdict_shift}
            </span>
            {adversary.recommendation_shift_to ? (
              <span className="rounded bg-red-bright/10 px-1.5 py-0.5 text-red-bright">
                → {adversary.recommendation_shift_to.replace("_", " ")}
              </span>
            ) : null}
            <span>
              {adversary.from_cache
                ? "● cached"
                : `● ${adversary.model_used}`}
            </span>
            <span className="ml-auto">
              {new Date(adversary.generated_at).toISOString().slice(0, 10)}
            </span>
          </div>

          {/* v1.7.7 — structured flag cards. */}
          {flags.length > 0 ? (
            <ul className="space-y-2">
              {flags.map((f, i) => (
                <li
                  key={i}
                  className={`rounded border-l-2 ${FLAG_SEVERITY_BORDER[f.severity]} border-y border-r border-y-transparent border-r-transparent p-2.5`}
                >
                  <div className="mb-1 flex flex-wrap items-baseline gap-2 font-mono text-[10px] uppercase tracking-wider">
                    <span
                      className={`${FLAG_SEVERITY_LABEL[f.severity]}`}
                    >
                      ● {f.severity}
                    </span>
                    <span className="text-magenta-bright">
                      {FLAG_TYPE_LABEL[f.flag_type]}
                    </span>
                    {f.cite.length > 0 ? (
                      <span className="text-text-dim">
                        cite: {f.cite.join(", ")}
                      </span>
                    ) : null}
                  </div>
                  <div className="mb-1.5 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
                    {f.title}
                  </div>
                  <p className="mb-2 font-prose text-[12px] leading-relaxed text-text-primary">
                    {f.rationale}
                  </p>
                  <div className="rounded border border-cyan-bright/30 bg-cyan-bright/5 p-2 font-mono text-[11px] text-text-primary">
                    <span className="mr-1.5 uppercase tracking-wider text-cyan-bright">
                      test ▸
                    </span>
                    {f.test}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}

          {/* Legacy findings — preserved for back-compat with cached payloads
              that predate the structured-flag format. */}
          {adversary.findings.length > 0 ? (
            <ul className="space-y-1 font-mono text-[11px]">
              {adversary.findings.map((f, i) => (
                <li
                  key={i}
                  className="grid grid-cols-[auto_auto_1fr] items-baseline gap-2"
                >
                  <span className="uppercase tracking-wider text-text-dim">
                    {LENS_LABEL[f.lens]}
                  </span>
                  <span
                    className={`uppercase tracking-wider ${SEVERITY_COLOR[f.severity]}`}
                  >
                    ● {f.severity}
                  </span>
                  <span className="font-prose text-[12px] normal-case tracking-normal text-text-primary">
                    {f.claim}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}

          {adversary.body_markdown ? (
            <article className="prose prose-sm max-w-none font-prose dark:prose-invert prose-headings:font-display prose-headings:uppercase prose-headings:tracking-wider prose-headings:text-text-bright prose-h2:text-base prose-h2:mt-4 prose-p:text-text-primary prose-strong:text-text-bright prose-li:text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {adversary.body_markdown}
              </ReactMarkdown>
            </article>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
