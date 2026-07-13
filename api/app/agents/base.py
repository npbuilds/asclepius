"""BaseAgent ABC — implemented by runtime agents in v1.1.

Each agent has a narrow contract:
  * manifest declares id, methodology_refs, model, cached_assets, etc.
  * `run(record)` returns a structured result that gets serialized to the
    /api/agents/<id>/run response

The constructor receives the manifest and the agent's directory so subclasses
can find their cache/ subfolder and prompt assets without hardcoded paths.

v1.1.3 — methodology loading is now a runtime contract:
  * AgentManifest.methodology_refs lists paths into the public methodology/
    folder. BaseAgent._load_methodology_context() reads them at init time
    and exposes them via the `methodology_context` attribute.
  * Each agent's _live_call() prepends self.methodology_context to its
    SYSTEM_PROMPT before sending to the API. This means the agents and the
    methodology page render the same source-of-truth content — they cannot
    drift.
  * The methodology root is resolved from the ASCLEPIUS_METHODOLOGY_DIR
    environment variable, defaulting to the methodology/ folder bundled
    into the container by the Dockerfile (../methodology relative to
    api/app/main.py). If a file is missing, the agent logs a warning and
    omits that section — failure is graceful.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..domain import DiligenceRecord

if TYPE_CHECKING:
    from ..registry import AgentManifest

log = logging.getLogger(__name__)


def _resolve_methodology_dir() -> Path:
    """Look up the methodology directory.

    Order of precedence:
      1. ASCLEPIUS_METHODOLOGY_DIR env var (used in local dev pointing at the
         repo's methodology/ folder).
      2. The methodology/ directory inside the api package (copied in by the
         Dockerfile for production).
      3. The repo's methodology/ folder relative to api/ (local dev fallback).
    """
    override = os.getenv("ASCLEPIUS_METHODOLOGY_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        if path.is_dir():
            return path
    pkg_path = Path(__file__).resolve().parent.parent / "methodology"
    if pkg_path.is_dir():
        return pkg_path
    repo_path = Path(__file__).resolve().parents[3] / "methodology"
    if repo_path.is_dir():
        return repo_path
    return pkg_path  # may not exist; caller will get empty context


class BaseAgent(ABC):
    """All runtime agents subclass this."""

    def __init__(self, manifest: "AgentManifest", agent_dir: Path) -> None:
        self.manifest = manifest
        self.agent_dir = agent_dir
        self.methodology_context: str = self._load_methodology_context()

    @property
    def id(self) -> str:
        return self.manifest.id

    def _load_methodology_context(self) -> str:
        """Read each file listed in manifest.methodology_refs and concatenate.

        Returns "" if no refs are declared or no files load. Each loaded file
        is delimited with a "=== <filename> ===" header so the model can
        attribute claims to specific sources.
        """
        refs = self.manifest.methodology_refs
        if not refs:
            return ""
        root = _resolve_methodology_dir()
        chunks: list[str] = []
        for ref in refs:
            path = (root / ref).resolve()
            # Defensive: don't follow symlinks or escape the methodology root
            try:
                path.relative_to(root)
            except ValueError:
                log.warning(
                    "agent %s methodology_ref %s escapes methodology root; skipping",
                    self.manifest.id,
                    ref,
                )
                continue
            if not path.is_file():
                log.warning(
                    "agent %s methodology_ref not found at %s; skipping",
                    self.manifest.id,
                    path,
                )
                continue
            try:
                content = path.read_text()
            except OSError as exc:
                log.warning(
                    "agent %s could not read methodology_ref %s: %s",
                    self.manifest.id,
                    path,
                    exc,
                )
                continue
            chunks.append(f"=== {ref} ===\n{content.strip()}")
        if not chunks:
            return ""
        header = (
            "The following methodology writeups are loaded into your "
            "context. Cite them where your analysis invokes their framing.\n\n"
        )
        return header + "\n\n".join(chunks)

    def _system_prompt_with_methodology(self, base_prompt: str) -> str:
        """Helper for subclasses — prepend methodology context to the base
        system prompt. If no methodology is loaded, returns base_prompt
        unchanged."""
        if not self.methodology_context:
            return base_prompt
        return f"{self.methodology_context}\n\n---\n\n{base_prompt}"

    def maybe_cached(self, record: DiligenceRecord) -> dict[str, Any] | None:
        """Return a pre-computed cached response for this record if one exists,
        WITHOUT doing any money-spending work; else None.

        Default: no cache (agents that don't cache never short-circuit). Caching
        agents override to delegate to their private cache lookup. The access
        gate uses this so FREE (cached) responses can be served without the
        passphrase, while money-spending LIVE calls stay gated. See
        app/agents/routes.py.
        """
        return None

    @abstractmethod
    def run(self, record: DiligenceRecord) -> dict[str, Any]:
        """Run the agent against a diligence record.

        Returns a dict whose keys match the manifest's `output_fields`. The
        caller serializes this to the HTTP response without further shaping.
        """
