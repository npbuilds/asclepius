"use client";

// Memo Writer panel — sits below the four module panels on the diligence
// workbench. The button triggers the agent; the result renders inline.
//
// Cache-first: for adagrasib (and any other asset listed in the agent's
// manifest cached_assets), the result returns instantly from disk. For
// asset names typed by the user, this fires a live Anthropic call and shows
// a clear 503 if no ANTHROPIC_API_KEY is set on the API.

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { type AgentError, runMemoWriter } from "@/lib/api-client";
import type { ClientDiligenceRecord } from "@/lib/module-registry";
import type { MemoOutput, Recommendation } from "@/lib/types";

const REC_COLOR: Record<Recommendation, string> = {
  strong_buy: "bg-green-bright text-white",
  buy: "bg-green-bright/20 text-green-bright",
  hold: "bg-bg-panel-hover text-text-primary",
  cautious: "bg-cyan-bright/10 text-cyan-bright",
  avoid: "bg-red-bright/20 text-red-bright",
};

export function MemoPanel({ record }: { record: ClientDiligenceRecord }) {
  const [memo, setMemo] = useState<MemoOutput | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AgentError | null>(null);

  const ready =
    record.pos && record.rnpv && record.scorecard && record.comparables;

  async function generate() {
    setLoading(true);
    setError(null);
    try {
      const result = await runMemoWriter(record as unknown as Record<string, unknown>);
      setMemo(result);
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
          Memo Writer · agent
        </h2>
        <button
          type="button"
          onClick={generate}
          disabled={!ready || loading}
          className="rounded border border-magenta-bright bg-magenta-bright/10 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-magenta-bright hover:bg-magenta-bright/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "[ generating… ]" : memo ? "[ regenerate ]" : "[ generate memo → ]"}
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

      {memo ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-text-dim">
            <span
              className={`rounded px-1.5 py-0.5 ${REC_COLOR[memo.recommendation]}`}
            >
              ● {memo.recommendation.replace("_", " ")}
            </span>
            <span>
              {memo.from_cache ? "● cached" : `● ${memo.model_used}`}
            </span>
            <span className="ml-auto">
              {new Date(memo.generated_at).toISOString().slice(0, 10)}
            </span>
          </div>

          <article className="prose prose-sm max-w-none font-prose dark:prose-invert prose-headings:font-display prose-headings:uppercase prose-headings:tracking-wider prose-headings:text-text-bright prose-h2:text-base prose-h2:mt-4 prose-p:text-text-primary prose-strong:text-text-bright prose-li:text-text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {memo.body_markdown}
            </ReactMarkdown>
          </article>
        </div>
      ) : null}
    </section>
  );
}
