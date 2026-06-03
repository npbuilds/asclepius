"""Methodology ↔ data-layer parity lint.

Catches numeric drift between `methodology/*.md` writeups and the reference
data they cite (`api/app/data/*.json` + selected engine constants in
`api/app/modules/*/engine.py`).

How it works:
  1. Build a numeric *index* from the data layer — every leaf-level number
     in the JSON files, plus engine-constant declarations matching the
     `_UPPER_CASE = 0.123` pattern. Each indexed value carries its
     source path so we can report which file backs which number.
  2. For each `methodology/*.md`, extract every percentage token
     (e.g. "28.9%", "10%") and convert to a probability decimal.
  3. Each extracted percentage falls into one of four classes:
       - MATCH       — value within ±tolerance of some indexed number
       - CITATION    — line cites an external paper (Doane / Wong / BIO 20XX
                       / Informa / Damodaran / Williamson / etc.); these
                       are expected to NOT match the data layer
       - COMPARISON  — line uses comparison markers (">", "<", "≥", "≤",
                       "around", "approximately", "~", "≈") which signal
                       the number is descriptive, not a precise lookup
       - ORPHAN      — neither matched nor explainable; deserves human eyes
  4. Print a digest. Exit 0 on success (orphans are informational, not
     errors); exit 2 only when the data-layer index is empty (script bug).

This is `detect, don't prevent`. False positives are acceptable — every
orphan is a 30-second human check, not a CI failure. The MVP design from
the plan: "tiny lint script... cheap insurance against drift."

Run with:
    python scripts/check_methodology_parity.py
    python scripts/check_methodology_parity.py --verbose       # show MATCH+CITATION lines
    python scripts/check_methodology_parity.py --tolerance 0.01  # ±1pp instead of ±0.5pp
    python scripts/check_methodology_parity.py --files methodology/01-pos-framework.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "api" / "app" / "data"
MODULES_DIR = REPO_ROOT / "api" / "app" / "modules"
METHODOLOGY_DIR = REPO_ROOT / "methodology"

# Percentage token: `12%`, `12.5%`, but NOT `1%-2%` ranges (just match
# each side) and NOT inside code (we strip those before extracting).
PERCENT_RE = re.compile(r"(?<!\d\.)(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%")

# A line containing any of these strings is treated as a citation/baseline/
# derived-statistic, so its numeric values are EXPECTED to live outside our
# data layer. Curated from auditing the existing methodology writeups.
CITATION_MARKERS = (
    # External-paper citations
    "doane", "wong", "bio 20", "biotechnology innovation", "informa",
    "damodaran", "williamson", "hwang", "mao", "soros", "ma et al",
    "fu et al", "gao et al", "ct open", "lo & thakor", "lo and thakor",
    "spence ", "spence (", "publishe", "literature", "et al",
    # Worked-example asset names + deal refs (numbers are case-specific,
    # not portfolio-wide reference data)
    "kras", "sotorasib", "krystal-", "bms",
    # Year-suffix citations
    "(2018)", "(2019)", "(2020)", "(2021)",
    "(2022)", "(2023)", "(2024)", "(2025)", "(2026)",
    # Derived statistics (model outputs, corpus stats, fetch coverage) —
    # these are computed from the system or from datasets, not values the
    # methodology owes the JSON data layer.
    "auc", "brier", "f1",         # model metrics
    "base rate", "success rate",  # corpus-level statistics
    "coverage",                   # data-fetch coverage stats
    "ml prior", "model artifact", "v1.5", "v0.",  # versioned model output refs
    "ph2 =", "ph3 =", "ph1 =",    # per-phase outcome descriptions
    "cto", "hint",                # corpus-name-tagged statistics
    "rank ",                      # feature-importance ranks
    "p25", "p50", "p75",          # monte-carlo / bootstrap percentile reports
    "monte carlo", "bootstrap",
    "parseable", "fetch ",        # recon / coverage probe reports
    "% of bootstrap",             # bootstrap-positive-fraction reports
    # Configuration values (declared in code constants not in data/*.json)
    "position floor", "kelly floor", "barbell",
    "ml-vs-rule disagreement", "disagreement ",
)

# Comparison / approximation markers — the number is descriptive, not a
# precise lookup, so a mismatch shouldn't flag as ORPHAN.
COMPARISON_MARKERS = (
    ">", "<", "≥", "≤", "≈", "~",
    "around", "approximately", "roughly", "about ",
    "more than", "less than", "at least", "at most",
    "compared to", "vs ", "versus ",
    "n=",  # sample size in stat reports
)

# Engine-constant pattern: `_NAME = 0.XX`, `NAME = 0.XX`, etc. We capture
# any module-level numeric assignment whose RHS looks like a probability
# or multiplier in the [-1, 5] range — those are the values that
# methodology actually cites.
ENGINE_CONST_RE = re.compile(
    r"^([A-Z_][A-Z0-9_]*)\s*=\s*(-?\d+\.\d+)\b", re.MULTILINE
)


@dataclass
class IndexedNumber:
    value: float        # canonical form: a decimal probability/multiplier
    source: str         # e.g. "api/app/data/base_rates.json#transitions[2].p2_to_p3"

    def __hash__(self) -> int:
        return hash((round(self.value, 4), self.source))


@dataclass
class ExtractedClaim:
    line_no: int
    line: str
    raw_token: str       # e.g. "28.9%"
    value: float         # 0.289
    classification: str  # MATCH | CITATION | COMPARISON | ORPHAN
    match_source: str | None = None


def walk_json(obj, path: str, out: list[IndexedNumber]) -> None:
    """Recursively flatten a JSON object into IndexedNumber rows.

    Numeric *leaves* are emitted with their JSON-pointer-ish path. We
    skip schema-version and other clearly non-data-layer fields.
    """
    SKIP_KEYS = {"schema_version", "year", "completion_year",
                 "deal_year", "year_announced"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            walk_json(v, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_json(v, f"{path}[{i}]", out)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        # Plausibility filter: drift lint targets probabilities + multipliers,
        # not raw dollar amounts. Skip values > 100 — those are deal sizes
        # ($4800M), patient counts, etc., and won't be linted against
        # methodology percentages anyway.
        if -2.0 <= obj <= 100.0:
            out.append(IndexedNumber(value=float(obj), source=path))


def build_index() -> list[IndexedNumber]:
    """Walk api/app/data/*.json + extract engine constants. Return the
    full indexed set with normalized values."""
    index: list[IndexedNumber] = []

    # JSON files (recursive)
    for jp in sorted(DATA_DIR.rglob("*.json")):
        try:
            data = json.loads(jp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"WARN: could not parse {jp}: {e}", file=sys.stderr)
            continue
        rel = jp.relative_to(REPO_ROOT)
        walk_json(data, str(rel), index)

    # Engine constants
    for ep in sorted(MODULES_DIR.rglob("engine.py")):
        text = ep.read_text(encoding="utf-8")
        rel = ep.relative_to(REPO_ROOT)
        for m in ENGINE_CONST_RE.finditer(text):
            name, raw_val = m.group(1), m.group(2)
            try:
                v = float(raw_val)
            except ValueError:
                continue
            if -2.0 <= v <= 100.0:
                index.append(IndexedNumber(value=v, source=f"{rel}#{name}"))

    return index


def classify_line(line: str) -> str | None:
    """Return CITATION or COMPARISON if the line carries a context marker
    that excuses a numeric from matching the data layer; else None.
    Case-insensitive matching against the lowercased line."""
    low = line.lower()
    for marker in CITATION_MARKERS:
        if marker in low:
            return "CITATION"
    for marker in COMPARISON_MARKERS:
        if marker in low:
            return "COMPARISON"
    return None


def strip_code_and_inline_code(md: str) -> str:
    """Remove fenced code blocks + inline-code spans. Numeric values inside
    code are usually examples (e.g., LightGBM hyperparams), not data-layer
    citations, so they shouldn't be linted against the JSON layer."""
    # Fenced code blocks
    md = re.sub(r"```.*?```", "", md, flags=re.DOTALL)
    # Inline-code spans
    md = re.sub(r"`[^`\n]+`", "", md)
    return md


def lint_file(
    path: Path,
    index: list[IndexedNumber],
    tolerance: float,
) -> list[ExtractedClaim]:
    """Extract percentage claims from one markdown file and classify each."""
    raw = path.read_text(encoding="utf-8")
    cleaned = strip_code_and_inline_code(raw)

    claims: list[ExtractedClaim] = []
    for line_no, line in enumerate(cleaned.splitlines(), start=1):
        for match in PERCENT_RE.finditer(line):
            raw_token = match.group(0)
            raw_pct = float(match.group(1))
            value = raw_pct / 100.0  # canonical decimal probability

            # Try to match against the index
            best = None
            for ind in index:
                if abs(ind.value - value) <= tolerance:
                    best = ind
                    break

            classification: str
            source: str | None = None
            if best is not None:
                classification = "MATCH"
                source = best.source
            else:
                ctx = classify_line(line)
                classification = ctx or "ORPHAN"

            claims.append(ExtractedClaim(
                line_no=line_no,
                line=line.strip(),
                raw_token=raw_token,
                value=value,
                classification=classification,
                match_source=source,
            ))

    return claims


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tolerance", type=float, default=0.005,
                    help="Match tolerance in decimal probability units (default 0.005 = ±0.5pp).")
    ap.add_argument("--verbose", action="store_true",
                    help="Print MATCH + CITATION + COMPARISON lines, not just ORPHANS.")
    ap.add_argument("--files", nargs="*",
                    help="Specific methodology files to lint; default all.")
    args = ap.parse_args(argv)

    if not METHODOLOGY_DIR.is_dir():
        print(f"ERROR: methodology dir not found at {METHODOLOGY_DIR}", file=sys.stderr)
        return 2

    index = build_index()
    if not index:
        print("ERROR: data-layer index is empty. Are JSON files missing?", file=sys.stderr)
        return 2
    print(f"Indexed {len(index)} numeric values from "
          f"{len({i.source.split('#')[0] for i in index})} source files\n")

    if args.files:
        # Accept both absolute and CWD-relative paths; normalize via resolve()
        # so the later relative_to(REPO_ROOT) works regardless of how the
        # user typed the argument (e.g. `methodology/01-pos-framework.md` or
        # an absolute path from a different CWD).
        targets = [Path(f).resolve() for f in args.files]
    else:
        targets = sorted(METHODOLOGY_DIR.glob("*.md"))

    totals = {"MATCH": 0, "CITATION": 0, "COMPARISON": 0, "ORPHAN": 0}
    orphans_by_file: dict[str, list[ExtractedClaim]] = {}

    for path in targets:
        if not path.is_file():
            print(f"  ! missing: {path}")
            continue
        claims = lint_file(path, index, tolerance=args.tolerance)
        file_counts = {"MATCH": 0, "CITATION": 0, "COMPARISON": 0, "ORPHAN": 0}
        for c in claims:
            file_counts[c.classification] += 1
            totals[c.classification] += 1
        rel = path.relative_to(REPO_ROOT)
        print(f"{rel}: {len(claims)} %-claims  "
              f"MATCH={file_counts['MATCH']}  "
              f"CITATION={file_counts['CITATION']}  "
              f"COMPARISON={file_counts['COMPARISON']}  "
              f"ORPHAN={file_counts['ORPHAN']}")

        orphans = [c for c in claims if c.classification == "ORPHAN"]
        if orphans:
            orphans_by_file[str(rel)] = orphans

        if args.verbose:
            for c in claims:
                tag = c.classification
                src = f" → {c.match_source}" if c.match_source else ""
                print(f"  [{tag:10}] L{c.line_no} {c.raw_token}{src}")
                if tag == "ORPHAN":
                    print(f"             ↳ {c.line[:120]}")

    print()
    print(f"=== TOTALS ===")
    print(f"  MATCH:      {totals['MATCH']:>4}  ({100*totals['MATCH']/max(sum(totals.values()),1):.1f}%)")
    print(f"  CITATION:   {totals['CITATION']:>4}  (numbers from cited papers; expected to NOT match)")
    print(f"  COMPARISON: {totals['COMPARISON']:>4}  (descriptive: >X%, ~X%, around X%)")
    print(f"  ORPHAN:     {totals['ORPHAN']:>4}  (no match + no context marker — review)")

    if orphans_by_file and not args.verbose:
        print()
        print(f"=== ORPHAN claims (likely drift OR uncaught citation; review each) ===")
        for fname, orphans in orphans_by_file.items():
            print(f"\n{fname}:")
            for c in orphans:
                print(f"  L{c.line_no} {c.raw_token}: {c.line[:110]}")

    # Always exit 0 — this is informational, not a CI gate. To make it a
    # gate, change the next line to: return 1 if totals["ORPHAN"] else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
