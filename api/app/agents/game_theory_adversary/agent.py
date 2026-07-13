"""Game-Theory Adversary agent.

Same cache-first / live-fallback shape as the Memo Writer. Accepts an
optional `memo_body` extra field on the request payload — if present, the
agent stress-tests the memo's specific claims; if absent, it critiques the
record's implied thesis.

v1.7.7: structured ``flags`` are the primary output. Legacy ``findings``
are still parsed (and emitted) for back-compat with older cached payloads.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ...domain import DiligenceRecord
from ..base import BaseAgent
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import AdversaryContent, AdversaryOutput

log = logging.getLogger(__name__)

# v1.6.1: slugify moved to app.utils.text (Codex F9).
from ...utils.text import slugify_asset_name as _slugify_asset_name  # noqa: E402,F401


# v1.9.2: tool-use replaces prose parsing (same migration as memo_writer).
# tool_choice forces emit_critique; its input_schema is AdversaryContent's
# JSON Schema, so block.input is already validated — no fenced-JSON parsing,
# no empty-critique class.
ADVERSARY_TOOL = {
    "name": "emit_critique",
    "description": (
        "Emit the structured game-theory critique: a markdown body, the verdict "
        "shift, and 3-5 framework-hooked flags. Fill every field."
    ),
    "input_schema": AdversaryContent.model_json_schema(),
}


def _extract_memo_body(record: DiligenceRecord) -> str | None:
    """Pull a memo_body off the record's `extra` payload if the caller
    supplied one. The DiligenceRecord model uses extra='ignore' by default;
    callers attach memo content via a sibling top-level field on the POST
    body which the agent route routes into request.state — but in v1.1 the
    simplest contract is to accept an optional Pydantic extra. None is fine."""
    # In v1.1.0 we keep this stateless and don't require a memo. v1.1.1 may
    # extend the agent route to accept (record, memo) tuples; for now the
    # critique runs against the record alone if no memo is on hand. The cache
    # ships with a memo-aware critique for adagrasib (the precompute step has
    # the memo available).
    return getattr(record, "_memo_body", None)


class Agent(BaseAgent):
    def __init__(self, manifest, agent_dir: Path) -> None:
        super().__init__(manifest, agent_dir)
        self.cache_dir = agent_dir / "cache"
        self._client = None

    def _cache_path(self, record: DiligenceRecord) -> Path:
        return self.cache_dir / f"{_slugify_asset_name(record.asset.asset_name)}.json"

    def maybe_cached(self, record: DiligenceRecord) -> dict[str, Any] | None:
        # Public hook for the access gate (serve free cached responses ungated).
        return self._maybe_cached(record)

    def _maybe_cached(self, record: DiligenceRecord) -> dict[str, Any] | None:
        key = _slugify_asset_name(record.asset.asset_name)
        if key not in self.manifest.cached_assets:
            return None
        path = self._cache_path(record)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            data["from_cache"] = True
            # Older cached payloads predate the ``flags`` field — default it.
            data.setdefault("flags", [])
            return data
        except Exception as exc:
            log.warning("cache file %s unreadable: %s", path, exc)
            return None

    def _anthropic_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def _assemble_from_tool(self, message, model_used: str) -> dict[str, Any]:
        """Build AdversaryOutput from the forced emit_critique tool call.

        tool_choice guarantees a tool_use block whose .input the API validated
        against AdversaryContent. Re-validate, wrap with the envelope + an
        empty legacy `findings` list. No prose parsing.
        """
        tool_block = next(
            (
                b
                for b in message.content
                if getattr(b, "type", None) == "tool_use"
                and getattr(b, "name", None) == "emit_critique"
            ),
            None,
        )
        if tool_block is None:
            raise HTTPException(
                status_code=502,
                detail="Game-Theory Adversary did not return the expected critique tool output.",
            )
        content = AdversaryContent(**tool_block.input)
        out = AdversaryOutput(
            **content.model_dump(),
            findings=[],
            model_used=model_used,
            from_cache=False,
            generated_at=datetime.now(timezone.utc),
        )
        return out.model_dump(mode="json")

    def _live_call(self, record: DiligenceRecord, memo_body: str | None = None) -> dict[str, Any]:
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ASCLEPIUS_ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Game-Theory Adversary requires ANTHROPIC_API_KEY for "
                    "assets without a pre-computed cached response."
                ),
            )
        if os.getenv("ASCLEPIUS_ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = os.environ["ASCLEPIUS_ANTHROPIC_API_KEY"]

        client = self._anthropic_client()
        model = self.manifest.model or "claude-opus-4-7"
        user_prompt = build_user_prompt(record, memo_body=memo_body)

        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=self._system_prompt_with_methodology(SYSTEM_PROMPT),
            tools=[ADVERSARY_TOOL],
            tool_choice={"type": "tool", "name": "emit_critique"},
            messages=[{"role": "user", "content": user_prompt}],
        )
        return self._assemble_from_tool(message, model_used=model)

    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        cached = self._maybe_cached(record)
        if cached is not None:
            return cached
        return self._live_call(record, memo_body=_extract_memo_body(record))
