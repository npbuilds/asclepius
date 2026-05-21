"use client";

import { useCallback, useEffect, useState } from "react";

import { AssetForm } from "@/components/AssetForm";
import { LimitationsPanel } from "@/components/LimitationsPanel";
import { ReflexivitySlider } from "@/components/ReflexivitySlider";
import { AdversaryPanel } from "@/components/agents/AdversaryPanel";
import { MemoPanel } from "@/components/agents/MemoPanel";
import { listModules } from "@/lib/api-client";
import {
  ClientDiligenceRecord,
  getPanelFor,
  orderModules,
} from "@/lib/module-registry";
import type { AssetInput, ModuleManifest, RnpvInputs } from "@/lib/types";

const ADAGRASIB: AssetInput = {
  asset_name: "adagrasib",
  sponsor: "Mirati Therapeutics",
  phase: "phase_2",
  therapeutic_area: "oncology",
  modality: "small_molecule",
  capital_position: "adequate",
  mechanism: "KRAS G12C inhibitor",
  target: "KRAS G12C",
  indication: "NSCLC (2L+, G12C-mutant)",
  regulatory_designations: ["breakthrough_therapy"],
  num_competitors: 1,
  target_validated: true,
  biomarker_enrichment: true,
};

const ADAGRASIB_RNPV: RnpvInputs = {
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

const DEFAULT_RNPV: RnpvInputs = {
  peak_sales_usd_m: 1000,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.20,
  wacc: 0.12,
  dev_cost_phase_1_usd_m: 25,
  dev_cost_phase_2_usd_m: 75,
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 1.5, phase_2: 2.5, phase_3: 3, regulatory: 1 },
};

function blankAsset(name: string): AssetInput {
  return {
    asset_name: name,
    sponsor: null,
    phase: "phase_2",
    therapeutic_area: "oncology",
    modality: "small_molecule",
    capital_position: "adequate",
    mechanism: null,
    target: null,
    indication: null,
    regulatory_designations: [],
    num_competitors: 0,
    target_validated: false,
    biomarker_enrichment: false,
  };
}

export default function DiligencePage({
  params,
}: {
  params: { asset: string };
}) {
  const isAdagrasib = params.asset.toLowerCase() === "adagrasib";

  const [record, setRecordState] = useState<ClientDiligenceRecord>(() => ({
    asset: isAdagrasib ? ADAGRASIB : blankAsset(decodeURIComponent(params.asset)),
    pos: null,
    rnpv_inputs: isAdagrasib ? ADAGRASIB_RNPV : DEFAULT_RNPV,
    rnpv: null,
    scorecard: null,
    comparables: null,
  }));

  const setRecord = useCallback<
    (u: Partial<ClientDiligenceRecord> | ((p: ClientDiligenceRecord) => ClientDiligenceRecord)) => void
  >((u) => {
    setRecordState((prev) => (typeof u === "function" ? u(prev) : { ...prev, ...u }));
  }, []);

  const [manifests, setManifests] = useState<ModuleManifest[]>([]);
  const [registryError, setRegistryError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listModules()
      .then((m) => !cancelled && setManifests(orderModules(m)))
      .catch((e) => !cancelled && setRegistryError(String(e)));
    return () => {
      cancelled = true;
    };
  }, []);

  function updateAsset(asset: AssetInput) {
    setRecord({ asset });
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-4">
      <header className="mb-4">
        <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
          ── Diligence workbench ──
        </div>
        <h1 className="mt-1 font-display text-xl font-bold uppercase leading-[1.15] tracking-[0.04em] text-text-bright sm:text-2xl">
          {record.asset.asset_name}
          {record.asset.sponsor ? (
            <span className="ml-2.5 font-body text-[13px] font-normal normal-case tracking-normal text-text-dim">
              · {record.asset.sponsor}
            </span>
          ) : null}
        </h1>
        {isAdagrasib ? (
          <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
            <strong className="text-text-bright">Retrospective backtest.</strong>{" "}
            Inputs locked to public information available before the KRYSTAL-12
            Phase 3 readout (June 2022 cutoff). This is calibration, not
            prediction — framework outputs should bracket BMS's actual $4.8B
            acquisition price for the post-readout (NDA) scenario.
          </p>
        ) : null}
      </header>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-[320px_1fr]">
        <aside className="space-y-3">
          <div className="rounded border border-border-dim bg-bg-panel p-3">
            <h2 className="mb-2 font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-text-dim">
              Asset
            </h2>
            <AssetForm value={record.asset} onChange={updateAsset} />
          </div>

          <ReflexivitySlider
            value={record.asset.capital_position}
            onChange={(capital_position) =>
              updateAsset({ ...record.asset, capital_position })
            }
          />

          <LimitationsPanel />
        </aside>

        <div className="space-y-3">
          {registryError ? (
            <div className="rounded border border-red-bright/40 bg-red-bright/10 p-4 text-sm text-red-bright">
              Could not load module registry: {registryError}. Is the API
              running on port 8000?
            </div>
          ) : null}

          {manifests.map((m) => {
            const Panel = getPanelFor(m);
            if (!Panel) {
              return (
                <section
                  key={m.id}
                  className="rounded border border-dashed border-border-dim bg-bg-panel p-5"
                >
                  <h2 className="font-display text-sm font-semibold uppercase tracking-wider text-text-bright">
                    {m.name}
                  </h2>
                  <p className="mt-1 text-xs text-text-dim">
                    Module discovered on backend ({m.id} v{m.version}) but no
                    frontend panel registered. Add one to{" "}
                    <code className="font-mono">
                      web/lib/module-registry.ts
                    </code>
                    .
                  </p>
                </section>
              );
            }
            return <Panel key={m.id} record={record} setRecord={setRecord} />;
          })}

          <MemoPanel record={record} />
          <AdversaryPanel record={record} />
        </div>
      </div>
    </div>
  );
}
