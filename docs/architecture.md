# Architecture

The contract for adding a new module, data source, runtime agent, or exporter to Asclepius without touching the core.

## The single rule

The `DiligenceRecord` pydantic model in [`api/app/domain.py`](../api/app/domain.py) is the only thing every module reads from and writes to. Phase, indication, modality, capital position, PoS waterfall, rNPV outputs, scorecard pillars, comparables — all fields on one schema with strict types.

If your extension needs state that isn't on `DiligenceRecord`, it doesn't exist. Either it's a real domain concept that should be added to the model (with a schema-version bump and migration discipline) or it's implementation detail that should stay inside your module. There is no third option.

This single rule is what makes everything else modular. Every module is a pure function over a slice of the record. There are no globals, no shared mutable state, no cross-module coupling outside the record.

## The four registries

Asclepius has four auto-discovered registries. Each is a folder under `api/app/`; dropping a folder with the right marker files registers your extension at server startup.

| Registry | Folder | Marker | Auto-discovery |
|---|---|---|---|
| Data sources | `api/app/data_sources/` | A class subclassing `DataSource` | Imported on startup; `id` attribute keys the registry |
| Analysis modules | `api/app/modules/<id>/` | `manifest.json` + `engine.py` | FastAPI mounts the `routes.py` router; `/api/modules` endpoint exposes the manifest |
| Runtime agents | `api/app/agents/<id>/` | `manifest.json` + `agent.py` (v1.1+) | Loaded but not invoked until a UI button triggers them |
| Exporters | `api/app/exporters/` | A class subclassing `Exporter` (v1.1+) | Imported on startup |

The discovery walker is in [`api/app/registry.py`](../api/app/registry.py). It walks each folder once at startup, validates the marker files, and registers the extension. Bad imports are logged and skipped — one broken module doesn't crash the server.

## Adding a new data source

Data sources wrap reference data or external APIs into a uniform `fetch(query) -> dict` interface. The v1 ships 5 data sources; adding a sixth is a single file.

### Steps

1. Create `api/app/data_sources/<your_source>.py`.
2. Subclass `DataSource` from `app.registry`. Set the class attributes `id` (unique string, snake_case) and `provides_fields` (tuple of field-name strings).
3. Implement `__init__` (load reference data, set up clients) and `fetch(query: dict) -> dict`.
4. Add a test under `api/tests/` that imports the source and exercises `fetch()` with realistic query shapes.

### Example skeleton

```python
# api/app/data_sources/my_source.py
from __future__ import annotations
from typing import Any
from ..registry import DataSource


class MySource(DataSource):
    id = "my_source"
    provides_fields = ("my_field", "my_other_field")

    def __init__(self) -> None:
        # Load reference data, initialize HTTP clients, etc.
        ...

    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        # Return a dict whose keys are a subset of provides_fields.
        # The query dict shape is documented per source — there is no
        # global contract beyond returning a dict.
        return {
            "my_field": ...,
            "my_other_field": ...,
            "source": "<citation string for provenance>",
        }
```

### Conventions

- **Cite provenance.** Every returned dict should include a `source` key with the citation. Modules consuming the data source will propagate this into their audit trail.
- **Cache loads.** If the source reads JSON or hits an external API, cache the loaded data per-instance (the registry instantiates each source once at startup).
- **Fail-fast on bad queries.** If the query is missing required keys, raise `ValueError`. Don't return silent defaults.
- **Filename is the module name, not the source id.** `my_source.py` is imported but the registry keys by the class's `id` attribute. Keep them consistent for readability.

## Adding a new analysis module

Analysis modules are the framework's primary unit of extension. They read from `DiligenceRecord`, do some computation, and write to a specific result field on the record.

### Required structure

```
api/app/modules/<your_module>/
  manifest.json    # registry metadata
  engine.py        # the compute() function — your math
  schemas.py       # request/response pydantic schemas for the HTTP surface
  routes.py        # FastAPI router (auto-mounted)
  tests/
    test_engine.py
    test_routes.py (optional)
```

### `manifest.json` schema

```json
{
  "id": "your_module",
  "name": "Human-readable name",
  "version": "0.1.0",
  "description": "One paragraph explaining what this module computes and why.",
  "inputs": ["asset.phase", "asset.therapeutic_area", "pos.final_loa"],
  "outputs": ["your_field"],
  "deps": ["bio_base_rates"]
}
```

- `id` must match the folder name and be snake_case.
- `inputs` lists `DiligenceRecord` field paths the module reads (dot-notation).
- `outputs` lists `DiligenceRecord` field paths the module writes. Usually one field, named after the module id.
- `deps` lists data-source ids and module ids this module depends on. The registry uses this for validation; bad deps fail at startup, not at runtime.

### `engine.py` — the compute function

Every module must export a `compute(record: DiligenceRecord) -> SomeResult` function. The function:

- Takes the full record as input.
- Reads from data sources via `registry.get_registry().data_sources[<id>]`.
- Returns a pydantic model whose type matches the `outputs` field declared in the manifest.

The function must be pure: no globals, no I/O outside data-source calls, no random state without an explicit seed.

```python
# api/app/modules/your_module/engine.py
from ...domain import DiligenceRecord, YourResult
from ...registry import get_registry


def compute(record: DiligenceRecord) -> YourResult:
    reg = get_registry()
    bio = reg.data_sources["bio_base_rates"]
    base = bio.fetch({"therapeutic_area": record.asset.therapeutic_area.value})
    # ... your math ...
    return YourResult(...)
```

### `schemas.py` — HTTP surface

```python
# api/app/modules/your_module/schemas.py
from pydantic import BaseModel, ConfigDict
from ...domain import AssetInput, YourResult


class YourRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset: AssetInput
    # Add any module-specific inputs here.


class YourResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    your_field: YourResult
```

### `routes.py` — FastAPI router

```python
# api/app/modules/your_module/routes.py
from fastapi import APIRouter
from ...domain import DiligenceRecord
from .engine import compute
from .schemas import YourRequest, YourResponse

router = APIRouter(prefix="/api/modules/your_module", tags=["your_module"])


@router.post("", response_model=YourResponse)
def run_your_module(req: YourRequest) -> YourResponse:
    record = DiligenceRecord(asset=req.asset)
    result = compute(record)
    return YourResponse(your_field=result)
```

The router is auto-mounted by `app/main.py`. No need to register it manually.

### Tests

Every module must have at least:

1. A unit test that exercises `compute()` with a synthetic `DiligenceRecord`.
2. (Optional but recommended) An integration test that POSTs to the route and asserts the response shape.

The framework's pytest config (`api/pyproject.toml`) auto-discovers tests under `app/modules/<id>/tests/` and `api/tests/`.

### Frontend mirror

If your module produces output that should render on the diligence dashboard, you also need:

1. **TypeScript type** mirroring your `YourResult` pydantic model in [`web/lib/types.ts`](../web/lib/types.ts).
2. **API client function** in [`web/lib/api-client.ts`](../web/lib/api-client.ts).
3. **React panel component** at `web/components/modules/<your_module>/<YourPanel>.tsx`. Take `ModulePanelProps` as the prop shape (record + setRecord).
4. **Register the panel** in [`web/lib/module-registry.ts`](../web/lib/module-registry.ts) — three lines mapping the module id to the dynamic import.

The 3-line frontend register is the one place where adding a module requires touching a core file. This is a Next.js constraint: dynamic imports must be statically analyzable, so true filesystem discovery requires a build-time codegen step the framework deliberately doesn't have. We accept the 3-line edit; it is the only edit needed.

## Adding a new runtime agent (v1.1+)

Agents are LLM-powered components that load Claude skills and run them against a `DiligenceRecord`. The interface is scaffolded in v1; agents themselves ship in v1.1.

### Required structure

```
api/app/agents/<your_agent>/
  manifest.json    # registry metadata
  agent.py         # the Agent class implementing BaseAgent
```

### `manifest.json` schema

```json
{
  "id": "your_agent",
  "name": "Human-readable name",
  "version": "0.1.0",
  "description": "What this agent does in one paragraph.",
  "skill_loadout": [
    "research/spelunker",
    "research/source-triangulator"
  ],
  "trigger_label": "Run Your Agent",
  "input_fields": ["asset.asset_name"],
  "output_fields": ["pos", "rnpv_inputs"]
}
```

- `skill_loadout` lists skill paths relative to `ASCLEPIUS_SKILLS_DIR` (set in `.env`).
- `trigger_label` is the UI button label.
- `input_fields` / `output_fields` are documented `DiligenceRecord` paths the agent reads from and writes to.

### `agent.py` — the Agent class

```python
# api/app/agents/your_agent/agent.py
from typing import Any
from ...agents.base import BaseAgent
from ...domain import DiligenceRecord


class Agent(BaseAgent):
    id = "your_agent"

    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        # Load skills, run the agent loop, return a dict whose keys match
        # the manifest's output_fields. The caller merges onto the record.
        ...
        return {"pos": ..., "rnpv_inputs": ...}
```

### v1.1 planned agents

- **`auto_diligence`** — spelunker-powered. Asset name → autofilled PoS/rNPV inputs with citations.
- **`memo_writer`** — investment-memo-writer skill. DiligenceRecord → 2-3 page narrative memo.
- **`game_theory_adversary`** — signaling-screening + auction-theory + bayesian-persuasion. DiligenceRecord → devil's-advocate critique.

## Adding a new exporter (v1.1+)

Exporters serialize a `DiligenceRecord` into a specific output format (PDF memo, JSON, Excel rNPV model). Same auto-discovery pattern as data sources but in `api/app/exporters/`.

```python
# api/app/exporters/your_exporter.py
from ..exporters.base import Exporter
from ..domain import DiligenceRecord


class YourExporter(Exporter):
    id = "your_exporter"
    file_extension = "pdf"
    mime_type = "application/pdf"

    def export(self, record: DiligenceRecord) -> bytes:
        # Return the file bytes.
        ...
```

## What NOT to add to the core

Deliberate non-features that protect modularity:

- **Cross-module event bus** — modules should not signal each other. If module A needs module B's output, declare it in `deps` and read from the record.
- **Module-to-module RPC** — same reason. Use the record.
- **Shared state outside `DiligenceRecord`** — globals, singletons, application-state managers. Every piece of state must live on the record or inside one module's `__init__` data.
- **Hot reload / dynamic plugin loading at runtime** — Python's import system is sufficient. Drop a folder, restart the server.
- **External plugin marketplace** — interesting for v3+; out of scope.
- **Dependency-graph resolution between modules** — the simple linear `deps` field is enough for v1. If you find yourself wanting a real DAG, the right move is probably to merge two modules instead.
- **Multi-tenant module isolation** — Asclepius is currently single-tenant. Multi-tenancy is a different architectural commitment.

## Testing requirements

Every new extension must include:

1. **Unit test** for the engine/agent/exporter logic.
2. **Manifest validation test** (for modules and agents — covered by the existing `test_registry.py` if the manifest is well-formed).
3. **Citation propagation test** (for data sources — confirm the `source` field flows through to the consuming module's audit trail).

The CI workflow at [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs `ruff check` and `pytest -q` on every push. New tests are picked up automatically.

For the frontend side, `pnpm typecheck` enforces type contract consistency between the TS interfaces and the Python pydantic models. If you add a field to `DiligenceRecord` and forget to mirror it in `web/lib/types.ts`, typecheck fails on the first panel that tries to read the field.

## A worked example: "Add a Catalyst Calendar module"

To make this concrete, here's what adding a `catalyst_calendar` module (next public catalyst for the asset — readout date, BLA filing window, advisory committee, etc.) looks like end-to-end:

1. `api/app/modules/catalyst_calendar/manifest.json`:
   ```json
   {
     "id": "catalyst_calendar",
     "name": "Upcoming Catalyst Calendar",
     "version": "0.1.0",
     "description": "Lists the next material catalysts for the asset with projected dates.",
     "inputs": ["asset.indication", "asset.phase"],
     "outputs": ["catalysts"],
     "deps": ["ct_gov"]
   }
   ```

2. `api/app/data_sources/ct_gov.py` — a new data source wrapping the ClinicalTrials.gov API. Returns trial-specific dates.

3. `api/app/modules/catalyst_calendar/engine.py` — reads asset indication/phase, queries `ct_gov`, computes projected readout / filing / AdCom dates.

4. `api/app/modules/catalyst_calendar/schemas.py` + `routes.py` — standard request/response wrapping.

5. `web/components/modules/catalyst_calendar/CatalystCalendarPanel.tsx` — renders a timeline.

6. `web/lib/module-registry.ts` — add three lines registering the panel by id.

7. Tests under `api/app/modules/catalyst_calendar/tests/`.

8. (Optional) `methodology/07-catalyst-calendar.md` — methodology writeup explaining what catalysts the module recognizes and why.

That's the contract. The framework's existing four modules all follow this pattern; adding a fifth doesn't require touching any of them.

## See also

- [`api/app/registry.py`](../api/app/registry.py) — the auto-discovery walker
- [`api/app/domain.py`](../api/app/domain.py) — the `DiligenceRecord` schema
- [`methodology/00-product-thesis.md`](../methodology/00-product-thesis.md) — why the architecture is the way it is
- [`docs/deployment.md`](deployment.md) — how to deploy the system
