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

from ...domain import DiligenceRecord, RegulatoryDesignation
from ..base import BaseAgent
from .prompts import ALLOWED_DOMAINS, SYSTEM_PROMPT, build_user_prompt
from .schemas import AutoDiligenceOutput, Citation, DiligenceExtraction, ExtractedAsset

# v1.6.2 (post-v1.5.3 hotfix): the LLM occasionally emits regulatory-
# designation strings that aren't in the domain enum (most common: the
# pre-fix prompt's `priority_review` and `regenerative_medicine`; same
# class of risk for any future drift between the prompt and the enum).
# The frontend's "Apply Record" button forwards extracted.regulatory_designations
# verbatim to /api/modules/pos which validates strictly via pydantic and
# 422s on unknown values, breaking the apply flow. We normalize at the
# agent boundary: filter to enum members, log drops, optionally remap
# obvious synonyms. Pure prompt-side fixes are fragile because LLMs can
# always invent new values; the filter is the actual safety net.
_REGULATORY_DESIGNATION_SYNONYMS: dict[str, str] = {
    # synonym → canonical enum value
    "regenerative_medicine": "rmat",
    "rmat_designation": "rmat",
    "regenerative_medicine_advanced_therapy": "rmat",
    "prime": "prime_ema",
    "ema_prime": "prime_ema",
    "btd": "breakthrough_therapy",
    "breakthrough": "breakthrough_therapy",
}
_VALID_REGULATORY_DESIGNATIONS: frozenset[str] = frozenset(
    rd.value for rd in RegulatoryDesignation
)


def _normalize_regulatory_designations(raw: list[str]) -> list[str]:
    """Filter LLM-emitted strings to known RegulatoryDesignation enum values.
    Applies a small synonym map first; drops anything still unrecognized."""
    out: list[str] = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, str):
            continue
        key = value.strip().lower()
        canonical = _REGULATORY_DESIGNATION_SYNONYMS.get(key, key)
        if canonical in _VALID_REGULATORY_DESIGNATIONS:
            if canonical not in seen:
                out.append(canonical)
                seen.add(canonical)
        else:
            log.warning(
                "auto_diligence dropping unknown regulatory_designation %r "
                "(not in RegulatoryDesignation enum; was the agent prompt "
                "updated without a matching enum?)",
                value,
            )
    return out

log = logging.getLogger(__name__)

JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


# v1.6.1: slugify moved to app.utils.text (Codex F9).
from ...utils.text import slugify_asset_name as _slugify_asset_name  # noqa: E402,F401


# v1.9.2: tool-use structured output. Unlike memo/adversary, emit_diligence is
# OFFERED alongside web_search (not forced via tool_choice — the model must be
# free to search first). The prompt tells the model to finish by calling it; if
# it emits a fenced JSON block instead, _live_call falls back to the prose parser.
EMIT_DILIGENCE_TOOL = {
    "name": "emit_diligence",
    "description": (
        "Call this ONCE research is complete to return the structured extraction "
        "(extracted fields + citations + field_confidence). Prefer this over "
        "emitting a JSON block."
    ),
    "input_schema": DiligenceExtraction.model_json_schema(),
}


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


def _assemble_output(
    parsed: dict[str, Any],
    web_citations: list[dict],
    search_count: int,
    model_used: str,
) -> dict[str, Any]:
    """Build AutoDiligenceOutput from a parsed extraction dict — sourced from
    either the emit_diligence tool block or the fenced-JSON fallback.
    Defensive on every field; merges web_search source URLs into citations.
    """
    extracted_raw = parsed.get("extracted") or {}
    # v1.6.2: normalize regulatory_designations before constructing the
    # ExtractedAsset so any drift between the LLM's prompt and the domain
    # enum gets filtered + remapped here (see _normalize_regulatory_designations).
    if isinstance(extracted_raw.get("regulatory_designations"), list):
        extracted_raw = {
            **extracted_raw,
            "regulatory_designations": _normalize_regulatory_designations(
                extracted_raw["regulatory_designations"]
            ),
        }
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

    return _assemble_output(parsed, web_citations, search_count, model_used)


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
            # v1.6.2 hotfix: cache files committed before the regulatory-
            # designation enum drift fix may still carry invalid values
            # (e.g., adagrasib.json had `priority_review` until 2026-05-25).
            # Normalize here so old fixtures are tolerated without
            # blocking the apply-record flow.
            extracted = data.get("extracted")
            if isinstance(extracted, dict) and isinstance(
                extracted.get("regulatory_designations"), list
            ):
                extracted["regulatory_designations"] = (
                    _normalize_regulatory_designations(
                        extracted["regulatory_designations"]
                    )
                )
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
            system=self._system_prompt_with_methodology(SYSTEM_PROMPT),
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": 10,
                    "allowed_domains": ALLOWED_DOMAINS,
                },
                EMIT_DILIGENCE_TOOL,
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text, web_citations, search_count = _walk_response(message)
        # Preferred: the model finished by calling emit_diligence (schema-validated
        # extraction). It's offered, not forced (web_search must stay available),
        # so if the model emitted a fenced JSON block instead, fall back to the
        # prose parser. Both paths share _assemble_output.
        tool_block = next(
            (
                b
                for b in message.content
                if getattr(b, "type", None) == "tool_use"
                and getattr(b, "name", None) == "emit_diligence"
            ),
            None,
        )
        if tool_block is not None:
            return _assemble_output(
                dict(tool_block.input), web_citations, search_count, model
            )
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
