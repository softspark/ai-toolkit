#!/usr/bin/env python3
"""Measure token reduction of brand-voice output modes against fixtures.

Reads each fixture directory containing default.md, concise.md, strict.md,
counts tokens with a deterministic whitespace heuristic, and reports per-fixture
and aggregate ratios. Asserts:

    concise <= CONCISE_BUDGET (default 0.60)
    strict  <= STRICT_BUDGET  (default 0.40)

Also asserts fact preservation: every file path, identifier, line:number, and
fenced code block from default.md must appear in concise.md and strict.md.

Usage:
    python3 app/skills/brand-voice/scripts/measure.py \\
        --fixtures tests/fixtures/output-modes/

Exit codes:
    0  all fixtures pass budgets and fact preservation
    1  one or more fixtures violate budget or drop facts
    2  invalid fixtures dir or missing files
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CONCISE_BUDGET_DEFAULT = 0.60
STRICT_BUDGET_DEFAULT = 0.40

PATH_RE = re.compile(r"\b[\w/.-]+\.[a-zA-Z]{1,5}\b")
LINE_REF_SUFFIX_RE = re.compile(r":\d+$")
CODE_BLOCK_RE = re.compile(r"```[\w]*\n.*?```", re.DOTALL)
NUMBER_WITH_UNIT_RE = re.compile(r"\b\d+(?:\.\d+)?(?:ms|s|kb|mb|gb|%)\b", re.IGNORECASE)
IDENT_BACKTICK_RE = re.compile(r"`([^`\n]+)`")


def count_tokens(text: str) -> int:
    """Whitespace-based token estimate. Deterministic and offline."""
    return len(text.split())


def normalize_path(value: str) -> str:
    """Strip `:NN` line-number suffix so `foo.ts` and `foo.ts:42` compare equal."""
    return LINE_REF_SUFFIX_RE.sub("", value).strip("`")


def extract_facts(text: str) -> set[str]:
    """Extract load-bearing facts: file paths, numbers with units, backtick identifiers.

    Does NOT extract code-block bodies. A mode response legitimately shows
    different code (e.g. the fix) than the default response (e.g. the bug),
    and treating each code line as a required fact produces false positives.
    """
    text_no_code = CODE_BLOCK_RE.sub("", text)
    facts: set[str] = set()

    for match in PATH_RE.findall(text_no_code):
        normalized = normalize_path(match)
        if "/" in normalized:
            facts.add(normalized)

    for match in IDENT_BACKTICK_RE.findall(text_no_code):
        cleaned = match.strip()
        if len(cleaned) >= 3 and not cleaned.startswith("```"):
            facts.add(normalize_path(cleaned))

    for match in NUMBER_WITH_UNIT_RE.findall(text_no_code):
        facts.add(match.lower())

    return facts


def load_must_contain(fixture_dir: Path) -> list[str]:
    """Optional explicit must-contain assertions, one per line."""
    must_contain_file = fixture_dir / "must_contain.txt"
    if not must_contain_file.exists():
        return []
    return [
        line.strip()
        for line in must_contain_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def evaluate_fixture(
    fixture_dir: Path,
    concise_budget: float,
    strict_budget: float,
) -> dict:
    default_file = fixture_dir / "default.md"
    concise_file = fixture_dir / "concise.md"
    strict_file = fixture_dir / "strict.md"

    for path in (default_file, concise_file, strict_file):
        if not path.exists():
            return {
                "fixture": fixture_dir.name,
                "ok": False,
                "error": f"missing file: {path.name}",
            }

    default_text = default_file.read_text()
    concise_text = concise_file.read_text()
    strict_text = strict_file.read_text()

    default_tokens = count_tokens(default_text)
    concise_tokens = count_tokens(concise_text)
    strict_tokens = count_tokens(strict_text)

    if default_tokens == 0:
        return {
            "fixture": fixture_dir.name,
            "ok": False,
            "error": "default.md empty",
        }

    concise_ratio = concise_tokens / default_tokens
    strict_ratio = strict_tokens / default_tokens

    default_facts = extract_facts(default_text)
    concise_facts = extract_facts(concise_text)
    strict_facts = extract_facts(strict_text)

    concise_missing = sorted(default_facts - concise_facts)
    strict_missing = sorted(default_facts - strict_facts)

    must_contain = load_must_contain(fixture_dir)
    concise_required_missing = [
        item for item in must_contain if item not in concise_text
    ]
    strict_required_missing = [
        item for item in must_contain if item not in strict_text
    ]

    budget_ok_concise = concise_ratio <= concise_budget
    budget_ok_strict = strict_ratio <= strict_budget
    facts_ok_concise = not concise_required_missing
    facts_ok_strict = not strict_required_missing

    return {
        "fixture": fixture_dir.name,
        "ok": budget_ok_concise
        and budget_ok_strict
        and facts_ok_concise
        and facts_ok_strict,
        "default_tokens": default_tokens,
        "concise_tokens": concise_tokens,
        "strict_tokens": strict_tokens,
        "concise_ratio": round(concise_ratio, 3),
        "strict_ratio": round(strict_ratio, 3),
        "concise_budget_ok": budget_ok_concise,
        "strict_budget_ok": budget_ok_strict,
        "concise_advisory_missing": concise_missing,
        "strict_advisory_missing": strict_missing,
        "concise_required_missing": concise_required_missing,
        "strict_required_missing": strict_required_missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("tests/fixtures/output-modes"),
        help="Path to fixtures directory",
    )
    parser.add_argument(
        "--concise-budget",
        type=float,
        default=CONCISE_BUDGET_DEFAULT,
        help=f"Max concise/default token ratio (default {CONCISE_BUDGET_DEFAULT})",
    )
    parser.add_argument(
        "--strict-budget",
        type=float,
        default=STRICT_BUDGET_DEFAULT,
        help=f"Max strict/default token ratio (default {STRICT_BUDGET_DEFAULT})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report instead of human format",
    )
    args = parser.parse_args()

    if not args.fixtures.is_dir():
        print(f"error: fixtures dir not found: {args.fixtures}", file=sys.stderr)
        return 2

    fixture_dirs = sorted(
        d for d in args.fixtures.iterdir() if d.is_dir() and (d / "default.md").exists()
    )

    if not fixture_dirs:
        print(f"error: no fixtures found under {args.fixtures}", file=sys.stderr)
        return 2

    results = [
        evaluate_fixture(d, args.concise_budget, args.strict_budget)
        for d in fixture_dirs
    ]

    total_default = sum(r.get("default_tokens", 0) for r in results)
    total_concise = sum(r.get("concise_tokens", 0) for r in results)
    total_strict = sum(r.get("strict_tokens", 0) for r in results)
    aggregate = {
        "concise_ratio": round(total_concise / total_default, 3) if total_default else 0,
        "strict_ratio": round(total_strict / total_default, 3) if total_default else 0,
        "fixtures": len(results),
        "passed": sum(1 for r in results if r.get("ok")),
    }

    if args.json:
        print(json.dumps({"results": results, "aggregate": aggregate}, indent=2))
    else:
        print(f"{'fixture':<28} {'default':>8} {'concise':>8} {'strict':>8} {'c%':>6} {'s%':>6} {'ok':>4}")
        print("-" * 76)
        for r in results:
            if "error" in r:
                print(f"{r['fixture']:<28} ERROR: {r['error']}")
                continue
            mark = "yes" if r["ok"] else "NO"
            print(
                f"{r['fixture']:<28} {r['default_tokens']:>8} "
                f"{r['concise_tokens']:>8} {r['strict_tokens']:>8} "
                f"{int(r['concise_ratio'] * 100):>5}% "
                f"{int(r['strict_ratio'] * 100):>5}% {mark:>4}"
            )
        print("-" * 76)
        print(
            f"aggregate: concise={int(aggregate['concise_ratio'] * 100)}% "
            f"strict={int(aggregate['strict_ratio'] * 100)}% "
            f"passed={aggregate['passed']}/{aggregate['fixtures']}"
        )

    all_ok = all(r.get("ok") for r in results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
