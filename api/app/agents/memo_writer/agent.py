"""Memo Writer agent — DiligenceRecord → 2-page investment memo (markdown).

Flow on every run():
  1. Compute cache key from the asset name. If a cached JSON exists under
     cache/<key>.json AND the manifest lists this asset in `cached_assets`,
     return it (sets from_cache=True, no LLM call).
  2. Otherwise make a live Anthropic call using the model named in the
     manifest. Returns from_cache=False.
  3. If no API key is set and no cache hit, raise HTTPException(503).

The body markdown contains a trailing fenced JSON block with the structured
signals (recommendation, red_flags). We parse it out, drop it from the body
the user sees, and surface the parsed fields on the response.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ...domain import DiligenceRecord
from ..base import BaseAgent
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import MemoOutput

log = logging.getLogger(__name__)

# Permissive — matches ```json ... ``` even with surrounding whitespace and
# newlines inside the block. Greedy on body, non-greedy on inner content would
# fail on multi-newline JSON.
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def _slugify_asset_name(name: str) -> str:
    """adagrasib (MRTX849) → adagrasib_mrtx849. Conservative — strip everything
    that isn't alphanumeric or underscore."""
    cleaned = re.sub(r"[^a-z0-9_]+", "_", name.lower())
    return cleaned.strip("_") or "unnamed"


def _parse_memo_response(raw: str, model_used: str) -> dict[str, Any]:
    """Extract the trailing JSON block, return body + structured fields.

    Defensive: if the JSON block is missing or unparseable, return a "hold"
    recommendation with the full raw text as body. Better to ship a degraded
    response than 500."""
    match = JSON_BLOCK_RE.search(raw)
    body = raw
    parsed: dict[str, Any] = {}
    if match:
        try:
            parsed = json.loads(match.group(1))
            body = raw[: match.start()].rstrip()
        except json.JSONDecodeError:
            log.warning("memo writer returned malformed JSON block; falling back")

    recommendation = parsed.get("recommendation", "hold")
    if recommendation not in {"strong_buy", "buy", "hold", "cautious", "avoid"}:
        recommendation = "hold"
    executive_summary = parsed.get("executive_summary", "").strip()
    if not executive_summary:
        # Pull the first paragraph under "## Executive summary" as a fallback
        es_match = re.search(
            r"##\s*Executive summary\s*\n+(.+?)(?=\n##|\Z)", body, re.DOTALL
        )
        executive_summary = es_match.group(1).strip() if es_match else ""

    return MemoOutput(
        body_markdown=body,
        executive_summary=executive_summary,
        recommendation=recommendation,
        red_flags=list(parsed.get("red_flags", [])),
        model_used=model_used,
        from_cache=False,
        generated_at=datetime.now(timezone.utc),
    ).model_dump(mode="json")


class Agent(BaseAgent):
    """The Memo Writer."""

    def __init__(self, manifest, agent_dir: Path) -> None:
        super().__init__(manifest, agent_dir)
        self.cache_dir = agent_dir / "cache"
        self._client = None  # lazy — don't instantiate Anthropic at import time

    # ---- cache lookup ----

    def _cache_path(self, record: DiligenceRecord) -> Path:
        return self.cache_dir / f"{_slugify_asset_name(record.asset.asset_name)}.json"

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
            return data
        except Exception as exc:
            log.warning("cache file %s unreadable: %s", path, exc)
            return None

    # ---- live call ----

    def _anthropic_client(self):
        if self._client is None:
            import anthropic  # local import — keeps test import cheap

            self._client = anthropic.Anthropic()
        return self._client

    def _live_call(self, record: DiligenceRecord) -> dict[str, Any]:
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ASCLEPIUS_ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Memo Writer requires ANTHROPIC_API_KEY for assets without a "
                    "pre-computed cached response. Set the key or use the "
                    "adagrasib worked example to see a cached memo."
                ),
            )
        # The Anthropic SDK reads ANTHROPIC_API_KEY from env by default; if the
        # operator set the Asclepius-namespaced one instead, forward it.
        if os.getenv("ASCLEPIUS_ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = os.environ["ASCLEPIUS_ANTHROPIC_API_KEY"]

        client = self._anthropic_client()
        model = self.manifest.model or "claude-opus-4-7"
        user_prompt = build_user_prompt(record)

        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        # SDK returns a list of content blocks; the first text block is the memo.
        text = next(
            (block.text for block in message.content if getattr(block, "type", None) == "text"),
            "",
        )
        return _parse_memo_response(text, model_used=model)

    # ---- BaseAgent contract ----

    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        cached = self._maybe_cached(record)
        if cached is not None:
            return cached
        return self._live_call(record)
