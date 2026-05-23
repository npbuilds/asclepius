"use client";

// v2.0 Portfolio Sizing page — different audience than the per-asset
// diligence page. This is the biotech fund-manager surface.
//
// The page renders a fixed 5-asset kinase-inhibitor cohort (matching the
// calibration seed) with interactive conviction sliders. The user can
// adjust convictions and fund parameters; the portfolio recommendation
// updates live via the multi-asset endpoint.
//
// Honest framing in the methodology writeup: Kelly applied to the
// framework's reflexivity-adjusted LOAs gives small positions because
// the framework's LOA estimates are conservative. Real biotech VCs sit
// above the base rate. The disagreement between framework-recommended
// sizing and an investor's gut sizing is the useful information.

import { useCallback, useEffect, useState } from "react";

import { runPortfolioSizing, runPoS, runRnpv } from "@/lib/api-client";
import type {
  AssetInput,
  AssetSizingInput,
  FundParameters,
  PortfolioRecommendation,
  PositionStatus,
  RnpvInputs,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Demo cohort — the same 5 approved kinase inhibitors that seed the
// calibration dashboard. The framework's PoS/rNPV chains run live against
// these on page load; the portfolio recommendation updates whenever the user
// adjusts a conviction slider or a fund parameter.
// ---------------------------------------------------------------------------

const COHORT_ASSETS: { name: string; sponsor: string; defaultConviction: number }[] = [
  { name: "adagrasib", sponsor: "Mirati", defaultConviction: 1.0 },
  { name: "sotorasib", sponsor: "Amgen", defaultConviction: 0.8 },
  { name: "selpercatinib", sponsor: "Loxo/Lilly", defaultConviction: 1.2 },
  { name: "larotrectinib", sponsor: "Loxo/Bayer", defaultConviction: 1.0 },
  { name: "encorafenib", sponsor: "Array/Pfizer", defaultConviction: 0.9 },
];

function buildAssetInput(name: string, sponsor: string): AssetInput {
  return {
    asset_name: name,
    sponsor,
    phase: "phase_2",
    therapeutic_area: "oncology",
    modality: "small_molecule",
    capital_position: "adequate",
    mechanism: null,
    target: null,
    indication: null,
    regulatory_designations: ["breakthrough_therapy"],
    num_competitors: 1,
    target_validated: true,
    biomarker_enrichment: true,
  };
}

const DEFAULT_RNPV_INPUTS: RnpvInputs = {
  peak_sales_usd_m: 1200,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.18,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 3, regulatory: 1 },
};

// ---------------------------------------------------------------------------

const STATUS_COLOR: Record<PositionStatus, string> = {
  recommended: "text-green-bright",
  below_floor: "text-amber-bright",
  above_cap: "text-cyan-bright",
  negative_kelly: "text-red-bright",
};

const STATUS_LABEL: Record<PositionStatus, string> = {
  recommended: "recommended",
  below_floor: "below floor",
  above_cap: "at cap",
  negative_kelly: "skip (–Kelly)",
};

interface SizingAsset {
  meta: { name: string; sponsor: string };
  conviction: number;
  sizing: AssetSizingInput | null;
}

export default function PortfolioPage() {
  const [assets, setAssets] = useState<SizingAsset[]>(
    COHORT_ASSETS.map((c) => ({
      meta: { name: c.name, sponsor: c.sponsor },
      conviction: c.defaultConviction,
      sizing: null,
    })),
  );
  const [fund, setFund] = useState<FundParameters>({
    total_capital_usd_m: 100,
    kelly_fraction: 0.25,
    max_position_pct: 0.20,
    min_position_pct: 0.02,
  });
  const [recommendation, setRecommendation] = useState<PortfolioRecommendation | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Compute PoS + rNPV for each asset on mount. Once all five are populated,
  // the portfolio request fires automatically and updates on any slider move.
  useEffect(() => {
    let cancelled = false;
    setError(null);
    (async () => {
      try {
        const sized = await Promise.all(
          COHORT_ASSETS.map(async (c) => {
            const asset = buildAssetInput(c.name, c.sponsor);
            const pos = await runPoS(asset);
            const rnpv = await runRnpv(asset, pos, DEFAULT_RNPV_INPUTS);
            return {
              meta: { name: c.name, sponsor: c.sponsor },
              conviction: c.defaultConviction,
              sizing: { asset, pos, rnpv, conviction: c.defaultConviction },
            };
          }),
        );
        if (!cancelled) setAssets(sized);
      } catch (e) {
        if (!cancelled) setError(String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const recompute = useCallback(
    async (currentAssets: SizingAsset[], currentFund: FundParameters) => {
      const ready = currentAssets.every((a) => a.sizing !== null);
      if (!ready) return;
      setLoading(true);
      try {
        const sizingInputs = currentAssets.map((a) => ({
          ...(a.sizing as AssetSizingInput),
          conviction: a.conviction,
        }));
        const r = await runPortfolioSizing(sizingInputs, currentFund);
        setRecommendation(r);
        setError(null);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    recompute(assets, fund);
  }, [assets, fund, recompute]);

  function setConviction(idx: number, v: number) {
    setAssets((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], conviction: v };
      return next;
    });
  }

  function setFundParam<K extends keyof FundParameters>(
    key: K,
    v: FundParameters[K],
  ) {
    setFund((prev) => ({ ...prev, [key]: v }));
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <header className="mb-4">
        <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
          ── Portfolio sizing · v2.0 ──
        </div>
        <h1 className="mt-1 font-display text-xl font-bold uppercase leading-[1.15] tracking-[0.04em] text-text-bright sm:text-2xl">
          Kinase inhibitor cohort · sample fund
        </h1>
        <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
          A 5-asset demo portfolio of approved KRAS / RET / TRK / BRAF
          kinase inhibitors — the same cohort that seeds the Calibration
          Dashboard. The framework's reflexivity-adjusted PoS and rNPV
          chains run live against each asset; the portfolio allocator
          applies Kelly + fractional + conviction + barbell math via the
          new <code className="font-mono text-[12px]">portfolio_sizing</code>{" "}
          module. Adjust convictions and fund parameters to see the
          recommendation update. See{" "}
          <a
            href="/methodology/11-portfolio-sizing"
            className="text-cyan-bright hover:underline"
          >
            methodology/11-portfolio-sizing
          </a>{" "}
          for the math + honest framing.
        </p>
      </header>

      {error ? (
        <div className="mb-3 rounded border border-red-bright/40 bg-red-bright/10 p-3 text-sm text-red-bright">
          {error}
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[1fr_320px]">
        {/* Left: portfolio output */}
        <div className="space-y-3">
          {recommendation ? (
            <>
              <section className="rounded border border-magenta-bright/30 bg-magenta-bright/5 p-3">
                <h2 className="mb-2 font-display text-[13px] font-semibold uppercase tracking-wider text-magenta-bright">
                  Portfolio recommendation
                  {loading ? (
                    <span className="ml-2 font-mono text-[9px] uppercase text-text-dim">
                      ● updating…
                    </span>
                  ) : null}
                </h2>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Stat
                    label="Deployed"
                    value={`${(recommendation.total_deployed_pct * 100).toFixed(1)}%`}
                    sub={`$${recommendation.total_deployed_usd_m.toFixed(1)}M`}
                    accent
                  />
                  <Stat
                    label="Cash"
                    value={`${(recommendation.cash_residual_pct * 100).toFixed(1)}%`}
                    sub={`$${recommendation.cash_residual_usd_m.toFixed(1)}M`}
                  />
                  <Stat
                    label="Gini"
                    value={recommendation.gini_coefficient.toFixed(3)}
                    sub="0 = equal, 1 = concentrated"
                  />
                  <Stat
                    label="Expected NPV"
                    value={`$${recommendation.expected_value_rnpv_usd_m.toFixed(0)}M`}
                    sub="prob-weighted, all positions"
                  />
                </div>
              </section>

              <section className="rounded border border-border-dim bg-bg-panel p-3">
                <h2 className="mb-2 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
                  Per-asset breakdown
                </h2>
                <table className="w-full font-mono text-[11px] tabular-nums">
                  <thead>
                    <tr className="text-left text-[9px] uppercase tracking-wider text-text-dim">
                      <th className="py-0.5 pr-2">Asset</th>
                      <th className="py-0.5 pr-2 text-right">LOA</th>
                      <th className="py-0.5 pr-2 text-right">b</th>
                      <th className="py-0.5 pr-2 text-right">Kelly</th>
                      <th className="py-0.5 pr-2 text-right">Frac</th>
                      <th className="py-0.5 pr-2 text-right">Final</th>
                      <th className="py-0.5 pr-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recommendation.positions.map((p) => (
                      <tr key={p.asset_name} className="border-t border-border-dim/30">
                        <td className="py-1 pr-2 text-text-bright">
                          {p.asset_name}
                        </td>
                        <td className="py-1 pr-2 text-right text-text-primary">
                          {(p.pos * 100).toFixed(1)}%
                        </td>
                        <td className="py-1 pr-2 text-right text-text-primary">
                          {p.payoff_multiple.toFixed(1)}x
                        </td>
                        <td className="py-1 pr-2 text-right text-text-primary">
                          {p.kelly_optimal.toFixed(3)}
                        </td>
                        <td className="py-1 pr-2 text-right text-text-primary">
                          {(p.kelly_fractional * 100).toFixed(2)}%
                        </td>
                        <td className="py-1 pr-2 text-right font-bold text-text-bright">
                          {(p.final_weight * 100).toFixed(2)}%
                        </td>
                        <td className={`py-1 pr-2 ${STATUS_COLOR[p.status]}`}>
                          ● {STATUS_LABEL[p.status]}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <details className="mt-2 font-mono text-[10px]">
                  <summary className="cursor-pointer uppercase tracking-wider text-text-dim">
                    show rationales
                  </summary>
                  <ul className="mt-2 space-y-1.5">
                    {recommendation.positions.map((p) => (
                      <li key={p.asset_name} className="font-prose text-[11px]">
                        <span className="font-mono uppercase tracking-wider text-text-dim">
                          {p.asset_name}:
                        </span>{" "}
                        <span className="text-text-primary">{p.rationale}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              </section>
            </>
          ) : (
            <section className="rounded border border-border-dim bg-bg-panel p-3">
              <h2 className="mb-2 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
                Portfolio recommendation
              </h2>
              <div className="h-32 animate-pulse rounded bg-bg-panel-hover" />
            </section>
          )}
        </div>

        {/* Right: controls (convictions + fund params) */}
        <aside className="space-y-3">
          <section className="rounded border border-border-dim bg-bg-panel p-3">
            <h2 className="mb-2 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-text-dim">
              Conviction sliders
            </h2>
            <div className="space-y-2">
              {assets.map((a, i) => (
                <label
                  key={a.meta.name}
                  className="grid grid-cols-[1fr_auto] items-center gap-2 text-[11px]"
                >
                  <span className="font-mono uppercase tracking-wider text-text-dim">
                    {a.meta.name}
                  </span>
                  <span className="text-right font-mono font-bold tabular-nums text-text-bright">
                    {a.conviction.toFixed(2)}x
                  </span>
                  <input
                    type="range"
                    min={0.5}
                    max={1.5}
                    step={0.05}
                    value={a.conviction}
                    onChange={(e) => setConviction(i, parseFloat(e.target.value))}
                    className="col-span-2 w-full accent-magenta-bright"
                  />
                </label>
              ))}
            </div>
          </section>

          <section className="rounded border border-border-dim bg-bg-panel p-3">
            <h2 className="mb-2 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-text-dim">
              Fund parameters
            </h2>
            <div className="space-y-2 text-[11px]">
              <FundSlider
                label="Total capital"
                value={fund.total_capital_usd_m}
                min={10}
                max={500}
                step={10}
                format={(v) => `$${v.toFixed(0)}M`}
                onChange={(v) => setFundParam("total_capital_usd_m", v)}
              />
              <FundSlider
                label="Kelly fraction"
                value={fund.kelly_fraction}
                min={0.1}
                max={1.0}
                step={0.05}
                format={(v) => `${(v * 100).toFixed(0)}%`}
                onChange={(v) => setFundParam("kelly_fraction", v)}
              />
              <FundSlider
                label="Max position"
                value={fund.max_position_pct}
                min={0.05}
                max={0.40}
                step={0.01}
                format={(v) => `${(v * 100).toFixed(0)}%`}
                onChange={(v) => setFundParam("max_position_pct", v)}
              />
              <FundSlider
                label="Min position"
                value={fund.min_position_pct}
                min={0.0}
                max={0.10}
                step={0.005}
                format={(v) => `${(v * 100).toFixed(1)}%`}
                onChange={(v) => setFundParam("min_position_pct", v)}
              />
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className="font-display text-[9px] uppercase tracking-[0.15em] text-text-dim">
        {label}
      </div>
      <div
        className={`mt-0.5 font-mono text-base font-bold tabular-nums ${accent ? "text-magenta-bright" : "text-text-bright"}`}
      >
        {value}
      </div>
      {sub ? (
        <div className="font-mono text-[9px] uppercase tracking-wider text-text-dim">
          {sub}
        </div>
      ) : null}
    </div>
  );
}

function FundSlider({
  label,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="grid grid-cols-[1fr_auto] items-center gap-2">
      <span className="font-mono uppercase tracking-wider text-text-dim">
        {label}
      </span>
      <span className="text-right font-mono font-bold tabular-nums text-text-bright">
        {format(value)}
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="col-span-2 w-full accent-cyan-bright"
      />
    </label>
  );
}
