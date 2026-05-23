"""Game-Theory Adversary agent.

Same cache-first / live-fallback shape as the Memo Writer. Accepts an
optional `memo_body` extra field on the request payload — if present, the
agent stress-tests the memo's specific claims; if absent, it critiques the
record's implied thesis.
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
from .schemas import AdversarialFinding, AdversaryOutput

log = logging.getLogger(__name__)

JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
VALID_VERDICTS = {"upgrade", "hold", "downgrade"}
VALID_RECS = {"strong_buy", "buy", "hold", "cautious", "avoid"}
VALID_LENSES = {"signaling", "auction", "persuasion"}
VALID_SEVERITIES = {"minor", "moderate", "critical"}


# v1.6.1: slugify moved to app.utils.text (Codex F9).
from ...utils.text import slugify_asset_name as _slugify_asset_name  # noqa: E402,F401


def _parse_adversary_response(raw: str, model_used: str) -> dict[str, Any]:
    """Extract JSON block, validate, return AdversaryOutput-shaped dict."""
    match = JSON_BLOCK_RE.search(raw)
    body = raw
    parsed: dict[str, Any] = {}
    if match:
        try:
            parsed = json.loads(match.group(1))
            body = raw[: match.start()].rstrip()
        except json.JSONDecodeError:
            log.warning("adversary returned malformed JSON block; falling back")

    verdict_shift = parsed.get("verdict_shift", "hold")
    if verdict_shift not in VALID_VERDICTS:
        verdict_shift = "hold"

    recommendation_shift_to = parsed.get("recommendation_shift_to")
    if recommendation_shift_to is not None and recommendation_shift_to not in VALID_RECS:
        recommendation_shift_to = None

    raw_findings = parsed.get("findings", []) or []
    findings: list[AdversarialFinding] = []
    for f in raw_findings:
        if not isinstance(f, dict):
            continue
        if f.get("lens") not in VALID_LENSES:
            continue
        if f.get("severity") not in VALID_SEVERITIES:
            continue
        if not f.get("claim"):
            continue
        findings.append(
            AdversarialFinding(
                lens=f["lens"], claim=f["claim"], severity=f["severity"]
            )
        )

    return AdversaryOutput(
        body_markdown=body,
        verdict_shift=verdict_shift,
        recommendation_shift_to=recommendation_shift_to,
        findings=findings,
        model_used=model_used,
        from_cache=False,
        generated_at=datetime.now(timezone.utc),
    ).model_dump(mode="json")


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
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = next(
            (b.text for b in message.content if getattr(b, "type", None) == "text"),
            "",
        )
        return _parse_adversary_response(text, model_used=model)

    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        cached = self._maybe_cached(record)
        if cached is not None:
            return cached
        return self._live_call(record, memo_body=_extract_memo_body(record))
