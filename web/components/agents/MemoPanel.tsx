"use client";

// Memo Writer panel (v1.7.7) — renders the structured 2-3 page memo as a
// stack of titled sections. Each section gets its own visual block, with
// theme tokens carrying the semantic weight: cyan-bright for section
// headers, magenta-bright for the rNPV bracket callout, amber-bright for
// risks, green/red bright for the recommendation chip.
//
// If the structured sections are missing (older response or fallback path),
// we drop back to rendering memo.body_markdown as a single article.

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { type AgentError, runMemoWriter } from "@/lib/api-client";
import type { ClientDiligenceRecord } from "@/lib/module-registry";
import type {
  MemoConviction,
  MemoOutput,
  MemoRiskItem,
  MemoRiskSeverity,
  Recommendation,
} from "@/lib/types";

const REC_COLOR: Record<Recommendation, string> = {
  strong_buy: "bg-green-bright text-white",
  buy: "bg-green-bright/20 text-green-bright",
  hold: "bg-bg-panel-hover text-text-primary",
  cautious: "bg-cyan-bright/10 text-cyan-bright",
  avoid: "bg-red-bright/20 text-red-bright",
};

// Conviction is orthogonal to the buy/hold direction — a confidence meter, not
// a verdict. Muted, monochromatic-ish scale so it never reads as good/bad.
const CONVICTION_COLOR: Record<MemoConviction, string> = {
  high: "border-cyan-bright/50 text-cyan-bright",
  medium: "border-amber-bright/40 text-amber-bright",
  low: "border-text-dim/40 text-text-dim",
};

const SEVERITY_COLOR: Record<MemoRiskSeverity, string> = {
  low: "border-text-dim/30 bg-bg-panel text-text-primary",
  medium: "border-amber-bright/40 bg-amber-bright/5 text-amber-bright",
  high: "border-red-bright/50 bg-red-bright/10 text-red-bright",
};

function formatUsdM(value: number | null | undefined): string {
  if (value == null) return "—";
  return `$${Math.round(value).toLocaleString()}M`;
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-2 font-display text-[11px] font-semibold uppercase tracking-wider text-cyan-bright">
      {children}
    </h3>
  );
}

function ProseBlock({ children }: { children: string }) {
  return (
    <div className="font-prose text-[13px] leading-relaxed text-text-primary [&_p]:mb-2 [&_p:last-child]:mb-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}

function TLDRBlock({ memo }: { memo: MemoOutput }) {
  const tldr = memo.tldr;
  if (!tldr) return null;

  return (
    <div className="rounded border border-magenta-bright/40 bg-magenta-bright/5 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <SectionHeader>TL;DR</SectionHeader>
        <span
          className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${REC_COLOR[tldr.recommendation]}`}
        >
          ● {tldr.recommendation.replace("_", " ")}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 font-mono text-[11px]">
        <div>
          <div className="text-text-dim uppercase tracking-wider">LOA</div>
          <div className="font-display text-base text-text-bright">
            {tldr.loa_pct.toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="text-text-dim uppercase tracking-wider">rNPV base</div>
          <div className="font-display text-base text-magenta-bright">
            {formatUsdM(tldr.rnpv_base_usd_m)}
          </div>
        </div>
        <div>
          <div className="text-text-dim uppercase tracking-wider">P25–P75</div>
          <div className="font-display text-base text-magenta-bright">
            {formatUsdM(tldr.rnpv_range_low_usd_m)} –{" "}
            {formatUsdM(tldr.rnpv_range_high_usd_m)}
          </div>
        </div>
      </div>
      <p className="mt-2 font-prose text-[13px] leading-relaxed text-text-bright">
        {tldr.thesis_one_liner}
      </p>
    </div>
  );
}

function RisksBlock({ risks }: { risks: MemoRiskItem[] }) {
  if (!risks.length) return null;
  return (
    <div className="rounded border border-amber-bright/30 bg-amber-bright/5 p-3">
      <SectionHeader>
        <span className="text-amber-bright">Risks</span>
      </SectionHeader>
      <ul className="space-y-2">
        {risks.map((r) => (
          <li
            key={r.label}
            className={`rounded border px-2.5 py-1.5 font-prose text-[12px] ${SEVERITY_COLOR[r.severity]}`}
          >
            <div className="mb-0.5 flex items-center justify-between">
              <span className="font-display text-[11px] uppercase tracking-wider">
                {r.label}
              </span>
              <span className="font-mono text-[9px] uppercase tracking-wider opacity-70">
                {r.severity}
              </span>
            </div>
            <div className="text-text-primary">{r.description}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StructuredMemo({ memo }: { memo: MemoOutput }) {
  const close = memo.recommendation_close;
  const closeBorder =
    close?.recommendation === "avoid" || close?.recommendation === "cautious"
      ? "border-red-bright/40 bg-red-bright/5"
      : "border-green-bright/40 bg-green-bright/5";

  return (
    <div className="space-y-3">
      <TLDRBlock memo={memo} />

      {memo.asset_overview ? (
        <div className="rounded border border-bg-panel-hover bg-bg-panel p-3">
          <SectionHeader>Asset overview</SectionHeader>
          <ProseBlock>{memo.asset_overview.paragraph}</ProseBlock>
        </div>
      ) : null}

      {memo.pos_analysis ? (
        <div className="rounded border border-bg-panel-hover bg-bg-panel p-3">
          <SectionHeader>PoS analysis</SectionHeader>
          <ProseBlock>{memo.pos_analysis.waterfall_narrative}</ProseBlock>
          <div className="mt-2 border-t border-bg-panel-hover pt-2">
            <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-text-dim">
              Reflexivity (Spence)
            </div>
            <ProseBlock>{memo.pos_analysis.reflexivity_note}</ProseBlock>
          </div>
          {memo.pos_analysis.supply_note ? (
            <div className="mt-2 border-t border-bg-panel-hover pt-2">
              <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-text-dim">
                Supply constraint (PoS × rNPV ceiling)
              </div>
              <ProseBlock>{memo.pos_analysis.supply_note}</ProseBlock>
            </div>
          ) : null}
        </div>
      ) : null}

      {memo.valuation ? (
        <div className="rounded border border-bg-panel-hover bg-bg-panel p-3">
          <SectionHeader>Valuation</SectionHeader>
          <ProseBlock>{memo.valuation.valuation_narrative}</ProseBlock>
        </div>
      ) : null}

      {memo.comparables ? (
        <div className="rounded border border-bg-panel-hover bg-bg-panel p-3">
          <SectionHeader>Comparables</SectionHeader>
          <ProseBlock>{memo.comparables.cohort_paragraph}</ProseBlock>
        </div>
      ) : null}

      {memo.operational ? (
        <div className="rounded border border-bg-panel-hover bg-bg-panel p-3">
          <SectionHeader>Operational diligence</SectionHeader>
          <ProseBlock>{memo.operational.pillars_paragraph}</ProseBlock>
        </div>
      ) : null}

      <RisksBlock risks={memo.risks} />

      {close ? (
        <div className={`rounded border p-3 ${closeBorder}`}>
          <div className="mb-2 flex items-center justify-between gap-2">
            <SectionHeader>Recommendation</SectionHeader>
            <div className="flex items-center gap-1.5">
              {close.conviction ? (
                <span
                  className={`rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${CONVICTION_COLOR[close.conviction]}`}
                >
                  {close.conviction} conviction
                </span>
              ) : null}
              <span
                className={`rounded px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${REC_COLOR[close.recommendation]}`}
              >
                ● {close.recommendation.replace("_", " ")}
              </span>
            </div>
          </div>
          {close.path_dependency_verdict ? (
            <div className="mb-2 rounded border border-cyan-bright/30 bg-cyan-bright/5 p-2">
              <div className="mb-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan-bright">
                Path-dependency verdict
              </div>
              <div className="font-prose text-[12px] text-text-primary">
                {close.path_dependency_verdict}
              </div>
            </div>
          ) : null}
          <ProseBlock>{close.closing_paragraph}</ProseBlock>
          <div className="mt-2 rounded border border-red-bright/40 bg-red-bright/10 p-2">
            <div className="mb-0.5 font-mono text-[10px] uppercase tracking-wider text-red-bright">
              Kill criterion
            </div>
            <div className="font-prose text-[12px] text-text-primary">
              {close.kill_criterion}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

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

  const hasStructured = Boolean(
    memo &&
      (memo.tldr ||
        memo.asset_overview ||
        memo.pos_analysis ||
        memo.valuation ||
        memo.recommendation_close),
  );

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
            <span>{memo.from_cache ? "● cached" : `● ${memo.model_used}`}</span>
            <span className="ml-auto">
              {new Date(memo.generated_at).toISOString().slice(0, 10)}
            </span>
          </div>

          {hasStructured ? (
            <StructuredMemo memo={memo} />
          ) : (
            <article className="prose prose-sm max-w-none font-prose dark:prose-invert prose-headings:font-display prose-headings:uppercase prose-headings:tracking-wider prose-headings:text-text-bright prose-h2:text-base prose-h2:mt-4 prose-p:text-text-primary prose-strong:text-text-bright prose-li:text-text-primary">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {memo.body_markdown}
              </ReactMarkdown>
            </article>
          )}
        </div>
      ) : null}
    </section>
  );
}
