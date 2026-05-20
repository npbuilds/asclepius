"use client";

import { useCallback, useEffect, useState } from "react";

import { AssetForm } from "@/components/AssetForm";
import { LimitationsPanel } from "@/components/LimitationsPanel";
import { ReflexivitySlider } from "@/components/ReflexivitySlider";
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
    <div className="mx-auto max-w-7xl px-6 py-10">
      <header className="mb-8">
        <div className="text-xs uppercase tracking-wider text-ink-400">
          Diligence workbench
        </div>
        <h1 className="mt-1 font-serif text-3xl text-ink-900">
          {record.asset.asset_name}
          {record.asset.sponsor ? (
            <span className="ml-3 text-base font-normal text-ink-400">
              · {record.asset.sponsor}
            </span>
          ) : null}
        </h1>
        {isAdagrasib ? (
          <p className="mt-2 max-w-3xl text-sm text-ink-600">
            <strong>Retrospective backtest.</strong> Inputs locked to public
            information available before the KRYSTAL-12 Phase 3 readout (June
            2022 cutoff). This is calibration, not prediction — framework
            outputs should bracket BMS's actual $4.8B acquisition price for the
            post-readout (NDA) scenario.
          </p>
        ) : null}
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <div className="rounded-lg border border-ink-200 bg-white p-5">
            <h2 className="mb-3 font-serif text-base text-ink-900">Asset</h2>
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

        <div className="space-y-5">
          {registryError ? (
            <div className="rounded border border-bad-500/30 bg-bad-500/10 p-4 text-sm text-bad-500">
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
                  className="rounded-lg border border-dashed border-ink-200 bg-white p-5"
                >
                  <h2 className="font-serif text-lg text-ink-900">{m.name}</h2>
                  <p className="mt-1 text-xs text-ink-400">
                    Module discovered on backend ({m.id} v{m.version}) but no
                    frontend panel registered. Add one to{" "}
                    <code>web/lib/module-registry.ts</code>.
                  </p>
                </section>
              );
            }
            return <Panel key={m.id} record={record} setRecord={setRecord} />;
          })}
        </div>
      </div>
    </div>
  );
}
