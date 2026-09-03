#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate knowledge skills from the top-level rule files in ``app/rules/``.

Each ``app/rules/<stem>.md`` becomes ``app/skills/<stem>/SKILL.md``. The
per-language directories are not touched here; ``generate_language_rules_skills``
owns those.

Why this exists
---------------
The rules were reachable only as Claude Code user-level files under
``~/.claude/rules/``, with the global ``CLAUDE.md`` carrying a pointer to them
rather than their content. That pointer is a Claude Code idiom. DeepSeek Harness
reads ``AGENTS.md``, ``AGENTS.local.md``, ``CLAUDE.md`` and ``CLAUDE.local.md``
and has no rules-directory support at all, so under DSH every one of those rules
was inert: named in an injected file, never loaded, never applied.

Shipping them as skills fixes that without changing the Claude Code surface. A
skill is discovered by every editor that reads the shared skill catalogue, and
the catalogue injects each skill's *description* into the session. So the
description here is written as the rule itself in one imperative line — it is in
context whether or not the model chooses to load the body.

Idempotent: rerunning overwrites the generated ``SKILL.md`` and leaves anything
else in the skill directory alone.

Usage:
    python3 scripts/generate_toolkit_rules_skills.py            # write all
    python3 scripts/generate_toolkit_rules_skills.py --check    # dry-run
    python3 scripts/generate_toolkit_rules_skills.py --rules git-conventions
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "app" / "rules"
SKILLS_DIR = ROOT / "app" / "skills"

# The description is the rule. It is injected into every session through the
# skill catalogue, so it has to state the obligation on its own — a reader who
# never opens the body should still know what is required. Keep it imperative,
# keep it one line, and put the reasoning in the file under app/rules/.
DESCRIPTIONS: dict[str, str] = {
    "edit-discipline": (
        "Change files with the edit and write tools, never by rewriting them "
        "through bash (sed, awk, tee, heredoc, redirection), and show `git diff` "
        "before reporting a file-changing task as done. "
        "Triggers: edit, write, modify, refactor, patch, fix, diff, review changes."
    ),
    "git-conventions": (
        "Conventional Commits only (feat, fix, docs, refactor, test, chore); no "
        "AI co-authorship trailer and no AI signature in a commit message. "
        "Triggers: commit, git, message, changelog, release, pull request."
    ),
    "output-mode": (
        "Answer concisely: lead with the result, no preamble, tables over prose, "
        "no trailing restatement of a diff the reader can already see. "
        "Triggers: response style, verbosity, summary, explanation, report."
    ),
    "quality-gates": (
        "Plan before work over an hour, and hold the gates: ruff clean, mypy "
        "--strict clean, pytest coverage above 70 percent, no secrets in code. "
        "Triggers: quality, lint, mypy, pytest, coverage, gate, definition of done."
    ),
    "claude-toolkit-rules": (
        "SoftSpark working agreement: never guess a home directory path, give at "
        "least three alternatives, and apply a devil's advocate critique to "
        "decisions. Triggers: toolkit, conventions, workflow, alternatives, review."
    ),
}


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) if present."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    return text[end + len("\n---\n"):]


def _title(stem: str) -> str:
    return stem.replace("-", " ").title()


def _build_skill_md(stem: str, rule_file: Path) -> str:
    description = DESCRIPTIONS[stem]
    body = _strip_frontmatter(rule_file.read_text(encoding="utf-8")).strip()
    frontmatter = dedent(
        f"""\
        ---
        name: {stem}
        description: "{description}"
        effort: low
        user-invocable: false
        allowed-tools: Read
        ---

        # {_title(stem)}

        This rule comes from `app/rules/{stem}.md` in ai-toolkit. It applies to
        every task in this workspace, not only when it is loaded.

        """
    )
    return frontmatter + body + "\n"


def discover_rules() -> list[str]:
    """List top-level rule files that have a description to ship them under.

    A rule with no entry in DESCRIPTIONS is skipped loudly rather than shipped
    with a generated summary: the description is the part that reaches every
    session, so it is written by a person.
    """
    if not RULES_DIR.is_dir():
        return []
    found: list[str] = []
    for path in sorted(RULES_DIR.glob("*.md")):
        if path.stem in DESCRIPTIONS:
            found.append(path.stem)
        else:
            print(
                f"  SKIP: {path.name} has no entry in DESCRIPTIONS; add one to ship it",
                file=sys.stderr,
            )
    return found


def generate(rules: list[str] | None = None, check: bool = False) -> int:
    """Generate skills. Returns the number written, or that would be written."""
    selected = rules if rules else discover_rules()
    written = 0
    for stem in selected:
        rule_file = RULES_DIR / f"{stem}.md"
        if not rule_file.is_file():
            print(f"  SKIP: {stem} (app/rules/{stem}.md missing)", file=sys.stderr)
            continue
        if stem not in DESCRIPTIONS:
            print(f"  SKIP: {stem} (no description)", file=sys.stderr)
            continue

        skill_dir = SKILLS_DIR / stem
        skill_md = skill_dir / "SKILL.md"
        content = _build_skill_md(stem, rule_file)

        if check:
            existing = skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
            status = "OK" if existing == content else "DIFF"
            print(f"  [{status}] {skill_md.relative_to(ROOT)}")
            if existing != content:
                written += 1
            continue

        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md.write_text(content, encoding="utf-8")
        print(f"  wrote {skill_md.relative_to(ROOT)}")
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report drift, write nothing")
    parser.add_argument("--rules", help="comma-separated rule stems")
    args = parser.parse_args()

    rules = [r.strip() for r in args.rules.split(",")] if args.rules else None
    written = generate(rules, check=args.check)
    if args.check:
        if written:
            print(f"{written} generated skill(s) differ from app/rules/", file=sys.stderr)
            return 1
        print("toolkit rule skills are up to date")
        return 0
    print(f"{written} toolkit rule skill(s) written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
