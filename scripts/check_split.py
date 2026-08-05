#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Split gate for skill refactors.

Proves that moving content out of a SKILL.md body into reference/ lost nothing.
Run it after every body -> reference/ split, before the change is considered done.

Four gates:

  A  code preservation   Every fenced code-block line from the pre-split body
                         still exists in the body + reference/ union. Commands,
                         snippets and templates are the risk surface — losing one
                         silently changes what the skill tells the model to run.
  B  content trace       Every non-blank line removed from the body reappears in
                         reference/. Warn by default (prose gets reworded into
                         pointers during a legitimate split), error under --strict.
  C  always-loaded        Sections that must load on every run stayed in the body:
     sections            Rules, Gotchas, When NOT to Use. Only sections that
                         existed before the split are required after it.
  D  routing stability   Frontmatter description is byte-identical. The
                         description decides which prompts select the skill, so
                         changing it during a refactor is a behavioural change
                         wearing a refactor's clothes.

Stdlib-only. Human-readable text to stdout; --json for machine use.

Usage:
    python3 scripts/check_split.py <skill> --before <path-to-pre-split-SKILL.md>
    python3 scripts/check_split.py <skill> --base-ref HEAD
    python3 scripts/check_split.py <skill> --base-ref HEAD --strict
    python3 scripts/check_split.py <skill> --base-ref HEAD --json
    python3 scripts/check_split.py <skill> --base-ref HEAD --toolkit-dir /path

Exit codes:
    0  all gates passed
    1  a gate failed
    2  usage error (unknown skill, missing/duplicate source, unreadable git ref)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir as default_toolkit_dir

# Sections that carry prescriptive process and environment-specific traps.
# They must load on every run, so they never move down into reference/.
ALWAYS_LOADED_SECTIONS = ("Rules", "Gotchas", "When NOT to Use")

HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_block, body). Frontmatter is '' when absent."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "", text
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return "\n".join(lines[1:idx]), "\n".join(lines[idx + 1:])
    # Unterminated frontmatter — treat the whole file as body rather than
    # silently swallowing it.
    return "", text


def description_of(frontmatter: str) -> str:
    """Extract the `description:` value, unquoted, from a frontmatter block."""
    for line in frontmatter.splitlines():
        if not line.startswith("description:"):
            continue
        value = line[len("description:"):].strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
            value = value[1:-1]
        return value
    return ""


def fenced_code_lines(body: str) -> list[str]:
    """Return the lines strictly inside fenced code blocks, stripped, non-empty.

    Nested fences are not a thing in CommonMark: the first fence opens, a fence
    of the same character closes. Tracking the opening character avoids treating
    a ``` inside a ~~~ block as a terminator.
    """
    out: list[str] = []
    fence_char = ""
    for line in body.splitlines():
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)[0]
            if not fence_char:
                fence_char = marker
                continue
            if marker == fence_char:
                fence_char = ""
                continue
        if fence_char:
            stripped = line.strip()
            if stripped:
                out.append(stripped)
    return out


def normalize(line: str) -> str:
    """Normalize a prose line for comparison.

    Headings lose their leading hashes so that a section promoted from `###` in
    the body to `##` in a reference file still matches. Internal whitespace runs
    collapse so that reflowed markdown does not read as lost content.
    """
    stripped = line.strip()
    heading = HEADING_RE.match(stripped)
    if heading:
        stripped = heading.group(1).strip()
    return " ".join(stripped.split())


def nonblank_normalized(text: str) -> list[str]:
    return [n for n in (normalize(line) for line in text.splitlines()) if n]


def section_headings(body: str) -> set[str]:
    """Return the set of heading titles present in a body."""
    out: set[str] = set()
    fence_char = ""
    for line in body.splitlines():
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)[0]
            if not fence_char:
                fence_char = marker
            elif marker == fence_char:
                fence_char = ""
            continue
        if fence_char:
            continue
        heading = HEADING_RE.match(line)
        if heading:
            out.add(heading.group(1).strip())
    return out


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def gate_a_code(before_body: str, union_lines: set[str]) -> dict:
    """Every fenced code line from the pre-split body survives somewhere."""
    missing = [line for line in fenced_code_lines(before_body) if line not in union_lines]
    # Preserve order, drop repeats — a line repeated in three snippets is one
    # loss to fix, not three.
    seen: set[str] = set()
    unique = [line for line in missing if not (line in seen or seen.add(line))]
    return {
        "status": "pass" if not unique else "fail",
        "code_lines_lost": len(unique),
        "missing": unique,
    }


def gate_b_trace(before_body: str, after_body: str, reference_text: str,
                 strict: bool) -> dict:
    """Every non-blank line removed from the body reappears in reference/."""
    after_set = set(nonblank_normalized(after_body))
    reference_set = set(nonblank_normalized(reference_text))
    reference_blob = "\n".join(reference_set)

    unmatched: list[str] = []
    seen: set[str] = set()
    for line in nonblank_normalized(before_body):
        if line in after_set or line in seen:
            continue
        seen.add(line)
        if line in reference_set:
            continue
        # Substring match catches a pointer that reworded the original line
        # while keeping its content, e.g. a heading folded into a sentence.
        if line in reference_blob:
            continue
        unmatched.append(line)

    if not unmatched:
        status = "pass"
    else:
        status = "fail" if strict else "warn"
    return {
        "status": status,
        "unmatched_count": len(unmatched),
        "unmatched": unmatched,
    }


def gate_c_sections(before_body: str, after_body: str) -> dict:
    """Sections that must load on every run did not move into reference/."""
    before_headings = section_headings(before_body)
    after_headings = section_headings(after_body)
    missing = [
        name for name in ALWAYS_LOADED_SECTIONS
        if name in before_headings and name not in after_headings
    ]
    return {
        "status": "pass" if not missing else "fail",
        "missing": missing,
        "checked": [name for name in ALWAYS_LOADED_SECTIONS if name in before_headings],
    }


def gate_d_description(before_fm: str, after_fm: str) -> dict:
    """Routing must not move during a refactor."""
    before = description_of(before_fm)
    after = description_of(after_fm)
    return {
        "status": "pass" if before == after else "fail",
        "before": before,
        "after": after,
    }


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def read_before_from_git(tk_dir: Path, skill: str, ref: str) -> str:
    """Read the pre-split SKILL.md out of a git ref."""
    rel = f"app/skills/{skill}/SKILL.md"
    try:
        result = subprocess.run(
            ["git", "-C", str(tk_dir), "show", f"{ref}:{rel}"],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as exc:  # git missing, bad argument shape
        fail_usage(f"cannot run git: {exc}")
    if result.returncode != 0:
        fail_usage(
            f"cannot read {rel} at ref '{ref}': "
            f"{result.stderr.strip() or 'git exited ' + str(result.returncode)}"
        )
    return result.stdout


def read_reference_text(skill_dir: Path) -> tuple[str, list[str]]:
    """Concatenate every reference/*.md file. Returns (text, filenames)."""
    ref_dir = skill_dir / "reference"
    if not ref_dir.is_dir():
        return "", []
    chunks: list[str] = []
    names: list[str] = []
    for path in sorted(ref_dir.rglob("*.md")):
        chunks.append(path.read_text(encoding="utf-8"))
        names.append(str(path.relative_to(skill_dir)))
    return "\n".join(chunks), names


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def fail_usage(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(2)


def parse_args(argv: list[str]) -> dict:
    opts = {
        "skill": "",
        "before": "",
        "base_ref": "",
        "toolkit_dir": str(default_toolkit_dir),
        "json": False,
        "strict": False,
    }
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--json":
            opts["json"] = True
        elif arg == "--strict":
            opts["strict"] = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        elif arg in ("--before", "--base-ref", "--toolkit-dir"):
            idx += 1
            if idx >= len(argv):
                fail_usage(f"{arg} requires a value")
            key = arg.lstrip("-").replace("-", "_")
            opts[key] = argv[idx]
        elif arg.startswith("-"):
            fail_usage(f"unknown option: {arg}")
        elif not opts["skill"]:
            opts["skill"] = arg
        else:
            fail_usage(f"unexpected argument: {arg}")
        idx += 1
    return opts


def report_text(result: dict) -> None:
    gates = result["gates"]
    print(f"## Split gate — {result['skill']}")
    print()

    code = gates["A_code_preservation"]
    print(f"  code lines lost: {code['code_lines_lost']}")
    for line in code["missing"][:20]:
        print(f"    LOST: {line}")
    if len(code["missing"]) > 20:
        print(f"    ... and {len(code['missing']) - 20} more")

    trace = gates["B_content_trace"]
    label = "ERROR" if trace["status"] == "fail" else "WARN"
    if trace["unmatched_count"]:
        print(f"  {label}: {trace['unmatched_count']} removed lines not found in reference/")
        for line in trace["unmatched"][:20]:
            print(f"    UNTRACED: {line}")
        if trace["unmatched_count"] > 20:
            print(f"    ... and {trace['unmatched_count'] - 20} more")
    else:
        print("  OK: every removed line traced to reference/")

    sections = gates["C_always_loaded_sections"]
    if sections["missing"]:
        print(f"  ERROR: always-loaded sections left the body: {', '.join(sections['missing'])}")
    else:
        checked = ", ".join(sections["checked"]) or "none present"
        print(f"  OK: always-loaded sections intact ({checked})")

    desc = gates["D_description_stable"]
    if desc["status"] == "fail":
        print("  ERROR: frontmatter description changed — routing moved")
        print(f"    before: {desc['before']}")
        print(f"    after:  {desc['after']}")
    else:
        print("  OK: description unchanged")

    print()
    print(f"  body: {result['body_before_bytes']} -> {result['body_after_bytes']} bytes")
    print(f"  reference files: {len(result['reference_files'])}")
    print()
    print("SPLIT GATE PASSED" if result["ok"] else "SPLIT GATE FAILED")


def main(argv: list[str]) -> int:
    opts = parse_args(argv)

    if not opts["skill"]:
        fail_usage("missing skill name")
    if bool(opts["before"]) == bool(opts["base_ref"]):
        fail_usage("pass exactly one of --before <path> or --base-ref <ref>")

    tk_dir = Path(opts["toolkit_dir"]).resolve()
    skill_dir = tk_dir / "app" / "skills" / opts["skill"]
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        fail_usage(f"no SKILL.md at {skill_file}")

    if opts["before"]:
        before_path = Path(opts["before"])
        if not before_path.is_file():
            fail_usage(f"--before file not found: {before_path}")
        before_text = before_path.read_text(encoding="utf-8")
    else:
        before_text = read_before_from_git(tk_dir, opts["skill"], opts["base_ref"])

    after_text = skill_file.read_text(encoding="utf-8")
    before_fm, before_body = split_frontmatter(before_text)
    after_fm, after_body = split_frontmatter(after_text)
    reference_text, reference_files = read_reference_text(skill_dir)

    union_lines = {
        line.strip()
        for line in (after_body + "\n" + reference_text).splitlines()
        if line.strip()
    }

    gates = {
        "A_code_preservation": gate_a_code(before_body, union_lines),
        "B_content_trace": gate_b_trace(before_body, after_body, reference_text, opts["strict"]),
        "C_always_loaded_sections": gate_c_sections(before_body, after_body),
        "D_description_stable": gate_d_description(before_fm, after_fm),
    }
    ok = all(gate["status"] != "fail" for gate in gates.values())

    result = {
        "skill": opts["skill"],
        "strict": opts["strict"],
        "gates": gates,
        "body_before_bytes": len(before_body.encode("utf-8")),
        "body_after_bytes": len(after_body.encode("utf-8")),
        "reference_files": reference_files,
        "ok": ok,
    }

    if opts["json"]:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        report_text(result)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
