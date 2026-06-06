"use client";

import { useEffect, useState } from "react";

import { runComparables } from "@/lib/api-client";
import { emitModuleLoad, type ModulePanelProps } from "@/lib/module-registry";

export default function ComparablesPanel({ record, setRecord }: ModulePanelProps) {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    emitModuleLoad("comparables", "start");
    runComparables(record.asset, record.rnpv_inputs)
      .then((comparables) => {
        if (cancelled) return;
        setRecord({ comparables });
        emitModuleLoad("comparables", "done");
      })
      .catch(() => {
        if (cancelled) return;
        emitModuleLoad("comparables", "error");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(record.asset), record.rnpv_inputs.peak_sales_usd_m]);

  const c = record.comparables;
  // v1.6: the engine now indexes comparables by (TA, modality) and routes
  // accordingly. Two curated cohorts ship today:
  //   - Oncology · small molecule (kinase-TKI: encorafenib, larotrectinib,
  //     selpercatinib)
  //   - CNS · small molecule (karuna, cerevel, reata — 2023 single-asset
  //     CNS M&A)
  // When the asset's (TA, modality) doesn't have a curated cohort with
  // ≥3 deals, the engine falls back to the kinase-TKI cohort and flags
  // cohort_matched=false; we render the fallback disclosure in that case
  // and omit it when the cohort genuinely matches the asset.
  const cohortMatched = c?.cohort_matched ?? true;
  return (
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <h2 className="mb-2.5 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">
        Deal comparables
        {loading && !c ? (
          <span className="ml-2 font-mono text-[9px] font-normal uppercase tracking-[0.15em] text-text-dim">
            · computing
          </span>
        ) : null}
      </h2>

      {/* Always surface the cohort label so the analyst knows which deals
          are driving the median. Backend ships "Oncology · small molecule
          (3 deals)" / "CNS · small molecule (3 deals)" / "Fallback: …" */}
      {c?.cohort_label ? (
        <p className="mb-2 font-mono text-[10px] uppercase tracking-wider text-text-dim">
          cohort: <span className="text-text-primary">{c.cohort_label}</span>
        </p>
      ) : null}

      {!cohortMatched ? (
        <p className="mb-3 rounded border border-amber-bright/30 bg-amber-bright/5 p-2 font-mono text-[10px] leading-snug text-amber-bright">
          ⚠ <strong className="font-semibold uppercase tracking-wider">cohort fallback:</strong> No curated cohort
          yet for{" "}
          <span className="font-semibold">
            {record.asset.therapeutic_area} · {record.asset.modality}
          </span>
          . Falling back to the kinase-TKI cohort so the framework still
          produces a number, but treat the median multiple as
          weakly-relevant to your asset. Adding new cohorts is a
          drop-a-JSON-and-restart operation &mdash; happy to wire your
          asset class in if it&apos;s a recurring use case.
        </p>
      ) : null}

      {loading && !c ? (
        // Structured skeleton: 3-stat strip + 4-row table preview. Renders
        // to roughly the loaded-panel height so the page flow below doesn't
        // shift when comparables resolves.
        <div aria-hidden="true">
          <div className="mb-4 grid grid-cols-2 gap-4 sm:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i}>
                <div className="h-2 w-24 animate-pulse rounded bg-bg-panel-hover" />
                <div className="mt-1 h-4 w-20 animate-pulse rounded bg-bg-panel-hover" />
              </div>
            ))}
          </div>
          <div className="space-y-1.5">
            <div className="h-3 w-full animate-pulse rounded bg-bg-deep" />
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-3 w-full animate-pulse rounded bg-bg-panel-hover"
              />
            ))}
          </div>
        </div>
      ) : !c ? (
        <div className="text-sm text-text-dim">No comparable data.</div>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-2 gap-4 text-sm tabular-nums sm:grid-cols-3">
            <Stat
              label="Cohort median EV/peak"
              value={
                c.median_ev_to_peak_sales != null
                  ? `${c.median_ev_to_peak_sales.toFixed(2)}×`
                  : "—"
              }
            />
            <Stat
              label="Implied value (target)"
              value={
                c.implied_value_usd_m != null
                  ? `$${c.implied_value_usd_m.toFixed(0)}M`
                  : "—"
              }
              accent
            />
            <Stat label="Cohort size" value={`${c.cohort.length}`} />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-bg-deep text-left text-[9px] uppercase tracking-[0.15em] text-text-dim">
                <tr>
                  <th className="p-1.5">Asset</th>
                  <th className="p-1.5">Acquirer</th>
                  <th className="p-1.5">Date</th>
                  <th className="p-1.5 text-right">Deal $M</th>
                  <th className="p-1.5 text-right">Peak $M</th>
                  <th className="p-1.5 text-right">EV/peak</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100 tabular-nums">
                {c.cohort.map((row, i) => (
                  <tr key={i}>
                    <td className="p-1.5 font-medium text-text-bright">
                      {row.asset_name}
                      {row.source ? (
                        <span
                          className="ml-1 cursor-help text-text-dim"
                          title={row.source}
                          aria-label={`Source: ${row.source}`}
                        >
                          ⓘ
                        </span>
                      ) : null}
                    </td>
                    <td className="p-1.5">{row.acquirer ?? "—"}</td>
                    <td className="p-1.5">{row.deal_date ?? "—"}</td>
                    <td className="p-1.5 text-right">
                      {row.deal_value_usd_m != null
                        ? row.deal_value_usd_m.toLocaleString()
                        : "—"}
                    </td>
                    <td className="p-1.5 text-right">
                      {row.peak_sales_estimate_usd_m != null
                        ? row.peak_sales_estimate_usd_m.toLocaleString()
                        : "—"}
                    </td>
                    <td className="p-1.5 text-right font-medium text-text-bright">
                      {row.ev_to_peak_sales != null
                        ? `${row.ev_to_peak_sales.toFixed(2)}×`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {c.cohort.some((row) => row.source) ? (
              <div className="mt-3 space-y-1 text-[11px] text-text-dim">
                <div className="font-medium uppercase tracking-wide text-text-primary">
                  Sources
                </div>
                {c.cohort
                  .filter((row) => row.source)
                  .map((row, i) => (
                    <div key={i}>
                      <span className="text-text-primary">{row.asset_name}:</span>{" "}
                      <span className="italic">{row.source}</span>
                    </div>
                  ))}
              </div>
            ) : null}
          </div>
        </>
      )}
    </section>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className="font-display text-[9px] uppercase tracking-[0.15em] text-text-dim">
        {label}
      </div>
      <div
        className={`mt-0.5 font-mono text-sm font-bold tabular-nums ${
          accent ? "text-green-bright" : "text-text-bright"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
