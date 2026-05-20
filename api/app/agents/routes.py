"""Generic agent-invocation route.

POST /api/agents/<agent_id>/run with a DiligenceRecord body returns the
agent's output dict. The shape of that dict is agent-specific and declared in
the agent's manifest (output_fields).

A single generic route handles all agents — adding a new agent never requires
editing this file.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..domain import DiligenceRecord
from ..registry import get_registry

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


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
