#!/usr/bin/env python3
"""Generate .cursor/rules/*.mdc files for Cursor IDE.

Cursor reads rules from .cursor/rules/*.mdc (since Cursor 0.45).
Each .mdc file has YAML frontmatter controlling when the rule applies:
  - alwaysApply: true  — always in context
  - globs: ["**/*.ts"] — auto-attached for matching files
  - description: "..." — AI decides whether to include (Agent Requested)

The legacy .cursorrules format is still generated separately by
generate_cursor_rules.py for backwards compatibility.

Usage:
  python3 scripts/generate_cursor_mdc.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    LANG_GLOBS,
    PREFIX,
    build_language_rules,
    build_registered_rules,
    cleanup_stale,
    rule_agents_and_skills,
    rule_code_style,
    rule_quality_standards,
    rule_security,
    rule_testing,
    rule_workflow,
)


# ---------------------------------------------------------------------------
# .mdc wrapper: prepends YAML frontmatter to markdown content
# ---------------------------------------------------------------------------

def _mdc(content: str, *, description: str = "",
         globs: list[str] | None = None,
         always_apply: bool = False) -> str:
    """Wrap markdown content with Cursor .mdc YAML frontmatter."""
    lines = ["---"]
    if description:
        lines.append(f"description: {description}")
    if globs:
        globs_str = ", ".join(f'"{g}"' for g in globs)
        lines.append(f"globs: [{globs_str}]")
    lines.append(f"alwaysApply: {'true' if always_apply else 'false'}")
    lines.append("---")
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Rule files registry
# ---------------------------------------------------------------------------

def _make_rules() -> dict[str, callable]:
    """Build the .mdc rule file registry."""
    return {
        # Always active
        f"{PREFIX}agents-and-skills.mdc": lambda: _mdc(
            rule_agents_and_skills(),
            description="AI toolkit agents, skills, and guidelines catalog",
            always_apply=True,
        ),
        f"{PREFIX}security.mdc": lambda: _mdc(
            rule_security(),
            description="Security rules — OWASP, secrets, input validation",
            always_apply=True,
        ),
        f"{PREFIX}quality-standards.mdc": lambda: _mdc(
            rule_quality_standards(),
            description="Quality standards — tests, safety, operational integrity",
            always_apply=True,
        ),
        # Auto-attached by file type
        f"{PREFIX}code-style.mdc": lambda: _mdc(
            rule_code_style(),
            description="Code style conventions for all languages",
        ),
        f"{PREFIX}testing.mdc": lambda: _mdc(
            rule_testing(),
            description="Testing standards and patterns",
            globs=["**/*.test.*", "**/*.spec.*", "**/test_*", "**/tests/**"],
        ),
        f"{PREFIX}workflow.mdc": lambda: _mdc(
            rule_workflow(),
            description="Development workflow — planning, commits, quality gates",
        ),
    }


RULES = _make_rules()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None) -> None:
    """Write .cursor/rules/*.mdc files to target_dir."""
    out_dir = target_dir / ".cursor" / "rules"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rules: dict[str, callable] = dict(RULES)

    # Add language rules wrapped in .mdc frontmatter
    for filename, content_fn in build_language_rules(language_modules).items():
        lang = filename.removeprefix(f"{PREFIX}lang-").removesuffix(".md")
        globs = LANG_GLOBS.get(lang)
        mdc_name = filename.replace(".md", ".mdc")
        all_rules[mdc_name] = (lambda fn, l, g: lambda: _mdc(
            fn(),
            description=f"{l.title()} language rules",
            globs=g if g else None,
            always_apply=not g,
        ))(content_fn, lang, globs)

    # Add registered rules wrapped in .mdc frontmatter
    for filename, content_fn in build_registered_rules(rules_dir).items():
        name = filename.removeprefix(f"{PREFIX}custom-").removesuffix(".md")
        mdc_name = filename.replace(".md", ".mdc")
        all_rules[mdc_name] = (lambda fn, n: lambda: _mdc(
            fn(),
            description=f"Custom rule: {n}",
            always_apply=True,
        ))(content_fn, name)

    # Clean stale ai-toolkit-*.mdc files
    current = set(all_rules.keys())
    if out_dir.is_dir():
        for f in out_dir.iterdir():
            if f.name.startswith(PREFIX) and f.suffix == ".mdc" and f.name not in current:
                f.unlink()
                print(f"  Removed stale: .cursor/rules/{f.name}")

    for filename, content_fn in all_rules.items():
        (out_dir / filename).write_text(content_fn(), encoding="utf-8")
        print(f"  Generated: .cursor/rules/{filename}")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
