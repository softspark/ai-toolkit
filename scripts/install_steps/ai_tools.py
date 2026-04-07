"""Install AI tool configs (Cursor, Windsurf, Gemini, Augment) and local project setup."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from _common import app_dir, inject_section, should_install, toolkit_dir
from injection import (
    collapse_blank_runs as _collapse_blank_runs,
    strip_section as _strip_section,
    trim_trailing_blanks as _trim_trailing_blanks,
)


def install_ai_tools(target_dir: Path, rules_dir: Path,
                     only: str, skip: str, dry_run: bool) -> None:
    """Install Cursor, Windsurf, Gemini global configs."""
    print()
    print("## Other AI Tools (global)")
    print()

    if should_install("cursor", only, skip):
        cursor_file = target_dir / ".cursor" / "rules"
        if dry_run:
            print("  Would inject: ~/.cursor/rules")
        else:
            inject_with_rules("generate-cursor-rules.sh", cursor_file, rules_dir)
    else:
        print("  Skipped: cursor")

    if should_install("windsurf", only, skip):
        windsurf_file = target_dir / ".codeium" / "windsurf" / "memories" / "global_rules.md"
        if dry_run:
            print("  Would inject: ~/.codeium/windsurf/memories/global_rules.md")
        else:
            inject_with_rules("generate-windsurf.sh", windsurf_file, rules_dir)
    else:
        print("  Skipped: windsurf")

    if should_install("gemini", only, skip):
        gemini_file = target_dir / ".gemini" / "GEMINI.md"
        if dry_run:
            print("  Would inject: ~/.gemini/GEMINI.md")
        else:
            inject_with_rules("generate-gemini.sh", gemini_file, rules_dir)
    else:
        print("  Skipped: gemini")

    if should_install("augment", only, skip):
        augment_file = target_dir / ".augment" / "rules" / "ai-toolkit.md"
        if dry_run:
            print("  Would inject: ~/.augment/rules/ai-toolkit.md")
        else:
            inject_with_rules("generate-augment.sh", augment_file, rules_dir)
    else:
        print("  Skipped: augment")

    print()
    print("  Note: Copilot, Cline, Roo Code, and Aider have no global config -- use 'ai-toolkit install --local' per project")


def inject_with_rules(
    generator_script: str,
    target_file: Path,
    rules_dir: Path,
) -> None:
    """Run a generator script, write output, then inject registered rules."""
    scripts_dir = toolkit_dir / "scripts"
    py_name = generator_script.replace(".sh", ".py").replace("-", "_")
    if (scripts_dir / py_name).is_file():
        cmd = ["python3", str(scripts_dir / py_name)]
    else:
        cmd = ["bash", str(scripts_dir / generator_script)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {generator_script} failed: {result.stderr.strip()}")
        return

    generated = result.stdout
    start_marker = "<!-- TOOLKIT:ai-toolkit START -->"

    target_file = Path(target_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists():
        target_file.touch()

    existing = target_file.read_text(encoding="utf-8")
    if start_marker in existing:
        existing = _strip_section(existing, "ai-toolkit")
    existing = _trim_trailing_blanks(existing)

    parts: list[str] = []
    if existing.strip():
        parts.append(existing)
        parts.append("")
    parts.append(generated.rstrip("\n"))

    output = "\n".join(parts) + "\n"
    output = _collapse_blank_runs(output)
    target_file.write_text(output, encoding="utf-8")

    if rules_dir.is_dir():
        for rule_file in sorted(rules_dir.glob("*.md")):
            inject_section(rule_file, target_file, rule_file.stem)

    print(f"  Updated: {target_file}")


def run_script(script_name: str, *args: str, capture: bool = False) -> str:
    """Run a script from the scripts/ directory (prefers .py over .sh)."""
    scripts_dir = toolkit_dir / "scripts"
    py_name = script_name.replace(".sh", ".py").replace("-", "_")
    if (scripts_dir / py_name).is_file():
        cmd = ["python3", str(scripts_dir / py_name), *args]
    else:
        cmd = ["bash", str(scripts_dir / script_name), *args]
    result = subprocess.run(cmd, capture_output=capture, text=True)
    return result.stdout if capture else ""


def install_local_project(rules_dir: Path, dry_run: bool, reset: bool,
                          language_modules: list[str] | None = None) -> None:
    """Install project-local configs."""
    cwd = Path.cwd()
    print()
    print(f"## Project-local ({cwd})")
    if reset:
        print("   Mode: RESET (all local configs will be wiped and recreated)")
    print()

    if dry_run:
        _install_local_dry_run(reset)
        if language_modules:
            print(f"  Would inject language rules: {', '.join(language_modules)}")
        return

    (cwd / ".claude").mkdir(parents=True, exist_ok=True)

    if reset:
        _reset_local_configs(cwd)

    _create_local_claude_md(cwd, reset)
    _create_local_settings(cwd, reset)

    legacy_local_hooks = cwd / ".claude" / "hooks.json"
    if legacy_local_hooks.is_file():
        legacy_local_hooks.unlink()
        print("  Removed: .claude/hooks.json (legacy)")
    print("  Note: hooks are merged into global ~/.claude/settings.json only (not project-local)")

    constitution_src = app_dir / "constitution.md"
    if constitution_src.is_file():
        inject_section(
            constitution_src,
            cwd / ".claude" / "constitution.md",
            "constitution",
        )
        print("  Injected: .claude/constitution.md")

    # Inject language-specific rules into project CLAUDE.md
    _inject_language_rules(cwd, language_modules)

    _create_local_ai_tool_configs(cwd, rules_dir)


def _inject_language_rules(cwd: Path, language_modules: list[str] | None) -> None:
    """Inject language-specific rule summary into project's .claude/CLAUDE.md.

    Instead of injecting full rule content (hundreds of lines), injects a
    compact summary with the key rules per category. Full rules are available
    as knowledge skills that Claude auto-loads contextually.
    """
    if not language_modules:
        return

    rules_src = app_dir / "rules"
    if not rules_src.is_dir():
        return

    # Detect language names
    langs: list[str] = []
    for mod in language_modules:
        if mod.startswith("rules-"):
            langs.append(mod[6:])

    if not langs:
        return

    # Build compact summary: first 5 key rules from each category
    lines: list[str] = ["# Language Rules (auto-detected)", ""]
    lines.append(f"Detected: **{', '.join(langs)}** + common rules.")
    lines.append("")
    lines.append("Detailed rules available as knowledge skills (auto-loaded by Claude).")
    lines.append("")

    # Deduplicate: common + unique language dirs
    all_dirs: list[str] = ["common"]
    for l in langs:
        if l not in all_dirs:
            all_dirs.append(l)

    for lang_dir in all_dirs:
        lang_path = rules_src / lang_dir
        if not lang_path.is_dir():
            continue
        lang_label = lang_dir.capitalize() if lang_dir != "common" else "Common"
        lines.append(f"## {lang_label} Rules")
        lines.append("")
        for rule_file in sorted(lang_path.glob("*.md")):
            content = rule_file.read_text(encoding="utf-8").strip()
            # Strip YAML frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].strip()
            # Extract first 3 bullet points as key rules
            bullets = [l.strip() for l in content.splitlines() if l.strip().startswith("- ")][:3]
            if bullets:
                category = rule_file.stem.replace("-", " ").title()
                lines.append(f"**{category}:** {' | '.join(b.lstrip('- ') for b in bullets)}")
        lines.append("")

    # Write summary to temp file, then inject as section
    import tempfile
    combined = "\n".join(lines)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(combined)
        tmp_path = Path(tmp.name)

    try:
        inject_section(tmp_path, cwd / ".claude" / "CLAUDE.md", "language-rules")
        lang_names = [l for l in langs if l != "common"]
        print(f"  Injected: language rules summary (common + {', '.join(lang_names)})")
    finally:
        tmp_path.unlink(missing_ok=True)


def _install_local_dry_run(reset: bool) -> None:
    if reset:
        print("  Would remove: CLAUDE.md, .claude/settings.local.json")
        print("  Would remove: .claude/constitution.md, .github/copilot-instructions.md, .clinerules, .roomodes, .aider.conf.yml")
        print("  Would recreate all from templates (clean slate)")
        print("  Would install git hooks (if .git/hooks exists)")
    else:
        print("  Would create: CLAUDE.md (if missing)")
        print("  Would create: .claude/settings.local.json (if missing)")
        print("  Would inject: .claude/constitution.md")
        print("  Would inject: .github/copilot-instructions.md")
        print("  Would inject: .clinerules")
        print("  Would inject: .roomodes")
        print("  Would inject: .aider.conf.yml")
        print("  Would install: .git/hooks/pre-commit")


def _reset_local_configs(cwd: Path) -> None:
    for rel in (
        "CLAUDE.md",
        ".claude/settings.local.json",
        ".claude/constitution.md",
        ".github/copilot-instructions.md",
        ".clinerules",
        ".roomodes",
        ".aider.conf.yml",
    ):
        p = cwd / rel
        if p.is_file():
            p.unlink()
            print(f"  Removed: {rel}")


def _create_local_claude_md(cwd: Path, reset: bool) -> None:
    claude_local = cwd / "CLAUDE.md"
    if reset or not claude_local.is_file():
        template = app_dir / "CLAUDE.md.template"
        if template.is_file():
            shutil.copy2(template, claude_local)
            print("  Created: CLAUDE.md (from template)")
        else:
            claude_local.write_text(
                """\
# [Project Name]

## Overview

## Tech Stack
- **Language**:
- **Framework**:
- **Database**:

## Commands
```bash
# Dev:
# Test:
# Lint:
# Build:
```

## Key Conventions

## MCP Servers
""",
                encoding="utf-8",
            )
            print("  Created: CLAUDE.md (default template)")
    else:
        print("  Kept: CLAUDE.md (already exists)")


def _create_local_settings(cwd: Path, reset: bool) -> None:
    settings_local = cwd / ".claude" / "settings.local.json"
    if reset or not settings_local.is_file():
        mcp_defaults = app_dir / "mcp-defaults.json"
        if mcp_defaults.is_file():
            shutil.copy2(mcp_defaults, settings_local)
            print("  Created: .claude/settings.local.json (from mcp-defaults)")
        else:
            settings_local.write_text(
                '{\n  "mcpServers": {},\n  "env": {}\n}\n',
                encoding="utf-8",
            )
            print("  Created: .claude/settings.local.json")
    else:
        print("  Kept: .claude/settings.local.json (already exists)")


def _create_local_ai_tool_configs(cwd: Path, rules_dir: Path) -> None:
    inject_with_rules(
        "generate-copilot.sh",
        cwd / ".github" / "copilot-instructions.md",
        rules_dir,
    )
    inject_with_rules(
        "generate-cline.sh",
        cwd / ".clinerules",
        rules_dir,
    )

    roo_output = run_script("generate-roo-modes.sh", capture=True)
    (cwd / ".roomodes").write_text(roo_output, encoding="utf-8")
    print("  Created: .roomodes")

    aider_output = run_script("generate-aider-conf.sh", capture=True)
    (cwd / ".aider.conf.yml").write_text(aider_output, encoding="utf-8")
    print("  Created: .aider.conf.yml")

    run_script("install-git-hooks.sh", str(cwd))
