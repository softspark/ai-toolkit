#!/usr/bin/env python3
"""Generate ``.clinerules/*.md`` files and companion workflows for Cline.

Cline reads rules from the ``.clinerules/`` directory (since Cline 3.7).
Each ``.md`` file inside is automatically loaded. The legacy single-file
``.clinerules`` format is replaced by this directory.

This generator also produces:
  * ``.clinerules/workflows/*.md`` — project-local workflow files that
    users invoke with ``/name.md`` in Cline chat. Emitted by default and
    mirrors the same workflow catalogue used by Antigravity and Codex.
  * Conditional rules (YAML ``paths:`` frontmatter) for file-type-scoped
    rules such as testing and language-specific guidance, so Cline only
    loads them when the user is editing matching files. See Cline docs:
    customization/cline-rules#conditional-rules.

Usage:
  python3 scripts/generate_cline_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    LANG_GLOBS,
    LANG_PREFIX,
    PREFIX,
    STANDARD_RULES,
    STANDARD_SCOPE,
    STANDARD_WORKFLOWS,
    build_language_rules,
    build_registered_rules,
    cleanup_stale,
    rule_testing,
    write_rules,
)


# ---------------------------------------------------------------------------
# Conditional-rule helper
# ---------------------------------------------------------------------------

def _conditional(content: str, paths: list[str]) -> str:
    """Prepend a Cline ``paths:`` YAML frontmatter block.

    Cline activates the rule only when the current working files match
    one of the globs. See docs.cline.bot → customization/cline-rules.
    """
    lines = ["---", "paths:"]
    for p in paths:
        lines.append(f'  - "{p}"')
    lines.append("---")
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _conditional_testing_rule() -> str:
    """Scope the testing rule to test files only (reduces context use)."""
    return _conditional(
        rule_testing(),
        ["**/*.test.*", "**/*.spec.*", "**/test_*", "**/tests/**"],
    )


def _wrap_language_rule(raw: str, lang: str) -> str:
    """Scope a language rule to its file extensions via conditional ``paths``."""
    globs = LANG_GLOBS.get(lang)
    if not globs:
        return raw
    return _conditional(raw, globs)


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None,
             cleanup: bool = True,
             emit_workflows: bool = True,
             managed_scopes: tuple[str, ...] = (STANDARD_SCOPE,)) -> None:
    """Write ``.clinerules/*.md`` (and workflow) files to target_dir."""
    # Migrate: if .clinerules exists as a single file, remove it so the
    # directory can be created (Cline 3.7+ uses directory format).
    clinerules = target_dir / ".clinerules"
    if clinerules.is_file():
        clinerules.unlink()

    rules: dict[str, callable] = dict(STANDARD_RULES)
    # Replace the testing rule with a conditional variant so it only
    # loads when the user is editing tests.
    rules[f"{PREFIX}testing.md"] = _conditional_testing_rule

    # Language rules — wrap each in conditional frontmatter scoped to
    # the language's file globs so the language-specific guidance only
    # loads for matching files.
    for filename, content_fn in build_language_rules(language_modules).items():
        lang = filename.removeprefix(LANG_PREFIX).removesuffix(".md")
        if lang == "common":
            # "common" spans all languages — apply unconditionally.
            rules[filename] = content_fn
            continue
        rules[filename] = (lambda fn, l: lambda: _wrap_language_rule(fn(), l))(
            content_fn, lang,
        )

    rules.update(build_registered_rules(rules_dir))

    write_rules(
        target_dir,
        rules,
        ".clinerules",
        cleanup=cleanup,
        managed_scopes=managed_scopes,
    )

    if emit_workflows:
        _write_workflows(target_dir, cleanup=cleanup)


def _write_workflows(target_dir: Path, *, cleanup: bool = True) -> None:
    """Write ``.clinerules/workflows/*.md`` files (Cline slash-invocable)."""
    workflows_dir = target_dir / ".clinerules" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    if cleanup:
        # Only touch ai-toolkit-* files; never remove user workflows.
        cleanup_stale(workflows_dir, set(STANDARD_WORKFLOWS.keys()))

    for filename, content_fn in STANDARD_WORKFLOWS.items():
        (workflows_dir / filename).write_text(content_fn(), encoding="utf-8")
        print(f"  Generated: .clinerules/workflows/{filename}")


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
