"use client";

import { useCallback, useEffect, useState } from "react";

import ActionSection from "@/components/ActionSection";
import { AssetForm, labelFor } from "@/components/AssetForm";
import IcVoterBanner from "@/components/banners/IcVoterBanner";
import QuantBanner from "@/components/banners/QuantBanner";
import ScientificBanner from "@/components/banners/ScientificBanner";
import ModelInfoRawCard from "@/components/cards/ModelInfoRawCard";
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

// v1.6: divarasib is the live FORWARD prediction (NCT06497556, Roche, Phase 3,
// KRAS G12C+ NSCLC head-to-head vs sotorasib/adagrasib, PCD 2027-09-30).
// Values MUST match scripts/log_divarasib_prediction.py so the workbench
// numbers reproduce the public predictions/2026-06-03-divarasib-...json
// record. See methodology/18-divarasib-live-forward-prediction.md for the
// per-field citations. The agent cache (if precomputed) is keyed by the
// asset_name slug so this exact AssetInput is what the cached memo /
// adversary / auto-diligence outputs were grounded on.
const DIVARASIB: AssetInput = {
  asset_name: "divarasib",
  sponsor: "Hoffmann-La Roche",
  phase: "phase_3",
  therapeutic_area: "oncology",
  modality: "small_molecule",
  capital_position: "well_capitalized",
  mechanism: "KRAS G12C inhibitor (covalent, second-generation)",
  target: "KRAS G12C",
  indication: "Previously treated KRAS G12C+ advanced/metastatic NSCLC",
  regulatory_designations: [],
  num_competitors: 3,
  target_validated: true,
  biomarker_enrichment: true,
};

const DIVARASIB_RNPV: RnpvInputs = {
  peak_sales_usd_m: 700,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.20,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  // Phase 3 enrollment is complete (ACTUAL n=338), so the development cost is
  // effectively the trial-conduct + analysis residual rather than the full
  // ~$250M cohort baseline. We use the framework default to stay
  // comparable to the rest of the cohort.
  dev_cost_phase_3_usd_m: 250,
  launch_cost_usd_m: 150,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 1.5, regulatory: 1 },
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

// v1.6 breadth-of-coverage: aducanumab as a third RETROSPECTIVE backtest,
// this time in CNS · small_molecule (the cohort we shipped this morning).
// Information cutoff: March 2019 — IMMEDIATELY after Biogen halted
// ENGAGE/EMERGE Phase 3 trials for futility (Mar 21 2019). The framework
// should produce a LOW LOA at this point; the asset's subsequent FDA
// accelerated approval (Jun 2021) over the advisory committee's
// objection is exactly the kind of contested-political-approval outcome
// the framework can't and shouldn't try to predict. Pre-staging as
// phase_3 (NOT approved) preserves the diligence framing — what would
// an analyst have concluded immediately after the Ph3 failure?
const ADUCANUMAB: AssetInput = {
  asset_name: "aducanumab",
  sponsor: "Biogen / Eisai",
  phase: "phase_3",
  therapeutic_area: "cns",
  modality: "monoclonal_antibody",
  capital_position: "well_capitalized",
  mechanism: "anti-amyloid-beta monoclonal antibody",
  target: "amyloid beta (Aβ) aggregates",
  indication: "Alzheimer's disease (mild cognitive impairment)",
  regulatory_designations: ["fast_track"],
  num_competitors: 2,
  // The amyloid hypothesis was NOT validated by approved drugs as of
  // March 2019 — every prior anti-amyloid (bapineuzumab, solanezumab,
  // gantenerumab Phase 3a) had failed. The validation came retroactively
  // via the 2021 controversial approval, not prospectively.
  target_validated: false,
  // ENGAGE/EMERGE enrolled amyloid-PET-positive patients but the
  // biomarker-enrichment field rewards a *predictive* biomarker that
  // identifies responders. Amyloid PET selection didn't outcome-enrich
  // (both Ph3 trials failed despite PET selection). Mark false to avoid
  // crediting an enrichment strategy that didn't work.
  biomarker_enrichment: false,
};

const ADUCANUMAB_RNPV: RnpvInputs = {
  peak_sales_usd_m: 4500,
  years_to_peak: 5,
  years_of_exclusivity: 12,
  cogs_pct: 0.15,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  // Phase 3 failed at futility — but Biogen continued program. Costs to
  // restart with a different statistical plan / new biomarker analysis.
  dev_cost_phase_3_usd_m: 200,
  launch_cost_usd_m: 200,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 2, regulatory: 1 },
};

// v1.6 breadth: lifileucel as a third FDA-APPROVED retrospective example,
// this time in cell therapy. Information cutoff: Jan 2024, the asset's
// BLA was accepted by FDA late 2023. Approved Feb 16 2024 as Amtagvi for
// 2L+ advanced melanoma. Pre-stage at phase_3 (with single-arm Phase 2
// data) to preserve the pre-approval framing. The framework's
// cell_therapy_autologous modality multiplier should appropriately
// adjust PoS for the manufacturing/durability/access challenges that
// distinguish TIL therapy from a small-molecule approval path.
const LIFILEUCEL: AssetInput = {
  asset_name: "lifileucel",
  sponsor: "Iovance Biotherapeutics",
  phase: "phase_3",
  therapeutic_area: "oncology",
  modality: "cell_therapy_autologous",
  capital_position: "constrained",
  mechanism: "autologous tumor-infiltrating lymphocyte (TIL) therapy",
  target: "patient-specific tumor neoantigens",
  indication: "Advanced/metastatic melanoma post-anti-PD1 + BRAF/MEK (if BRAF+)",
  regulatory_designations: ["breakthrough_therapy", "orphan_drug", "fast_track"],
  num_competitors: 0,
  target_validated: true,
  biomarker_enrichment: false,
};

const LIFILEUCEL_RNPV: RnpvInputs = {
  peak_sales_usd_m: 1100,
  years_to_peak: 6,
  years_of_exclusivity: 12,
  // Cell therapy manufacturing is genuinely expensive — 35-40% COGS is
  // typical for autologous cell therapy in the first 5 years. Higher
  // than small molecule (15-20%) or biologics (20-25%).
  cogs_pct: 0.38,
  wacc: 0.12,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  dev_cost_phase_3_usd_m: 150,
  // Launch costs for cell therapy are higher: manufacturing facilities,
  // ATC (authorized treatment center) network buildout, REMS programs.
  launch_cost_usd_m: 300,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 1, regulatory: 1 },
};

// v1.6 breadth: tulisokibart as a third FORWARD prediction, this time
// in autoimmune · biologic (the cohort we added today). Phase 3 ATLAS-UC
// and ATLAS-CD trials ongoing; primary completion estimated 2026-2027.
// Merck-sponsored after the April 2023 Prometheus acquisition; the
// framework's well-capitalized reflexivity tier applies. Anti-TL1A is a
// novel target — target_validated is FALSE because no anti-TL1A asset
// has been approved (Roivant's parallel program is also Phase 3).
const TULISOKIBART: AssetInput = {
  asset_name: "tulisokibart",
  sponsor: "Merck & Co. (acquired from Prometheus)",
  phase: "phase_3",
  therapeutic_area: "autoimmune",
  modality: "monoclonal_antibody",
  capital_position: "well_capitalized",
  mechanism: "anti-TL1A (TNFSF15) monoclonal antibody",
  target: "TL1A (TNFSF15)",
  indication: "Ulcerative colitis (Phase 3 ATLAS-UC) and Crohn's disease (Phase 3 ATLAS-CD)",
  regulatory_designations: [],
  num_competitors: 2,
  target_validated: false,
  biomarker_enrichment: false,
};

const TULISOKIBART_RNPV: RnpvInputs = {
  peak_sales_usd_m: 5000,
  years_to_peak: 6,
  years_of_exclusivity: 12,
  cogs_pct: 0.22,
  wacc: 0.10,
  dev_cost_phase_1_usd_m: 0,
  dev_cost_phase_2_usd_m: 0,
  // Large IBD Phase 3 program — multiple indications, dose-ranging,
  // active comparator possible. Heftier than the cohort default.
  dev_cost_phase_3_usd_m: 400,
  launch_cost_usd_m: 200,
  years_per_phase: { phase_1: 0, phase_2: 0, phase_3: 3, regulatory: 1 },
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
  const assetSlug = params.asset.toLowerCase();
  const isAdagrasib = assetSlug === "adagrasib";
  const isDivarasib = assetSlug === "divarasib";
  const isAducanumab = assetSlug === "aducanumab";
  const isLifileucel = assetSlug === "lifileucel";
  const isTulisokibart = assetSlug === "tulisokibart";

  // Pre-staged asset wiring: each known showcase asset gets its hardcoded
  // AssetInput + RnpvInputs + (optionally) an NCT ID for the PubMedBERT
  // criteria fetch path. Any unknown asset falls through to the blank-
  // form path, which renders an editable form for the analyst persona.
  // Adding a new showcase asset is a 3-step pattern:
  //   1. Define const NAME / NAME_RNPV at the top of the file
  //   2. Add the isName branch here
  //   3. Add the isName === true branch into the framing-paragraph block
  //      further down (for the retrospective / forward / contested label)
  const stagedAsset: AssetInput = isAdagrasib
    ? ADAGRASIB
    : isDivarasib
      ? DIVARASIB
      : isAducanumab
        ? ADUCANUMAB
        : isLifileucel
          ? LIFILEUCEL
          : isTulisokibart
            ? TULISOKIBART
            : blankAsset(decodeURIComponent(params.asset));
  const stagedRnpv: RnpvInputs = isAdagrasib
    ? ADAGRASIB_RNPV
    : isDivarasib
      ? DIVARASIB_RNPV
      : isAducanumab
        ? ADUCANUMAB_RNPV
        : isLifileucel
          ? LIFILEUCEL_RNPV
          : isTulisokibart
            ? TULISOKIBART_RNPV
            : DEFAULT_RNPV;
  const stagedNctId: string | null = isAdagrasib
    ? "NCT04685135"  // KRYSTAL-1 — Ph2 registrational adagrasib
    : isDivarasib
      ? "NCT06497556" // divarasib vs sotorasib/adagrasib Ph3
      : isAducanumab
        ? "NCT02484547" // ENGAGE — one of the failed Ph3 aducanumab trials
        : isLifileucel
          ? "NCT02360579" // C-144-01 — pivotal Ph2 lifileucel in melanoma
          : isTulisokibart
            ? "NCT06430879" // ATLAS-UC — Ph3 tulisokibart UC
            : null;

  const [record, setRecordState] = useState<ClientDiligenceRecord>(() => ({
    asset: stagedAsset,
    pos: null,
    rnpv_inputs: stagedRnpv,
    rnpv: null,
    scorecard: null,
    comparables: null,
    // v1.7.0: ml_pos lifted from MLPosPriorPanel to the record so HeroBanner
    // can surface the LOA microsplit (BIO → Reflexivity → ML) from a single
    // source. Populated by MLPosPriorPanel's fetch effect.
    ml_pos: null,
    // The backend's PubMedBERT path embeds this trial's eligibility
    // criteria when the feature-fingerprint cache misses; cached
    // pre-computed agent JSON is used when the asset is the canonical
    // record verbatim.
    ml_pos_nct_id: stagedNctId,
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
  // Pre-staged assets get the form default-closed — the values are
  // already correct; an analyst would only open the form to sensitivity-
  // test, not to populate. Unknown assets default-open because the form
  // is the only way to populate them.
  const isStaged =
    isAdagrasib || isDivarasib || isAducanumab || isLifileucel || isTulisokibart;
  const [assetFormOpen, setAssetFormOpen] = useState(!isStaged);

  // v1.8.0 Phase 3: persona-driven layout. The page reads the current
  // persona on every render and looks up its config (module ordering,
  // hidden modules, banner variant, ActionSection visibility). For the
  // default VC Associate persona the config produces the v1.7.0 layout
  // unchanged; for IC Voter / Scientific Reviewer / Quant it diverges
  // per persona-config.ts. The `useCurrentPersona` hook subscribes to
  // the PERSONA_CHANGE_EVENT dispatched by `setPersona` in lib/persona.ts,
  // so dropdown changes in the global header re-render this page live.
  //
  // v1.8.0-rc3.1 (Codex MINOR #2 fix): the hook returns DEFAULT_PERSONA on
  // the initial render to keep SSR + client-hydration in agreement; it
  // updates to the persisted persona only after its useEffect fires. For
  // users with a persisted non-default persona, that previously caused a
  // visible "HeroBanner → IcVoterBanner" flash on deep-link refresh. The
  // `personaResolved` gate now defers persona-aware rendering until the
  // hook has resolved — the page shows a single-row skeleton during the
  // brief hydration window instead of the wrong banner. Eliminates the
  // flash without breaking SSR.
  const persona = useCurrentPersona();
  const personaConfig = getPersonaConfig(persona);
  const [personaResolved, setPersonaResolved] = useState(false);
  useEffect(() => {
    setPersonaResolved(true);
  }, []);

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
        ) : isDivarasib ? (
          <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
            <strong className="text-text-bright">Live forward prediction.</strong>{" "}
            Phase 3 NCT06497556 head-to-head vs sotorasib/adagrasib. Enrollment
            complete (ACTUAL n=338); primary completion 2027-09-30. Framework
            output committed to git on 2026-06-03 before any outcome was known
            — see {" "}
            <a
              href="/methodology/18-divarasib-live-forward-prediction"
              className="underline hover:text-cyan-bright"
            >
              methodology/18
            </a>{" "}
            for the pre-registered prediction with resolution criteria.
          </p>
        ) : isAducanumab ? (
          <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
            <strong className="text-text-bright">Contested-approval retrospective.</strong>{" "}
            Information cutoff: <strong>March 2019</strong>, immediately after
            Biogen halted ENGAGE/EMERGE Phase 3 trials for futility. Framework
            should report a low LOA. The actual outcome — FDA accelerated
            approval in June 2021 over the AdCom&apos;s 10-0 reject vote — is a
            political-process outcome the framework can&apos;t and shouldn&apos;t
            predict. Useful for testing how the framework handles a controversial
            Phase 3 readout.
          </p>
        ) : isLifileucel ? (
          <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
            <strong className="text-text-bright">Cell therapy retrospective.</strong>{" "}
            Information cutoff: <strong>January 2024</strong>, BLA accepted by
            FDA but pre-approval. Iovance had filed on Phase 2 single-arm data
            (C-144-01). Subsequent approval Feb 16 2024 as Amtagvi for 2L+
            advanced melanoma. Useful for testing the framework on autologous
            cell therapy economics — higher COGS, capital-intensive manufacturing,
            ATC network requirements, and a constrained sponsor.
          </p>
        ) : isTulisokibart ? (
          <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
            <strong className="text-text-bright">Autoimmune biologic forward prediction.</strong>{" "}
            Phase 3 ATLAS-UC (NCT06430879) and ATLAS-CD trials ongoing for
            ulcerative colitis and Crohn&apos;s. Merck-sponsored after the April
            2023 Prometheus acquisition ($10.8B). Anti-TL1A is a novel target
            class — no anti-TL1A asset has been FDA-approved yet (Roivant&apos;s
            parallel program is also in Phase 3). Exercises the framework on
            the new autoimmune-biologic cohort.
          </p>
        ) : null}

        {/* v1.6 custom-asset guardrail: Auto-Diligence can populate phase
            "approved" for FDA-approved assets (e.g., generalist types
            "lecanemab" or "voranigo"). The PoS chain trivially returns
            1.0 for approved phase — mathematically correct but uninformative.
            Surface a friendly redirect to the methodology + the two
            pre-staged showcase assets rather than letting the user see
            100% PoS and bounce. */}
        {record.asset.phase === "approved" ? (
          <div className="mt-3 rounded border border-amber-bright/30 bg-amber-bright/5 p-3 text-[12px] leading-relaxed">
            <p className="font-mono text-[10px] uppercase tracking-wider text-amber-bright">
              ⚠ post-approval asset
            </p>
            <p className="mt-1.5 font-prose text-text-primary">
              This asset is FDA-approved, so the rule-based PoS chain
              returns the trivial 1.0 (already past the gates). Asclepius&apos;s
              valuation surfaces are calibrated for pre-approval assets —
              the LOA microsplit, reflexivity slider, and rNPV PoS-weighting
              all assume an open question about whether the asset reaches
              market. For an approved asset, switch the rNPV to a
              straight DCF over remaining exclusivity and treat the
              scorecard as commercial-execution-only.
            </p>
            <p className="mt-2 font-prose text-text-dim">
              Try a pre-approval asset to see the framework in its actual
              domain &mdash;{" "}
              <a href="/diligence/adagrasib" className="text-cyan-bright underline hover:text-cyan-bright">
                adagrasib
              </a>{" "}
              (retrospective backtest) or{" "}
              <a href="/diligence/divarasib" className="text-cyan-bright underline hover:text-cyan-bright">
                divarasib
              </a>{" "}
              (live forward prediction).
            </p>
          </div>
        ) : null}
      </header>

      {/* v1.7.0: HeroBanner ("30-second read"). v1.8.0: swap to a
          persona-specific banner when the config calls for it.
            ic_voter → IcVoterBanner (1-page summary, Phase 3)
            scientific → ScientificBanner (science + trial design, Phase 4)
            quant → QuantBanner (Phase 5, pending)
            vc (default) → HeroBanner (the v1.7.0 reading-journey banner)
          v1.8.0-rc3.1: skeleton banner during the brief pre-mount window
          so a persisted non-default persona doesn't flash through
          HeroBanner first. After `personaResolved` flips true (post-mount),
          the correct persona banner mounts directly. */}
      {!personaResolved ? (
        <div className="mb-4 h-32 animate-pulse rounded border border-border-dim bg-bg-panel" />
      ) : personaConfig.bannerVariant === "ic_voter" ? (
        <IcVoterBanner record={record} />
      ) : personaConfig.bannerVariant === "scientific" ? (
        <ScientificBanner record={record} />
      ) : personaConfig.bannerVariant === "quant" ? (
        <QuantBanner record={record} />
      ) : (
        <HeroBanner record={record} />
      )}

      {/* v1.6 friend-test prompt: when an unstaged asset has an
          essentially-blank record (no sponsor / no mechanism / default
          competitors / default biomarker), surface a one-line nudge that
          points at Auto-Diligence. Without this, the friend lands on a
          half-empty form with no signal that the agent will populate it.
          The heuristic for "blank": no sponsor AND no mechanism. Once
          Auto-Diligence runs (or the analyst types into the form), one of
          those will be populated and the prompt disappears — no manual
          dismiss state needed. Adagrasib + divarasib bypass this entirely
          because their pre-staged records always have sponsor + mechanism. */}
      {!isStaged && !record.asset.sponsor && !record.asset.mechanism ? (
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2 rounded border border-cyan-bright/30 bg-cyan-bright/5 p-3 text-[12px]">
          <p className="font-prose text-text-primary">
            <strong className="font-display text-[11px] uppercase tracking-wider text-cyan-bright">
              Start here →
            </strong>{" "}
            Scroll to the bottom action strip and click{" "}
            <span className="font-mono text-text-bright">Auto-Diligence</span>{" "}
            to populate every field on this page from public sources
            (CT.gov, FDA, EDGAR, top journals). Takes ~30 seconds.
          </p>
          <p className="font-mono text-[10px] uppercase tracking-wider text-text-dim">
            or [ edit ] the asset strip below to enter values manually
          </p>
        </div>
      ) : null}

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
              renders only when personaConfig.showActionSection is true.

              v1.8.0-rc4.1 (Codex Part A follow-up on the hydration gate):
              extending `personaResolved` to wrap the sections list AND
              ActionSection below — the rc3.1 gate only covered the banner,
              which left a visible layout shift below it for users with
              persisted non-default personas. Now every persona-aware
              region waits for the post-mount persona resolve uniformly. */}
          {!personaResolved ? (
            <div className="space-y-3" aria-hidden="true">
              <div className="h-24 animate-pulse rounded border border-border-dim bg-bg-panel" />
              <div className="h-24 animate-pulse rounded border border-border-dim bg-bg-panel" />
              <div className="h-24 animate-pulse rounded border border-border-dim bg-bg-panel" />
            </div>
          ) : sections.map(({ section, manifests: sectionManifests }) => (
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
              {/* v1.8.0 Phase 5: ModelInfoRawCard as the Calibration section's
                  leading element (Quant persona only). Lazy-fetches the
                  /model_info JSON when the user expands the <details>
                  primitive. The "show me your work" surface for readers who
                  want raw artifact metadata over the QuantBanner's summary. */}
              {section.id === "calibration" ? <ModelInfoRawCard /> : null}
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
              show it.
              v1.8.0-rc4.1 (Codex Part A follow-up): also gate on
              personaResolved so the action strip doesn't flash-in for
              IC Voter users (whose config hides it post-resolve). */}
          {personaResolved && personaConfig.showActionSection ? (
            <ActionSection record={record} setRecord={setRecord} />
          ) : null}
        </div>
      </div>
  );
}
