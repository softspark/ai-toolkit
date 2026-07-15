"""Install global and project-local AI tool configs."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from _common import app_dir, inject_section, toolkit_dir
from codex_skill_adapter import (
    cleanup_codex_skills,
    prepare_codex_skills_dir,
    sync_codex_skill,
    unmanaged_codex_skill_names,
)
from mcp_editors import sync_project_mcp_to_editors
from injection import (
    collapse_blank_runs as _collapse_blank_runs,
    strip_all_sections as _strip_all_sections,
    trim_trailing_blanks as _trim_trailing_blanks,
)


def install_ai_tools(target_dir: Path, rules_dir: Path,
                     dry_run: bool,
                     editors: list[str] | None = None,
                     profile: str = "standard") -> list[str]:
    """Install global editor configs.

    Args:
        editors: Explicit list of editors to install globally. If None,
                 uses DEFAULT_GLOBAL_EDITORS (empty = Claude only).
        profile: Install profile. Gates each editor's optional native surfaces
                 the same way the local install does — hooks at
                 standard/strict/full, sub-agents/commands/skills at full.

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

    _profile = profile if profile in {"minimal", "standard", "strict", "full"} else "standard"
    add_hooks = _profile in {"standard", "strict", "full"}
    add_native_surfaces = _profile == "full"

    print()
    print("## Other AI Tools (global)")
    print()

    installed: list[str] = []

    # Editors are opt-in via --editors, not filtered by --only/--skip (those
    # control Claude components like agents, hooks, rules).  If an editor is
    # in the requested set, install it unconditionally.

    if "windsurf" in eds:
        if dry_run:
            print("  Would inject: ~/.codeium/windsurf/memories/global_rules.md")
            print("  Would generate: ~/.codeium/windsurf/skills/ai-toolkit-skill-catalogue/SKILL.md")
            print("  Would inject: ~/.config/devin/AGENTS.md (Devin CLI global rules)")
        else:
            _install_windsurf_global(target_dir, rules_dir)
        installed.append("windsurf")

    if "gemini" in eds:
        gemini_file = target_dir / ".gemini" / "GEMINI.md"
        if dry_run:
            print("  Would inject: ~/.gemini/GEMINI.md")
            if add_hooks:
                print("  Would generate: ~/.gemini/settings.json (hooks)")
            if add_native_surfaces:
                print("  Would generate: ~/.gemini/commands/, ~/.gemini/skills/")
        else:
            inject_with_rules("generate-gemini.sh", gemini_file, rules_dir)
            # Hooks (~/.gemini/settings.json), commands (~/.gemini/commands/),
            # and the skills pointer (~/.gemini/skills/) are documented user-tier
            # surfaces — install them globally, gated like the local install.
            if add_hooks:
                _try_generator("generate_gemini_hooks", target_dir)
            if add_native_surfaces:
                _try_generator("generate_gemini_commands", target_dir)
                _try_generator("generate_gemini_skills", target_dir)
        installed.append("gemini")

    if "augment" in eds:
        augment_file = target_dir / ".augment" / "rules" / "ai-toolkit.md"
        if dry_run:
            print("  Would inject: ~/.augment/rules/ai-toolkit.md")
            if add_native_surfaces:
                print("  Would generate: ~/.augment/agents/, ~/.augment/commands/, ~/.augment/settings.json (hooks)")
        else:
            inject_with_rules("generate-augment.sh", augment_file, rules_dir)
            # Sub-agents, commands, and hooks all have documented user-tier
            # surfaces under ~/.augment — a global-only Augment user otherwise
            # gets no hooks/agents/commands. Gate them like the local install.
            if add_native_surfaces:
                _try_generator("generate_augment_agents", target_dir)
                _try_generator("generate_augment_commands", target_dir)
                _try_generator("generate_augment_hooks", target_dir)
        installed.append("augment")

    if "cline" in eds:
        if dry_run:
            print("  Would generate: ~/Documents/Cline/Rules/ai-toolkit-*.md")
            if _claude_skills_discoverable(target_dir):
                print("  Would reuse: ~/.claude/skills/ (Cline-compatible discovery)")
            else:
                print("  Would generate: ~/.cline/skills/ai-toolkit-skill-catalogue/SKILL.md")
        else:
            _install_cline_global(target_dir, rules_dir)
        installed.append("cline")

    if "roo" in eds:
        if dry_run:
            print("  Would generate: ~/.roo/rules/ai-toolkit-*.md")
            if "codex" not in eds:
                print("  Would generate: ~/.agents/skills/* (Roo native skill discovery)")
        else:
            _install_roo_global(target_dir, rules_dir)
            # Roo/Zoo Code natively discover skills from ~/.agents/skills. Reuse
            # the shared installer, but skip when codex is also selected — its
            # branch populates the same directory — to avoid a duplicate pass.
            if "codex" not in eds:
                _install_codex_skills(target_dir)
        installed.append("roo")

    if "aider" in eds:
        if dry_run:
            print("  Would create if missing: ~/.aider.conf.yml + ~/.aider-ai-toolkit-CONVENTIONS.md")
        else:
            _install_aider_global(target_dir, rules_dir)
        installed.append("aider")

    if "codex" in eds:
        if dry_run:
            print("  Would inject: $CODEX_HOME/AGENTS.md, $CODEX_HOME/agents/, "
                  "$CODEX_HOME/hooks.json")
            print("  Would generate: ~/.agents/skills/ (shared Codex skill discovery)")
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

    if "cursor" in eds:
        # Cursor RULES have no mergeable global file surface (Settings UI only),
        # but ~/.cursor/hooks.json is a documented user-level hooks scope — so a
        # global Cursor install activates the safety/quality hooks everywhere.
        if dry_run:
            if add_hooks:
                print("  Would generate: ~/.cursor/hooks.json (global hooks)")
        elif add_hooks:
            _try_generator("generate_cursor_hooks", target_dir)
        installed.append("cursor")

    if "copilot" in eds:
        # Copilot CLI reads every personal customization from its active config
        # root. COPILOT_HOME replaces ~/.copilot rather than extending it.
        from generate_copilot_hooks import copilot_home

        copilot_root = copilot_home(target_dir)
        if copilot_root.is_symlink():
            raise RuntimeError(
                f"Refusing symlinked Copilot configuration root: {copilot_root}"
            )
        if dry_run:
            print("  Would inject: $COPILOT_HOME/copilot-instructions.md")
            print("  Would generate: $COPILOT_HOME/{instructions,agents,skills}/")
            if add_hooks:
                print("  Would generate: $COPILOT_HOME/hooks/ai-toolkit.json")
        else:
            inject_with_rules(
                "generate_copilot.py",
                copilot_root / "copilot-instructions.md",
                rules_dir,
            )
            _try_generator("generate_copilot", target_dir,
                           rules_dir=rules_dir, config_root=copilot_root,
                           emit_prompts=False)
            if add_hooks:
                _try_generator(
                    "generate_copilot_hooks",
                    target_dir,
                    config_root=copilot_root,
                )
        installed.append("copilot")

    if "antigravity" in eds:
        # Antigravity RULES stay project-local, but the skill pointer has a
        # documented global surface: ~/.gemini/config/skills (all Antigravity
        # products) and ~/.gemini/antigravity-cli/skills (CLI-private).
        if dry_run:
            print("  Would generate: ~/.gemini/config/skills/, ~/.gemini/antigravity-cli/skills/ (skill pointer)")
        else:
            from generate_antigravity import generate_global as gen_antigravity_global
            gen_antigravity_global(target_dir)
        installed.append("antigravity")

    print()
    print(f"  Available: {', '.join(GLOBAL_CAPABLE_EDITORS)}")
    print("  Note: Cursor and Antigravity RULES stay project-local (no mergeable "
          "global file surface); their global installs cover hooks/skills only. "
          "Use 'ai-toolkit install --local' for full per-project setup.")

    return installed


def _resolve_global_codex_home(target_dir: Path) -> Path:
    """Resolve the active Codex user root without changing project paths."""
    configured = os.environ.get("CODEX_HOME")
    if not configured:
        return target_dir / ".codex"

    codex_home = Path(configured).expanduser()
    if not codex_home.is_absolute():
        raise RuntimeError("CODEX_HOME must be an absolute path")
    if not codex_home.is_dir():
        raise RuntimeError("Configured CODEX_HOME must already exist")
    if codex_home.is_symlink():
        raise RuntimeError(f"Refusing symlinked CODEX_HOME: {codex_home}")
    return codex_home


def _install_codex_global(target_dir: Path, rules_dir: Path) -> None:
    """Install Codex at the active user-level ``CODEX_HOME`` layer.

    Creates:
      - ``$CODEX_HOME/AGENTS.md`` (defaults to ``~/.codex/AGENTS.md``)
      - ``$CODEX_HOME/agents/*`` and ``$CODEX_HOME/hooks.json``
      - ``~/.agents/skills/*`` (the documented shared user-skill path)
    """
    codex_home = _resolve_global_codex_home(target_dir)
    inject_with_rules(
        "generate_codex.py",
        codex_home / "AGENTS.md",
        rules_dir,
    )

    # Migration: earlier versions wrote global instructions to ~/AGENTS.md,
    # which Codex never loads as global instructions. Strip that stale toolkit
    # section so upgraders are not left with dead, unread content.
    if _strip_toolkit_sections(target_dir / "AGENTS.md"):
        print("  Migrated: removed stale ai-toolkit section from ~/AGENTS.md")

    override = codex_home / "AGENTS.override.md"
    if override.is_file() and override.read_text(encoding="utf-8").strip():
        print(
            f"  Warning: {override} exists and takes precedence over "
            f"{codex_home / 'AGENTS.md'} — toolkit rules will be masked."
        )

    from generate_codex_hooks import generate as gen_codex_hooks
    gen_codex_hooks(
        target_dir,
        global_install=True,
        codex_home=codex_home,
    )
    print(f"  Created: {codex_home / 'hooks.json'}")

    _install_codex_agents(target_dir, config_root=codex_home)
    _install_codex_skills(target_dir)


def _claude_skills_discoverable(project_dir: Path | None = None) -> bool:
    """True when real ai-toolkit skills already exist at a ``.claude/skills``
    directory the editor scans natively (project-local or global
    ``~/.claude/skills``), making an editor skill-catalogue pointer redundant.

    Cursor, Cline and Augment discover ``SKILL.md`` from ``.claude/skills`` and
    ``~/.claude/skills`` by default, so when those are populated the pointer adds
    nothing. (Windsurf/Devin gates that scan behind a setting and is excluded
    from the conditional by its callers.) Returns ``False`` for editor-only
    installs (no Claude skills present), where the pointer is the only
    skill-discovery surface.
    """
    candidates = [Path.home() / ".claude" / "skills"]
    if project_dir is not None:
        candidates.insert(0, project_dir / ".claude" / "skills")
    return any(d.is_dir() and any(d.glob("*/SKILL.md")) for d in candidates)


def _install_windsurf_global(target_dir: Path, rules_dir: Path) -> None:
    """Install Windsurf global rules plus an Agent Skills catalogue pointer."""
    windsurf_file = target_dir / ".codeium" / "windsurf" / "memories" / "global_rules.md"
    inject_with_rules("generate-windsurf.sh", windsurf_file, rules_dir)

    # Devin CLI reads global rules from ~/.config/devin/AGENTS.md, NOT the
    # Desktop ~/.codeium/windsurf/memories/global_rules.md (that path is absent
    # from read_config_from.windsurf). Cover editor-only Devin CLI installs
    # where no global Claude install (~/.claude/CLAUDE.md compat read) exists.
    devin_agents = target_dir / ".config" / "devin" / "AGENTS.md"
    inject_with_rules("generate-windsurf.sh", devin_agents, rules_dir)

    from generate_windsurf_skills import generate as gen_windsurf_skills
    # Windsurf is excluded from the .claude/skills conditional: its native scan
    # of .claude/skills is gated behind a Devin "Claude Code config reading"
    # setting, so we always emit the pointer as a reliable fallback.
    gen_windsurf_skills(
        target_dir,
        skill_root=".codeium/windsurf/skills",
    )


def _cleanup_retired_windsurf_surfaces(cwd: Path) -> None:
    """Remove only ai-toolkit content from retired/undocumented Devin paths."""
    import json

    legacy_hooks = cwd / ".windsurf" / "hooks.json"
    if legacy_hooks.is_file():
        try:
            document = json.loads(legacy_hooks.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print("  Warning: kept invalid .windsurf/hooks.json for manual review")
        else:
            hooks = document.get("hooks") if isinstance(document, dict) else None
            changed = False
            if isinstance(hooks, dict):
                kept_hooks: dict = {}
                for event, entries in hooks.items():
                    if not isinstance(entries, list):
                        kept_hooks[event] = entries
                        continue
                    survivors = [
                        entry
                        for entry in entries
                        if not (
                            isinstance(entry, dict)
                            and (
                                entry.get("_source") == "ai-toolkit"
                                or any(
                                    isinstance(handler, dict)
                                    and handler.get("_source") == "ai-toolkit"
                                    for handler in entry.get("hooks", [])
                                )
                            )
                        )
                    ]
                    if len(survivors) != len(entries):
                        changed = True
                    if survivors:
                        kept_hooks[event] = survivors
                if changed:
                    if kept_hooks:
                        document["hooks"] = kept_hooks
                    else:
                        document.pop("hooks", None)
                    if document:
                        legacy_hooks.write_text(
                            json.dumps(
                                document,
                                indent=4,
                                ensure_ascii=False,
                                sort_keys=True,
                            ) + "\n",
                            encoding="utf-8",
                        )
                    else:
                        legacy_hooks.unlink()
                    print("  Migrated: removed retired ai-toolkit Cascade hooks")

    retired_pointer = (
        cwd / ".devin" / "skills" / "ai-toolkit-skill-catalogue"
    )
    skill_file = retired_pointer / "SKILL.md"
    if skill_file.is_file() and "name: ai-toolkit-skill-catalogue" in (
        skill_file.read_text(encoding="utf-8")
    ):
        if retired_pointer.is_symlink():
            retired_pointer.unlink()
        else:
            shutil.rmtree(retired_pointer)
        for parent in (retired_pointer.parent, retired_pointer.parent.parent):
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
        print("  Migrated: removed undocumented .devin/skills toolkit pointer")


def _install_cline_global(target_dir: Path, rules_dir: Path) -> None:
    """Install Cline global rules in the documented ~/.cline directory."""
    from generate_cline_rules import generate as gen_cline_rules

    # Cline reads GLOBAL rules from ~/Documents/Cline/Rules/ (docs.cline.bot);
    # ~/.cline/rules/ is not a Cline-read path.
    rules_root = target_dir / "Documents" / "Cline" / "Rules"
    gen_cline_rules(
        target_dir,
        rules_dir=rules_dir,
        output_root=rules_root,
        emit_workflows=False,
        managed_scopes=("standard", "custom"),
    )
    print("  Created: ~/Documents/Cline/Rules/ai-toolkit-*.md")

    from generate_cline_skills import generate as gen_cline_skills
    gen_cline_skills(target_dir, emit_skill_pointer=not _claude_skills_discoverable(target_dir))


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
    # complete source of truth (includes ai-toolkit block + custom rules).
    # The shared parser also repairs nested legacy sections and orphan markers.
    existing = _strip_all_sections(existing)
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


def _strip_toolkit_sections(target_file: Path) -> bool:
    """Remove ai-toolkit ``<!-- TOOLKIT:* -->`` marker sections from an existing
    file, preserving any non-toolkit content. Returns True if the file changed.

    Used to clean a stale ~/AGENTS.md after Codex global instructions moved to
    ~/.codex/AGENTS.md. If stripping leaves the file empty (it only ever held
    toolkit content), the file is removed.
    """
    if not target_file.is_file():
        return False
    original = target_file.read_text(encoding="utf-8")
    stripped = _strip_all_sections(original)
    if stripped == original:
        return False
    stripped = stripped.lstrip("\n")
    if stripped.strip():
        target_file.write_text(stripped, encoding="utf-8")
    else:
        target_file.unlink()
    return True


def _install_copilot_agents_md(cwd: Path, rules_dir: Path) -> None:
    """Emit the same effective AGENTS.md used by Codex, including rules."""
    inject_with_rules(
        "generate_codex.py",
        cwd / "AGENTS.md",
        rules_dir,
    )
    print("  Updated: AGENTS.md (shared Codex/Copilot instructions)")


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
    ".github/instructions": "copilot",
    ".github/prompts": "copilot",
    ".github/agents": "copilot",
    ".github/skills": "copilot",
    ".github/hooks": "copilot",
    ".github/mcp.json": "copilot",
    ".cursorrules": "cursor",
    ".cursor/rules": "cursor",
    ".windsurfrules": "windsurf",
    ".windsurf/rules": "windsurf",
    # .devin/ is the primary Devin Desktop tree since the 2026-06-02 rebrand;
    # .windsurf/ markers stay to detect legacy installs.
    ".devin/rules": "windsurf",
    ".clinerules": "cline",
    ".roomodes": "roo",
    ".roo/rules": "roo",
    ".aider.conf.yml": "aider",
    "CONVENTIONS.md": "aider",
    ".augment/rules": "augment",
    # Antigravity 2.0 default is plural .agents/; .agents/workflows is the
    # unambiguous marker (Codex also writes .agents/rules but no workflows).
    # Singular .agent/rules is kept to detect legacy installs.
    ".agents/workflows": "antigravity",
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
        if not p.exists():
            continue
        if marker == ".agents/skills" and _is_pointer_only_skills_dir(p):
            # The Antigravity CLI pointer skill also lives in .agents/skills/;
            # only real (materialized) skills indicate a Codex install.
            continue
        found.add(editor)
    return sorted(found)


def _is_pointer_only_skills_dir(skills_dir: Path) -> bool:
    """True when a skills dir holds only the ai-toolkit pointer skill."""
    try:
        entries = [e.name for e in skills_dir.iterdir() if not e.name.startswith(".")]
    except OSError:
        return False
    return entries == ["ai-toolkit-skill-catalogue"]


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
            print("  Would apply merged config from extends")
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
        print("  Saved: .softspark-toolkit-extends.json (resolution metadata)")


def _inject_language_rules(cwd: Path, language_modules: list[str] | None) -> None:
    """Install Claude language-rule entrypoints for a project.

    Per-language rules (``app/rules/<lang>/``) are NOT injected here -- they
    ship as ``<lang>-rules`` knowledge skills under ``app/skills/`` and load
    contextually via the Agent Skills progressive-disclosure mechanism.

    Common rules are written as Claude Code path-scoped rules under
    ``.claude/rules/``. Current Claude Code guidance targets under 200 lines
    per ``CLAUDE.md`` file; path-scoped rules keep startup context smaller
    while still loading the rule bodies when project files are opened.
    """
    if not language_modules:
        return

    rules_src = app_dir / "rules"
    common_dir = rules_src / "common"
    if not common_dir.is_dir():
        return

    rule_files = _sync_claude_common_rules(cwd, common_dir)

    # Detect requested per-language modules so we can name the linked skills
    # in the marker block. The modules themselves are not inlined.
    langs: list[str] = []
    for mod in language_modules:
        if mod.startswith("rules-"):
            name = mod[6:]
            if name != "common":
                langs.append(name)

    lines: list[str] = ["# Language Rules", ""]
    lines.append(
        "Common ai-toolkit rules live in `.claude/rules/ai-toolkit-*.md` "
        "with Claude Code `paths` frontmatter so they load when project files "
        "are opened instead of expanding this CLAUDE.md at session startup."
    )
    if rule_files:
        lines.append("")
        lines.append("Common rule files: " + ", ".join(f"`{p}`" for p in rule_files) + ".")
    lines.append("")
    lines.append(
        "Language-specific rules live in `<lang>-rules` knowledge skills "
        "(e.g. `python-rules`, `typescript-rules`) and load automatically "
        "when their triggers match -- you do not need to Read them manually."
    )
    if langs:
        skill_names = ", ".join(f"`{language}-rules`" for language in langs)
        lines.append("")
        lines.append(f"Detected languages: {skill_names}.")

    # Write to temp file, then inject as a single named section so reruns are
    # idempotent (existing block is replaced, not duplicated).
    import tempfile
    combined = "\n".join(lines).rstrip() + "\n"
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


def _strip_rule_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def _sync_claude_common_rules(cwd: Path, common_dir: Path) -> list[str]:
    """Write common ai-toolkit rules as Claude Code path-scoped rules.

    Only ``ai-toolkit-*.md`` files are managed. User-authored files in
    ``.claude/rules/`` are preserved.
    """
    rules_dir = cwd / ".claude" / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)

    source_files = sorted(common_dir.glob("*.md"))
    expected = {f"ai-toolkit-{src.stem}.md" for src in source_files}
    for stale in sorted(rules_dir.glob("ai-toolkit-*.md")):
        if stale.name not in expected:
            stale.unlink()

    written: list[str] = []
    for src in source_files:
        body = _strip_rule_frontmatter(src.read_text(encoding="utf-8")).rstrip()
        rel = Path(".claude") / "rules" / f"ai-toolkit-{src.stem}.md"
        target = cwd / rel
        target.write_text(
            "\n".join([
                "---",
                "paths:",
                '  - "**/*"',
                "---",
                "",
                body,
                "",
            ]),
            encoding="utf-8",
        )
        written.append(rel.as_posix())

    return written


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
        print("  Would generate: .claude/rules/ai-toolkit-*.md")

    add_copilot_dir = profile in {"standard", "strict", "full"}
    add_gemini_hooks = profile in {"standard", "strict", "full"}
    add_native_surfaces = profile == "full"

    # Editor-specific dry-run messages
    _EDITOR_DRY_RUN = {
        "copilot":      "  Would inject: .github/copilot-instructions.md + AGENTS.md",
        "cursor":       "  Would generate: .cursorrules + .cursor/rules/*.mdc",
        "windsurf":     "  Would generate: .windsurfrules + .devin/rules/*.md + .windsurf/rules/*.md",
        "cline":        "  Would generate: .clinerules/*.md",
        "roo":          "  Would generate: .roomodes + .roo/rules/*.md",
        "aider":        "  Would generate: .aider.conf.yml + CONVENTIONS.md",
        "augment":      "  Would generate: .augment/rules/ai-toolkit-*.md",
        "antigravity":  "  Would generate: .agents/rules/ + .agents/workflows/",
        "gemini":       "  Would generate: GEMINI.md",
        "opencode":     "  Would generate: AGENTS.md + .opencode/{agents,commands,plugins}/ + opencode.json",
    }
    for ed, msg in _EDITOR_DRY_RUN.items():
        if ed in eds:
            print(msg)

    if "windsurf" in eds:
        if (Path.cwd() / ".windsurf" / "hooks.json").is_file():
            print("  Would migrate: remove retired ai-toolkit Cascade hooks")
        if (
            Path.cwd()
            / ".devin"
            / "skills"
            / "ai-toolkit-skill-catalogue"
            / "SKILL.md"
        ).is_file():
            print("  Would migrate: remove undocumented .devin/skills toolkit pointer")

    # Profile-driven extras (matrix in kb/reference/global-install-model.md)
    if "copilot" in eds:
        print("  Would generate: .github/agents/ + .github/skills/")
        if add_copilot_dir:
            print("  Would generate: .github/instructions/ + .github/prompts/ + "
                  ".github/hooks/ (profile >= standard)")
    if "gemini" in eds and add_gemini_hooks:
        print("  Would generate: .gemini/settings.json hooks (profile >= standard)")
    if add_native_surfaces:
        if "cursor" in eds:
            print("  Would generate: .cursor/hooks.json + .cursor/agents/ + .cursor/skills/ (profile=full)")
        if "windsurf" in eds:
            print("  Would generate: .devin/hooks.v1.json + .windsurf/skills/ (profile=full)")
        if "cline" in eds:
            print("  Would generate: .cline/skills/ (profile=full)")
        if "augment" in eds:
            print("  Would generate: .augment/agents/ + .augment/commands/ + "
                  "$HOME/.augment/settings.json + .augment/skills/ (profile=full)")
        if "gemini" in eds:
            print("  Would generate: .gemini/commands/ + .gemini/skills/ (profile=full)")
    if "codex" in eds:
        print("  Would generate: .codex/agents/ native agents")
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

    skills_dst = prepare_codex_skills_dir(cwd)
    user_names = unmanaged_codex_skill_names(skills_dst, skills_src)

    linked = 0
    adapted = 0
    skipped = 0
    for skill_dir in sorted(skills_src.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        if skill_dir.name in user_names:
            skipped += 1
            continue

        mode = sync_codex_skill(skill_dir, skills_dst)
        if mode == "linked":
            linked += 1
        elif mode == "adapted":
            adapted += 1
        else:
            skipped += 1

    cleanup_codex_skills(skills_dst, skills_src, user_names)

    print(
        f"  Installed: {linked + adapted} skills to .agents/skills/"
        f" ({linked} linked, {adapted} adapted, {skipped} skipped)"
    )


def _install_codex_agents(cwd: Path, *, config_root: Path | None = None) -> None:
    """Generate native Codex custom-agent TOML files."""
    from generate_codex_agents import generate as gen_codex_agents

    written, removed = gen_codex_agents(cwd, config_root=config_root)
    agents_dir = (
        config_root / "agents"
        if config_root is not None
        else Path(".codex/agents")
    )
    message = f"  Created: {agents_dir}/ ({written} agents"
    if removed:
        message += f", {removed} stale removed"
    print(message + ")")


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
    # Skip the editor skill-catalogue pointer when real skills are already
    # discoverable at .claude/skills (project or ~/.claude/skills global):
    # Cursor/Cline/Augment read those natively and by default. Emit it only as
    # the editor-only fallback when no Claude skills are present. Windsurf is
    # excluded (its .claude scan is gated) and keeps its pointer unconditionally.
    emit_pointer = not _claude_skills_discoverable(cwd)

    if "copilot" in eds:
        inject_with_rules(
            "generate-copilot.sh",
            cwd / ".github" / "copilot-instructions.md",
            rules_dir,
        )
        _install_copilot_agents_md(cwd, rules_dir)
        # Agents and skills are the minimal Copilot surface. Standard and above
        # add path instructions, prompts, and native lifecycle hooks.
        from generate_copilot import generate as gen_copilot_dir
        gen_copilot_dir(
            cwd,
            language_modules=language_modules,
            rules_dir=rules_dir,
            emit_prompts=add_copilot_dir,
            emit_instructions=add_copilot_dir,
        )
        if add_copilot_dir:
            _try_generator("generate_copilot_hooks", cwd)

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
            _try_generator("generate_cursor_skills", cwd, emit_skill_pointer=emit_pointer)

    if "windsurf" in eds:
        _cleanup_retired_windsurf_surfaces(cwd)
        inject_with_rules(
            "generate-windsurf.sh",
            cwd / ".windsurfrules",
            rules_dir,
        )
        from generate_windsurf_rules import generate as gen_windsurf_rules
        gen_windsurf_rules(cwd, language_modules=language_modules,
                           rules_dir=rules_dir)
        if add_native_surfaces:
            # Cascade's .windsurf/hooks.json surface ended on 2026-07-01.
            # Devin CLI uses the Claude-compatible .devin/hooks.v1.json format.
            _try_generator("generate_devin_hooks", cwd)
            # Current Devin docs list .windsurf/skills as a supported path;
            # .devin/skills is not documented.
            _try_generator("generate_windsurf_skills", cwd)

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
        if add_native_surfaces:
            _try_generator("generate_cline_skills", cwd, emit_skill_pointer=emit_pointer)

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
            _try_generator("generate_augment_skills", cwd, emit_skill_pointer=emit_pointer)

    if "antigravity" in eds:
        from generate_antigravity import generate as gen_antigravity
        gen_antigravity(cwd, language_modules=language_modules,
                        rules_dir=rules_dir)

    if "codex" in eds:
        # AGENTS.md — marker injection; universal coding rules are inlined into
        # AGENTS.md (Codex reads instructions only from AGENTS.md, not a
        # .agents/rules/ directory). Language rules reach Codex via .agents/skills/.
        inject_with_rules(
            "generate_codex.py",
            cwd / "AGENTS.md",
            rules_dir,
        )
        # .codex/hooks.json — Codex lifecycle hooks
        from generate_codex_hooks import generate as gen_codex_hooks
        gen_codex_hooks(cwd, global_install=False)
        print("  Created: .codex/hooks.json")
        # .codex/agents/ -- native Codex custom-agent definitions
        _install_codex_agents(cwd)
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
