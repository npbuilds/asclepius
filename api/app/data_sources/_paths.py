"""Filesystem helpers shared by data-source modules."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=16)
def load_json(filename: str) -> dict[str, Any]:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"data file not found: {path}")
    return json.loads(path.read_text())
