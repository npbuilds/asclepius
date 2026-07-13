"""Generic agent-invocation route.

POST /api/agents/<agent_id>/run with a DiligenceRecord body returns the
agent's output dict. The shape of that dict is agent-specific and declared in
the agent's manifest (output_fields).

A single generic route handles all agents — adding a new agent never requires
editing this file.

ACCESS GATE: the three agents are the only routes that spend money (live
Anthropic calls + web search). When the demo runs with a live ANTHROPIC_API_KEY
behind a public URL, anyone who finds the endpoint could drain the key.
`require_access` gates the money-spending path behind a shared passphrase stored
in the ASCLEPIUS_ACCESS_PASSPHRASE env var (a Fly secret).

The gate is applied ONLY to the LIVE path (R3 rescope): a request whose result is
served from a pre-computed cache spends nothing, so it is returned WITHOUT
requiring the passphrase. This is what lets a cold visitor see the AI features on
the pre-cached staged assets (e.g. adagrasib's memo) without a token, while a
custom/uncached asset — which would fire a live Anthropic call — still needs it.

Design is FAIL-OPEN: if the passphrase env var is unset, the gate is inert and
the routes are fully public. Only this router is gated — the deterministic module
routes (/api/modules/*), the manifest list, and the methodology/staged-asset
surfaces stay public regardless.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Header, HTTPException

from ..domain import DiligenceRecord
from ..registry import get_registry

log = logging.getLogger(__name__)


def require_access(
    x_asclepius_access: str | None = Header(default=None),
) -> None:
    """Gate the agent routes behind a shared passphrase.

    Reads the expected passphrase from ASCLEPIUS_ACCESS_PASSPHRASE. If that env
    var is unset the gate is inert (fail-open → current public behavior). When
    set, requests must carry a matching `X-Asclepius-Access` header or get 403.
    The frontend attaches that header from an `?access=<passphrase>` URL token
    (persisted to localStorage) — see web/lib/api-client.ts.
    """
    expected = os.getenv("ASCLEPIUS_ACCESS_PASSPHRASE")
    if not expected:
        return  # gate not configured → public (fail-open by design)
    if x_asclepius_access != expected:
        raise HTTPException(
            status_code=403,
            detail=(
                "This demo's AI features (memo, adversary, auto-diligence) are "
                "access-gated to protect the API key. Append "
                "?access=<passphrase> to the URL, or ask the owner for the demo "
                "passphrase. The quantitative workbench, methodology, and "
                "pre-staged assets remain open without it."
            ),
        )


router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/{agent_id}/run")
def run_agent(
    agent_id: str,
    record: DiligenceRecord,
    x_asclepius_access: str | None = Header(default=None),
) -> dict:
    registry = get_registry()
    loaded = registry.agents.get(agent_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"agent '{agent_id}' not registered")
    try:
        # Free path: if a pre-computed cached response exists, serve it ungated —
        # it spends no money. Only the LIVE (key-spending) path requires the
        # passphrase, so cached staged assets stay visible to a cold visitor.
        cached = loaded.instance.maybe_cached(record)
        if cached is not None:
            return cached
        require_access(x_asclepius_access)
        return loaded.instance.run(record)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("agent %s failed", agent_id)
        raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc
