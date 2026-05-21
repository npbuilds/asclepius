"""Auto-Diligence agent — asset name → structured AssetInput + citations.

Cache-first run() with disk lookup; live path enables web_search_20250305
restricted to a high-signal domain allowlist. Walks message.content for
both the trailing JSON block (extraction) and the search/citation server-
tool blocks (search count, citation augmentation).
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
from .prompts import ALLOWED_DOMAINS, SYSTEM_PROMPT, build_user_prompt
from .schemas import AutoDiligenceOutput, Citation, ExtractedAsset

log = logging.getLogger(__name__)

JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def _slugify_asset_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]+", "_", name.lower())
    return cleaned.strip("_") or "unnamed"


def _walk_response(message) -> tuple[str, list[dict], int]:
    """Walk the Anthropic message content blocks. Returns (full_text,
    web_search_citations, search_count). web_search_result_location blocks
    are flattened into the citation list with field='' (model will assign
    via the JSON block; these are the source-of-truth URLs)."""
    full_text: list[str] = []
    web_citations: list[dict] = []
    search_count = 0
    for block in message.content:
        btype = getattr(block, "type", None)
        if btype == "text":
            full_text.append(block.text)
            for cite in getattr(block, "citations", None) or []:
                ctype = getattr(cite, "type", None)
                if ctype == "web_search_result_location":
                    web_citations.append(
                        {
                            "url": getattr(cite, "url", ""),
                            "title": getattr(cite, "title", None),
                            "span": getattr(cite, "cited_text", ""),
                        }
                    )
        elif btype == "server_tool_use":
            tool_name = getattr(block, "name", "")
            if tool_name == "web_search":
                search_count += 1
    return "".join(full_text), web_citations, search_count


def _parse_diligence_response(
    raw_text: str,
    web_citations: list[dict],
    search_count: int,
    model_used: str,
) -> dict[str, Any]:
    """Extract the trailing JSON block. Defensive on every field — missing
    or malformed values become null/empty rather than 500ing."""
    match = JSON_BLOCK_RE.search(raw_text)
    parsed: dict[str, Any] = {}
    if match:
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            log.warning("auto_diligence returned malformed JSON; degrading to empty")

    extracted_raw = parsed.get("extracted") or {}
    extracted = ExtractedAsset(**{k: v for k, v in extracted_raw.items() if v is not None})

    citations: list[Citation] = []
    for c in parsed.get("citations") or []:
        if not isinstance(c, dict):
            continue
        if not c.get("field") or not c.get("url") or not c.get("span"):
            continue
        try:
            citations.append(
                Citation(
                    field=c["field"],
                    url=c["url"],
                    title=c.get("title"),
                    span=c["span"][:500],  # cap defensively
                )
            )
        except Exception:
            continue

    # If the model didn't surface citations via the JSON block but the SDK
    # captured web_search_result_location blocks, append them with field='' so
    # the frontend can still surface the sources used.
    seen_urls = {c.url for c in citations}
    for wc in web_citations:
        if wc["url"] and wc["url"] not in seen_urls:
            citations.append(
                Citation(field="", url=wc["url"], title=wc["title"], span=wc["span"][:500])
            )

    field_confidence = parsed.get("field_confidence") or {}
    if not isinstance(field_confidence, dict):
        field_confidence = {}
    field_confidence = {
        k: v
        for k, v in field_confidence.items()
        if v in {"high", "medium", "low", "missing"}
    }

    return AutoDiligenceOutput(
        extracted=extracted,
        citations=citations,
        field_confidence=field_confidence,
        web_searches_used=search_count,
        model_used=model_used,
        from_cache=False,
        generated_at=datetime.now(timezone.utc),
    ).model_dump(mode="json")


class Agent(BaseAgent):
    def __init__(self, manifest, agent_dir: Path) -> None:
        super().__init__(manifest, agent_dir)
        self.cache_dir = agent_dir / "cache"
        self._client = None

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

    def _anthropic_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def _live_call(self, record: DiligenceRecord) -> dict[str, Any]:
        if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ASCLEPIUS_ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Auto-Diligence requires ANTHROPIC_API_KEY for assets "
                    "without a pre-computed cached response."
                ),
            )
        if os.getenv("ASCLEPIUS_ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = os.environ["ASCLEPIUS_ANTHROPIC_API_KEY"]

        client = self._anthropic_client()
        model = self.manifest.model or "claude-opus-4-7"
        user_prompt = build_user_prompt(record.asset.asset_name)

        message = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 10,
                    "allowed_domains": ALLOWED_DOMAINS,
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text, web_citations, search_count = _walk_response(message)
        return _parse_diligence_response(
            raw_text=raw_text,
            web_citations=web_citations,
            search_count=search_count,
            model_used=model,
        )

    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        cached = self._maybe_cached(record)
        if cached is not None:
            return cached
        return self._live_call(record)
