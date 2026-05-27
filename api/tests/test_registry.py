"""Registry tests — discovery, manifest validation, and end-to-end module surface."""

from __future__ import annotations

from app.registry import ModuleManifest, get_registry, reset_registry_for_tests


def setup_module(_mod) -> None:
    reset_registry_for_tests()


def test_data_sources_discovered() -> None:
    reg = get_registry()
    # v1 ships five cited data sources (four reference JSONs + EDGAR shim)
    assert "bio_base_rates" in reg.data_sources
    assert "modality_multipliers" in reg.data_sources
    assert "reflexivity_adjustments" in reg.data_sources
    assert "wacc_benchmarks" in reg.data_sources
    assert "edgar_filings" in reg.data_sources


def test_modules_discovered() -> None:
    reg = get_registry()
    assert "pos" in reg.modules
    assert "rnpv" in reg.modules
    assert "scorecard" in reg.modules
    assert "comparables" in reg.modules


def test_edgar_shim_returns_curated_data() -> None:
    reg = get_registry()
    edgar = reg.data_sources["edgar_filings"]
    result = edgar.fetch({"sponsor": "Mirati Therapeutics"})
    assert "cash_and_equivalents_usd_m" in result
    assert result["cash_and_equivalents_usd_m"] == 890


def test_edgar_shim_unknown_sponsor_returns_error() -> None:
    reg = get_registry()
    edgar = reg.data_sources["edgar_filings"]
    result = edgar.fetch({"sponsor": "Acme Bio"})
    assert "error" in result
    assert "available_sponsors" in result


def test_reflexivity_parity_between_backend_json_and_frontend_constants() -> None:
    """Reflexivity multipliers are duplicated between the backend JSON
    (api/app/data/reflexivity_adjustments.json — the source of truth) and a
    shared frontend constants module (web/lib/reflexivity-tiers.ts — imported
    by ReflexivitySlider, HeroBanner, and any future consumer). If they drift,
    the UI will silently lie about what the PoS engine is computing. This
    test grep-asserts parity.

    v1.7.1: the parity target moved from ReflexivitySlider.tsx to the new
    lib/reflexivity-tiers.ts module after v1.7.0 introduced banner-stats.ts
    with a duplicate (drifting) table. Consolidating into one module means
    one grep target instead of chasing every new consumer.

    If this test fails: either update web/lib/reflexivity-tiers.ts's
    REFLEXIVITY_TIERS array to match reflexivity_adjustments.json, or
    vice versa.
    """
    import json
    import re
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    backend_json = repo_root / "api" / "app" / "data" / "reflexivity_adjustments.json"
    frontend_ts = repo_root / "web" / "lib" / "reflexivity-tiers.ts"

    # If the web/ directory doesn't exist yet (or isn't on this checkout),
    # skip rather than fail — backend tests shouldn't be blocked on frontend.
    if not frontend_ts.exists():
        return

    backend = {
        a["capital_position"]: a["multiplier"]
        for a in json.loads(backend_json.read_text())["adjustments"]
    }

    # Parse REFLEXIVITY_TIERS entries from the TS with a simple regex.
    # Same shape as the TSX-era table but in a module-level array literal:
    #   { value: "distressed", label: "Distressed", multiplier: 0.78, ... }
    ts = frontend_ts.read_text()
    pattern = re.compile(
        r'value:\s*"(\w+)".*?multiplier:\s*([\d.]+)',
        re.DOTALL,
    )
    frontend = {m.group(1): float(m.group(2)) for m in pattern.finditer(ts)}

    assert frontend, "Could not parse REFLEXIVITY_TIERS from reflexivity-tiers.ts"
    assert set(frontend.keys()) == set(backend.keys()), (
        f"capital_position keys diverged. backend={sorted(backend)}, "
        f"frontend={sorted(frontend)}"
    )
    for k, backend_mult in backend.items():
        front_mult = frontend[k]
        assert abs(front_mult - backend_mult) < 1e-6, (
            f"reflexivity multiplier for '{k}' drifted: "
            f"backend JSON has {backend_mult}, frontend has {front_mult}"
        )


def test_module_manifests_valid() -> None:
    """Every loaded module must have a well-formed manifest."""
    reg = get_registry()
    for module_id, loaded in reg.modules.items():
        assert isinstance(loaded.manifest, ModuleManifest)
        assert loaded.manifest.id == module_id
        assert loaded.manifest.outputs, f"{module_id} declares no outputs"


def test_list_modules_returns_serializable_payload() -> None:
    reg = get_registry()
    payload = reg.list_modules()
    assert isinstance(payload, list)
    for m in payload:
        assert "id" in m and "version" in m and "inputs" in m and "outputs" in m


def test_pos_module_has_router() -> None:
    reg = get_registry()
    assert reg.modules["pos"].router is not None


def test_rnpv_module_has_router() -> None:
    reg = get_registry()
    assert reg.modules["rnpv"].router is not None


def test_module_deps_reference_real_data_sources() -> None:
    """Every declared dep should resolve to a loaded data source or module."""
    reg = get_registry()
    known = set(reg.data_sources.keys()) | set(reg.modules.keys())
    for module_id, loaded in reg.modules.items():
        for dep in loaded.manifest.deps:
            assert dep in known, (
                f"module {module_id} declares unknown dep '{dep}'"
            )
