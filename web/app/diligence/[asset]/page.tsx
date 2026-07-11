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
import UnresearchedAssetHero from "@/components/UnresearchedAssetHero";
import { getAnalysis, listModules } from "@/lib/api-client";
import {
  ClientDiligenceRecord,
  getPanelFor,
  groupModulesBySection,
  MODULE_LOAD_EVENT,
  type ModuleLoadDetail,
  orderModules,
  type SectionWithManifests,
} from "@/lib/module-registry";
import { getPersonaConfig, type PersonaSection } from "@/lib/persona-config";
import { useCurrentPersona } from "@/lib/use-persona";
import { DEFAULT_RNPV, findStagedAsset } from "@/lib/staged-assets";
import type { AssetInput, ModuleManifest, RnpvInputs } from "@/lib/types";

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
  const isAc225 = assetSlug === "ac-225";

  // Pre-staged asset wiring: each known showcase asset gets its hardcoded
  // AssetInput + RnpvInputs + (optionally) an NCT ID for the PubMedBERT
  // criteria fetch path. Any unknown asset falls through to the blank-
  // form path, which renders an editable form for the analyst persona.
  // Adding a new showcase asset is a 3-step pattern:
  //   1. Define const NAME / NAME_RNPV at the top of the file
  //   2. Add the isName branch here
  //   3. Add the isName === true branch into the framing-paragraph block
  //      further down (for the retrospective / forward / contested label)
  // v1.9: all pre-staged asset DATA (AssetInput + RnpvInputs + NCT ID)
  // now lives in the canonical registry at lib/staged-assets.ts.
  // findStagedAsset returns null for unknown slugs → fall back to a blank
  // form + default rNPV. The framing-paragraph prose further down stays in
  // this page (the registry header documents that the rich per-asset prose
  // lives here, not in the registry).
  const staged = findStagedAsset(assetSlug);
  const stagedAsset: AssetInput =
    staged?.asset ?? blankAsset(decodeURIComponent(params.asset));
  const stagedRnpv: RnpvInputs = staged?.rnpv ?? DEFAULT_RNPV;
  const stagedNctId: string | null = staged?.ml_pos_nct_id ?? null;

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

  // Reload-from-saved: if the URL carries ?analysis_id=<uuid>, hydrate the full
  // record from the saved-analyses store, overriding the staged/blank defaults.
  // Read from window.location (client-only) so we don't need a Suspense
  // boundary. The deterministic module panels recompute identically from the
  // restored asset; agent outputs (memo/adversary) re-run on demand as before.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const analysisId = new URL(window.location.href).searchParams.get(
      "analysis_id",
    );
    if (!analysisId) return;
    let cancelled = false;
    getAnalysis(analysisId)
      .then((detail) => {
        if (cancelled) return;
        const r = detail.record as {
          asset: AssetInput;
          rnpv_inputs?: RnpvInputs;
          pos?: ClientDiligenceRecord["pos"];
          rnpv?: ClientDiligenceRecord["rnpv"];
          scorecard?: ClientDiligenceRecord["scorecard"];
          comparables?: ClientDiligenceRecord["comparables"];
        };
        setRecordState({
          asset: r.asset,
          pos: r.pos ?? null,
          rnpv_inputs: r.rnpv_inputs ?? stagedRnpv,
          rnpv: r.rnpv ?? null,
          scorecard: r.scorecard ?? null,
          comparables: r.comparables ?? null,
          ml_pos: null,
          ml_pos_nct_id: stagedNctId,
          ml_pos_criteria_text: null,
        });
      })
      .catch((e) => {
        // Leave the staged/blank defaults in place on failure (e.g. 403 when
        // the access token is missing, or 404 for a deleted analysis).
        if (!cancelled) console.error("reload saved analysis failed:", e);
      });
    return () => {
      cancelled = true;
    };
    // Run once on mount — the analysis_id is a deep-link param, not reactive.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
  // Any registry-known asset is "staged" — derive from the lookup the page
  // already did rather than re-hardcoding the slug list (which drifts). The
  // per-asset isName booleans below stay only for the framing-prose branch.
  const isStaged = staged !== null;
  const [assetFormOpen, setAssetFormOpen] = useState(!isStaged);

  // v1.7.1: "ready to use" UX for the friend-test "type your own asset" path.
  // A blank custom asset (no sponsor, no mechanism) has no real values to
  // compute the framework against — the modules would render real-looking but
  // meaningless numbers from the schema defaults (phase_2 / oncology /
  // small_molecule / adequate). Detect this state and switch the page from
  // "full workbench" to "focused research hero" — Auto-Diligence as the
  // page's centerpiece, manual entry as a collapsed alternative. Once
  // sponsor + mechanism are populated (via Auto-Diligence apply or manual
  // edit), the predicate flips false and the full workbench renders.
  const isUnresearched =
    !isStaged && !record.asset.sponsor && !record.asset.mechanism;

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

  // v1.8.0: module load progress tracking. Each panel emits start/done/error
  // events on window via `emitModuleLoad`; we tally them here to drive a
  // small "computing… 2/6" chip in the page header. `started` is the
  // denominator (only count modules that have actually begun fetching;
  // hidden-by-persona panels never fire) and `done` is the numerator.
  // Resets implicitly when the user navigates to a new asset (component
  // remounts).
  const [moduleLoadState, setModuleLoadState] = useState<
    Map<string, "loading" | "done" | "error">
  >(new Map());
  useEffect(() => {
    function onLoad(e: Event) {
      const detail = (e as CustomEvent<ModuleLoadDetail>).detail;
      if (!detail) return;
      setModuleLoadState((prev) => {
        const next = new Map(prev);
        next.set(
          detail.moduleId,
          detail.state === "start"
            ? "loading"
            : detail.state === "done"
              ? "done"
              : "error",
        );
        return next;
      });
    }
    window.addEventListener(MODULE_LOAD_EVENT, onLoad);
    return () => window.removeEventListener(MODULE_LOAD_EVENT, onLoad);
  }, []);

  const totalStarted = moduleLoadState.size;
  const totalDone = Array.from(moduleLoadState.values()).filter(
    (v) => v === "done" || v === "error",
  ).length;
  const isComputing = totalStarted > 0 && totalDone < totalStarted;

  function updateAsset(asset: AssetInput) {
    setRecord({ asset });
  }

  // v1.7.1: ready-to-use empty-state. When `isUnresearched` is true the page
  // renders a focused research hero instead of the full workbench — see the
  // predicate definition above and UnresearchedAssetHero.tsx header for the
  // full rationale. This early return keeps the unresearched layout
  // visually minimal (header + hero only) and avoids 200+ lines of
  // workbench JSX evaluating against meaningless schema-default inputs.
  if (isUnresearched) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-8">
        <header className="mb-6">
          <div className="font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
            ── Diligence workbench ──
          </div>
          <h1 className="mt-1 font-display text-xl font-bold uppercase leading-[1.15] tracking-[0.04em] text-text-bright sm:text-2xl">
            {record.asset.asset_name}
            <span className="ml-2.5 font-body text-[13px] font-normal normal-case tracking-normal text-amber-bright">
              · unresearched
            </span>
          </h1>
        </header>
        <UnresearchedAssetHero
          record={record}
          setRecord={setRecord}
          onAssetChange={updateAsset}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-4">
      <header className="mb-4">
        <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.2em] text-text-dim">
          <span>── Diligence workbench ──</span>
          {/* v1.8.0: per-module compute progress chip. Surfaces "computing…
              N/M" while any panel is still in flight, then quietly switches
              to "● ready" for ~one-second after the last module resolves
              (the steady-state isn't rendered to keep header noise low).
              The chip lives in the header line so it's eye-anchored to the
              workbench label without competing with the asset name below. */}
          {isComputing ? (
            <span className="inline-flex items-center gap-1 rounded border border-cyan-bright/30 bg-cyan-bright/5 px-1.5 py-0.5 normal-case text-[10px] tracking-normal text-cyan-bright">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-bright" />
              computing… {totalDone}/{totalStarted}
            </span>
          ) : null}
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
            <strong className="text-text-bright">Second-generation competitor example.</strong>{" "}
            Divarasib (Roche) is a covalent second-gen KRAS G12C inhibitor in a
            Phase 3 head-to-head (NCT06497556) vs sotorasib/adagrasib. A clean
            test of the framework on a well-capitalized sponsor in a competitive,
            target-validated field.
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
            <strong className="text-text-bright">Autoimmune biologic example.</strong>{" "}
            Phase 3 ATLAS-UC (NCT06430879) and ATLAS-CD trials ongoing for
            ulcerative colitis and Crohn&apos;s. Merck-sponsored after the April
            2023 Prometheus acquisition ($10.8B). Anti-TL1A is a novel target
            class — no anti-TL1A asset has been FDA-approved yet (Roivant&apos;s
            parallel program is also in Phase 3). Exercises the framework on
            the new autoimmune-biologic cohort.
          </p>
        ) : isAc225 ? (
          <p className="mt-2 max-w-3xl font-prose text-[13px] text-text-primary">
            <strong className="text-text-bright">Frontier case study.</strong>{" "}
            An illustrative Actinium-225 alpha-emitter from a capital-constrained
            junior — the asset behind the{" "}
            <a href="/showcase" className="underline hover:text-cyan-bright">
              /showcase
            </a>{" "}
            walkthrough. It exercises both path-dependencies at once: the
            reflexivity multiplier (constrained capital) and the supply
            constraint (severe isotope supply — a PoS multiplier{" "}
            <em>and</em> a peak-sales ceiling in rNPV), plus the curated
            radiopharmaceutical comp cohort. Not a specific company&apos;s drug;
            a representative frontier exemplar.
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
              (Phase 3 second-gen G12C).
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
