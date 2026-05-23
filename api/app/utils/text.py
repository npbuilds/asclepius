"""Shared text utilities for the Asclepius API.

`slugify_asset_name` was duplicated across four modules (memo_writer,
game_theory_adversary, auto_diligence, the public-log sync script) before
v1.6.1 — extracted here to one canonical implementation per the Codex
F9 finding. All call sites import this version; the per-module copies
keep a thin alias for backward compatibility within the same module.

The slug rule is deliberately conservative — lowercase, replace any run
of non-`[a-z0-9_]` characters with `_`, strip leading/trailing
underscores, fall back to "unnamed" for empty input. This is what
several existing on-disk artifacts (agent caches, predictions JSON
filenames, seed_data.json prediction ids) were already generated with;
changing the rule would invalidate those artifacts and force a
regeneration cycle.
"""

from __future__ import annotations

import re

_NON_SLUG_CHAR = re.compile(r"[^a-z0-9_]+")


def slugify_asset_name(name: str) -> str:
    """Canonicalize an asset name into a filesystem/URL-safe slug.

    Examples:
      "adagrasib"                       -> "adagrasib"
      "adagrasib (MRTX849)"             -> "adagrasib_mrtx849"
      "Datopotamab Deruxtecan (Dato-DXd)" -> "datopotamab_deruxtecan_dato_dxd"
      "ADAGRASIB"                       -> "adagrasib"
      ""                                -> "unnamed"
    """
    cleaned = _NON_SLUG_CHAR.sub("_", name.lower())
    return cleaned.strip("_") or "unnamed"
