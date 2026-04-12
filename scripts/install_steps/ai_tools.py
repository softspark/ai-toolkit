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
    existing = existing.lstrip("\n")  # no leading blank lines

    parts: list[str] = []
    if existing.strip():
        parts.append(existing)
        parts.append("")
    parts.append(generated.rstrip("\n"))

    output = "\n".join(parts) + "\n"
    output = _collapse_blank_runs(output)
    output = output.lstrip("\n")  # no leading blank lines
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


# All known editor identifiers for --editors flag
ALL_EDITORS = [
    "copilot", "cursor", "windsurf", "cline", "roo",
    "aider", "augment", "antigravity",
]

# Map of project files/dirs → editor names for auto-detection
_EDITOR_MARKERS: dict[str, str] = {
    ".github/copilot-instructions.md": "copilot",
    ".cursorrules": "cursor",
    ".cursor/rules": "cursor",
    ".windsurfrules": "windsurf",
    ".windsurf/rules": "windsurf",
    ".clinerules": "cline",
    ".roomodes": "roo",
    ".roo/rules": "roo",
    ".aider.conf.yml": "aider",
    "CONVENTIONS.md": "aider",
    ".augment/rules": "augment",
    ".agent/rules": "antigravity",
}


def _detect_editors(cwd: Path) -> list[str]:
    """Detect which editors have configs in the project directory."""
    found: set[str] = set()
    for marker, editor in _EDITOR_MARKERS.items():
        p = cwd / marker
        if p.exists():
            found.add(editor)
    return sorted(found)


def _resolve_editors(editors_arg: str, cwd: Path) -> list[str]:
    """Resolve --editors argument to a list of editor names.

    - ""           → auto-detect from existing project files (empty if none found)
    - "all"        → all editors
    - "cursor,aider" → explicit list
    """
    if editors_arg == "all":
        return list(ALL_EDITORS)
    if editors_arg:
        return [e.strip() for e in editors_arg.split(",") if e.strip()]
    # Auto-detect: return editors that already have configs in the project
    return _detect_editors(cwd)


def install_local_project(rules_dir: Path, dry_run: bool, reset: bool,
                          language_modules: list[str] | None = None,
                          editors: str = "",
                          merged_config: dict | None = None) -> None:
    """Install project-local configs.

    Claude Code configs (CLAUDE.md, settings, constitution) are always installed.
    Editor configs are installed based on ``--editors`` flag:
    - ``--editors all``: install all editors
    - ``--editors cursor,aider``: install only these
    - (empty): auto-detect from existing project files, install only those

    If ``merged_config`` is provided (from .ai-toolkit.json extends resolution),
    additional rules and constitution amendments from the base config are injected.
    """
    cwd = Path.cwd()
    resolved_editors = _resolve_editors(editors, cwd)

    print()
    print(f"## Project-local ({cwd})")
    if merged_config and merged_config.get("_extends_meta"):
        meta = merged_config["_extends_meta"]
        print(f"   Config: .ai-toolkit.json (extends: {meta['source']})")
    if reset:
        print("   Mode: RESET (all local configs will be wiped and recreated)")
    if resolved_editors:
        print(f"   Editors: {', '.join(resolved_editors)}")
    else:
        print("   Editors: none (use --editors <list> or --editors all to enable)")
    print()

    if dry_run:
        _install_local_dry_run(reset, resolved_editors)
        if language_modules:
            print(f"  Would inject language rules: {', '.join(language_modules)}")
        if merged_config:
            print(f"  Would apply merged config from extends")
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

    # Apply extends: inject base rules and constitution amendments
    if merged_config:
        _apply_extends_config(cwd, merged_config)

    # Inject language-specific rules into project CLAUDE.md
    _inject_language_rules(cwd, language_modules)

    # Install editor configs only for resolved editors
    _create_local_ai_tool_configs(cwd, rules_dir, resolved_editors,
                                  language_modules=language_modules)


def _apply_extends_config(cwd: Path, merged: dict) -> None:
    """Apply merged extends config — inject base rules and constitution amendments."""
    import json as _json

    # Inject base rules into CLAUDE.md
    rules = merged.get("rules", {})
    inject_rules = rules.get("inject", [])
    if inject_rules:
        claude_md = cwd / ".claude" / "CLAUDE.md"
        if claude_md.is_file():
            content = claude_md.read_text(encoding="utf-8")
        else:
            content = ""

        # Add extends rules section if not already present
        marker_start = "<!-- TOOLKIT:extends-rules START -->"
        marker_end = "<!-- TOOLKIT:extends-rules END -->"

        rules_block = f"\n{marker_start}\n"
        rules_block += "# Inherited Rules (from base config)\n\n"
        for rule_path in inject_rules:
            rules_block += f"- Rule: `{rule_path}`\n"
        rules_block += f"{marker_end}\n"

        if marker_start in content:
            # Replace existing section
            import re
            content = re.sub(
                f"{re.escape(marker_start)}.*?{re.escape(marker_end)}",
                f"{marker_start}\n# Inherited Rules (from base config)\n\n"
                + "".join(f"- Rule: `{r}`\n" for r in inject_rules)
                + marker_end,
                content,
                flags=re.DOTALL,
            )
        else:
            content += rules_block

        claude_md.write_text(content, encoding="utf-8")
        print(f"  Injected: {len(inject_rules)} rule(s) from base config")

    # Inject constitution amendments
    amendments = merged.get("constitution", {}).get("amendments", [])
    # Filter to non-toolkit articles (6+)
    custom_amendments = [a for a in amendments if a.get("article", 0) >= 6]
    if custom_amendments:
        constitution_file = cwd / ".claude" / "constitution.md"
        if constitution_file.is_file():
            content = constitution_file.read_text(encoding="utf-8")
        else:
            content = ""

        marker_start = "<!-- TOOLKIT:extends-constitution START -->"
        marker_end = "<!-- TOOLKIT:extends-constitution END -->"

        amendments_block = f"\n{marker_start}\n"
        for a in custom_amendments:
            amendments_block += f"\n## Article {a['article']}: {a['title']}\n\n"
            amendments_block += f"{a['text']}\n"
        amendments_block += f"\n{marker_end}\n"

        if marker_start in content:
            import re
            new_inner = ""
            for a in custom_amendments:
                new_inner += f"\n## Article {a['article']}: {a['title']}\n\n"
                new_inner += f"{a['text']}\n"
            content = re.sub(
                f"{re.escape(marker_start)}.*?{re.escape(marker_end)}",
                f"{marker_start}{new_inner}\n{marker_end}",
                content,
                flags=re.DOTALL,
            )
        else:
            content += amendments_block

        constitution_file.write_text(content, encoding="utf-8")
        print(f"  Injected: {len(custom_amendments)} constitution amendment(s) from base config")

    # Record merged config summary
    meta = merged.get("_extends_meta")
    if meta:
        state_file = cwd / ".ai-toolkit-extends.json"
        state_file.write_text(_json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"  Saved: .ai-toolkit-extends.json (resolution metadata)")


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

    # Build a lightweight reference pointer — NOT the full rules content.
    # Full rules are available as knowledge skills (auto-loaded by Claude)
    # and as files Claude can Read on demand.
    toolkit_pkg = app_dir.parent
    lines: list[str] = ["# Language Rules", ""]
    lines.append(f"This project uses: **{', '.join(langs)}**")
    lines.append("")
    lines.append("When writing or reviewing code, use the Glob and Read tools to read the rules:")
    # Resolve actual installed path for the rules
    rules_resolved = str(rules_src.resolve())
    all_dirs: list[str] = ["common"]
    for l in langs:
        if l not in all_dirs:
            all_dirs.append(l)
    for lang in all_dirs:
        lang_path = rules_src / lang
        if lang_path.is_dir():
            categories = ", ".join(f.stem for f in sorted(lang_path.glob("*.md")))
            lines.append(f"- `{lang_path.resolve()}/` ({categories})")
    lines.append("")
    lines.append("Read the relevant rule files before making code changes. Do NOT guess — read first.")

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


def _install_local_dry_run(reset: bool, editors: list[str] | None = None) -> None:
    eds = set(editors or [])
    if reset:
        print("  Would remove: CLAUDE.md, .claude/settings.local.json")
        print("  Would remove: .claude/constitution.md and all editor configs")
        print("  Would recreate all from templates (clean slate)")
    else:
        print("  Would create: CLAUDE.md (if missing)")
        print("  Would create: .claude/settings.local.json (if missing)")
        print("  Would inject: .claude/constitution.md")

    # Editor-specific dry-run messages
    _EDITOR_DRY_RUN = {
        "copilot":      "  Would inject: .github/copilot-instructions.md",
        "cursor":       "  Would generate: .cursorrules + .cursor/rules/*.mdc",
        "windsurf":     "  Would generate: .windsurfrules + .windsurf/rules/*.md",
        "cline":        "  Would generate: .clinerules/*.md",
        "roo":          "  Would generate: .roomodes + .roo/rules/*.md",
        "aider":        "  Would generate: .aider.conf.yml + CONVENTIONS.md",
        "augment":      "  Would generate: .augment/rules/ai-toolkit-*.md",
        "antigravity":  "  Would generate: .agent/rules/ + .agent/workflows/",
    }
    for ed, msg in _EDITOR_DRY_RUN.items():
        if ed in eds:
            print(msg)

    if not eds:
        print("  No editors selected (use --editors <list> or --editors all)")

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


def _create_local_ai_tool_configs(cwd: Path, rules_dir: Path,
                                   editors: list[str],
                                   language_modules: list[str] | None = None) -> None:
    eds = set(editors)

    if "copilot" in eds:
        inject_with_rules(
            "generate-copilot.sh",
            cwd / ".github" / "copilot-instructions.md",
            rules_dir,
        )

    if "cursor" in eds:
        inject_with_rules(
            "generate-cursor-rules.sh",
            cwd / ".cursorrules",
            rules_dir,
        )
        from generate_cursor_mdc import generate as gen_cursor_mdc
        gen_cursor_mdc(cwd, language_modules=language_modules,
                       rules_dir=rules_dir)

    if "windsurf" in eds:
        inject_with_rules(
            "generate-windsurf.sh",
            cwd / ".windsurfrules",
            rules_dir,
        )
        from generate_windsurf_rules import generate as gen_windsurf_rules
        gen_windsurf_rules(cwd, language_modules=language_modules,
                           rules_dir=rules_dir)

    if "cline" in eds:
        # Migrate: remove legacy .clinerules single file (replaced by directory)
        legacy_clinerules = cwd / ".clinerules"
        if legacy_clinerules.is_file():
            legacy_clinerules.unlink()
            print("  Migrated: .clinerules file → .clinerules/ directory")
        from generate_cline_rules import generate as gen_cline_rules
        gen_cline_rules(cwd, language_modules=language_modules,
                        rules_dir=rules_dir)

    if "roo" in eds:
        roo_output = run_script("generate-roo-modes.sh", capture=True)
        (cwd / ".roomodes").write_text(roo_output, encoding="utf-8")
        print("  Created: .roomodes")
        from generate_roo_rules import generate as gen_roo_rules
        gen_roo_rules(cwd, language_modules=language_modules,
                      rules_dir=rules_dir)

    if "aider" in eds:
        aider_output = run_script("generate-aider-conf.sh", capture=True)
        (cwd / ".aider.conf.yml").write_text(aider_output, encoding="utf-8")
        print("  Created: .aider.conf.yml")
        inject_with_rules("generate_conventions.py", cwd / "CONVENTIONS.md", rules_dir)

    if "augment" in eds:
        from generate_augment_rules import generate as gen_augment_rules
        gen_augment_rules(cwd, language_modules=language_modules,
                          rules_dir=rules_dir)

    if "antigravity" in eds:
        from generate_antigravity import generate as gen_antigravity
        gen_antigravity(cwd, language_modules=language_modules,
                        rules_dir=rules_dir)

    run_script("install-git-hooks.sh", str(cwd))
