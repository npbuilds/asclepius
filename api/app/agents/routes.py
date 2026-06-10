"""Generic agent-invocation route.

POST /api/agents/<agent_id>/run with a DiligenceRecord body returns the
agent's output dict. The shape of that dict is agent-specific and declared in
the agent's manifest (output_fields).

A single generic route handles all agents — adding a new agent never requires
editing this file.

ACCESS GATE (v1.9.1): the three agents are the only routes that spend money
(live Anthropic calls + web search). When the demo runs with a live
ANTHROPIC_API_KEY behind a public URL, anyone who finds the endpoint could
drain the key. `require_access` gates this router behind a single shared
passphrase stored in the ASCLEPIUS_ACCESS_PASSPHRASE env var (a Fly secret).

Design is FAIL-OPEN: if the passphrase env var is unset, the gate is inert and
the routes behave exactly as before (public). This lets the gate code deploy
without breaking anything; the owner ACTIVATES it by setting the secret, and
REVOKES access by rotating it. Only this router is gated — the deterministic
module routes (/api/modules/*), the manifest list (GET /api/agents), and the
methodology/staged-asset surfaces stay public so the portfolio value and the
quantitative workbench remain visible to anyone.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException

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


router = APIRouter(
    prefix="/api/agents",
    tags=["agents"],
    dependencies=[Depends(require_access)],
)


@router.post("/{agent_id}/run")
def run_agent(agent_id: str, record: DiligenceRecord) -> dict:
    registry = get_registry()
    loaded = registry.agents.get(agent_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"agent '{agent_id}' not registered")
    try:
        return loaded.instance.run(record)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("agent %s failed", agent_id)
        raise HTTPException(status_code=500, detail=f"agent error: {exc}") from exc
