"""Pre-compute agent outputs for the demo path and seed the cache.

Adagrasib is the worked-example asset shown on the live deploy. Caching its
agent outputs means recruiter clicks return instantly and incur zero API cost.

Usage::

    python scripts/precompute_agent_outputs.py adagrasib            # all agents
    python scripts/precompute_agent_outputs.py adagrasib memo_writer  # one

Run from the api/ directory with the venv active. Requires ANTHROPIC_API_KEY.
The script overwrites the existing cache file for the asset; commit the
result.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make app/ importable when running this file directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain import AssetInput, DiligenceRecord  # noqa: E402
from app.modules.comparables.engine import compute as compute_comparables  # noqa: E402
from app.modules.pos.engine import compute as compute_pos  # noqa: E402
from app.modules.rnpv.engine import compute as compute_rnpv  # noqa: E402
from app.modules.scorecard.engine import compute as compute_scorecard  # noqa: E402
from app.registry import get_registry  # noqa: E402

CACHEABLE_ASSETS: dict[str, dict] = {
    "adagrasib": {
        "asset_input": {
            "asset_name": "adagrasib",
            "sponsor": "Mirati Therapeutics",
            "phase": "phase_2",
            "therapeutic_area": "oncology",
            "modality": "small_molecule",
            "capital_position": "adequate",
            "mechanism": "KRAS G12C inhibitor",
            "target": "KRAS G12C",
            "indication": "NSCLC (2L+, G12C-mutant)",
            "regulatory_designations": ["breakthrough_therapy"],
            "num_competitors": 1,
            "target_validated": True,
            "biomarker_enrichment": True,
        },
        # rNPV inputs MUST match web/app/diligence/[asset]/page.tsx ADAGRASIB_RNPV,
        # otherwise the cached memo references numbers different from those on
        # the live workbench. Phase 1/2 are sunk at the June 2022 cutoff so
        # their costs and timelines are zero.
        "rnpv_inputs": {
            "peak_sales_usd_m": 1200.0,
            "years_to_peak": 5,
            "years_of_exclusivity": 12,
            "cogs_pct": 0.18,
            "wacc": 0.10,
            "dev_cost_phase_1_usd_m": 0.0,
            "dev_cost_phase_2_usd_m": 0.0,
            "dev_cost_phase_3_usd_m": 250.0,
            "launch_cost_usd_m": 150.0,
            "years_per_phase": {
                "phase_1": 0,
                "phase_2": 0,
                "phase_3": 3,
                "regulatory": 1,
            },
        },
        # Scorecard inputs MUST match the ScorecardRadarPanel defaults so the
        # cached memo's aggregate score and pillar discussion line up with what
        # the page actually renders. (Defaults: clinical/regulatory/manufacturing/
        # ip/team 7, competitive/financial 6, computational 5, no flags.)
        "scorecard_input": {
            "clinical": {"score": 7.0},
            "regulatory": {"score": 7.0},
            "competitive": {"score": 6.0},
            "manufacturing": {"score": 7.0},
            "ip": {"score": 7.0},
            "financial": {"score": 6.0},
            "team": {"score": 7.0},
            "computational": {"score": 5.0},
            "red_flags": [],
            "green_flags": [],
        },
    }
}


def build_record(asset_slug: str) -> DiligenceRecord:
    """Compute PoS → rNPV → scorecard → comparables, in order."""
    config = CACHEABLE_ASSETS[asset_slug]
    record = DiligenceRecord(asset=AssetInput(**config["asset_input"]))
    if "rnpv_inputs" in config:
        from app.domain import RnpvInputs

        record.rnpv_inputs = RnpvInputs(**config["rnpv_inputs"])
    record.pos = compute_pos(record)
    record.rnpv = compute_rnpv(record)
    if "scorecard_input" in config:
        from app.modules.scorecard.schemas import ScorecardInput

        record.scorecard = compute_scorecard(
            record, scorecard_input=ScorecardInput(**config["scorecard_input"])
        )
    record.comparables = compute_comparables(record)
    return record


def _seed_invoke(loaded, record):
    """Per-agent seeding logic.

    The Adversary stress-tests memo claims when a memo is available. During
    seeding we look up the already-cached memo for the same asset and pass
    its body via the agent's _live_call extra arg, bypassing the public
    cache-first run() path (since we just deleted that file).
    """
    agent_id = loaded.manifest.id
    if agent_id == "game_theory_adversary":
        registry = get_registry()
        memo_loaded = registry.agents.get("memo_writer")
        memo_body = None
        if memo_loaded is not None:
            slug = record.asset.asset_name.lower().replace(" ", "_")
            memo_path = memo_loaded.path / "cache" / f"{slug}.json"
            if memo_path.exists():
                try:
                    memo_body = json.loads(memo_path.read_text()).get("body_markdown")
                except Exception:
                    pass
        return loaded.instance._live_call(record, memo_body=memo_body)
    return loaded.instance.run(record)


def precompute_for_agent(asset_slug: str, agent_id: str) -> Path:
    """Run one agent against the record, save to cache/<slug>.json.

    Deletes any existing cache file before invoking the agent — otherwise the
    agent's own cache-first logic would short-circuit and just re-serialize
    the stale entry without calling the LLM. This is the only place we need
    to force the cache-miss path.
    """
    registry = get_registry()
    loaded = registry.agents.get(agent_id)
    if loaded is None:
        raise RuntimeError(f"agent {agent_id!r} not registered")
    cache_path = loaded.path / "cache" / f"{asset_slug}.json"
    if cache_path.exists():
        cache_path.unlink()
    record = build_record(asset_slug)
    print(f"  → running {agent_id} for {asset_slug}…", flush=True)
    result = _seed_invoke(loaded, record)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"  ✓ wrote {cache_path}")
    return cache_path


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    asset = argv[0]
    if asset not in CACHEABLE_ASSETS:
        print(f"unknown asset {asset!r}. Known: {list(CACHEABLE_ASSETS)}")
        return 2
    agent_ids = argv[1:]
    if not agent_ids:
        registry = get_registry()
        agent_ids = list(registry.agents.keys())
    print(f"precomputing {asset!r} for {agent_ids}")
    for aid in agent_ids:
        precompute_for_agent(asset, aid)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
