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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ...domain import DiligenceRecord
from ..base import BaseAgent
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .schemas import MemoContent, MemoOutput

log = logging.getLogger(__name__)

# v1.6.1: slugify moved to app.utils.text (Codex F9). Kept as a thin
# alias here so existing internal call sites + the test imports keep
# working without surface churn.
from ...utils.text import slugify_asset_name as _slugify_asset_name  # noqa: E402,F401


# v1.9.2: tool-use replaces prose parsing. tool_choice forces the model to call
# emit_memo, whose input_schema is MemoContent's JSON Schema — the Anthropic API
# validates structure before returning, so `block.input` is already a dict
# matching MemoContent. No fenced-JSON, no recovery parser, no empty-memo class.
MEMO_TOOL = {
    "name": "emit_memo",
    "description": (
        "Emit the complete structured investment memo. Every field is required "
        "— fill all sections; do not omit any."
    ),
    "input_schema": MemoContent.model_json_schema(),
}


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
        if pos.get("supply_note"):
            parts.append("\n" + pos["supply_note"].strip())

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
        rec_bits: list[str] = []
        if close.get("recommendation"):
            rec_bits.append(f"**Call:** {close['recommendation'].replace('_', ' ')}")
        if close.get("conviction"):
            rec_bits.append(f"**Conviction:** {close['conviction']}")
        if rec_bits:
            parts.append("  \n".join(rec_bits))
        if close.get("path_dependency_verdict"):
            parts.append(
                f"\n**Path-dependency verdict:** {close['path_dependency_verdict'].strip()}"
            )
        if close.get("closing_paragraph"):
            parts.append("\n" + close["closing_paragraph"].strip())
        if close.get("kill_criterion"):
            parts.append(f"\n**Kill criterion:** {close['kill_criterion'].strip()}")

    return "\n".join(parts).strip()


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

    def _assemble_from_tool(self, message, model_used: str) -> dict[str, Any]:
        """Build MemoOutput from the forced emit_memo tool call.

        tool_choice guarantees a tool_use block whose .input the API already
        validated against MemoContent's schema. We re-validate through
        MemoContent (belt-and-suspenders), render the back-compat
        body_markdown, and wrap with the envelope fields. No prose parsing,
        so the empty-memo failure class (v1.7.10) cannot recur.
        """
        tool_block = next(
            (
                b
                for b in message.content
                if getattr(b, "type", None) == "tool_use"
                and getattr(b, "name", None) == "emit_memo"
            ),
            None,
        )
        if tool_block is None:
            raise HTTPException(
                status_code=502,
                detail="Memo Writer model did not return the expected memo tool output.",
            )
        content = MemoContent(**tool_block.input)
        parsed = content.model_dump()
        out = MemoOutput(
            **parsed,
            body_markdown=_render_body_markdown(parsed),
            model_used=model_used,
            from_cache=False,
            generated_at=datetime.now(timezone.utc),
        )
        return out.model_dump(mode="json")

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
            tools=[MEMO_TOOL],
            tool_choice={"type": "tool", "name": "emit_memo"},
            messages=[{"role": "user", "content": user_prompt}],
        )
        return self._assemble_from_tool(message, model_used=model)

    # ---- BaseAgent contract ----

    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        cached = self._maybe_cached(record)
        if cached is not None:
            return cached
        return self._live_call(record)
