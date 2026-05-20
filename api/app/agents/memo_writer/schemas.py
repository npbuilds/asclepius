"""Output shape for the Memo Writer agent.

The agent's run() returns this dict-form. The frontend renders body_markdown
verbatim and uses recommendation + red_flags to colour the result chip.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Recommendation = Literal["strong_buy", "buy", "hold", "cautious", "avoid"]


class MemoOutput(BaseModel):
    body_markdown: str = Field(
        description="Full memo, markdown, with required H2 sections."
    )
    executive_summary: str = Field(
        description="100-150 word stand-alone summary, also embedded inside body_markdown."
    )
    recommendation: Recommendation
    red_flags: list[str] = Field(
        default_factory=list,
        description="Critical concerns the memo body discusses in the Red flags section.",
    )
    model_used: str = Field(description="Anthropic model id or 'cache' if served from disk.")
    from_cache: bool
    generated_at: datetime
