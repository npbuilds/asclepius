"use client";

// The hero interactive: drag through capital-position tiers and watch the
// reflexivity multiplier visibly move PoS. This is the single component that
// makes "reflexivity" feel like a real mechanism instead of an abstract claim.
//
// NOTE: The multipliers below mirror api/app/data/reflexivity_adjustments.json.
// `test_reflexivity_parity` in api/tests/test_registry.py asserts they stay in
// sync — if you change one side, update the other and the test will pass again.

import type { CapitalPosition } from "@/lib/types";

const TIERS: { value: CapitalPosition; label: string; multiplier: number; runway: string }[] = [
  { value: "distressed", label: "Distressed", multiplier: 0.78, runway: "<6 mo" },
  { value: "constrained", label: "Constrained", multiplier: 0.88, runway: "6–12 mo" },
  { value: "adequate", label: "Adequate", multiplier: 1.0, runway: "12–24 mo" },
  { value: "well_capitalized", label: "Well capitalized", multiplier: 1.08, runway: "≥24 mo" },
];

export function ReflexivitySlider({
  value,
  onChange,
}: {
  value: CapitalPosition;
  onChange: (next: CapitalPosition) => void;
}) {
  const activeIdx = TIERS.findIndex((t) => t.value === value);
  const active = TIERS[activeIdx] ?? TIERS[2];

  return (
    <div className="rounded border border-cyan-bright/30 bg-gradient-to-br from-accent-50 to-white p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-text-bright">Reflexivity adjustment</h3>
        <span className="font-mono text-sm tabular-nums text-cyan-bright">
          ×{active.multiplier.toFixed(2)}
        </span>
      </div>
      <p className="mt-1 text-xs text-text-primary">
        Sponsor capital position. Well-capitalized sponsors run better trials
        (larger N, biomarker enrichment, adaptive designs) — a Spence-style
        costly signal capital-constrained sponsors can't credibly emit.
      </p>

      <div className="mt-4">
        <input
          type="range"
          min={0}
          max={TIERS.length - 1}
          step={1}
          value={activeIdx === -1 ? 2 : activeIdx}
          onChange={(e) => onChange(TIERS[parseInt(e.target.value, 10)].value)}
          className="w-full accent-cyan-bright"
        />
        <div className="mt-2 flex justify-between text-[10px] uppercase tracking-wider text-text-dim">
          {TIERS.map((t) => (
            <span
              key={t.value}
              className={t.value === value ? "font-medium text-cyan-bright" : ""}
            >
              {t.label}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-4 rounded border border-border-dim bg-bg-panel p-3 text-xs text-text-primary">
        <span className="font-medium text-text-bright">{active.label}</span> —
        runway {active.runway}. Reflexivity multiplier applied last in the PoS
        chain. Empirical backing: Ma 2025 trial-accrual model (AUC 0.74) shows
        sponsor + protocol features predict structural trial breakdown.
      </div>
    </div>
  );
}
