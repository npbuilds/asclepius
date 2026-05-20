"""Pluggable registries — data sources, analysis modules, runtime agents.

The contract:
  * Data sources subclass `DataSource` and live in `app/data_sources/`.
  * Analysis modules live in `app/modules/<id>/` with a `manifest.json` and an
    `engine.py` exposing `compute(record) -> result`.
  * Runtime agents live in `app/agents/<id>/` with a `manifest.json` and an
    `agent.py` exposing a `BaseAgent` subclass. (v1.1+ — the ABC ships in v1.)

Discovery is filesystem-based, runs once at startup, and is idempotent.
"""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from .domain import DiligenceRecord

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Manifest schemas
# ---------------------------------------------------------------------------


class ModuleManifest(BaseModel):
    """The contract every analysis-module folder must satisfy."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    version: str
    description: str
    inputs: list[str] = Field(
        description="DiligenceRecord field paths this module reads, e.g. 'asset.phase'."
    )
    outputs: list[str] = Field(
        description="DiligenceRecord field paths this module writes, e.g. 'pos'."
    )
    deps: list[str] = Field(
        default_factory=list,
        description="IDs of data sources or other modules this module depends on.",
    )


class AgentManifest(BaseModel):
    """The contract every runtime-agent folder must satisfy. Used in v1.1+."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    version: str
    description: str
    skill_loadout: list[str] = Field(
        description="Skill paths (relative to ASCLEPIUS_SKILLS_DIR) this agent loads."
    )
    trigger_label: str = Field(description="UI button label for this agent.")
    input_fields: list[str]
    output_fields: list[str]


# ---------------------------------------------------------------------------
# Data Source ABC
# ---------------------------------------------------------------------------


class DataSource(ABC):
    """A pluggable provider of input data for the diligence record.

    Subclasses declare which fields they can populate via `provides_fields`. The
    registry routes a `fetch(query)` request to the appropriate source. Sources
    are stateless; any caching belongs in the source's own implementation.
    """

    id: str = ""
    provides_fields: tuple[str, ...] = ()

    @abstractmethod
    def fetch(self, query: dict[str, Any]) -> dict[str, Any]:
        """Return a dict whose keys are a subset of `provides_fields`."""


# ---------------------------------------------------------------------------
# Module wrapper — what the registry holds for each loaded module
# ---------------------------------------------------------------------------


@dataclass
class LoadedModule:
    manifest: ModuleManifest
    compute: Callable[[DiligenceRecord], BaseModel]
    router: Any | None  # FastAPI router, attached if module has routes.py
    path: Path


@dataclass
class LoadedAgent:
    manifest: AgentManifest
    agent_cls: type
    path: Path


# ---------------------------------------------------------------------------
# Registries — three top-level dicts populated at startup
# ---------------------------------------------------------------------------


class Registry:
    """Holds the three registries. One instance per running app."""

    def __init__(self) -> None:
        self.data_sources: dict[str, DataSource] = {}
        self.modules: dict[str, LoadedModule] = {}
        self.agents: dict[str, LoadedAgent] = {}

    # ---- discovery ----

    def discover_data_sources(self, package: str = "app.data_sources") -> None:
        """Walk the data_sources package; instantiate each DataSource subclass."""
        try:
            pkg = importlib.import_module(package)
        except ModuleNotFoundError:
            log.warning("data sources package %s not found", package)
            return

        pkg_path = Path(pkg.__file__).parent if pkg.__file__ else None
        if not pkg_path:
            return

        for py in sorted(pkg_path.glob("*.py")):
            if py.name.startswith("_") or py.name == "base.py":
                continue
            modname = f"{package}.{py.stem}"
            try:
                mod = importlib.import_module(modname)
            except Exception as exc:
                log.error("failed to import data source %s: %s", modname, exc)
                continue
            for attr in vars(mod).values():
                if (
                    isinstance(attr, type)
                    and issubclass(attr, DataSource)
                    and attr is not DataSource
                ):
                    instance = attr()
                    if not instance.id:
                        log.warning(
                            "data source %s.%s declares no id; skipping", modname, attr.__name__
                        )
                        continue
                    self.data_sources[instance.id] = instance
                    log.info("registered data source: %s (%s)", instance.id, modname)

    def discover_modules(self, package: str = "app.modules") -> None:
        """Walk modules/<id>/ folders; require manifest.json + engine.py."""
        try:
            pkg = importlib.import_module(package)
        except ModuleNotFoundError:
            log.warning("modules package %s not found", package)
            return

        pkg_path = Path(pkg.__file__).parent if pkg.__file__ else None
        if not pkg_path:
            return

        for child in sorted(pkg_path.iterdir()):
            if not child.is_dir() or child.name.startswith("_") or child.name == "tests":
                continue
            manifest_file = child / "manifest.json"
            engine_file = child / "engine.py"
            if not manifest_file.exists() or not engine_file.exists():
                continue
            try:
                manifest = ModuleManifest.model_validate_json(manifest_file.read_text())
            except Exception as exc:
                log.error("invalid manifest %s: %s", manifest_file, exc)
                continue

            try:
                engine_mod = importlib.import_module(f"{package}.{child.name}.engine")
            except Exception as exc:
                # Don't let one bad module crash the whole registry
                log.error("failed to import module %s engine.py: %s", child.name, exc)
                continue
            compute = getattr(engine_mod, "compute", None)
            if not callable(compute):
                log.error("module %s has no compute() in engine.py", child.name)
                continue

            router = None
            routes_file = child / "routes.py"
            if routes_file.exists():
                try:
                    routes_mod = importlib.import_module(f"{package}.{child.name}.routes")
                    router = getattr(routes_mod, "router", None)
                except Exception as exc:
                    log.error("failed to import module %s routes.py: %s", child.name, exc)
                    # engine still works; route just won't be mounted

            self.modules[manifest.id] = LoadedModule(
                manifest=manifest, compute=compute, router=router, path=child
            )
            log.info("registered module: %s v%s", manifest.id, manifest.version)

    def discover_agents(self, package: str = "app.agents") -> None:
        """Walk agents/<id>/ folders; agents are introduced in v1.1.

        v1 only validates that the directory and ABC exist so the discovery
        machinery is exercised end-to-end before any real agents ship.
        """
        try:
            pkg = importlib.import_module(package)
        except ModuleNotFoundError:
            return

        pkg_path = Path(pkg.__file__).parent if pkg.__file__ else None
        if not pkg_path:
            return

        for child in sorted(pkg_path.iterdir()):
            if not child.is_dir() or child.name.startswith("_"):
                continue
            manifest_file = child / "manifest.json"
            agent_file = child / "agent.py"
            if not manifest_file.exists() or not agent_file.exists():
                continue
            try:
                manifest = AgentManifest.model_validate_json(manifest_file.read_text())
            except Exception as exc:
                log.error("invalid agent manifest %s: %s", manifest_file, exc)
                continue
            agent_mod = importlib.import_module(f"{package}.{child.name}.agent")
            agent_cls = getattr(agent_mod, "Agent", None)
            if agent_cls is None:
                log.error("agent %s has no Agent class in agent.py", child.name)
                continue
            self.agents[manifest.id] = LoadedAgent(
                manifest=manifest, agent_cls=agent_cls, path=child
            )
            log.info("registered agent: %s v%s", manifest.id, manifest.version)

    def discover_all(self) -> None:
        self.discover_data_sources()
        self.discover_modules()
        self.discover_agents()

    # ---- lookups ----

    def list_modules(self) -> list[dict[str, Any]]:
        """Manifest list for the /api/modules endpoint — the frontend reads this."""
        return [m.manifest.model_dump() for m in self.modules.values()]

    def list_agents(self) -> list[dict[str, Any]]:
        return [a.manifest.model_dump() for a in self.agents.values()]

    def list_data_sources(self) -> list[dict[str, Any]]:
        return [
            {"id": ds.id, "provides_fields": list(ds.provides_fields)}
            for ds in self.data_sources.values()
        ]


# ---------------------------------------------------------------------------
# Module-level singleton — main.py reaches for this on startup
# ---------------------------------------------------------------------------


_registry: Registry | None = None


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry()
        _registry.discover_all()
    return _registry


def reset_registry_for_tests() -> Registry:
    """Force a clean rediscover. Tests call this; production should not."""
    global _registry
    _registry = Registry()
    _registry.discover_all()
    return _registry
