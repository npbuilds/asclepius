"""Memo Writer agent — DiligenceRecord → structured 2-3 page investment memo.

v1.7.7: the agent now returns a structured multi-section memo. The Anthropic
model returns one fenced ```json``` object matching the MemoOutput schema
(minus envelope fields). We parse it, render a markdown body from the
structured sections for back-compat with the older renderer, and surface
both the structured sections and the markdown body to the API.

Flow on every run():
  1. Compute cache key from the asset name. If a cached JSON exists under
     cache/<key>.json AND the manifest lists this asset in `cached_assets`,
     return it (sets from_cache=True, no LLM call).
  2. Otherwise make a live Anthropic call using the model named in the
     manifest. Returns from_cache=False.
  3. If no API key is set and no cache hit, raise HTTPException(503).
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
# newlines inside the block. Multiline DOTALL because the structured JSON is
# spread over many lines.
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*\})\s*```", re.DOTALL)


def _parse_json_with_recovery(json_str: str) -> dict[str, Any]:
    """Parse a JSON object that the model may have emitted with stray '},'
    fragments prematurely closing the outer container.

    v1.7.10: live-call testing on adagrasib (HTTP 200, 51s) surfaced a
    real-world failure mode: Sonnet/Opus emitting one fenced ```json``` block
    where the response is structurally invalid — a stray '}' after a deeply
    nested field (e.g. reflexivity_note) closes the outer object early, then
    the model continues with more top-level keys at the same indent level as
    if it were still inside.

    Strict json.loads() returns "Extra data" on this; pre-recovery the parser
    fell through to the markdown fallback path and returned a memo with every
    structured field null. The new MemoPanel frontend renders that as a
    completely empty memo card.

    Recovery strategy: iteratively raw_decode the next valid object from the
    remaining string, treating each successful parse as a continuation of
    the same top-level container and merging keys. Skip stray '}' (premature
    close) + ',' (continuation) tokens between objects. Wrap the remainder
    in '{' when we see another '"key":' starter so raw_decode treats it as
    an object. Bail out cleanly when the remainder is no longer parseable.

    Returns whatever fragment could be salvaged; the caller still does its
    own null-tolerant field extraction so partial recovery is fine."""
    decoder = json.JSONDecoder()
    s = json_str.strip()
    if not s.startswith("{"):
        i = s.find("{")
        if i < 0:
            return {}
        s = s[i:]

    merged: dict[str, Any] = {}
    while s:
        try:
            obj, end = decoder.raw_decode(s)
        except json.JSONDecodeError:
            break
        if isinstance(obj, dict):
            merged.update(obj)
        # Advance past the parsed object
        s = s[end:].lstrip()
        # Skip stray '}' / ',' / whitespace between fragments
        while s and s[0] in "},":
            s = s[1:].lstrip()
        # If what follows looks like more "key":value pairs, wrap them so
        # raw_decode treats the next chunk as another object.
        if s and s[0] == '"':
            s = "{" + s
        elif not s:
            break
        else:
            break
    return merged


# v1.6.1: slugify moved to app.utils.text (Codex F9). Kept as a thin
# alias here so existing internal call sites + the test imports keep
# working without surface churn.
from ...utils.text import slugify_asset_name as _slugify_asset_name  # noqa: E402,F401


_VALID_RECS = {"strong_buy", "buy", "hold", "cautious", "avoid"}


def _render_body_markdown(parsed: dict[str, Any]) -> str:
    """Compose a markdown body from the structured sections.

    Kept so any older renderer that reads `body_markdown` still gets a
    usable string. The new MemoPanel reads the structured sections
    directly and ignores this field.
    """
    parts: list[str] = []

    tldr = parsed.get("tldr") or {}
    if tldr:
        loa = tldr.get("loa_pct")
        rnpv = tldr.get("rnpv_base_usd_m")
        lo = tldr.get("rnpv_range_low_usd_m")
        hi = tldr.get("rnpv_range_high_usd_m")
        rec = tldr.get("recommendation", "hold")
        thesis = tldr.get("thesis_one_liner", "")
        parts.append("## TL;DR\n")
        bits = [f"**Recommendation:** {rec.replace('_', ' ')}"]
        if loa is not None:
            bits.append(f"**LOA:** {loa:.1f}%")
        if rnpv is not None:
            range_str = ""
            if lo is not None and hi is not None:
                range_str = f" (P25–P75: ${lo:.0f}M – ${hi:.0f}M)"
            bits.append(f"**rNPV base:** ${rnpv:.0f}M{range_str}")
        parts.append("  \n".join(bits))
        if thesis:
            parts.append(f"\n{thesis}")

    es = parsed.get("executive_summary", "").strip()
    if es:
        parts.append("\n## Executive summary\n")
        parts.append(es)

    overview = (parsed.get("asset_overview") or {}).get("paragraph", "").strip()
    if overview:
        parts.append("\n## Asset overview\n")
        parts.append(overview)

    pos = parsed.get("pos_analysis") or {}
    if pos:
        parts.append("\n## PoS analysis\n")
        if pos.get("waterfall_narrative"):
            parts.append(pos["waterfall_narrative"].strip())
        if pos.get("reflexivity_note"):
            parts.append("\n" + pos["reflexivity_note"].strip())

    val = (parsed.get("valuation") or {}).get("valuation_narrative", "").strip()
    if val:
        parts.append("\n## Valuation\n")
        parts.append(val)

    comp = (parsed.get("comparables") or {}).get("cohort_paragraph", "").strip()
    if comp:
        parts.append("\n## Comparables\n")
        parts.append(comp)

    ops = (parsed.get("operational") or {}).get("pillars_paragraph", "").strip()
    if ops:
        parts.append("\n## Operational diligence\n")
        parts.append(ops)

    risks = parsed.get("risks") or []
    if risks:
        parts.append("\n## Risks\n")
        for r in risks:
            label = r.get("label", "Risk")
            desc = r.get("description", "")
            sev = r.get("severity", "medium")
            parts.append(f"- **{label}** _(severity: {sev})_ — {desc}")

    close = parsed.get("recommendation_close") or {}
    if close:
        parts.append("\n## Recommendation\n")
        if close.get("closing_paragraph"):
            parts.append(close["closing_paragraph"].strip())
        if close.get("kill_criterion"):
            parts.append(f"\n**Kill criterion:** {close['kill_criterion'].strip()}")

    return "\n".join(parts).strip()


def _parse_memo_response(raw: str, model_used: str) -> dict[str, Any]:
    """Extract the structured JSON block and assemble the MemoOutput.

    Defensive: if the JSON block is missing/unparseable, return a "hold"
    recommendation with the raw text dropped into body_markdown."""
    match = JSON_BLOCK_RE.search(raw)
    parsed: dict[str, Any] = {}
    fallback_body = raw.strip()

    if match:
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            # v1.7.10: try recovery before falling back to the markdown
            # dump. Some live responses emit a stray '},' that closes the
            # outer object early; _parse_json_with_recovery() salvages the
            # rest by raw_decode-and-merge. If recovery still yields
            # nothing, fall through to the older markdown-fallback path.
            log.warning(
                "memo writer returned malformed JSON block; trying recovery parser"
            )
            parsed = _parse_json_with_recovery(match.group(1))
            if parsed:
                log.info(
                    "memo writer recovery parser salvaged %d top-level keys",
                    len(parsed),
                )
            else:
                log.warning("memo writer recovery parser also failed; markdown fallback")

    # v1.7.10: shape normalization. The schema requires `reflexivity_note`
    # nested inside `pos_analysis` (one paragraph alongside `waterfall_narrative`).
    # Live-call testing shows Sonnet/Opus emit `reflexivity_note` as a TOP-LEVEL
    # sibling instead. Normalize: if reflexivity_note appears at the top level
    # and pos_analysis is a dict without it, fold it in. Preserves the original
    # schema intent without forcing a schema migration. Skip if parsed is empty
    # (markdown-fallback path takes over downstream).
    if parsed and isinstance(parsed.get("pos_analysis"), dict):
        if "reflexivity_note" not in parsed["pos_analysis"]:
            top_level_rn = parsed.pop("reflexivity_note", None)
            if isinstance(top_level_rn, str) and top_level_rn.strip():
                parsed["pos_analysis"]["reflexivity_note"] = top_level_rn

    # Recommendation gating
    recommendation = parsed.get("recommendation")
    if not recommendation:
        recommendation = (parsed.get("tldr") or {}).get("recommendation")
    if not recommendation:
        recommendation = (parsed.get("recommendation_close") or {}).get("recommendation")
    if recommendation not in _VALID_RECS:
        recommendation = "hold"

    # Executive summary fallback
    executive_summary = (parsed.get("executive_summary") or "").strip()
    if not executive_summary:
        executive_summary = ((parsed.get("tldr") or {}).get("thesis_one_liner") or "").strip()

    # Red flags fallback — derive from risks[] if not given explicitly
    red_flags = list(parsed.get("red_flags") or [])
    if not red_flags and parsed.get("risks"):
        red_flags = [
            r["label"] for r in parsed["risks"]
            if isinstance(r, dict) and r.get("label")
        ]

    # Body markdown — render from structured sections if we have any
    if parsed:
        body_markdown = _render_body_markdown(parsed)
        if not body_markdown:
            body_markdown = fallback_body
    else:
        body_markdown = fallback_body

    # Drop nested sections that won't pass enum validation rather than
    # raising — the front-end can degrade gracefully on a missing section.
    tldr_payload = parsed.get("tldr")
    if isinstance(tldr_payload, dict) and tldr_payload.get("recommendation") not in _VALID_RECS:
        tldr_payload = None
    close_payload = parsed.get("recommendation_close")
    if isinstance(close_payload, dict) and close_payload.get("recommendation") not in _VALID_RECS:
        close_payload = None

    # Build the MemoOutput. Pydantic will validate each nested section
    # and drop any that fail.
    payload: dict[str, Any] = {
        "tldr": tldr_payload,
        "asset_overview": parsed.get("asset_overview"),
        "pos_analysis": parsed.get("pos_analysis"),
        "valuation": parsed.get("valuation"),
        "comparables": parsed.get("comparables"),
        "operational": parsed.get("operational"),
        "risks": parsed.get("risks") or [],
        "recommendation_close": close_payload,
        "body_markdown": body_markdown,
        "executive_summary": executive_summary,
        "recommendation": recommendation,
        "red_flags": red_flags,
        "model_used": model_used,
        "from_cache": False,
        "generated_at": datetime.now(timezone.utc),
    }

    return MemoOutput(**payload).model_dump(mode="json")


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
            max_tokens=6144,
            system=self._system_prompt_with_methodology(SYSTEM_PROMPT),
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
