"use client";

import { useEffect, useState } from "react";

import { runComparables } from "@/lib/api-client";
import type { ModulePanelProps } from "@/lib/module-registry";

export default function ComparablesPanel({ record, setRecord }: ModulePanelProps) {
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    runComparables(record.asset, record.rnpv_inputs)
      .then((comparables) => !cancelled && setRecord({ comparables }))
      .catch(() => undefined)
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(record.asset), record.rnpv_inputs.peak_sales_usd_m]);

  const c = record.comparables;
  return (
    <section className="rounded border border-border-dim bg-bg-panel p-5">
      <h2 className="mb-4 font-display text-lg text-text-bright">Deal comparables</h2>

      {loading && !c ? (
        <div className="h-32 animate-pulse rounded bg-bg-panel-hover" />
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
              <thead className="bg-bg-deep text-left text-[10px] uppercase tracking-wide text-text-dim">
                <tr>
                  <th className="p-2">Asset</th>
                  <th className="p-2">Acquirer</th>
                  <th className="p-2">Date</th>
                  <th className="p-2 text-right">Deal $M</th>
                  <th className="p-2 text-right">Peak $M</th>
                  <th className="p-2 text-right">EV/peak</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-100 tabular-nums">
                {c.cohort.map((row, i) => (
                  <tr key={i}>
                    <td className="p-2 font-medium text-text-bright">
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
                    <td className="p-2">{row.acquirer ?? "—"}</td>
                    <td className="p-2">{row.deal_date ?? "—"}</td>
                    <td className="p-2 text-right">
                      {row.deal_value_usd_m != null
                        ? row.deal_value_usd_m.toLocaleString()
                        : "—"}
                    </td>
                    <td className="p-2 text-right">
                      {row.peak_sales_estimate_usd_m != null
                        ? row.peak_sales_estimate_usd_m.toLocaleString()
                        : "—"}
                    </td>
                    <td className="p-2 text-right font-medium text-text-bright">
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
      <div className="text-[10px] uppercase tracking-wide text-text-dim">{label}</div>
      <div
        className={`mt-0.5 font-medium ${accent ? "text-cyan-bright" : "text-text-bright"}`}
      >
        {value}
      </div>
    </div>
  );
}
