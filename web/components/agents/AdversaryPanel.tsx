"use client";

// Game-Theory Adversary panel — runs after the memo (conceptually) and
// surfaces findings under three game-theoretic lenses: signaling, auction,
// persuasion. Magenta-tinted to match the reflexivity/agent palette
// assignment (this agent operationalizes the same Spence/Akerlof framework
// behind the reflexivity adjustment).

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
  Recommendation,
} from "@/lib/types";

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

export function AdversaryPanel({ record }: { record: ClientDiligenceRecord }) {
  const [adversary, setAdversary] = useState<AdversaryOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AgentError | null>(null);

  const ready =
    record.pos && record.rnpv && record.scorecard && record.comparables;

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const result = await runGameTheoryAdversary(
        record as unknown as Record<string, unknown>,
      );
      setAdversary(result);
    } catch (e) {
      setError(e as AgentError);
    } finally {
      setLoading(false);
    }
  }

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

          <article className="prose prose-sm max-w-none font-prose dark:prose-invert prose-headings:font-display prose-headings:uppercase prose-headings:tracking-wider prose-headings:text-text-bright prose-h2:text-base prose-h2:mt-4 prose-p:text-text-primary prose-strong:text-text-bright prose-li:text-text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {adversary.body_markdown}
            </ReactMarkdown>
          </article>
        </div>
      ) : null}
    </section>
  );
}
