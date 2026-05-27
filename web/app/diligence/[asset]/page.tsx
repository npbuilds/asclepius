"use client";

import { useCallback, useEffect, useState } from "react";

import ActionSection from "@/components/ActionSection";
import { AssetForm, labelFor } from "@/components/AssetForm";
import IcVoterBanner from "@/components/banners/IcVoterBanner";
import ScientificBanner from "@/components/banners/ScientificBanner";
import TrialDesignCard from "@/components/cards/TrialDesignCard";
import HeroBanner from "@/components/HeroBanner";
import { ReflexivitySlider } from "@/components/ReflexivitySlider";
import RiskSection from "@/components/RiskSection";
import { listModules } from "@/lib/api-client";
import {
  ClientDiligenceRecord,
  getPanelFor,
  groupModulesBySection,
  orderModules,
  type SectionWithManifests,
} from "@/lib/module-registry";
import { getPersonaConfig, type PersonaSection } from "@/lib/persona-config";
import { useCurrentPersona } from "@/lib/use-persona";
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

// v1.7.0 Phase 4: collapsed-summary line for the asset-form <details> strip.
// Reads like a terse roll-up of the form's contents so a reader can grok
// the staged inputs without expanding. Order chosen to mirror what an
// equity-research report's "asset card" would surface first: phase →
// therapeutic area → modality → capital tier → designation count →
// competitor count.
function assetSummaryLine(asset: AssetInput): string {
  const parts: string[] = [
    labelFor(asset.phase),
    labelFor(asset.therapeutic_area),
    labelFor(asset.modality),
    labelFor(asset.capital_position),
  ];
  const designations = asset.regulatory_designations.length;
  parts.push(
    `${designations} designation${designations === 1 ? "" : "s"}`,
  );
  parts.push(
    `${asset.num_competitors} competitor${asset.num_competitors === 1 ? "" : "s"}`,
  );
  return parts.join(" · ");
}

// v1.8.0 Phase 3: turn a persona's PersonaSection[] config into the
// SectionWithManifests shape the section render loop already expects.
// Each PersonaSection lists module IDs to render in order; we look up
// the corresponding manifest from the (already filtered) list and skip
// any moduleId that isn't backend-discovered. Empty sections (zero
// resolved modules) are dropped so we don't render a dangling header.
function adaptPersonaSections(
  personaSections: PersonaSection[],
  manifests: ModuleManifest[],
): SectionWithManifests[] {
  const byId = new Map(manifests.map((m) => [m.id, m]));
  const out: SectionWithManifests[] = [];
  for (const section of personaSections) {
    const sectionManifests = section.moduleIds
      .map((id) => byId.get(id))
      .filter((m): m is ModuleManifest => Boolean(m));
    if (sectionManifests.length === 0) continue;
    out.push({
      section: {
        id: section.id,
        label: section.label,
        question: section.question,
        moduleIds: section.moduleIds,
      },
      manifests: sectionManifests,
    });
  }
  return out;
}

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
    // v1.7.0: ml_pos lifted from MLPosPriorPanel to the record so HeroBanner
    // can surface the LOA microsplit (BIO → Reflexivity → ML) from a single
    // source. Populated by MLPosPriorPanel's fetch effect.
    ml_pos: null,
    // v1.5.2: NCT04685135 = KRYSTAL-1 (the Phase-2 registrational adagrasib
    // trial). The backend's PubMedBERT path embeds this trial's eligibility
    // criteria when the feature-fingerprint cache misses; the cached
    // pre-computed adagrasib.json is used when the asset is the canonical
    // record verbatim.
    ml_pos_nct_id: isAdagrasib ? "NCT04685135" : null,
    ml_pos_criteria_text: null,
  }));

  const setRecord = useCallback<
    (u: Partial<ClientDiligenceRecord> | ((p: ClientDiligenceRecord) => ClientDiligenceRecord)) => void
  >((u) => {
    setRecordState((prev) => (typeof u === "function" ? u(prev) : { ...prev, ...u }));
  }, []);

  const [manifests, setManifests] = useState<ModuleManifest[]>([]);
  const [registryError, setRegistryError] = useState<string | null>(null);

  // v1.7.0 Phase 4: asset form collapse state. Default-open for assets
  // the user just typed in (they need to edit fields); default-closed
  // for pre-staged assets like adagrasib (already populated, summary
  // line communicates the state). Browser then handles toggle via the
  // `onToggle` handler so the choice sticks across record updates.
  const [assetFormOpen, setAssetFormOpen] = useState(!isAdagrasib);

  // v1.8.0 Phase 3: persona-driven layout. The page reads the current
  // persona on every render and looks up its config (module ordering,
  // hidden modules, banner variant, ActionSection visibility). For the
  // default VC Associate persona the config produces the v1.7.0 layout
  // unchanged; for IC Voter / Scientific Reviewer / Quant it diverges
  // per persona-config.ts. The `useCurrentPersona` hook subscribes to
  // the PERSONA_CHANGE_EVENT dispatched by `setPersona` in lib/persona.ts,
  // so dropdown changes in the global header re-render this page live.
  const persona = useCurrentPersona();
  const personaConfig = getPersonaConfig(persona);

  // Filter modules per persona's hiddenModules. The registry pattern's
  // promise — "any backend-discovered module is visible" — is preserved
  // for personas with hiddenModules == [], and intentionally narrowed
  // for personas that drop modules they don't care about (e.g.
  // Scientific Reviewer drops rnpv + comparables).
  const visibleManifests = personaConfig.hiddenModules.length === 0
    ? manifests
    : manifests.filter((m) => !personaConfig.hiddenModules.includes(m.id));

  // Section grouping override. Empty `sections` → use the v1.7.0 default
  // (MODULE_SECTIONS from module-registry.ts). Non-empty → adapt the
  // persona's sections to the SectionWithManifests shape that the
  // existing render loop expects. PersonaSection has the same shape as
  // the registry's ModuleSection, so the adapter is just a shallow
  // re-wrap with the filtered manifests list.
  const sections: SectionWithManifests[] = personaConfig.sections.length === 0
    ? groupModulesBySection(visibleManifests)
    : adaptPersonaSections(personaConfig.sections, visibleManifests);

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

      {/* v1.7.0: HeroBanner ("30-second read"). v1.8.0: swap to a
          persona-specific banner when the config calls for it.
            ic_voter → IcVoterBanner (1-page summary, Phase 3)
            scientific → ScientificBanner (science + trial design, Phase 4)
            quant → QuantBanner (Phase 5, pending)
            vc (default) → HeroBanner (the v1.7.0 reading-journey banner) */}
      {personaConfig.bannerVariant === "ic_voter" ? (
        <IcVoterBanner record={record} />
      ) : personaConfig.bannerVariant === "scientific" ? (
        <ScientificBanner record={record} />
      ) : (
        <HeroBanner record={record} />
      )}

      {/* v1.7.0 Phase 4: Asset form collapsed to a top strip with a
          one-line summary. Default-open on non-adagrasib assets (the user
          needs to edit fields); default-closed on adagrasib (pre-staged,
          summary line tells the story). Controlled via React state so a
          user toggle persists across re-renders. */}
      <details
        open={assetFormOpen}
        onToggle={(e) => setAssetFormOpen(e.currentTarget.open)}
        className="group mb-3 rounded border border-border-dim bg-bg-panel"
      >
        <summary className="flex cursor-pointer items-baseline justify-between gap-3 px-3 py-2 [&::-webkit-details-marker]:hidden">
          <span className="flex items-baseline gap-2 truncate">
            <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
              Asset ▸
            </span>
            <span className="font-mono text-[11px] text-text-primary group-open:text-text-dim">
              {assetSummaryLine(record.asset)}
            </span>
          </span>
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-text-dim">
            {assetFormOpen ? "[ collapse ]" : "[ edit ]"}
          </span>
        </summary>
        <div className="border-t border-border-dim/60 p-3">
          <AssetForm value={record.asset} onChange={updateAsset} />
        </div>
      </details>

      {/* v1.7.0 Phase 4: full-width content column. The previous 320px aside
          is gone — AssetForm collapsed to the strip above; LimitationsPanel
          moves into the main flow near the bottom (Phase 5 will wrap it
          + AdversaryPanel into a consolidated Risk section). */}
      <div className="space-y-3">
          {registryError ? (
            <div className="rounded border border-red-bright/40 bg-red-bright/10 p-4 text-sm text-red-bright">
              Could not load module registry: {registryError}. Is the API
              running on port 8000?
            </div>
          ) : null}

          {/* v1.7.0 + v1.8.0 Phase 3: section-grouped module rendering with
              persona override. `sections` is computed at the top of the
              component — VC Associate uses MODULE_SECTIONS, the other 3
              personas override via persona-config.ts. The Risk and Action
              surfaces live outside the module system; ActionSection
              renders only when personaConfig.showActionSection is true. */}
          {sections.map(({ section, manifests: sectionManifests }) => (
            <div key={section.id} className="space-y-3">
              <div className="border-b border-border-dim/60 pb-1">
                <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
                  ── {section.label} ─────────────────────────
                </div>
                <p className="mt-1 font-prose text-[11px] italic leading-snug text-text-dim">
                  Q: {section.question}
                </p>
              </div>
              {/* v1.7.0 Phase 3: Reflexivity slider as the Thesis section's
                  leading element — full-width, magenta-accented. Dragging
                  it live-updates the PoS waterfall + ML PoS Prior + the
                  banner LOA row below; that's the v1.7.0 demo beat. */}
              {section.id === "thesis" ? (
                <ReflexivitySlider
                  value={record.asset.capital_position}
                  onChange={(capital_position) =>
                    updateAsset({ ...record.asset, capital_position })
                  }
                />
              ) : null}
              {/* v1.8.0 Phase 4: TrialDesignCard as the Science section's
                  leading element (Scientific Reviewer persona only). Surfaces
                  the NCT ID + protocol context that informs the ML PoS Prior's
                  supervised signal — auditable trial design, biomarker
                  enrichment + target-validation flags, link out to CT.gov. */}
              {section.id === "science" ? (
                <TrialDesignCard record={record} />
              ) : null}
              {sectionManifests.map((m) => {
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
                        Module discovered on backend ({m.id} v{m.version}) but
                        no frontend panel registered. Add one to{" "}
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
            </div>
          ))}

          {/* v1.7.0 Phase 5: RiskSection — consolidates LimitationsPanel +
              AdversaryPanel under one named section matching the Phase 2
              pattern. Per the healthcare-VC research this is the "section
              that determines a yes/no vote" — visually co-equal with
              Valuation, not a sidebar afterthought. */}
          <RiskSection record={record} />

          {/* v1.7.0 Phase 6 + v1.8.0 Phase 3: ActionSection renders for
              personas whose config flags showActionSection true. IC Voter
              hides it (one-page summary target); VC / Scientific / Quant
              show it. */}
          {personaConfig.showActionSection ? (
            <ActionSection record={record} setRecord={setRecord} />
          ) : null}
        </div>
      </div>
  );
}
