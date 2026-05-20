"""FastAPI entry — registry auto-discovery and dynamic router mounting.

On startup:
  1. Walk data_sources/ to register DataSource subclasses.
  2. Walk modules/ to discover analysis modules (manifest + engine + optional routes).
  3. Walk agents/ to register runtime agents (none in v1, but the discovery runs).

The frontend reads /api/modules to learn what's available and which panels to render.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .registry import get_registry


def create_app() -> FastAPI:
    app = FastAPI(
        title="Asclepius API",
        version=__version__,
        description=(
            "Biotech venture valuation backend. Modules are auto-discovered "
            "from app/modules/<id>/ at startup."
        ),
    )

    origins_env = os.getenv("ASCLEPIUS_CORS_ORIGINS", "http://localhost:3000")
    origins = [o.strip() for o in origins_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trigger registry discovery and mount per-module routers
    registry = get_registry()
    for loaded in registry.modules.values():
        if loaded.router is not None:
            app.include_router(loaded.router)

    # Generic agent invocation route — handles every agent registered above
    from .agents.routes import router as agents_router

    app.include_router(agents_router)

    # ---- Built-in routes ----

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/api/modules")
    def list_modules() -> dict[str, list]:
        """Manifest list — the frontend reads this to decide which panels to render."""
        return {"modules": registry.list_modules()}

    @app.get("/api/data_sources")
    def list_data_sources() -> dict[str, list]:
        return {"data_sources": registry.list_data_sources()}

    @app.get("/api/agents")
    def list_agents() -> dict[str, list]:
        return {"agents": registry.list_agents()}

    return app


app = create_app()
