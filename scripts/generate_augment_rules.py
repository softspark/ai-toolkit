#!/usr/bin/env python3
"""Generate .augment/rules/ai-toolkit-*.md files for Augment Code.

Augment supports per-file rules with frontmatter:
  - type: always_apply  — always in context
  - type: auto_attached + globs — attached for matching files

The existing generate_augment.py creates a single always_apply file.
This generator adds granular per-category rules with appropriate types.

Usage:
  python3 scripts/generate_augment_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    PREFIX,
    cleanup_stale,
    rule_agents_and_skills,
    rule_code_style,
    rule_quality_standards,
    rule_security,
    rule_testing,
    rule_workflow,
)


def _augment_wrap(content: str, *, description: str,
                  rule_type: str = "always_apply",
                  globs: list[str] | None = None) -> str:
    """Wrap content with Augment YAML frontmatter."""
    lines = ["---"]
    lines.append(f"type: {rule_type}")
    lines.append(f"description: {description}")
    if globs:
        globs_str = ", ".join(f'"{g}"' for g in globs)
        lines.append(f"globs: [{globs_str}]")
    lines.append("---")
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _make_rules() -> dict[str, callable]:
    return {
        # Always active
        f"{PREFIX}agents-and-skills.md": lambda: _augment_wrap(
            rule_agents_and_skills(),
            description="AI toolkit agents, skills, and guidelines catalog",
        ),
        f"{PREFIX}security.md": lambda: _augment_wrap(
            rule_security(),
            description="Security rules — OWASP, secrets, input validation",
        ),
        f"{PREFIX}quality-standards.md": lambda: _augment_wrap(
            rule_quality_standards(),
            description="Quality standards — tests, safety, operational integrity",
        ),
        f"{PREFIX}workflow.md": lambda: _augment_wrap(
            rule_workflow(),
            description="Development workflow — planning, commits, quality gates",
        ),
        # Auto-attached by file type
        f"{PREFIX}code-style.md": lambda: _augment_wrap(
            rule_code_style(),
            description="Code style conventions",
            rule_type="auto_attached",
            globs=["*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs",
                   "*.java", "*.kt", "*.swift", "*.dart", "*.cs", "*.php",
                   "*.cpp", "*.cc", "*.rb"],
        ),
        f"{PREFIX}testing.md": lambda: _augment_wrap(
            rule_testing(),
            description="Testing standards and patterns",
            rule_type="auto_attached",
            globs=["*.test.*", "*.spec.*", "test_*", "**/tests/**",
                   "**/test/**", "**/__tests__/**"],
        ),
    }


RULES = _make_rules()


def generate(target_dir: Path) -> None:
    """Write .augment/rules/ai-toolkit-*.md files to target_dir."""
    rules_dir = target_dir / ".augment" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    cleanup_stale(rules_dir, set(RULES.keys()) | {"ai-toolkit.md"})

    for filename, content_fn in RULES.items():
        (rules_dir / filename).write_text(content_fn(), encoding="utf-8")
        print(f"  Generated: .augment/rules/{filename}")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    generate(target)


if __name__ == "__main__":
    main()
