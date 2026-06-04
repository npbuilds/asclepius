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
  // v1 limitation: the comparables engine returns a fixed kinase-TKI
  // single-asset M&A cohort (selpercatinib, larotrectinib, encorafenib)
  // regardless of the input asset's TA or modality. This is *honest* for
  // KRAS/kinase oncology assets (adagrasib, divarasib, olomorasib — the
  // model's distribution) but visibly off for non-kinase indications.
  // Surface the limitation rather than silently misframe the cohort.
  // Routing comparables by (asset.therapeutic_area × asset.modality) is
  // the v2 enhancement; see methodology/00-product-thesis.md §v2 roadmap.
  const isKinaseOncologyContext =
    record.asset.therapeutic_area === "oncology" &&
    record.asset.modality === "small_molecule";
  return (
    <section className="rounded border border-border-dim bg-bg-panel p-3">
      <h2 className="mb-2.5 font-display text-[13px] font-semibold uppercase tracking-wider text-text-bright">Deal comparables</h2>

      {!isKinaseOncologyContext ? (
        <p className="mb-3 rounded border border-amber-bright/30 bg-amber-bright/5 p-2 font-mono text-[10px] leading-snug text-amber-bright">
          ⚠ <strong className="font-semibold uppercase tracking-wider">v1 cohort note:</strong> Asclepius v1 ships
          a fixed reference cohort (kinase-TKI single-asset M&A:
          selpercatinib, larotrectinib, encorafenib). This is calibrated
          to the model&apos;s training distribution but not asset-matched
          for this {record.asset.therapeutic_area}/{record.asset.modality}{" "}
          input. Routing by therapeutic area × modality is the v2
          enhancement &mdash; see the product thesis.
        </p>
      ) : null}

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
