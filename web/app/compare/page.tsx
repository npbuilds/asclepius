"use client";

/**
 * v1.6 Session 2 — multi-asset comparison view.
 *
 * The literal answer to "test on multiple assets": render up to 5 assets
 * side-by-side in a comparison table, computing PoS / rNPV / scorecard /
 * comparables per asset against the shared module engines.
 *
 * URL state lives in `?assets=adagrasib,divarasib,tulisokibart` so the
 * comparison is shareable. Empty / missing query → default to the two
 * canonical showcase assets (adagrasib + divarasib). Asset selection
 * updates the URL via history.replaceState (no nav, no scroll jump).
 *
 * Each asset's metrics fetch independently — adding or removing one
 * asset doesn't block the others. Loading state is per-cell so the
 * table doesn't flash entirely blank when one asset is mid-load.
 *
 * What this page does NOT do:
 *   - Run agents (memo/adversary/auto-diligence) per asset; that's the
 *     diligence page's job
 *   - Persist conviction sliders or fund parameters; this is comparison,
 *     not portfolio sizing (see /portfolio for that)
 *   - Side-by-side rNPV distribution charts (could be v1.7 add)
 */

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";

import {
  runComparables,
  runPoS,
  runRnpv,
  runScorecard,
} from "@/lib/api-client";
import { findStagedAsset, STAGED_ASSETS } from "@/lib/staged-assets";
import type {
  AssetInput,
  ComparablesResult,
  PoSResult,
  RnpvInputs,
  RnpvResult,
  ScorecardInput,
  ScorecardResult,
} from "@/lib/types";

// Mirrors the defaults in ScorecardRadarPanel so a /compare without any
// per-asset scorecard tweaking shows the same baseline scores the user
// would see on /diligence/<asset>. Pillar weights live server-side.
const DEFAULT_SCORECARD_INPUT: ScorecardInput = {
  clinical: { score: 7 },
  regulatory: { score: 7 },
  competitive: { score: 6 },
  manufacturing: { score: 7 },
  ip: { score: 7 },
  financial: { score: 6 },
  team: { score: 7 },
  computational: { score: 5 },
  red_flags: [],
  green_flags: [],
};

const MAX_ASSETS = 5;
const DEFAULT_SLUGS = ["adagrasib", "divarasib"];

interface AssetCell {
  slug: string;
  asset: AssetInput | null; // null = unknown slug, render placeholder column
  rnpv_inputs: RnpvInputs | null;
  pos: PoSResult | null;
  rnpv: RnpvResult | null;
  scorecard: ScorecardResult | null;
  comparables: ComparablesResult | null;
  error: string | null;
  loading: boolean;
}

function emptyCell(slug: string): AssetCell {
  const staged = findStagedAsset(slug);
  return {
    slug,
    asset: staged?.asset ?? null,
    rnpv_inputs: staged?.rnpv ?? null,
    pos: null,
    rnpv: null,
    scorecard: null,
    comparables: null,
    error: null,
    loading: true,
  };
}

export default function ComparePage() {
  // Next.js 14 requires useSearchParams() consumers to be wrapped in a
  // <Suspense> boundary so the page can prerender the shell while the
  // search-param-dependent inner component bails out to client-side
  // render only. The fallback is a tiny skeleton so the outer page
  // structure is still SSR'd (improves first-paint perception).
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-7xl px-6 py-8">
          <h1 className="font-display text-2xl font-black uppercase tracking-wider text-text-bright sm:text-3xl">
            Compare
          </h1>
          <div className="mt-6 h-32 animate-pulse rounded border border-border-dim bg-bg-panel" />
        </div>
      }
    >
      <CompareInner />
    </Suspense>
  );
}

function CompareInner() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL → asset slug list. Cap at MAX_ASSETS to keep the table from
  // overflowing horizontally; the cap is permissive (5 cols readable on
  // a 1440px screen) but the per-cell metric labels stay vertical.
  const slugsFromUrl = useMemo<string[]>(() => {
    const raw = searchParams.get("assets");
    if (!raw) return DEFAULT_SLUGS;
    const cleaned = raw
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter((s) => s.length > 0);
    return cleaned.length === 0 ? DEFAULT_SLUGS : cleaned.slice(0, MAX_ASSETS);
  }, [searchParams]);

  const [cells, setCells] = useState<AssetCell[]>(() =>
    slugsFromUrl.map(emptyCell),
  );

  // Whenever the slug list changes, recompute cells from scratch.
  useEffect(() => {
    setCells(slugsFromUrl.map(emptyCell));
  }, [slugsFromUrl]);

  // Per-cell metric fetch. Runs once per cell on mount and whenever the
  // cell's slug changes. PoS first (no dependency); then PoS-result fed
  // into rNPV / scorecard / comparables so the implied-value and the
  // scorecard rNPV-tier calculations can chain.
  useEffect(() => {
    cells.forEach((cell, idx) => {
      if (!cell.asset || !cell.rnpv_inputs) return;
      if (cell.pos !== null || cell.error !== null) return; // already loaded or errored
      const asset = cell.asset;
      const rnpv_inputs = cell.rnpv_inputs;

      (async () => {
        try {
          const pos = await runPoS(asset);
          // Chain: rnpv / scorecard / comparables all need the computed
          // PoS to populate their dependent fields. Run in parallel.
          const [rnpv, scorecard, comparables] = await Promise.all([
            runRnpv(asset, pos, rnpv_inputs),
            runScorecard(asset, DEFAULT_SCORECARD_INPUT),
            runComparables(asset, rnpv_inputs),
          ]);
          setCells((prev) =>
            prev.map((c, i) =>
              i === idx
                ? { ...c, pos, rnpv, scorecard, comparables, loading: false }
                : c,
            ),
          );
        } catch (e) {
          setCells((prev) =>
            prev.map((c, i) =>
              i === idx
                ? {
                    ...c,
                    error: e instanceof Error ? e.message : "fetch failed",
                    loading: false,
                  }
                : c,
            ),
          );
        }
      })();
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cells.length, cells.map((c) => c.slug).join(",")]);

  // Asset list manipulation — push to URL so the comparison is shareable.
  const setSlugs = useCallback(
    (next: string[]) => {
      const capped = next.slice(0, MAX_ASSETS);
      const usp = new URLSearchParams(searchParams.toString());
      if (capped.length === 0) {
        usp.delete("assets");
      } else {
        usp.set("assets", capped.join(","));
      }
      router.replace(`?${usp.toString()}`, { scroll: false });
    },
    [router, searchParams],
  );

  const removeSlug = useCallback(
    (slug: string) => {
      setSlugs(slugsFromUrl.filter((s) => s !== slug));
    },
    [setSlugs, slugsFromUrl],
  );

  const addSlug = useCallback(
    (slug: string) => {
      const clean = slug.trim().toLowerCase();
      if (!clean) return;
      if (slugsFromUrl.includes(clean)) return;
      setSlugs([...slugsFromUrl, clean]);
    },
    [setSlugs, slugsFromUrl],
  );

  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl font-black uppercase tracking-wider text-text-bright sm:text-3xl">
          Compare
        </h1>
        <p className="mt-2 max-w-3xl font-prose text-[13px] leading-relaxed text-text-primary">
          Side-by-side comparison across up to {MAX_ASSETS} assets. PoS,
          rNPV, scorecard, and cohort multiple computed live per asset.
          The URL captures the comparison set, so this page is shareable.
        </p>
      </header>

      <AssetSelector
        selectedSlugs={slugsFromUrl}
        onAdd={addSlug}
        onRemove={removeSlug}
      />

      <ComparisonTable cells={cells} />

      <p className="mt-8 font-mono text-[10px] uppercase tracking-wider text-text-dim">
        Per-asset deep dive available at{" "}
        <Link
          href="/diligence/adagrasib"
          className="text-cyan-bright underline hover:text-cyan-bright"
        >
          /diligence/&lt;asset&gt;
        </Link>{" "}
        · custom assets accepted (Auto-Diligence populates the record).
      </p>
    </div>
  );
}

function AssetSelector({
  selectedSlugs,
  onAdd,
  onRemove,
}: {
  selectedSlugs: string[];
  onAdd: (slug: string) => void;
  onRemove: (slug: string) => void;
}) {
  const [customInput, setCustomInput] = useState("");

  // Pre-staged assets not already selected — surfaced as chips in the
  // "add from library" row.
  const available = STAGED_ASSETS.filter((a) => !selectedSlugs.includes(a.slug));

  function onSubmitCustom(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const clean = customInput.trim();
    if (!clean) return;
    onAdd(clean);
    setCustomInput("");
  }

  return (
    <div className="mb-6 space-y-3">
      {/* Selected assets — chip per asset with X to remove */}
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
          comparing →
        </span>
        {selectedSlugs.map((slug) => {
          const staged = findStagedAsset(slug);
          return (
            <span
              key={slug}
              className="inline-flex items-center gap-1.5 rounded border border-cyan-bright/40 bg-cyan-bright/5 px-2 py-1 font-mono text-[11px] text-cyan-bright"
            >
              {staged ? staged.name : slug}
              <button
                type="button"
                onClick={() => onRemove(slug)}
                className="text-cyan-bright/60 hover:text-cyan-bright"
                aria-label={`remove ${slug}`}
              >
                ×
              </button>
            </span>
          );
        })}
        {selectedSlugs.length === 0 ? (
          <span className="font-mono text-[11px] text-text-dim">
            no assets selected — pick from the library below
          </span>
        ) : null}
      </div>

      {/* Add from pre-staged library */}
      {available.length > 0 && selectedSlugs.length < MAX_ASSETS ? (
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
            add from library →
          </span>
          {available.map((a) => (
            <button
              key={a.slug}
              type="button"
              onClick={() => onAdd(a.slug)}
              className="inline-flex items-center gap-1 rounded border border-border-dim bg-bg-panel px-2 py-1 font-mono text-[11px] text-text-primary transition hover:border-cyan-bright hover:text-cyan-bright"
            >
              + {a.name}
            </button>
          ))}
        </div>
      ) : null}

      {/* Add by custom name */}
      {selectedSlugs.length < MAX_ASSETS ? (
        <form
          onSubmit={onSubmitCustom}
          className="flex flex-wrap items-baseline gap-2"
        >
          <label
            htmlFor="custom-asset"
            className="font-mono text-[10px] uppercase tracking-wider text-text-dim"
          >
            or by name →
          </label>
          <input
            id="custom-asset"
            type="text"
            value={customInput}
            onChange={(e) => setCustomInput(e.target.value)}
            placeholder="e.g., olomorasib"
            className="w-44 rounded border border-border-dim bg-bg-deep px-2 py-1 font-mono text-[11px] text-text-primary placeholder:text-text-dim focus:border-cyan-bright focus:outline-none"
            spellCheck={false}
            autoComplete="off"
          />
          <button
            type="submit"
            disabled={!customInput.trim()}
            className="rounded border border-cyan-bright bg-cyan-bright/10 px-2 py-1 font-mono text-[11px] uppercase tracking-wider text-cyan-bright transition hover:bg-cyan-bright/20 disabled:cursor-not-allowed disabled:border-border-dim disabled:bg-bg-panel disabled:text-text-dim"
          >
            [ add ]
          </button>
        </form>
      ) : (
        <p className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
          maximum {MAX_ASSETS} assets — remove one to add another
        </p>
      )}
    </div>
  );
}

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

function fmtMoneyM(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  if (Math.abs(v) >= 1000) return `$${(v / 1000).toFixed(2)}B`;
  return `$${v.toFixed(0)}M`;
}

// Per-metric skeleton widths (in pixel widths matching expected populated
// content). Keeping these as a Tailwind arbitrary value so the skeleton
// reads as "this is the shape you'll get" rather than a generic blob.
const SKELETON_WIDTHS: Record<string, string> = {
  phase: "w-12",
  "TA · modality": "w-32",
  capital: "w-20",
  "PoS final LOA": "w-14",
  "PoS confidence band": "w-28",
  "BIO base rate": "w-14",
  "rNPV base case": "w-16",
  "MC P25 / P50 / P75": "w-36",
  "downside (failed P3)": "w-16",
  cohort: "w-24",
  "median EV/peak": "w-12",
  "implied value": "w-16",
  "scorecard aggregate": "w-16",
  recommendation: "w-20",
};

function StatusBadge({ cell }: { cell: AssetCell }) {
  if (!cell.asset || !cell.rnpv_inputs) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded border border-amber-bright/40 bg-amber-bright/10 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-amber-bright"
        title="No staged data for this slug — run Auto-Diligence on /diligence/<slug> first"
      >
        <span className="h-1 w-1 rounded-full bg-amber-bright" />
        unstaged
      </span>
    );
  }
  if (cell.error) {
    return (
      <span
        className="inline-flex items-center gap-1 rounded border border-red-bright/40 bg-red-bright/10 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-red-bright"
        title={cell.error}
      >
        <span className="h-1 w-1 rounded-full bg-red-bright" />
        error
      </span>
    );
  }
  if (cell.loading) {
    return (
      <span className="inline-flex items-center gap-1 rounded border border-cyan-bright/30 bg-cyan-bright/5 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-cyan-bright">
        <span className="h-1 w-1 animate-pulse rounded-full bg-cyan-bright" />
        loading…
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded border border-green-bright/40 bg-green-bright/10 px-1.5 py-px font-mono text-[9px] uppercase tracking-wider text-green-bright">
      <span className="h-1 w-1 rounded-full bg-green-bright" />
      ready
    </span>
  );
}

function ComparisonTable({ cells }: { cells: AssetCell[] }) {
  if (cells.length === 0) {
    return (
      <div className="rounded border border-border-dim bg-bg-panel p-6 text-center font-mono text-[12px] text-text-dim">
        Add an asset from the library above to populate the comparison.
      </div>
    );
  }

  // Helper that takes a metric extractor and returns a row component. The
  // value is rendered per cell with skeleton/error fallbacks. Errors are
  // contained per-cell so a single asset's failure doesn't blank the row.
  function MetricRow<T>({
    label,
    getValue,
    format,
    highlight,
  }: {
    label: string;
    getValue: (c: AssetCell) => T | null | undefined;
    format: (v: T) => string;
    highlight?: boolean;
  }) {
    const skelW = SKELETON_WIDTHS[label] ?? "w-16";
    return (
      <tr className={highlight ? "bg-bg-deep/30" : ""}>
        <th
          scope="row"
          className="border-b border-border-dim/40 px-3 py-2 text-left font-mono text-[10px] font-normal uppercase tracking-wider text-text-dim"
        >
          {label}
        </th>
        {cells.map((c) => {
          let display: React.ReactNode = (
            <span className="text-text-dim">—</span>
          );
          let cellExtra = "";
          if (!c.asset || !c.rnpv_inputs) {
            // Unstaged slug — render an em-dash, status badge in header
            // already tells the user why this column is blank.
            display = (
              <span
                className="text-text-dim"
                title="no staged data for this slug"
              >
                —
              </span>
            );
          } else if (c.error) {
            // Per-cell error containment. The cell shows "error" with the
            // full message on hover; row stays intact for other assets.
            display = (
              <span
                className="cursor-help text-red-bright underline decoration-dotted decoration-red-bright/50 underline-offset-2"
                title={c.error}
              >
                error
              </span>
            );
            cellExtra = "bg-red-bright/[0.03]";
          } else if (c.loading) {
            // Skeleton block at expected width — animate-pulse gives the
            // "this is incoming" cue. Width is per-metric so the table
            // doesn't reflow when data arrives.
            display = (
              <span
                className={`inline-block h-3 ${skelW} animate-pulse rounded-sm bg-border-dim/60 align-middle`}
                aria-label={`${label} loading`}
              />
            );
          } else {
            const v = getValue(c);
            if (v != null) {
              // Stagger reveal: each cell fades in as its data arrives.
              display = (
                <span
                  className={`${
                    highlight ? "font-bold text-text-bright" : "text-text-primary"
                  } animate-[fade-in_180ms_ease-out]`}
                  style={{
                    animation: "compareCellFadeIn 220ms ease-out",
                  }}
                >
                  {format(v)}
                </span>
              );
            }
          }
          return (
            <td
              key={c.slug}
              className={`border-b border-border-dim/40 px-3 py-2 text-right font-mono text-[12px] tabular-nums ${cellExtra}`}
            >
              {display}
            </td>
          );
        })}
      </tr>
    );
  }

  return (
    <div className="overflow-x-auto rounded border border-border-dim bg-bg-panel">
      {/* Inline keyframes — cell stagger reveal. Scoped to this page so
          it doesn't pollute the global stylesheet (which another agent
          may be editing in parallel). */}
      <style jsx>{`
        @keyframes compareCellFadeIn {
          from {
            opacity: 0;
            transform: translateY(-2px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
      <table className="w-full">
        <thead>
          <tr className="border-b border-border-dim bg-bg-panel">
            <th
              scope="col"
              className="px-3 py-2 text-left font-mono text-[10px] uppercase tracking-wider text-text-dim"
            >
              metric
            </th>
            {cells.map((c) => {
              const staged = findStagedAsset(c.slug);
              return (
                <th
                  key={c.slug}
                  scope="col"
                  className="px-3 py-2 text-right font-display text-[12px] font-semibold uppercase tracking-wider text-text-bright"
                >
                  <div className="flex flex-col items-end gap-1">
                    <Link
                      href={`/diligence/${c.slug}`}
                      className="hover:text-cyan-bright"
                    >
                      {staged ? staged.name : c.slug}
                    </Link>
                    {staged ? (
                      <div className="font-mono text-[9px] font-normal uppercase tracking-wider text-text-dim">
                        {staged.sponsor}
                      </div>
                    ) : null}
                    <StatusBadge cell={c} />
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {/* Identity rows — static asset metadata */}
          <MetricRow
            label="phase"
            getValue={(c) => c.asset?.phase}
            format={(v) => (typeof v === "string" ? v : "—")}
          />
          <MetricRow
            label="TA · modality"
            getValue={(c) => c.asset}
            format={(a) => `${a.therapeutic_area} · ${a.modality.replace(/_/g, " ")}`}
          />
          <MetricRow
            label="capital"
            getValue={(c) => c.asset?.capital_position}
            format={(v) => (typeof v === "string" ? v.replace(/_/g, " ") : "—")}
          />

          {/* PoS — the framework's headline output */}
          <MetricRow
            label="PoS final LOA"
            getValue={(c) => c.pos?.final_loa}
            format={(v) => fmtPct(v as number, 1)}
            highlight
          />
          <MetricRow
            label="PoS confidence band"
            getValue={(c) =>
              c.pos
                ? `[${fmtPct(c.pos.confidence_low, 1)}, ${fmtPct(c.pos.confidence_high, 1)}]`
                : null
            }
            format={(v) => v as string}
          />
          <MetricRow
            label="BIO base rate"
            getValue={(c) => c.pos?.base_rate}
            format={(v) => fmtPct(v as number, 1)}
          />

          {/* rNPV — the dollar number */}
          <MetricRow
            label="rNPV base case"
            getValue={(c) => c.rnpv?.base_case_usd_m}
            format={(v) => fmtMoneyM(v as number)}
            highlight
          />
          <MetricRow
            label="MC P25 / P50 / P75"
            getValue={(c) =>
              c.rnpv && c.rnpv.monte_carlo_p25_usd_m != null
                ? `${fmtMoneyM(c.rnpv.monte_carlo_p25_usd_m)} / ${fmtMoneyM(c.rnpv.monte_carlo_p50_usd_m)} / ${fmtMoneyM(c.rnpv.monte_carlo_p75_usd_m)}`
                : null
            }
            format={(v) => v as string}
          />
          <MetricRow
            label="downside (failed P3)"
            getValue={(c) => c.rnpv?.downside_failed_p3_usd_m}
            format={(v) => fmtMoneyM(v as number)}
          />

          {/* Comparables — cohort context */}
          <MetricRow
            label="cohort"
            getValue={(c) => c.comparables?.cohort_label}
            format={(v) => v as string}
          />
          <MetricRow
            label="median EV/peak"
            getValue={(c) => c.comparables?.median_ev_to_peak_sales}
            format={(v) => `${(v as number).toFixed(2)}×`}
          />
          <MetricRow
            label="implied value"
            getValue={(c) => c.comparables?.implied_value_usd_m}
            format={(v) => fmtMoneyM(v as number)}
          />

          {/* Scorecard */}
          <MetricRow
            label="scorecard aggregate"
            getValue={(c) => c.scorecard?.aggregate_score}
            format={(v) => `${(v as number).toFixed(1)} / 10`}
          />
          <MetricRow
            label="recommendation"
            getValue={(c) => c.scorecard?.recommendation}
            format={(v) => (typeof v === "string" ? v.replace(/_/g, " ") : "—")}
            highlight
          />
        </tbody>
      </table>
    </div>
  );
}
