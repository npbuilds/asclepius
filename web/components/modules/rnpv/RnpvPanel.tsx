"use client";

import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { runRnpv } from "@/lib/api-client";
import type { ModulePanelProps } from "@/lib/module-registry";
import type { RnpvInputs, RnpvResult } from "@/lib/types";

export default function RnpvPanel({ record, setRecord }: ModulePanelProps) {
  const { asset, pos, rnpv_inputs } = record;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pos) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    runRnpv(asset, pos, rnpv_inputs)
      .then((rnpv) => !cancelled && setRecord({ rnpv }))
      .catch((e) => !cancelled && setError(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(asset), JSON.stringify(pos), JSON.stringify(rnpv_inputs)]);

  if (!pos) {
    return (
      <PanelShell title="Risk-Adjusted NPV">
        <div className="text-sm text-ink-400">Waiting for PoS…</div>
      </PanelShell>
    );
  }

  function patchInputs(patch: Partial<RnpvInputs>) {
    setRecord((prev) => ({ ...prev, rnpv_inputs: { ...prev.rnpv_inputs, ...patch } }));
  }

  const result = record.rnpv;

  return (
    <PanelShell title="Risk-Adjusted NPV">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_auto]">
        <Sliders inputs={rnpv_inputs} onPatch={patchInputs} />
        <div className="lg:w-72">
          <ResultStats result={result} loading={loading} />
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded border border-bad-500/30 bg-bad-500/10 p-3 text-sm text-bad-500">
          {error}
        </div>
      ) : null}

      {result ? (
        <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Tornado tornado={result.tornado} base={result.base_case_usd_m} />
          <Histogram
            p25={result.monte_carlo_p25_usd_m}
            p50={result.monte_carlo_p50_usd_m}
            p75={result.monte_carlo_p75_usd_m}
            base={result.base_case_usd_m}
          />
        </div>
      ) : null}
    </PanelShell>
  );
}

function ResultStats({
  result,
  loading,
}: {
  result: RnpvResult | null;
  loading: boolean;
}) {
  if (loading && !result)
    return <div className="h-32 animate-pulse rounded bg-ink-100" />;
  if (!result) return null;
  const fmt = (n: number | null | undefined) =>
    n == null ? "—" : `$${n.toFixed(0)}M`;
  return (
    <div className="space-y-3 text-sm tabular-nums">
      <Stat label="Base case (closed-form)" value={fmt(result.base_case_usd_m)} accent />
      <Stat
        label="Monte Carlo P25 / P50 / P75"
        value={`${fmt(result.monte_carlo_p25_usd_m)} / ${fmt(result.monte_carlo_p50_usd_m)} / ${fmt(result.monte_carlo_p75_usd_m)}`}
      />
      <Stat
        label="Downside (P3 failure)"
        value={fmt(result.downside_failed_p3_usd_m)}
        bad
      />
      <div className="text-[10px] uppercase tracking-wide text-ink-400">
        {result.monte_carlo_paths.toLocaleString()} simulated paths · seeded
      </div>
    </div>
  );
}

function Sliders({
  inputs,
  onPatch,
}: {
  inputs: RnpvInputs;
  onPatch: (patch: Partial<RnpvInputs>) => void;
}) {
  return (
    <div className="space-y-3 text-sm">
      <Slider
        label={`Peak sales: $${inputs.peak_sales_usd_m.toFixed(0)}M`}
        min={100}
        max={5000}
        step={50}
        value={inputs.peak_sales_usd_m}
        onChange={(v) => onPatch({ peak_sales_usd_m: v })}
      />
      <Slider
        label={`WACC: ${(inputs.wacc * 100).toFixed(1)}%`}
        min={4}
        max={20}
        step={0.5}
        value={inputs.wacc * 100}
        onChange={(v) => onPatch({ wacc: v / 100 })}
      />
      <Slider
        label={`COGS: ${(inputs.cogs_pct * 100).toFixed(0)}%`}
        min={5}
        max={45}
        step={1}
        value={inputs.cogs_pct * 100}
        onChange={(v) => onPatch({ cogs_pct: v / 100 })}
      />
      <Slider
        label={`Phase 3 cost: $${inputs.dev_cost_phase_3_usd_m.toFixed(0)}M`}
        min={50}
        max={600}
        step={10}
        value={inputs.dev_cost_phase_3_usd_m}
        onChange={(v) => onPatch({ dev_cost_phase_3_usd_m: v })}
      />
      <Slider
        label={`Launch cost: $${inputs.launch_cost_usd_m.toFixed(0)}M`}
        min={20}
        max={500}
        step={10}
        value={inputs.launch_cost_usd_m}
        onChange={(v) => onPatch({ launch_cost_usd_m: v })}
      />
    </div>
  );
}

function Slider({
  label,
  min,
  max,
  step,
  value,
  onChange,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-1 text-[11px] uppercase tracking-wide text-ink-400">
        {label}
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-accent-600"
      />
    </label>
  );
}

function Tornado({
  tornado,
  base,
}: {
  tornado: RnpvResult["tornado"];
  base: number;
}) {
  const data = useMemo(() => {
    return tornado.map((b) => {
      const lo = Math.min(b.low_value_usd_m, b.high_value_usd_m);
      const hi = Math.max(b.low_value_usd_m, b.high_value_usd_m);
      return {
        variable: b.variable.replace(/_usd_m|_pct/g, ""),
        left: lo - base,
        right: hi - base,
      };
    });
  }, [tornado, base]);

  return (
    <div className="rounded border border-ink-200 bg-ink-50 p-3">
      <div className="mb-2 text-xs uppercase tracking-wide text-ink-400">
        Tornado sensitivity (Δ vs base case)
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 8, left: 8, bottom: 4 }}
        >
          <XAxis type="number" tick={{ fontSize: 10 }} />
          <YAxis
            type="category"
            dataKey="variable"
            tick={{ fontSize: 11 }}
            width={100}
          />
          <Tooltip
            formatter={(v: number) => `$${v.toFixed(0)}M`}
            cursor={{ fill: "rgba(0,0,0,0.04)" }}
          />
          <Bar dataKey="left" fill="#c4503b" stackId="t" />
          <Bar dataKey="right" fill="#3a9a64" stackId="t" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Histogram({
  p25,
  p50,
  p75,
  base,
}: {
  p25: number | null;
  p50: number | null;
  p75: number | null;
  base: number;
}) {
  if (p25 == null || p50 == null || p75 == null) return null;

  const min = Math.min(p25, base) - 50;
  const max = Math.max(p75, base) + 50;
  const range = max - min;
  const pctNum = (v: number) => ((v - min) / range) * 100;

  const leftP25 = pctNum(p25);
  const leftP75 = pctNum(p75);

  return (
    <div className="rounded border border-ink-200 bg-ink-50 p-3">
      <div className="mb-2 text-xs uppercase tracking-wide text-ink-400">
        Monte Carlo distribution
      </div>
      <div className="relative h-8 rounded bg-ink-100">
        <div
          className="absolute h-full rounded bg-accent-400/50"
          style={{ left: `${leftP25}%`, width: `${leftP75 - leftP25}%` }}
        />
        <div
          className="absolute h-full w-0.5 bg-accent-700"
          style={{ left: `${pctNum(p50)}%` }}
          title={`Median $${p50.toFixed(0)}M`}
        />
        <div
          className="absolute h-full w-0.5 bg-ink-900"
          style={{ left: `${pctNum(base)}%` }}
          title={`Base case $${base.toFixed(0)}M`}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] tabular-nums text-ink-400">
        <span>${p25.toFixed(0)}M</span>
        <span>P50 ${p50.toFixed(0)}M</span>
        <span>${p75.toFixed(0)}M</span>
      </div>
      <div className="mt-1 text-[10px] text-ink-400">
        Black tick = closed-form base. Orange tick = MC median.
      </div>
    </div>
  );
}

function PanelShell({
  title,
  children,
}: {
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-ink-200 bg-white p-5">
      <h2 className="mb-4 font-serif text-lg text-ink-900">{title}</h2>
      {children}
    </section>
  );
}

function Stat({
  label,
  value,
  accent,
  bad,
}: {
  label: string;
  value: string;
  accent?: boolean;
  bad?: boolean;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-ink-400">{label}</div>
      <div
        className={`mt-0.5 font-medium ${
          accent ? "text-accent-700" : bad ? "text-bad-500" : "text-ink-900"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
