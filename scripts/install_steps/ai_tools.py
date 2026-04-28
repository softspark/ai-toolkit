"""Install global and project-local AI tool configs."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from _common import app_dir, inject_section, should_install, toolkit_dir
from codex_skill_adapter import (
    cleanup_codex_skills,
    sync_codex_skill,
)
from mcp_editors import sync_project_mcp_to_editors
from injection import (
    collapse_blank_runs as _collapse_blank_runs,
    strip_section as _strip_section,
    trim_trailing_blanks as _trim_trailing_blanks,
)


def install_ai_tools(target_dir: Path, rules_dir: Path,
                     dry_run: bool,
                     editors: list[str] | None = None) -> list[str]:
    """Install global editor configs.

    Args:
        editors: Explicit list of editors to install globally. If None,
                 uses DEFAULT_GLOBAL_EDITORS (empty = Claude only).

    Returns:
        List of editors that were actually installed (for state tracking).
    """
    from install_steps.install_state import DEFAULT_GLOBAL_EDITORS, GLOBAL_CAPABLE_EDITORS

    if editors is None:
        eds = set(DEFAULT_GLOBAL_EDITORS)
    else:
        eds = set(editors)

    # Filter to only globally-capable editors
    eds = eds & set(GLOBAL_CAPABLE_EDITORS)

    if not eds:
        return []

    print()
    print("## Other AI Tools (global)")
    print()

    installed: list[str] = []

    # Editors are opt-in via --editors, not filtered by --only/--skip (those
    # control Claude components like agents, hooks, rules).  If an editor is
    # in the requested set, install it unconditionally.

    if "windsurf" in eds:
        windsurf_file = target_dir / ".codeium" / "windsurf" / "memories" / "global_rules.md"
        if dry_run:
            print("  Would inject: ~/.codeium/windsurf/memories/global_rules.md")
        else:
            inject_with_rules("generate-windsurf.sh", windsurf_file, rules_dir)
        installed.append("windsurf")

    if "gemini" in eds:
        gemini_file = target_dir / ".gemini" / "GEMINI.md"
        if dry_run:
            print("  Would inject: ~/.gemini/GEMINI.md")
        else:
            inject_with_rules("generate-gemini.sh", gemini_file, rules_dir)
        installed.append("gemini")

    if "augment" in eds:
        augment_file = target_dir / ".augment" / "rules" / "ai-toolkit.md"
        if dry_run:
            print("  Would inject: ~/.augment/rules/ai-toolkit.md")
        else:
            inject_with_rules("generate-augment.sh", augment_file, rules_dir)
        installed.append("augment")

    if "cline" in eds:
        if dry_run:
            print("  Would generate: ~/Documents/Cline/Rules/ai-toolkit-*.md")
        else:
            _install_cline_global(target_dir, rules_dir)
        installed.append("cline")

    if "roo" in eds:
        if dry_run:
            print("  Would generate: ~/.roo/rules/ai-toolkit-*.md")
        else:
            _install_roo_global(target_dir, rules_dir)
        installed.append("roo")

    if "aider" in eds:
        if dry_run:
            print("  Would create if missing: ~/.aider.conf.yml + ~/.aider-ai-toolkit-CONVENTIONS.md")
        else:
            _install_aider_global(target_dir, rules_dir)
        installed.append("aider")

    if "codex" in eds:
        if dry_run:
            print("  Would inject: ~/AGENTS.md, ~/.agents/, ~/.codex/hooks.json")
        else:
            _install_codex_global(target_dir, rules_dir)
        installed.append("codex")

    if "opencode" in eds:
        if dry_run:
            print("  Would inject: ~/.config/opencode/{AGENTS.md, agents/, "
                  "commands/, plugins/ai-toolkit-hooks.js, opencode.json}")
        else:
            _install_opencode_global(target_dir, rules_dir)
        installed.append("opencode")

    print()
    print(f"  Available: {', '.join(GLOBAL_CAPABLE_EDITORS)}")
    print("  Note: Cursor, Copilot, and Antigravity rule installs are project-local; use 'ai-toolkit install --local' for those.")

    return installed


def _install_codex_global(target_dir: Path, rules_dir: Path) -> None:
    """Install Codex at the global level (~/ layer).

    Creates:
      - ~/AGENTS.md (marker injection with rules)
      - ~/.agents/rules/*.md (directory-based rules)
      - ~/.agents/skills/* (skill symlinks)
      - ~/.codex/hooks.json (lifecycle hooks)
    """
    inject_with_rules(
        "generate_codex.py",
        target_dir / "AGENTS.md",
        rules_dir,
    )

    from generate_codex_rules import generate as gen_codex_rules
    gen_codex_rules(
        target_dir,
        rules_dir=rules_dir,
        managed_scopes=("standard", "custom"),
    )

    from generate_codex_hooks import generate as gen_codex_hooks
    gen_codex_hooks(target_dir)
    print("  Created: ~/.codex/hooks.json")

    _install_codex_skills(target_dir)


def _install_cline_global(target_dir: Path, rules_dir: Path) -> None:
    """Install Cline global rules in the documented user rules directory."""
    from generate_cline_rules import generate as gen_cline_rules

    rules_root = target_dir / "Documents" / "Cline" / "Rules"
    gen_cline_rules(
        target_dir,
        rules_dir=rules_dir,
        output_root=rules_root,
        emit_workflows=False,
        managed_scopes=("standard", "custom"),
    )
    print("  Created: ~/Documents/Cline/Rules/ai-toolkit-*.md")


def _install_roo_global(target_dir: Path, rules_dir: Path) -> None:
    """Install Roo Code global rules in ~/.roo/rules."""
    from generate_roo_rules import generate as gen_roo_rules

    gen_roo_rules(target_dir, rules_dir=rules_dir, output_root=target_dir / ".roo" / "rules")
    print("  Created: ~/.roo/rules/ai-toolkit-*.md")


def _install_aider_global(target_dir: Path, rules_dir: Path) -> None:
    """Install an Aider global config only when it can be created safely.

    Aider supports ~/.aider.conf.yml, but YAML merging without a parser risks
    clobbering user settings. For existing files we leave the user's config
    untouched and print an explicit next step.
    """
    conventions_file = target_dir / ".aider-ai-toolkit-CONVENTIONS.md"
    inject_with_rules("generate_conventions.py", conventions_file, rules_dir)

    config_file = target_dir / ".aider.conf.yml"
    if config_file.exists():
        print("  Kept: ~/.aider.conf.yml (already exists; not merging YAML automatically)")
        print(f"  Available: {conventions_file} for manual read: entry")
        return

    default_model = _aider_default_model()
    config_file.write_text(
        "\n".join([
            "# Aider configuration generated by ai-toolkit",
            "# Aider docs: https://aider.chat/docs/config/aider_conf.html",
            "",
            "architect: true",
            "auto-accept-architect: true",
            "",
            "read:",
            f'  - "{conventions_file}"',
            "",
            f"model: {default_model}",
            f"editor-model: {default_model}",
            "",
            'commit-prompt: "Write a short, concise commit message following Conventional Commits (feat/fix/chore/docs/test/refactor)."',
            "attribute-co-authored-by: false",
            "attribute-commit-message-author: false",
            "attribute-commit-message-committer: false",
            "",
        ]),
        encoding="utf-8",
    )
    print("  Created: ~/.aider.conf.yml")


def _aider_default_model() -> str:
    from _common import DEFAULT_CLAUDE_MODELS

    return DEFAULT_CLAUDE_MODELS["sonnet"]


def _install_opencode_global(target_dir: Path, rules_dir: Path) -> None:
    """Install opencode at the global level (~/.config/opencode/).

    Creates:
      - ~/.config/opencode/AGENTS.md (marker injection with rules)
      - ~/.config/opencode/agents/ai-toolkit-*.md (subagents)
      - ~/.config/opencode/commands/ai-toolkit-*.md (slash commands)
      - ~/.config/opencode/plugins/ai-toolkit-hooks.js (hook bridge)
      - ~/.config/opencode/opencode.json (MCP merge, preserves user keys)
    """
    opencode_home = target_dir / ".config" / "opencode"
    inject_with_rules(
        "generate_opencode.py",
        opencode_home / "AGENTS.md",
        rules_dir,
    )

    from generate_opencode_agents import generate as gen_opencode_agents
    written, removed = gen_opencode_agents(target_dir, config_root=opencode_home)
    msg = f"  Created: ~/.config/opencode/agents/ ({written} agents"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)

    from generate_opencode_commands import generate as gen_opencode_commands
    written, removed = gen_opencode_commands(target_dir, config_root=opencode_home)
    msg = f"  Created: ~/.config/opencode/commands/ ({written} commands"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)

    from generate_opencode_plugin import generate as gen_opencode_plugin
    gen_opencode_plugin(target_dir, config_root=opencode_home)
    print("  Created: ~/.config/opencode/plugins/ai-toolkit-hooks.js")

    from generate_opencode_json import merge_into_opencode_json
    _, count = merge_into_opencode_json(
        target_dir, output_path=opencode_home / "opencode.json"
    )
    suffix = f" ({count} MCP server(s) merged)" if count else " (no MCP servers)"
    print(f"  Created: ~/.config/opencode/opencode.json{suffix}")


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

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"  ERROR: {generator_script} timed out after 120s")
        return
    if result.returncode != 0:
        print(f"  ERROR: {generator_script} failed: {result.stderr.strip()}")
        return

    generated = result.stdout

    target_file = Path(target_file)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if not target_file.exists():
        target_file.touch()

    existing = target_file.read_text(encoding="utf-8")
    # Strip ALL toolkit sections from existing — generated output is the
    # complete source of truth (includes ai-toolkit block + custom rules)
    import re
    existing = re.sub(
        r"<!-- TOOLKIT:[^ ]+ START -->.*?<!-- TOOLKIT:[^ ]+ END -->\n?",
        "",
        existing,
        flags=re.DOTALL,
    )
    existing = _trim_trailing_blanks(existing)
    existing = existing.lstrip("\n")

    parts: list[str] = []
    if existing.strip():
        parts.append(existing)
        parts.append("")  # blank line separator
    parts.append(generated.rstrip("\n"))

    output = "\n".join(parts) + "\n"
    output = _collapse_blank_runs(output)
    output = output.lstrip("\n")
    target_file.write_text(output, encoding="utf-8")
    print(f"  Updated: {target_file}")


def run_script(script_name: str, *args: str, capture: bool = False) -> str:
    """Run a script from the scripts/ directory (prefers .py over .sh)."""
    scripts_dir = toolkit_dir / "scripts"
    py_name = script_name.replace(".sh", ".py").replace("-", "_")
    if (scripts_dir / py_name).is_file():
        cmd = ["python3", str(scripts_dir / py_name), *args]
    else:
        cmd = ["bash", str(scripts_dir / script_name), *args]
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print(f"  ERROR: {script_name} timed out after 120s")
        return ""
    return result.stdout if capture else ""


# All known editor identifiers for --editors flag
ALL_EDITORS = [
    "copilot", "cursor", "windsurf", "cline", "roo",
    "aider", "augment", "antigravity", "codex", "gemini", "opencode",
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
    ".agents/skills": "codex",
    ".codex": "codex",
    # NOTE: AGENTS.md alone is ambiguous (Codex + opencode both read it);
    # prefer the dedicated .opencode/ and opencode.json markers when
    # disambiguating. If only AGENTS.md is present, Codex takes precedence
    # to preserve v2.4.x behavior.
    "AGENTS.md": "codex",
    "opencode.json": "opencode",
    ".opencode": "opencode",
    ".opencode/agents": "opencode",
    ".opencode/commands": "opencode",
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
                          merged_config: dict | None = None,
                          profile: str = "standard",
                          codex_skills: bool = False) -> None:
    """Install project-local configs.

    Claude Code configs (CLAUDE.md, settings, constitution) are always installed.
    Editor configs are installed based on ``--editors`` flag:
    - ``--editors all``: install all editors
    - ``--editors cursor,aider``: install only these
    - (empty): auto-detect from existing project files, install only those

    ``profile`` controls which native surfaces are emitted for each editor:
    - ``minimal``  / ``standard`` / ``strict``: rules (+ Copilot directory mode
      and Gemini hooks from ``standard`` onwards — both non-breaking).
    - ``full``: adds every native surface an editor can host (subagents,
      custom commands, hooks, skill-catalogue pointers).

    ``codex_skills`` (opt-in, off by default) explicitly refreshes the full
    Codex skill catalog under ``.agents/skills/``. ``--editors codex`` already
    installs this catalog for normal local installs; the flag is kept as a
    direct generator contract for scripts and dry-run verification.

    If ``merged_config`` is provided (from .softspark-toolkit.json extends resolution),
    additional rules and constitution amendments from the base config are injected.
    """
    cwd = Path.cwd()
    resolved_editors = _resolve_editors(editors, cwd)

    print()
    print(f"## Project-local ({cwd})")
    if merged_config and merged_config.get("_extends_meta"):
        meta = merged_config["_extends_meta"]
        print(f"   Config: .softspark-toolkit.json (extends: {meta['source']})")
    if reset:
        print("   Mode: RESET (all local configs will be wiped and recreated)")
    if resolved_editors:
        print(f"   Editors: {', '.join(resolved_editors)}")
    else:
        print("   Editors: none (use --editors <list> or --editors all to enable)")
    if profile:
        print(f"   Profile: {profile}")
    print()

    if dry_run:
        _install_local_dry_run(reset, resolved_editors, profile=profile,
                               codex_skills=codex_skills)
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
                                  language_modules=language_modules,
                                  profile=profile,
                                  codex_skills=codex_skills)


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
        state_file = cwd / ".softspark-toolkit-extends.json"
        state_file.write_text(_json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"  Saved: .softspark-toolkit-extends.json (resolution metadata)")


def _inject_language_rules(cwd: Path, language_modules: list[str] | None) -> None:
    """Inject ``app/rules/common/*.md`` content into project's ``.claude/CLAUDE.md``.

    Per-language rules (``app/rules/<lang>/``) are NOT injected here -- they
    ship as ``<lang>-rules`` knowledge skills under ``app/skills/`` and load
    contextually via the Agent Skills progressive-disclosure mechanism. This
    keeps ``CLAUDE.md`` small while ensuring language-specific guidance still
    reaches Claude when relevant.

    Common rules are language-agnostic (security, git workflow, testing,
    coding-style, performance) and stay inlined so they remain in scope for
    every prompt.
    """
    if not language_modules:
        return

    rules_src = app_dir / "rules"
    common_dir = rules_src / "common"
    if not common_dir.is_dir():
        return

    # Detect requested per-language modules so we can name the linked skills
    # in the marker block. The modules themselves are not inlined.
    langs: list[str] = []
    for mod in language_modules:
        if mod.startswith("rules-"):
            name = mod[6:]
            if name != "common":
                langs.append(name)

    # Inline full content of every common rule file, stripping YAML
    # frontmatter so the resulting block reads as plain Markdown.
    inlined: list[str] = []
    for f in sorted(common_dir.glob("*.md")):
        body = f.read_text(encoding="utf-8")
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end != -1:
                body = body[end + 4:].lstrip("\n")
        inlined.append(body.rstrip())

    lines: list[str] = ["# Language Rules", ""]
    lines.append(
        "Common (language-agnostic) rules apply to every change in this "
        "project. Language-specific rules live in `<lang>-rules` knowledge "
        "skills (e.g. `python-rules`, `typescript-rules`) and load "
        "automatically when their triggers match -- you do not need to "
        "Read them manually."
    )
    if langs:
        skill_names = ", ".join(f"`{l}-rules`" for l in langs)
        lines.append("")
        lines.append(f"Detected languages: {skill_names}.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.extend(inlined)

    # Write to temp file, then inject as a single named section so reruns are
    # idempotent (existing block is replaced, not duplicated).
    import tempfile
    combined = "\n\n".join(lines).rstrip() + "\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False,
                                     encoding="utf-8") as tmp:
        tmp.write(combined)
        tmp_path = Path(tmp.name)

    try:
        inject_section(tmp_path, cwd / ".claude" / "CLAUDE.md", "language-rules")
        if langs:
            print(f"  Injected: common rules + {len(langs)} language skill(s) "
                  f"({', '.join(langs)})")
        else:
            print("  Injected: common rules")
    finally:
        tmp_path.unlink(missing_ok=True)


def _install_local_dry_run(reset: bool, editors: list[str] | None = None,
                            profile: str = "standard",
                            codex_skills: bool = False) -> None:
    eds = set(editors or [])
    if reset:
        print("  Would remove: CLAUDE.md, .claude/settings.local.json")
        print("  Would remove: .claude/constitution.md and all editor configs")
        print("  Would recreate all from templates (clean slate)")
    else:
        print("  Would create: CLAUDE.md (if missing)")
        print("  Would create: .claude/settings.local.json (if missing)")
        print("  Would inject: .claude/constitution.md")

    add_copilot_dir = profile in {"standard", "strict", "full"}
    add_gemini_hooks = profile in {"standard", "strict", "full"}
    add_native_surfaces = profile == "full"

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
        "gemini":       "  Would generate: GEMINI.md",
        "opencode":     "  Would generate: AGENTS.md + .opencode/{agents,commands,plugins}/ + opencode.json",
    }
    for ed, msg in _EDITOR_DRY_RUN.items():
        if ed in eds:
            print(msg)

    # Profile-driven extras (matrix in kb/reference/global-install-model.md)
    if "copilot" in eds and add_copilot_dir:
        print("  Would generate: .github/instructions/ + .github/prompts/ (profile >= standard)")
    if "gemini" in eds and add_gemini_hooks:
        print("  Would generate: .gemini/settings.json hooks (profile >= standard)")
    if add_native_surfaces:
        if "cursor" in eds:
            print("  Would generate: .cursor/hooks.json + .cursor/agents/ (profile=full)")
        if "windsurf" in eds:
            print("  Would generate: .windsurf/hooks.json (profile=full)")
        if "augment" in eds:
            print("  Would generate: .augment/agents/ + .augment/commands/ + "
                  "$HOME/.augment/settings.json + .augment/skills/ (profile=full)")
        if "gemini" in eds:
            print("  Would generate: .gemini/commands/ + .gemini/skills/ (profile=full)")
    if "codex" in eds:
        print("  Would generate: .agents/skills/ Codex skills")
        if codex_skills:
            print("  Would refresh: .agents/skills/ via --codex-skills")

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

    # opencode: remove only ai-toolkit-prefixed generated files so the
    # user's own .opencode/agents/ or commands/ entries are preserved.
    # opencode.json is left alone — it may contain user MCP servers and other
    # project settings; reinstall re-merges our MCP entries idempotently.
    opencode_plugin = cwd / ".opencode" / "plugins" / "ai-toolkit-hooks.js"
    if opencode_plugin.is_file():
        opencode_plugin.unlink()
        print("  Removed: .opencode/plugins/ai-toolkit-hooks.js")
    for sub in ("agents", "commands"):
        sub_dir = cwd / ".opencode" / sub
        if sub_dir.is_dir():
            removed_any = False
            for f in sorted(sub_dir.glob("ai-toolkit-*.md")):
                f.unlink()
                removed_any = True
            if removed_any:
                print(f"  Removed: .opencode/{sub}/ai-toolkit-*.md")


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


def _install_codex_skills(cwd: Path) -> None:
    """Install all skills to `.agents/skills/` for Codex.

    Native Codex-compatible skills are symlinked directly. Skills that rely on
    Claude-only orchestration primitives are rendered into generated wrappers
    with Codex-native delegation guidance.
    """
    skills_src = app_dir / "skills"
    if not skills_src.is_dir():
        return

    skills_dst = cwd / ".agents" / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)

    linked = 0
    adapted = 0
    skipped = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue

        mode = sync_codex_skill(skill_dir, skills_dst)
        if mode == "linked":
            linked += 1
        elif mode == "adapted":
            adapted += 1
        else:
            skipped += 1

    cleanup_codex_skills(skills_dst, skills_src)

    print(
        f"  Installed: {linked + adapted} skills to .agents/skills/"
        f" ({linked} linked, {adapted} adapted, {skipped} skipped)"
    )


def _try_generator(module_name: str, *args, **kwargs) -> bool:
    """Import and invoke ``<module>.generate(...)``.

    Post v3.0.0 all referenced generators ship with the toolkit. An ImportError
    here therefore indicates a real packaging bug, not a roll-out gap. We print
    a loud error and re-raise so CI and interactive installs fail fast instead
    of silently skipping a native surface.
    """
    try:
        module = __import__(module_name)
    except ImportError as exc:
        print(f"  INTERNAL ERROR: shipped generator '{module_name}' failed to "
              f"import ({exc.msg}). Please file a bug at "
              f"https://github.com/softspark/ai-toolkit/issues")
        raise

    gen = getattr(module, "generate", None)
    if gen is None:
        raise RuntimeError(
            f"INTERNAL ERROR: shipped generator '{module_name}' has no "
            f"generate() function. This is a packaging bug."
        )

    gen(*args, **kwargs)
    return True


def _create_local_ai_tool_configs(cwd: Path, rules_dir: Path,
                                   editors: list[str],
                                   language_modules: list[str] | None = None,
                                   profile: str = "standard",
                                   codex_skills: bool = False) -> None:
    eds = set(editors)
    # `full` implies the `standard` additions (Copilot dir + Gemini hooks)
    # plus every native-surface generator we ship. Normalize unknown
    # profiles to `standard` so callers never produce a silent no-op.
    _profile = profile if profile in {"minimal", "standard", "strict", "full"} else "standard"
    add_copilot_dir = _profile in {"standard", "strict", "full"}
    add_gemini_hooks = _profile in {"standard", "strict", "full"}
    add_native_surfaces = _profile == "full"

    if "copilot" in eds:
        inject_with_rules(
            "generate-copilot.sh",
            cwd / ".github" / "copilot-instructions.md",
            rules_dir,
        )
        # `standard` and above: emit path-specific instructions + prompt files
        # (directory mode). `minimal` stays backwards-compatible with v2.
        if add_copilot_dir:
            from generate_copilot import generate as gen_copilot_dir
            gen_copilot_dir(cwd, language_modules=language_modules,
                            rules_dir=rules_dir)

    if "cursor" in eds:
        inject_with_rules(
            "generate-cursor-rules.sh",
            cwd / ".cursorrules",
            rules_dir,
        )
        from generate_cursor_mdc import generate as gen_cursor_mdc
        gen_cursor_mdc(cwd, language_modules=language_modules,
                       rules_dir=rules_dir)
        if add_native_surfaces:
            _try_generator("generate_cursor_hooks", cwd)
            _try_generator("generate_cursor_agents", cwd)

    if "windsurf" in eds:
        inject_with_rules(
            "generate-windsurf.sh",
            cwd / ".windsurfrules",
            rules_dir,
        )
        from generate_windsurf_rules import generate as gen_windsurf_rules
        gen_windsurf_rules(cwd, language_modules=language_modules,
                           rules_dir=rules_dir)
        if add_native_surfaces:
            _try_generator("generate_windsurf_hooks", cwd)

    if "cline" in eds:
        # Migrate: remove legacy .clinerules single file (replaced by directory)
        legacy_clinerules = cwd / ".clinerules"
        if legacy_clinerules.is_file():
            legacy_clinerules.unlink()
            print("  Migrated: .clinerules file → .clinerules/ directory")
        from generate_cline_rules import generate as gen_cline_rules
        gen_cline_rules(
            cwd,
            language_modules=language_modules,
            rules_dir=rules_dir,
            managed_scopes=("standard", "lang", "custom"),
        )

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
        if add_native_surfaces:
            _try_generator("generate_augment_agents", cwd)
            _try_generator("generate_augment_commands", cwd)
            # Augment hooks live under $HOME/.augment/settings.json. The
            # generator takes HOME (not cwd) per bucket-1 contract.
            _try_generator("generate_augment_hooks", Path.home())
            _try_generator("generate_augment_skills", cwd)

    if "antigravity" in eds:
        from generate_antigravity import generate as gen_antigravity
        gen_antigravity(cwd, language_modules=language_modules,
                        rules_dir=rules_dir)

    if "codex" in eds:
        # AGENTS.md — marker injection (like CLAUDE.md)
        inject_with_rules(
            "generate_codex.py",
            cwd / "AGENTS.md",
            rules_dir,
        )
        # .agents/rules/ — directory-based rules
        from generate_codex_rules import generate as gen_codex_rules
        gen_codex_rules(
            cwd,
            language_modules=language_modules,
            rules_dir=rules_dir,
            managed_scopes=("standard", "lang", "custom"),
        )
        # .codex/hooks.json — Codex lifecycle hooks
        from generate_codex_hooks import generate as gen_codex_hooks
        gen_codex_hooks(cwd)
        print("  Created: .codex/hooks.json")
        # .agents/skills/ — Codex discovery path for repo-local skills
        _install_codex_skills(cwd)
        # --codex-skills explicitly re-runs the same Codex skill sync path.
        # Codex upstream discovers skills from .agents/skills/, not .codex/skills/.
        if codex_skills:
            _try_generator("generate_codex_skills", cwd,
                           enable_codex_skills=True)

    if "gemini" in eds:
        # GEMINI.md — marker injection from the shared generator output
        inject_with_rules(
            "generate-gemini.sh",
            cwd / "GEMINI.md",
            rules_dir,
        )
        if add_gemini_hooks:
            _try_generator("generate_gemini_hooks", cwd)
        if add_native_surfaces:
            _try_generator("generate_gemini_commands", cwd)
            _try_generator("generate_gemini_skills", cwd)

    if "opencode" in eds:
        # AGENTS.md — shared with Codex via marker injection (opencode reads same file)
        # Use a dedicated section tag so Codex and opencode don't clobber each other.
        inject_with_rules(
            "generate_opencode.py",
            cwd / "AGENTS.md",
            rules_dir,
        )
        # .opencode/agents/ — native subagents
        from generate_opencode_agents import generate as gen_opencode_agents
        written, removed = gen_opencode_agents(cwd)
        msg = f"  Created: .opencode/agents/ ({written} agents"
        if removed:
            msg += f", {removed} stale removed"
        msg += ")"
        print(msg)
        # .opencode/commands/ — native slash commands
        from generate_opencode_commands import generate as gen_opencode_commands
        written, removed = gen_opencode_commands(cwd)
        msg = f"  Created: .opencode/commands/ ({written} commands"
        if removed:
            msg += f", {removed} stale removed"
        msg += ")"
        print(msg)
        # .opencode/plugins/ai-toolkit-hooks.js — lifecycle hook bridge
        from generate_opencode_plugin import generate as gen_opencode_plugin
        gen_opencode_plugin(cwd)
        print("  Created: .opencode/plugins/ai-toolkit-hooks.js")
        # opencode.json — merge MCP servers from .mcp.json (preserves user keys)
        from generate_opencode_json import merge_into_opencode_json
        _, mcp_count = merge_into_opencode_json(cwd)
        if mcp_count:
            print(f"  Updated: opencode.json ({mcp_count} MCP server(s) from .mcp.json)")
        else:
            print("  Updated: opencode.json ($schema set)")

    synced_paths = sync_project_mcp_to_editors(cwd, sorted(eds))
    for path in synced_paths:
        rel = path.relative_to(cwd)
        print(f"  Synced: {rel} (from .mcp.json)")

    run_script("install-git-hooks.sh", str(cwd))
