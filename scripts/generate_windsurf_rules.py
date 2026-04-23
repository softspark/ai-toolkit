#!/usr/bin/env python3
"""Generate ``.windsurf/rules/*.md`` (and workflows) for Windsurf IDE.

Windsurf reads directory-based rules from ``.windsurf/rules/*.md`` (since
mid-2025). Each rule file supports YAML frontmatter with these fields
(from docs.windsurf.com/windsurf/cascade/memories):

* ``trigger`` — activation mode: ``always_on`` | ``glob`` | ``model_decision``
  | ``manual``. When omitted, Windsurf defaults to manual-only.
* ``globs`` — comma-separated glob patterns (only when ``trigger: glob``).
* ``description`` — shown to the model when ``trigger: model_decision``.

Windsurf also reads workflow markdown files from ``.windsurf/workflows/*.md``
which users invoke via ``/<name>`` slash commands (Cascade). This generator
emits the same workflow catalogue used by Antigravity and Cline.

The legacy ``.windsurfrules`` single-file format is still produced by
``generate_windsurf.py`` for backwards compatibility.

Usage:
  python3 scripts/generate_windsurf_rules.py [target-dir]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    CUSTOM_SCOPE,
    LANG_GLOBS,
    LANG_PREFIX,
    LANG_SCOPE,
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
# Frontmatter helpers — Windsurf rule activation modes
# ---------------------------------------------------------------------------

def _frontmatter(content: str, *,
                 trigger: str,
                 description: str = "",
                 globs: list[str] | None = None) -> str:
    """Prepend a Windsurf YAML frontmatter block to rule content.

    ``trigger`` must be one of: ``always_on``, ``glob``, ``model_decision``,
    ``manual``. ``description`` is shown to the model for ``model_decision``
    mode; ignored otherwise. ``globs`` is only meaningful for ``glob`` mode.
    """
    lines = ["---", f"trigger: {trigger}"]
    if description:
        lines.append(f"description: {description}")
    if trigger == "glob" and globs:
        lines.append("globs: " + ",".join(globs))
    lines.append("---")
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _always_on(content_fn):
    """Wrap a content callable so Windsurf treats it as always-on."""
    return lambda: _frontmatter(content_fn(), trigger="always_on")


def _glob_rule(content_fn, globs: list[str]):
    """Wrap a content callable for Windsurf's glob activation mode."""
    return lambda: _frontmatter(content_fn(), trigger="glob", globs=globs)


def _model_decision(content_fn, description: str):
    """Wrap a content callable for Windsurf's model-decision activation."""
    return lambda: _frontmatter(
        content_fn(), trigger="model_decision", description=description,
    )


def _build_rules(language_modules: list[str] | None,
                 rules_dir: Path | None) -> dict[str, callable]:
    """Build the full rule registry with per-rule activation frontmatter."""
    rules: dict[str, callable] = {}

    # Standard rules: agents/skills index + quality/security are always-on.
    # Code style + testing + workflow are model-decision so Cascade only
    # expands them when relevant.
    always_on_names = {
        f"{PREFIX}agents-and-skills.md",
        f"{PREFIX}security.md",
        f"{PREFIX}quality-standards.md",
    }
    model_decision_descs = {
        f"{PREFIX}code-style.md":
            "Code style conventions for all languages",
        f"{PREFIX}workflow.md":
            "Development workflow, commits, and quality gates",
    }
    testing_globs = ["**/*.test.*", "**/*.spec.*", "**/test_*", "**/tests/**"]

    for filename, content_fn in STANDARD_RULES.items():
        if filename in always_on_names:
            rules[filename] = _always_on(content_fn)
        elif filename == f"{PREFIX}testing.md":
            rules[filename] = _glob_rule(content_fn, testing_globs)
        elif filename in model_decision_descs:
            rules[filename] = _model_decision(
                content_fn, model_decision_descs[filename],
            )
        else:
            rules[filename] = _always_on(content_fn)

    # Language rules: scope to their own file globs so they activate only
    # when touching matching files.
    for filename, content_fn in build_language_rules(language_modules).items():
        lang = filename.removeprefix(LANG_PREFIX).removesuffix(".md")
        if lang == "common":
            rules[filename] = _always_on(content_fn)
            continue
        globs = LANG_GLOBS.get(lang)
        if globs:
            rules[filename] = _glob_rule(content_fn, globs)
        else:
            rules[filename] = _always_on(content_fn)

    # Custom user-registered rules — always-on by default (user intent).
    rules.update({
        name: _always_on(fn)
        for name, fn in build_registered_rules(rules_dir).items()
    })

    return rules


# ---------------------------------------------------------------------------
# Workflows — .windsurf/workflows/<name>.md invocable via /<name>
# ---------------------------------------------------------------------------

def _write_workflows(target_dir: Path, *, cleanup: bool = True) -> None:
    """Write ``.windsurf/workflows/*.md`` files for Cascade slash commands."""
    workflows_dir = target_dir / ".windsurf" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    if cleanup:
        cleanup_stale(workflows_dir, set(STANDARD_WORKFLOWS.keys()))

    for filename, content_fn in STANDARD_WORKFLOWS.items():
        (workflows_dir / filename).write_text(content_fn(), encoding="utf-8")
        print(f"  Generated: .windsurf/workflows/{filename}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None,
             cleanup: bool = True,
             emit_workflows: bool = True,
             managed_scopes: tuple[str, ...] = (
                 STANDARD_SCOPE, LANG_SCOPE, CUSTOM_SCOPE,
             )) -> None:
    """Write ``.windsurf/rules/*.md`` and ``.windsurf/workflows/*.md``."""
    rules = _build_rules(language_modules, rules_dir)
    write_rules(
        target_dir,
        rules,
        ".windsurf/rules",
        cleanup=cleanup,
        managed_scopes=managed_scopes,
    )

    if emit_workflows:
        _write_workflows(target_dir, cleanup=cleanup)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    from paths import RULES_DIR
    generate(target, rules_dir=RULES_DIR)


if __name__ == "__main__":
    main()
