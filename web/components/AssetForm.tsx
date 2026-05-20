"use client";

import type { AssetInput, CapitalPosition, Modality, Phase, RegulatoryDesignation, TherapeuticArea } from "@/lib/types";

const PHASES: Phase[] = ["preclinical", "phase_1", "phase_2", "phase_3", "nda", "approved"];
const TAS: TherapeuticArea[] = [
  "oncology",
  "rare_orphan",
  "cns",
  "metabolic",
  "infectious",
  "cardiovascular",
  "autoimmune",
  "ophthalmology",
  "hematology",
  "respiratory",
  "other",
];
const MODALITIES: Modality[] = [
  "small_molecule",
  "monoclonal_antibody",
  "antibody_drug_conjugate",
  "gene_therapy",
  "cell_therapy_autologous",
  "cell_therapy_allogeneic",
  "mrna",
  "protein",
  "oligonucleotide",
  "peptide",
  "other",
];
const CAPITAL_POSITIONS: CapitalPosition[] = [
  "well_capitalized",
  "adequate",
  "constrained",
  "distressed",
];
const REG_DESIGNATIONS: RegulatoryDesignation[] = [
  "breakthrough_therapy",
  "orphan_drug",
  "fast_track",
  "accelerated_approval",
  "rmat",
  "prime_ema",
];

export function AssetForm({
  value,
  onChange,
}: {
  value: AssetInput;
  onChange: (next: AssetInput) => void;
}) {
  function set<K extends keyof AssetInput>(key: K, v: AssetInput[K]) {
    onChange({ ...value, [key]: v });
  }

  function toggleDesignation(d: RegulatoryDesignation) {
    const has = value.regulatory_designations.includes(d);
    set(
      "regulatory_designations",
      has
        ? value.regulatory_designations.filter((x) => x !== d)
        : [...value.regulatory_designations, d],
    );
  }

  return (
    <div className="space-y-5">
      <Row label="Asset name">
        <input
          className="w-full rounded border border-ink-200 px-3 py-2 text-sm"
          value={value.asset_name}
          onChange={(e) => set("asset_name", e.target.value)}
        />
      </Row>

      <Row label="Sponsor">
        <input
          className="w-full rounded border border-ink-200 px-3 py-2 text-sm"
          value={value.sponsor ?? ""}
          onChange={(e) => set("sponsor", e.target.value || null)}
        />
      </Row>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Row label="Phase">
          <Select
            value={value.phase}
            onChange={(v) => set("phase", v as Phase)}
            options={PHASES}
          />
        </Row>
        <Row label="Therapeutic area">
          <Select
            value={value.therapeutic_area}
            onChange={(v) => set("therapeutic_area", v as TherapeuticArea)}
            options={TAS}
          />
        </Row>
        <Row label="Modality">
          <Select
            value={value.modality}
            onChange={(v) => set("modality", v as Modality)}
            options={MODALITIES}
          />
        </Row>
      </div>

      <Row label="Mechanism">
        <input
          className="w-full rounded border border-ink-200 px-3 py-2 text-sm"
          placeholder="e.g. KRAS G12C inhibitor"
          value={value.mechanism ?? ""}
          onChange={(e) => set("mechanism", e.target.value || null)}
        />
      </Row>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Row label="Target validated by prior approval">
          <Checkbox
            checked={value.target_validated}
            onChange={(v) => set("target_validated", v)}
          />
        </Row>
        <Row label="Biomarker-enriched trial">
          <Checkbox
            checked={value.biomarker_enrichment}
            onChange={(v) => set("biomarker_enrichment", v)}
          />
        </Row>
      </div>

      <Row label={`Direct competitors in this indication: ${value.num_competitors}`}>
        <input
          type="range"
          min={0}
          max={6}
          step={1}
          value={value.num_competitors}
          onChange={(e) => set("num_competitors", parseInt(e.target.value, 10))}
          className="w-full accent-accent-600"
        />
      </Row>

      <Row label="Regulatory designations">
        <div className="flex flex-wrap gap-2">
          {REG_DESIGNATIONS.map((d) => {
            const on = value.regulatory_designations.includes(d);
            return (
              <button
                key={d}
                type="button"
                onClick={() => toggleDesignation(d)}
                className={`rounded-full border px-3 py-1 text-xs ${
                  on
                    ? "border-accent-600 bg-accent-50 text-accent-700"
                    : "border-ink-200 bg-white text-ink-600 hover:bg-ink-50"
                }`}
              >
                {labelFor(d)}
              </button>
            );
          })}
        </div>
      </Row>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="mb-1 text-xs uppercase tracking-wide text-ink-400">
        {label}
      </div>
      {children}
    </label>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: readonly string[];
}) {
  return (
    <select
      className="w-full rounded border border-ink-200 bg-white px-3 py-2 text-sm"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {labelFor(opt)}
        </option>
      ))}
    </select>
  );
}

function Checkbox({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`rounded border px-3 py-1.5 text-xs ${
        checked
          ? "border-good-500 bg-good-500/10 text-good-500"
          : "border-ink-200 bg-white text-ink-600 hover:bg-ink-50"
      }`}
    >
      {checked ? "Yes" : "No"}
    </button>
  );
}

export function labelFor(v: string): string {
  return v.replace(/_/g, " ");
}

export { CAPITAL_POSITIONS };
