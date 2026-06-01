"use client";

// ModelInfoRawCard — v1.8.0 Phase 5.
//
// Renders inside the Calibration section (Quant persona only). Exposes
// the literal /api/modules/ml_pos_prior/model_info JSON in a collapsible
// <details> so a quant reader can audit the model artifact end-to-end.
//
// Design intent: the QuantBanner already surfaces the headline numbers
// (AUC, Brier, conformal coverage). This card is for the reader who
// wants the FULL response — confusion matrix, classification report,
// embedding model ID, lightgbm version, n_calibration per phase, etc.
// Showing the raw JSON is the "show me your work" promise made literal.
//
// Fetch policy: lazy. The full /model_info response is ~5-10 KB but
// includes nested objects (classification_report, conformal block);
// rendering JSON.stringify for that on every page load when the user
// might not expand the card is wasteful. We only fetch when the user
// expands the <details> for the first time. After that the data
// persists in component state until unmount.
//
// Why not share state with QuantBanner: the banner only consumes a
// handful of top-level fields (AUC, Brier, coverage, n_models). It
// could fetch separately or share state. We chose to fetch separately
// because the response is small, the browser caches identical GETs,
// and the indirection of sharing state across two components in the
// same section isn't worth the abstraction.

import { useState } from "react";

import { getMLPosPriorModelInfo } from "@/lib/api-client";

export default function ModelInfoRawCard() {
  const [info, setInfo] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadIfNeeded(e: React.SyntheticEvent<HTMLDetailsElement>) {
    if (!e.currentTarget.open || info || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getMLPosPriorModelInfo();
      setInfo(data);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <details
      className="rounded border border-cyan-bright/30 bg-cyan-bright/5 p-2.5"
      onToggle={loadIfNeeded}
    >
      <summary className="flex cursor-pointer items-baseline justify-between gap-2">
        <span className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-cyan-bright">
          /model_info · raw artifact metadata
        </span>
        <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
          {info ? "loaded" : loading ? "loading…" : "[ expand to load ]"}
        </span>
      </summary>

      <div className="mt-2.5 font-prose text-[11px] leading-snug text-text-primary">
        {error ? (
          <p className="text-red-bright">
            Failed to load /model_info: {error}
          </p>
        ) : !info ? (
          <p className="text-text-dim">
            Click anywhere on the strip above to fetch the full model_info
            response. Includes the held-out test metrics, conformal radii +
            coverage per phase, confusion matrix, n_calibration sizes,
            sklearn classification report, embedding model ID + version,
            and the LightGBM major version stamped at training time.
          </p>
        ) : (
          <pre className="max-h-[480px] overflow-auto rounded border border-border-dim bg-bg-panel p-2 font-mono text-[10px] leading-snug tabular-nums text-text-bright">
            {JSON.stringify(info, null, 2)}
          </pre>
        )}
      </div>
    </details>
  );
}
