// Shared reflexivity tier constants — the single TypeScript source of truth
// for the four capital-position tiers and their PoS multipliers.
//
// Why this module exists:
//   - v1.5.x mirrored the multipliers in `web/components/ReflexivitySlider.tsx`
//     with a NOTE comment + a Python parity test in
//     `api/tests/test_registry.py::test_reflexivity_parity_between_backend_json_and_frontend_slider`
//     that grep-asserts the slider stays in sync with the backend JSON
//     (api/app/data/reflexivity_adjustments.json).
//   - v1.7.0 introduced `web/lib/banner-stats.ts` which duplicated the same
//     values for the HeroBanner stat grid. That duplicate silently used
//     `0.72` for the distressed tier (the JSON's `range_low`) instead of
//     the canonical `multiplier` `0.78`. The parity test only covered the
//     slider, so the drift shipped without a failure signal.
//
// This module is the consolidation: every TypeScript surface that needs
// reflexivity multipliers imports from here. The Python parity test now
// guards THIS file (one grep target) instead of N consumer files.
//
// IMPORTANT: The numeric multipliers below must mirror the `multiplier`
// field (not `range_low` / `range_high`) of every adjustment row in
// `api/app/data/reflexivity_adjustments.json`. The parity test fails
// loud if they drift.

import type { CapitalPosition } from "./types";

export interface ReflexivityTier {
  value: CapitalPosition;
  // Display label for both the slider tier markers and banner display.
  label: string;
  // Numeric multiplier applied by the backend PoS engine.
  multiplier: number;
  // Short runway band used in the slider's tier explainer.
  runway: string;
  // Uppercase token used by the HeroBanner's compact "tier" column.
  // Kept separate from `label` because the slider uses "Well capitalized"
  // (sentence case) and the banner uses "WELL CAPITALIZED" (caps for
  // mono-typography contrast); deriving via toUpperCase() would be brittle
  // for multi-word tiers.
  bannerTier: string;
}

export const REFLEXIVITY_TIERS: ReflexivityTier[] = [
  {
    value: "distressed",
    label: "Distressed",
    multiplier: 0.78,
    runway: "<6 mo",
    bannerTier: "DISTRESSED",
  },
  {
    value: "constrained",
    label: "Constrained",
    multiplier: 0.88,
    runway: "6–12 mo",
    bannerTier: "CONSTRAINED",
  },
  {
    value: "adequate",
    label: "Adequate",
    multiplier: 1.0,
    runway: "12–24 mo",
    bannerTier: "ADEQUATE",
  },
  {
    value: "well_capitalized",
    label: "Well capitalized",
    multiplier: 1.08,
    runway: "≥24 mo",
    bannerTier: "WELL CAPITALIZED",
  },
];

// Lookup by CapitalPosition for O(1) access (the banner needs this per
// render; the slider doesn't care because it iterates the array).
export const REFLEXIVITY_TIER_BY_VALUE: Record<CapitalPosition, ReflexivityTier> = Object.fromEntries(
  REFLEXIVITY_TIERS.map((t) => [t.value, t]),
) as Record<CapitalPosition, ReflexivityTier>;

// Convenience: formatted multiplier string ("×1.08") for the banner.
export function formatReflexivityMultiplier(tier: ReflexivityTier): string {
  return `×${tier.multiplier.toFixed(2)}`;
}
