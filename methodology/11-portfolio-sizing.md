# Portfolio Sizing — Kelly + fractional + barbell

The framework's first eleven modules are oriented at single-asset
diligence. v2.0 opens a second audience surface: the biotech fund
manager. The Portfolio Sizing module takes a list of computed
DiligenceRecords, an analyst conviction score per asset, and fund-level
parameters (total capital, Kelly fraction, position cap, position
floor), and returns the recommended position weights.

The math is intentionally well-established — Kelly criterion (Kelly
1956), fractional Kelly (Thorp 1969), and barbell allocation are
investing fundamentals. The interesting work in v2.0 is the
*adaptation* to biotech VC: how do you map rNPV outputs to the b in
f* = (bp - q)/b, and what fraction of Kelly is defensible for
trial-outcome-driven payoffs?

## The math, briefly

For one asset:

1. **Kelly optimal**: `f* = (bp - q) / b`, where:
   - `p` = the framework's reflexivity-adjusted LOA (from the PoS module)
   - `q` = `1 - p`
   - `b` = the conditional-on-success payoff multiple (derivation below)
2. **Fractional Kelly**: `f_frac = max(0, f* × kelly_fraction)`. The
   practitioner default for biotech VC is `kelly_fraction = 0.25`. LOA
   estimates carry standard errors on the order of ±5pp at the
   reflexivity-tier level; full Kelly over-bets on PoS noise.
3. **Conviction-adjusted**: `f_conv = min(1, f_frac × conviction)`,
   where conviction is the analyst's 0.5×–1.5× scaling on the
   framework's numbers.
4. **Barbell cap/floor**: cap at `fund.max_position_pct` (typical 20%),
   floor at `fund.min_position_pct` (typical 2%). Positions below the <!-- parity-allow: fund-config -->
   floor are dropped; positions above the cap are pinned at the cap.

For the portfolio: the per-asset sizings are computed independently
(no covariance term in v2.0 — see "Documented limitations" below) and
aggregated. The output surfaces total deployed pct + dollars, cash
residual, Gini coefficient on weights (concentration metric), and a
probability-weighted expected NPV in $M.

## The biotech-specific payoff multiple

A naive reading would set `b = base_case_rnpv / |downside_loss|`. This
is wrong, and v2.0 caught the wrongness during development: it
under-states b because base_case_rnpv is already probability-weighted
(it's the rNPV — the success-probability times the conditional value).
Plugging that into Kelly double-counts the probability.

The correct biotech-VC formulation:

```
conditional_upside  = base_case_rnpv / LOA      (un-probability-weighted)
cost_basis          = |downside_failed_p3|      (capital at risk on failure)
b                   = (conditional_upside - cost_basis) / cost_basis
```

For adagrasib at the June 2022 cutoff (LOA 16.1%, base_case_rnpv
$516M, downside_failed_p3 -$118M):

- conditional_upside ≈ $516M / 0.161 = $3,205M
- cost_basis = $118M
- b ≈ ($3,205 - $118) / $118 = 26.2× payoff multiple
- Kelly = (26.2 × 0.161 - 0.839) / 26.2 = 3.38 / 26.2 = 0.129
- Fractional × 0.25 = 0.032 = **3.2% of fund** for this asset alone

That's a sensible biotech-VC allocation for a single Phase 2 oncology
asset with BTD + biomarker enrichment + target validation. A
fund-of-five at similar profiles deploys ~15% of fund; the remaining
~85% is cash residual or reserved for follow-on rounds — the barbell
the methodology delivers.

## What the demo on `/portfolio` shows

The page renders a 5-asset cohort (the same kinase inhibitors that
seed the Calibration Dashboard) with interactive conviction sliders
and fund-parameter sliders. Default behavior produces:

| | Adagrasib | Sotorasib | Selpercatinib | Larotrectinib | Encorafenib |
|---|---:|---:|---:|---:|---:|
| Conviction | 1.0 | 0.8 | 1.2 | 1.0 | 0.9 |
| Final weight | 3.0% | 2.4% | 3.6% | 3.0% | 2.7% | <!-- parity-allow: worked-example -->
| Status | rec | rec | rec | rec | rec |

Total deployed ≈ 14.7%; cash residual 85.3%. This is the *barbell*
shape: heavy cash, modest equal-ish positions, no concentration. A
recruiter clicking through the conviction sliders sees how analyst
conviction translates to deployed dollars; clicking through the fund
parameters sees how Kelly fraction and position caps reshape the
allocation.

## Why the framework's recommended sizing is "small"

A recruiter familiar with biotech VC will look at 3% per position and
think: "That's smaller than what real VCs deploy." That observation is
correct, and the methodology owns it explicitly:

1. The framework's reflexivity-adjusted LOA is *conservative*. It
   represents what the BIO base rate + Spence-style signaling-equilibrium
   adjustment + structural multipliers add up to. Real biotech VCs
   typically believe their internal LOA estimate is higher than the
   base rate (otherwise why invest). The gap between the framework's
   LOA and the VC's internal LOA is the *implicit conviction premium*
   — and v2.0 lets the analyst express that explicitly via the
   conviction slider (capped at 1.5× to keep the math defensible).

2. The Kelly fraction is fractional (0.25) precisely *because* the LOA
   is noisy. Full Kelly bets the absolute expected-edge optimum and
   blows up the portfolio on PoS error. Real biotech investors,
   implicitly or explicitly, also use fractional Kelly.

3. Cash residual is the *barbell*. Holding 85% cash is not under-
   investment; it's the optionality reserve for follow-on rounds and
   the dry powder for new opportunities. The framework's recommendation
   matches biotech-VC industry posture; a recommendation of 80%+
   deployed would be the wrong answer.

The disagreement between framework-recommended sizing and what an
investor's gut says to deploy is itself the useful information: it
isolates exactly what *the investor must believe above the framework's
public PoS chain* to justify their actual position size. That's an
auditable input to a portfolio meeting.

## Documented limitations

**No covariance term in v2.0.** Each asset's Kelly is computed
independently. Real portfolio Kelly accounts for correlation between
assets — two oncology kinase inhibitors share systematic biotech risk,
so their joint Kelly is less than the sum of their independent
Kellys. v2.1 will add a correlation-matrix input to the request
schema; v2.0 treats assets as conditionally independent.

**No follow-on capital reserve.** The framework recommends a single
allocation snapshot. In a real fund, ~30-50% of committed capital is
reserved for follow-on rounds in winning assets; only the initial
allocation is sized via Kelly. v2.0 doesn't model the reserve;
analysts should interpret the "cash residual" as a *minimum* —
actual deployable initial capital is the residual minus the reserve.

**No catalyst-timing dimension.** Sizing is treated as a one-shot
decision. Real biotech sizing is staged: initial position, top-up at
positive Phase 3 readout, exit at acquisition. v2.x could expose a
"staged sizing schedule" output that names the next milestone and
the next sizing action. Out of scope for v2.0.

**Expected-value calculation can go negative.** The portfolio
recommendation surface reports an `expected_value_rnpv_usd_m`
computed as `sum(weight × (pos × upside + (1-pos) × downside))`. With
the framework's conservative LOAs and substantial downside-on-failure
scenarios, this number can be negative for individual assets or even
the whole portfolio. That isn't a bug — it tells the investor that
*at the framework's stated probabilities*, the position has negative
expected value, and the sizing recommendation only makes sense if the
investor believes their internal LOA is higher than the framework's
public output. The number is intentionally surfaced rather than
hidden.

## Where this slots in the audience map

| Audience | Surface | Primary tool |
|---|---|---|
| Single-asset diligence (biotech VC associate) | `/diligence/[asset]` | PoS waterfall + rNPV + scorecard + 3 agents |
| Fund-manager portfolio sizing (biotech VC partner) | `/portfolio` | this module |
| Methodology platform reader (recruiter) | `/methodology` | the writeups, including this one |
| Calibration auditor | `/diligence/adagrasib` (Calibration Dashboard panel) + `predictions/` | the v1.5 + v1.6 deliverables |

v2.0 is the audience-expansion the plan flagged as "arguably a
separate product." The plan is right that it expands surface area; the
implementation choice was to slot it in as another registry module so
the architecture stays consistent rather than forking. That keeps the
methodology-platform thesis intact (the same DiligenceRecord →
modules → outputs flow applies; portfolio sizing is just another
output) and preserves the registry pattern's drop-in claim — adding
the 7th module on top of v1.6.1's six was zero edits to any existing
module.

## Cross-references

- [`02-reflexivity-thesis.md`](02-reflexivity-thesis.md) — the LOA the
  Kelly math consumes is reflexivity-adjusted.
- [`03-rnpv-monte-carlo.md`](03-rnpv-monte-carlo.md) — the rNPV outputs
  the payoff multiple is derived from.
- [`08-calibration-dashboard.md`](08-calibration-dashboard.md) — the
  per-capital-position Brier scores are what would ultimately
  re-calibrate the LOAs that drive these position sizes.
- [`00-product-thesis.md`](00-product-thesis.md) — the
  productization-of-methodology thesis that v2.0 audience-expands
  against.
- Archon's `position-sizing` skill — the methodology source for the
  Kelly + fractional + conviction + barbell pattern (private skill
  suite; the public-facing implementation is this module).
