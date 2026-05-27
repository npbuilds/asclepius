// Pure derivers for the HeroBanner stat grid.
//
// Each function takes a slice of ClientDiligenceRecord and returns a
// display-ready string + a status flag the banner uses for skeleton vs
// populated states. No fetching here — the data either is or isn't in
// the record yet; the page-level orchestrator handles the fetches.
//
// v1.7.0: introduced with the reader-journey IA redesign. The banner is
// the "30-second read" surface that answers "should I keep reading?",
// per equity-research convention (Buy/Hold/Sell + target-price range +
// catalyst on page 1). See docs/ia-redesign-notes.md for the research
// + decision rationale, and methodology/00-product-thesis.md for the
// public-facing summary.

import {
  REFLEXIVITY_TIER_BY_VALUE,
  formatReflexivityMultiplier,
} from "./reflexivity-tiers";
import type { Recommendation } from "./types";
import type { ClientDiligenceRecord } from "./module-registry";

// ---------------------------------------------------------------------------
// Recommendation chip
// ---------------------------------------------------------------------------

export interface RecommendationChip {
  label: string;
  tone: "positive" | "neutral" | "cautious" | "negative" | "pending";
  // Short qualifier suffixing the recommendation, e.g. "price-conditioned" for
  // a hold. Kept stable across renders so it doesn't visually flicker.
  qualifier: string | null;
}

const RECOMMENDATION_CHIPS: Record<Recommendation, RecommendationChip> = {
  strong_buy: { label: "STRONG BUY", tone: "positive", qualifier: null },
  buy: { label: "BUY", tone: "positive", qualifier: null },
  hold: { label: "HOLD", tone: "neutral", qualifier: "price-conditioned" },
  cautious: { label: "CAUTIOUS", tone: "cautious", qualifier: null },
  avoid: { label: "AVOID", tone: "negative", qualifier: null },
};

export function recommendationChip(
  record: ClientDiligenceRecord,
): RecommendationChip {
  if (!record.scorecard) {
    return { label: "PENDING", tone: "pending", qualifier: "scorecard loading" };
  }
  return RECOMMENDATION_CHIPS[record.scorecard.recommendation];
}

// ---------------------------------------------------------------------------
// rNPV — base case + Monte Carlo range
// ---------------------------------------------------------------------------

export interface RnpvDisplay {
  base: string;        // "$570M" or "$—M"
  range: string | null; // "$440-680M" or null when MC hasn't run
  isPending: boolean;
}

function formatUsdM(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "$—M";
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(2)}B`;
  }
  return `$${Math.round(value)}M`;
}

export function rnpvDisplay(record: ClientDiligenceRecord): RnpvDisplay {
  const r = record.rnpv;
  if (!r) {
    return { base: "$—M", range: null, isPending: true };
  }
  const p25 = r.monte_carlo_p25_usd_m;
  const p75 = r.monte_carlo_p75_usd_m;
  const range =
    p25 != null && p75 != null
      ? `${formatUsdM(p25)}–${formatUsdM(p75)}`
      : null;
  return {
    base: formatUsdM(r.base_case_usd_m),
    range,
    isPending: false,
  };
}

// ---------------------------------------------------------------------------
// LOA — final + microsplit (BIO base → reflexivity-adjusted → ML)
// ---------------------------------------------------------------------------

export interface LoaDisplay {
  final: string; // "13.2%" or "—%"
  microsplit: string | null; // "BIO 7.9% → Reflexivity 13.2% → ML 23.6%" or null
  isPending: boolean;
}

function pct(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return "—%";
  return `${(value * 100).toFixed(digits)}%`;
}

export function loaDisplay(record: ClientDiligenceRecord): LoaDisplay {
  if (!record.pos) {
    return { final: "—%", microsplit: null, isPending: true };
  }
  const final = pct(record.pos.final_loa);
  const baseRate = pct(record.pos.base_rate);
  const reflex = pct(record.pos.final_loa);
  // The "BIO → Reflexivity → ML" microsplit shows when ALL three numbers
  // are available. ML PoS is fetched separately and may settle after PoS
  // — until then we show the abbreviated "BIO → Reflexivity" line so the
  // user sees progressive enhancement rather than a long stall.
  if (record.ml_pos) {
    const ml = pct(record.ml_pos.predicted_pos);
    return {
      final,
      microsplit: `BIO ${baseRate} → Reflexivity ${reflex} → ML ${ml}`,
      isPending: false,
    };
  }
  return {
    final,
    microsplit: `BIO ${baseRate} → Reflexivity ${reflex} → ML —%`,
    isPending: false,
  };
}

// ---------------------------------------------------------------------------
// Reflexivity tier — sourced directly from asset.capital_position
// ---------------------------------------------------------------------------

export interface ReflexivityDisplay {
  tier: string;       // "ADEQUATE"
  multiplier: string; // "×1.00"
}

// v1.7.1: tier values pulled from lib/reflexivity-tiers.ts (the shared
// TypeScript source-of-truth that mirrors api/app/data/reflexivity_adjustments.json
// and is guarded by the test_reflexivity_parity Python test). Pre-v1.7.1
// this function had its own table that silently used `×0.72` for the
// distressed tier (the JSON's range_low) instead of the canonical
// multiplier `×0.78` — a drift the parity test couldn't catch because
// it only covered ReflexivitySlider.tsx.
export function reflexivityDisplay(
  record: ClientDiligenceRecord,
): ReflexivityDisplay {
  const tier = REFLEXIVITY_TIER_BY_VALUE[record.asset.capital_position];
  return {
    tier: tier.bannerTier,
    multiplier: formatReflexivityMultiplier(tier),
  };
}

// ---------------------------------------------------------------------------
// Catalyst — per-asset map, fallback to a neutral string for unknown assets
// ---------------------------------------------------------------------------

// Keyed by lowercased asset_name. Hand-curated; adding a new entry is the
// honest way to surface a catalyst (vs. trying to auto-derive from CT.gov,
// which would lag real news cycles by weeks and isn't worth the
// engineering for a portfolio tool).
const CATALYSTS: Record<string, string> = {
  adagrasib: "KRYSTAL-12 Ph3 readout — post-cutoff for backtest",
};

export function catalystLine(record: ClientDiligenceRecord): string {
  const key = record.asset.asset_name.trim().toLowerCase();
  return CATALYSTS[key] ?? "No catalyst configured for this asset";
}

// ---------------------------------------------------------------------------
// Subtitle — asset identity at a glance (phase · TA · indication or modality)
// ---------------------------------------------------------------------------

const PHASE_LABELS: Record<string, string> = {
  preclinical: "Preclinical",
  phase_1: "Phase 1",
  phase_2: "Phase 2",
  phase_3: "Phase 3",
  nda: "NDA",
  approved: "Approved",
};

export function subtitleLine(record: ClientDiligenceRecord): string {
  const asset = record.asset;
  const parts: string[] = [];
  if (asset.sponsor) parts.push(asset.sponsor);
  parts.push(PHASE_LABELS[asset.phase] ?? asset.phase);
  if (asset.indication) {
    parts.push(asset.indication);
  } else {
    // Fall back to TA + modality for assets the user typed in
    parts.push(asset.therapeutic_area);
  }
  return parts.join(" · ");
}
