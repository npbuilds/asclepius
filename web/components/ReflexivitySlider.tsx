"use client";

// The hero interactive: drag through capital-position tiers and watch the
// reflexivity multiplier visibly move PoS. This is the single component that
// makes "reflexivity" feel like a real mechanism instead of an abstract claim.
//
// Tinted MAGENTA because reflexivity is the framework's headline differentiator
// — semantically distinct from the cyan flow of base-rate-and-modality math.
//
// v1.7.1: tier table moved to `web/lib/reflexivity-tiers.ts` so the
// HeroBanner (and any future surface) shares a single TypeScript source
// of truth. The Python parity test (`test_reflexivity_parity` in
// `api/tests/test_registry.py`) now grep-asserts that shared module
// against the backend JSON.

import type { CapitalPosition } from "@/lib/types";
import { REFLEXIVITY_TIERS } from "@/lib/reflexivity-tiers";

const TIERS = REFLEXIVITY_TIERS;

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
    <div className="rounded border border-magenta-bright/30 bg-magenta-bright/5 p-3">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-[10px] font-semibold uppercase tracking-[0.2em] text-magenta-bright">
          Reflexivity adjustment
        </h3>
        <span className="font-mono text-[13px] font-bold tabular-nums text-magenta-bright">
          ×{active.multiplier.toFixed(2)}
        </span>
      </div>
      <p className="mt-1.5 font-prose text-[11px] leading-snug text-text-primary">
        Sponsor capital position. Well-capitalized sponsors run better trials
        (larger N, biomarker enrichment, adaptive designs) — a Spence-style
        costly signal capital-constrained sponsors can't credibly emit.
      </p>

      <div className="mt-2.5">
        <input
          type="range"
          min={0}
          max={TIERS.length - 1}
          step={1}
          value={activeIdx === -1 ? 2 : activeIdx}
          onChange={(e) => onChange(TIERS[parseInt(e.target.value, 10)].value)}
          className="w-full accent-magenta-bright"
        />
        <div className="mt-1 flex justify-between font-display text-[8px] uppercase tracking-[0.1em] text-text-dim">
          {TIERS.map((t) => (
            <span
              key={t.value}
              className={t.value === value ? "font-bold text-magenta-bright" : ""}
            >
              {t.label}
            </span>
          ))}
        </div>
      </div>

      <div className="mt-2.5 rounded border border-border-dim bg-bg-panel p-2 font-prose text-[11px] leading-snug text-text-primary">
        <span className="font-bold text-text-bright">{active.label}</span> —
        runway {active.runway}. Applied last in the PoS chain. Empirical:{" "}
        Ma 2025 trial-accrual model (AUC 0.74) shows sponsor + protocol features
        predict structural trial breakdown.
      </div>
    </div>
  );
}
