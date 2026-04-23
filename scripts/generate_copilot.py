#!/usr/bin/env python3
"""Generate GitHub Copilot customization files.

This generator produces three surfaces, all on the OSS/Free/Pro tier
(no Business/Enterprise gating, no server-side MCP config):

1. ``.github/copilot-instructions.md`` — always-on repository instructions.
   Supported by GitHub.com Copilot Chat, Copilot cloud agent, and VS Code
   Copilot. Generated to stdout by default (backwards compatible).

2. ``.github/instructions/*.instructions.md`` — path-specific instructions.
   Each file has ``applyTo`` frontmatter with a glob pattern. Supported
   by VS Code Copilot and Copilot cloud agent / code review on GitHub.com.
   Written only when ``generate()`` is called with a target directory.

3. ``.github/prompts/*.prompt.md`` — prompt files (slash commands).
   Invoked manually in VS Code Copilot Chat via ``/name``. Written only
   when ``generate()`` is called with a target directory.

Features that live on Pro/Pro+/Business/Enterprise tiers are intentionally
not generated (classified as class C in the ecosystem-sync SOP):
  * ``.github/agents/*.agent.md`` — custom agent profiles (tier-gated)
  * repo-level MCP configuration (GitHub repo Settings UI, tier-gated)
  * organization-wide and enterprise-wide instructions

Usage:
  # Legacy stdout mode (repo-wide instructions only)
  python3 scripts/generate_copilot.py > .github/copilot-instructions.md

  # Directory mode (repo-wide + path-specific + prompt files)
  python3 scripts/generate_copilot.py <target-dir>
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
    rule_code_style,
    rule_quality_standards,
    rule_security,
    rule_testing,
    rule_workflow,
)
from emission import (
    agents_dir,
    skills_dir,
)
from frontmatter import frontmatter_field
from generator_base import render_generator

# ---------------------------------------------------------------------------
# Shared configuration for the legacy stdout output
# ---------------------------------------------------------------------------

_STDOUT_CONFIG: dict = {
    "title": "# GitHub Copilot Instructions",
    "intro_template": (
        "This repository uses the ai-toolkit — a shared AI development toolkit"
        " with specialized agent personas and skills."
    ),
    "agents_section": "## Available Agent Personas",
    "agents_intro": "Apply the expertise of these agents when working on relevant tasks:",
    "agents_format": "headings",
    "agents_level": "###",
    "skills_section": "## Available Skills",
    "skills_intro": "The following skills are available as slash commands or knowledge sources:",
    "skills_format": "headings",
    "skills_level": "###",
    "guidelines": ["quality"],
}


# ---------------------------------------------------------------------------
# Path-specific .instructions.md emission
# ---------------------------------------------------------------------------

def _instructions_file(content: str, *, apply_to: str,
                       description: str = "") -> str:
    """Wrap markdown content with Copilot ``.instructions.md`` frontmatter."""
    lines = ["---"]
    lines.append(f'applyTo: "{apply_to}"')
    if description:
        lines.append(f"description: {description}")
    lines.append("---")
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _make_instruction_files() -> dict[str, callable]:
    """Build the ``.instructions.md`` file registry.

    Filenames use the standard ai-toolkit prefix so they can be cleaned up
    on re-run without touching user files.
    """
    return {
        # Always applies (repo-wide)
        f"{PREFIX}security.instructions.md": lambda: _instructions_file(
            rule_security(),
            apply_to="**",
            description="Security rules — OWASP, secrets, input validation",
        ),
        f"{PREFIX}quality-standards.instructions.md": lambda: _instructions_file(
            rule_quality_standards(),
            apply_to="**",
            description="Quality standards — tests, safety, operational integrity",
        ),
        f"{PREFIX}workflow.instructions.md": lambda: _instructions_file(
            rule_workflow(),
            apply_to="**",
            description="Development workflow — planning, commits, quality gates",
        ),
        f"{PREFIX}code-style.instructions.md": lambda: _instructions_file(
            rule_code_style(),
            apply_to="**",
            description="Code style conventions for all languages",
        ),
        # Scoped to test files only
        f"{PREFIX}testing.instructions.md": lambda: _instructions_file(
            rule_testing(),
            apply_to="**/*.test.*,**/*.spec.*,**/test_*,**/tests/**",
            description="Testing standards and patterns",
        ),
    }


# ---------------------------------------------------------------------------
# Prompt-file emission (.github/prompts/*.prompt.md)
# ---------------------------------------------------------------------------

def _prompt_file(description: str, body: str, *,
                 agent: str | None = None) -> str:
    """Wrap a skill body with Copilot ``.prompt.md`` frontmatter."""
    lines = ["---"]
    # Description is required for visibility in the slash menu.
    lines.append(f"description: {description}")
    if agent:
        lines.append(f"agent: {agent}")
    lines.append("---")
    lines.append("")
    lines.append(body.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _read_skill_body(skill_file: Path) -> str:
    """Read SKILL.md body after the closing frontmatter delimiter."""
    lines: list[str] = []
    fence_count = 0
    with open(skill_file, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                fence_count += 1
                continue
            if fence_count >= 2:
                lines.append(line.rstrip("\n"))
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _user_invocable_skills() -> list[tuple[str, str, str]]:
    """Return user-invocable skills as (name, description, body) tuples.

    Only skills whose SKILL.md is suitable for slash-command invocation
    are returned. Knowledge-only skills (``user-invocable: false`` or
    ``disable-model-invocation: true``) are filtered out.
    """
    if not skills_dir.is_dir():
        return []
    result: list[tuple[str, str, str]] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.name.startswith("_") or not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = frontmatter_field(skill_file, "name")
        description = frontmatter_field(skill_file, "description")
        if not name or not description:
            continue
        # Honour the same visibility filter used by generate_opencode_commands
        user_invocable = frontmatter_field(skill_file, "user-invocable")
        disable_model = frontmatter_field(skill_file, "disable-model-invocation")
        if user_invocable == "false":
            continue
        # Task skills (disable-model-invocation: true) are still fine as
        # slash commands; knowledge skills with user-invocable: false are not.
        del disable_model  # not used beyond inspection
        body = _read_skill_body(skill_file)
        if not body:
            continue
        result.append((name, description, body))
    return result


# ---------------------------------------------------------------------------
# Directory-mode generation
# ---------------------------------------------------------------------------

def _cleanup_prefixed(directory: Path, suffix: str,
                      keep: set[str]) -> None:
    """Remove ai-toolkit-prefixed files in ``directory`` that aren't in ``keep``."""
    if not directory.is_dir():
        return
    for f in directory.iterdir():
        if f.name.startswith(PREFIX) and f.name.endswith(suffix) and f.name not in keep:
            f.unlink()
            rel = f.relative_to(directory.parent.parent) if len(directory.parents) >= 2 else f
            print(f"  Removed stale: {rel}")


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None,
             emit_prompts: bool = True,
             emit_instructions: bool = True) -> None:
    """Write Copilot path-specific instructions and prompt files.

    ``.github/copilot-instructions.md`` is intentionally not written here —
    the legacy ``main()`` entry point still emits it to stdout so existing
    scripts (including ``ai-toolkit install``) keep working unchanged.
    """
    github_dir = target_dir / ".github"

    if emit_instructions:
        instr_dir = github_dir / "instructions"
        instr_dir.mkdir(parents=True, exist_ok=True)

        instruction_files: dict[str, callable] = dict(_make_instruction_files())

        # Language-specific instructions (auto-applied by file glob)
        for filename, content_fn in build_language_rules(language_modules).items():
            lang = filename.removeprefix(f"{PREFIX}lang-").removesuffix(".md")
            globs = LANG_GLOBS.get(lang)
            apply_to = ",".join(globs) if globs else "**"
            new_name = f"{PREFIX}lang-{lang}.instructions.md"
            instruction_files[new_name] = (lambda fn, l, a: lambda: _instructions_file(
                fn(),
                apply_to=a,
                description=f"{l.title()} language rules",
            ))(content_fn, lang, apply_to)

        # User-registered custom rules (always-on)
        for filename, content_fn in build_registered_rules(rules_dir).items():
            stem = filename.removeprefix(f"{PREFIX}custom-").removesuffix(".md")
            new_name = f"{PREFIX}custom-{stem}.instructions.md"
            instruction_files[new_name] = (lambda fn, n: lambda: _instructions_file(
                fn(),
                apply_to="**",
                description=f"Custom rule: {n}",
            ))(content_fn, stem)

        _cleanup_prefixed(instr_dir, ".instructions.md", set(instruction_files.keys()))

        for name, content_fn in instruction_files.items():
            (instr_dir / name).write_text(content_fn(), encoding="utf-8")
            print(f"  Generated: .github/instructions/{name}")

    if emit_prompts:
        prompt_dir = github_dir / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)

        skills = _user_invocable_skills()
        prompt_filenames: set[str] = set()
        for name, description, body in skills:
            filename = f"{PREFIX}{name}.prompt.md"
            prompt_filenames.add(filename)
            content = _prompt_file(description, body)
            (prompt_dir / filename).write_text(content, encoding="utf-8")
            print(f"  Generated: .github/prompts/{filename}")

        _cleanup_prefixed(prompt_dir, ".prompt.md", prompt_filenames)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point.

    With no argument: emit the repo-wide ``copilot-instructions.md`` to stdout
    (preserves the historical contract).

    With a directory argument: write the path-specific ``instructions/`` and
    ``prompts/`` files under ``<target>/.github/``. The caller is responsible
    for redirecting the stdout generator separately if they want the full set.
    """
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        from paths import RULES_DIR
        generate(target, rules_dir=RULES_DIR)
        return

    render_generator(_STDOUT_CONFIG)


if __name__ == "__main__":
    main()
