"""8-pillar diligence scorecard with red/green flag adjustments.

Weights per methodology/04-scorecard-pillars.md:

  Clinical                 20%   "Is the clinical evidence compelling for Phase 3?"
  Regulatory               15%   "Pathway has precedent and manageable risk?"
  Competitive              15%   "Can this asset win meaningful market share?"
  Financial                15%   "Does rNPV justify the capital at risk?"
  Manufacturing            10%   "Commercial scale at acceptable COGS?"
  IP                       10%   "Protects returns through peak sales?"
  Team                     10%   "Can execute and navigate setbacks?"
  Computational            5%    "AI/ML/data assets accelerate development?"

Red flag → recommendation auto-capped at 'cautious' regardless of aggregate.
Green flag → aggregate gets +0.5 each (capped at 10.0).

The 8th (computational) pillar is the methodology's novel framing — no standard
biotech scorecard explicitly prices a sponsor's computational/AI/data infrastructure
as a value driver. We do.
"""

from __future__ import annotations

from ...domain import (
    DiligenceRecord,
    PillarScore,
    ScorecardResult,
)


PILLAR_WEIGHTS: dict[str, float] = {
    "clinical": 0.20,
    "regulatory": 0.15,
    "competitive": 0.15,
    "financial": 0.15,
    "manufacturing": 0.10,
    "ip": 0.10,
    "team": 0.10,
    "computational": 0.05,
}

# Sanity: weights sum to 1.0
assert abs(sum(PILLAR_WEIGHTS.values()) - 1.0) < 1e-9


def _recommend(aggregate: float, has_red_flag: bool) -> str:
    """Map aggregate score to recommendation tier; red flags auto-cap."""
    capped = "cautious" if has_red_flag and aggregate > 4.9 else None

    if aggregate >= 8.0:
        tier = "strong_buy"
    elif aggregate >= 6.5:
        tier = "buy"
    elif aggregate >= 5.0:
        tier = "hold"
    elif aggregate >= 3.5:
        tier = "cautious"
    else:
        tier = "avoid"

    return capped or tier


def compute(record: DiligenceRecord, scorecard_input=None) -> ScorecardResult:
    """Required entrypoint. `scorecard_input` is required for this module —
    we accept it as a kwarg so the route can pass it, but the registry doesn't
    call this directly during introspection (it only invokes `compute(record)`
    for modules with no extra inputs).
    """
    if scorecard_input is None:
        raise ValueError(
            "scorecard requires user-supplied pillar scores (scorecard_input)"
        )

    pillars_input = {
        "clinical": scorecard_input.clinical,
        "regulatory": scorecard_input.regulatory,
        "competitive": scorecard_input.competitive,
        "financial": scorecard_input.financial,
        "manufacturing": scorecard_input.manufacturing,
        "ip": scorecard_input.ip,
        "team": scorecard_input.team,
        "computational": scorecard_input.computational,
    }

    pillars: list[PillarScore] = []
    aggregate = 0.0
    for name, weight in PILLAR_WEIGHTS.items():
        pi = pillars_input[name]
        pillars.append(
            PillarScore(name=name, weight=weight, score=pi.score, rationale=pi.rationale)
        )
        aggregate += weight * pi.score

    # Green flags boost aggregate by +0.5 each (capped at 10.0)
    aggregate += 0.5 * len(scorecard_input.green_flags)
    aggregate = min(10.0, aggregate)

    has_red_flag = bool(scorecard_input.red_flags)
    recommendation = _recommend(aggregate, has_red_flag)

    # Ensure aggregate stays within [1.0, 10.0] for ScorecardResult validation.
    aggregate = max(1.0, min(10.0, round(aggregate, 2)))

    return ScorecardResult(
        pillars=pillars,
        aggregate_score=aggregate,
        recommendation=recommendation,  # type: ignore[arg-type]
        red_flags=list(scorecard_input.red_flags),
        green_flags=list(scorecard_input.green_flags),
    )
