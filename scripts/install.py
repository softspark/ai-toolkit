#!/usr/bin/env python3
"""AI Toolkit Installer.

Installs toolkit GLOBALLY -- Claude Code + all supported AI tools.
Re-running is idempotent: updates only marker-delimited sections,
never touching user content outside the markers.

Claude Code (~/.claude/):
  - Per-file symlinks: agents/*.md, skills/*/  (merges with user files)
  - Merged JSON: hooks.json (toolkit entries tagged with _source)
  - Marker injection: constitution.md, ARCHITECTURE.md (preserves user content)
  - Rules injected into ~/.claude/CLAUDE.md

Other tools (global config locations):
  - Cursor:   ~/.cursor/rules
  - Windsurf: ~/.codeium/windsurf/memories/global_rules.md
  - Gemini:   ~/.gemini/GEMINI.md

Registered rules (~/.softspark/ai-toolkit/rules/*.md) are also injected into
all of the above. Add rules with: ai-toolkit add-rule <rule.md>

Usage:
  python3 scripts/install.py [target-dir] [options]

Options:
  --only agents,hooks     Install only listed components
  --skip skills           Skip listed components
  --local                 Also inject into project-local configs
  --list, --dry-run       Dry-run: show what would be installed
  --reset                 Wipe and recreate local configs
  --profile <p>           minimal|standard|strict
  --persona <p>           backend-lead|frontend-lead|devops-eng|junior-dev
  --modules <list>        Install specific modules (comma-separated)
  --auto-detect           Detect project languages and install matching rules
  --status                Show installed modules and exit
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir, app_dir, inject_rule
from emission import agent_count as count_agents, skill_count as count_skills

# Step modules
from install_steps.symlinks import install_agents, install_skills, clean_legacy_commands
from install_steps.hooks import install_hooks
from install_steps.markers import install_marker_files, inject_rules, refresh_url_hooks
from install_steps.ai_tools import install_ai_tools, install_local_project, run_script
from install_steps.install_state import (
    load_state,
    record_install,
    get_installed_modules,
    get_installed_profile,
    get_global_editors,
    record_global_editors,
    print_status,
    GLOBAL_CAPABLE_EDITORS,
)
from install_steps.detect_language import detect_languages
from install_steps.project_registry import register_project

# Config inheritance (extends system)
from config_resolver import (
    ConfigResolverError,
    load_project_config,
    resolve_extends,
)
from config_merger import ConfigMergeError, merge_config_chain
from config_validator import validate_project_config
from config_lock import save_lock_file


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def _load_manifest() -> dict:
    """Load manifest.json from toolkit root."""
    manifest_path = toolkit_dir / "manifest.json"
    if not manifest_path.is_file():
        return {}
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def _get_manifest_profiles() -> dict[str, list[str]]:
    """Return profiles from manifest.json."""
    manifest = _load_manifest()
    return manifest.get("profiles", {})


def _get_manifest_modules() -> dict[str, dict]:
    """Return modules from manifest.json."""
    manifest = _load_manifest()
    return manifest.get("modules", {})


def resolve_modules_from_profile(profile: str) -> list[str]:
    """Resolve a profile name to a list of module names.

    Returns an empty list if the profile is not found in manifest.
    """
    profiles = _get_manifest_profiles()
    return profiles.get(profile, [])


def resolve_requested_modules(
    modules_arg: str,
    profile: str,
    auto_detect: bool,
    project_dir: Path,
) -> list[str] | None:
    """Determine which modules to install based on CLI flags.

    Only activates when ``--modules`` or ``--auto-detect`` is passed.
    A bare ``--profile`` without those flags returns None so the
    legacy code path handles it unchanged.

    Returns:
        A sorted list of module names to install, or None if no
        module-level flags were provided (legacy mode).
    """
    # If neither --modules nor --auto-detect was given, stay in legacy mode.
    # This ensures --profile alone behaves exactly as before.
    if not modules_arg and not auto_detect:
        return None

    manifest_modules = _get_manifest_modules()
    result: set[str] = set()

    # Always include required modules
    for name, cfg in manifest_modules.items():
        if cfg.get("required"):
            result.add(name)

    # --modules flag takes precedence
    if modules_arg:
        for name in modules_arg.split(","):
            name = name.strip()
            if name and name in manifest_modules:
                result.add(name)
            elif name:
                print(f"Warning: unknown module '{name}' (skipped)")
        if auto_detect:
            detected = detect_languages(project_dir, toolkit_dir)
            result.update(detected)
        return sorted(result)

    # --auto-detect (without --modules): add profile or defaults + detected
    if auto_detect:
        if profile:
            profile_modules = resolve_modules_from_profile(profile)
            if profile_modules:
                result.update(profile_modules)
        else:
            for name, cfg in manifest_modules.items():
                if cfg.get("default"):
                    result.add(name)
        detected = detect_languages(project_dir, toolkit_dir)
        result.update(detected)
        return sorted(result)

    # Should not reach here, but return None for safety
    return None


def modules_to_component_filter(modules: list[str]) -> str:
    """Convert module names to a comma-separated component filter string.

    Maps module names back to the component names used by the existing
    ``--only`` system (e.g. "agents", "skills", "hooks", "rules").
    This bridges the new module system with the old component system.
    """
    components: set[str] = set()

    for module in modules:
        if module == "core":
            # Core maps to hooks, constitution, architecture, output-styles
            components.update(["hooks", "constitution", "architecture", "rules"])
        elif module == "agents":
            components.add("agents")
        elif module == "skills":
            components.add("skills")
        elif module.startswith("rules-"):
            components.add("rules")
        elif module == "mcp-templates":
            # MCP templates don't map to a legacy component
            pass

    return ",".join(sorted(components))


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> dict:
    """Parse CLI arguments into a config dict."""
    cfg: dict = {
        "target_dir": Path.home(),
        "only": "",
        "skip": "",
        "dry_run": False,
        "local": False,
        "reset": False,
        "profile": "",
        "persona": "",
        "modules": "",
        "auto_detect": False,
        "status": False,
        "lang": "",
        "editors": "",
        "config": "",
        "refresh_base": False,
        "skip_register": False,
    }
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--list", "--dry-run"):
            cfg["dry_run"] = True
        elif arg == "--local":
            cfg["local"] = True
        elif arg == "--reset":
            cfg["reset"] = True
        elif arg == "--auto-detect":
            cfg["auto_detect"] = True
        elif arg == "--status":
            cfg["status"] = True
        elif arg.startswith("--only="):
            cfg["only"] = arg.split("=", 1)[1]
        elif arg == "--only":
            i += 1
            cfg["only"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--skip="):
            cfg["skip"] = arg.split("=", 1)[1]
        elif arg == "--skip":
            i += 1
            cfg["skip"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--profile="):
            cfg["profile"] = arg.split("=", 1)[1]
        elif arg == "--profile":
            i += 1
            cfg["profile"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--persona="):
            cfg["persona"] = arg.split("=", 1)[1]
        elif arg == "--persona":
            i += 1
            cfg["persona"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--modules="):
            cfg["modules"] = arg.split("=", 1)[1]
        elif arg == "--modules":
            i += 1
            cfg["modules"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--lang="):
            cfg["lang"] = arg.split("=", 1)[1]
        elif arg == "--lang":
            i += 1
            cfg["lang"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--editors="):
            cfg["editors"] = arg.split("=", 1)[1]
        elif arg == "--editors":
            i += 1
            cfg["editors"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--config="):
            cfg["config"] = arg.split("=", 1)[1]
        elif arg == "--config":
            i += 1
            cfg["config"] = argv[i] if i < len(argv) else ""
        elif arg == "--refresh-base":
            cfg["refresh_base"] = True
        elif arg == "--skip-register":
            cfg["skip_register"] = True
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}")
            sys.exit(1)
        else:
            cfg["target_dir"] = Path(arg)
        i += 1
    return cfg


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

VALID_COMPONENTS = {"agents", "skills", "hooks", "rules", "constitution", "architecture"}
VALID_LANGS = {"python", "typescript", "golang", "go", "rust", "java", "kotlin",
               "swift", "ruby", "php", "dart", "cpp", "csharp", "c++", "c#", "cs",
               "common"}


def validate_args(cfg: dict) -> None:
    """Validate parsed arguments — exit non-zero on invalid values."""
    from install_steps.ai_tools import ALL_EDITORS

    errors: list[str] = []

    # Validate --only components
    if cfg["only"]:
        for c in cfg["only"].split(","):
            c = c.strip()
            if c and c not in VALID_COMPONENTS:
                errors.append(f"Unknown component in --only: '{c}' (valid: {', '.join(sorted(VALID_COMPONENTS))})")

    # Validate --skip components
    if cfg["skip"]:
        for c in cfg["skip"].split(","):
            c = c.strip()
            if c and c not in VALID_COMPONENTS:
                errors.append(f"Unknown component in --skip: '{c}' (valid: {', '.join(sorted(VALID_COMPONENTS))})")

    # Validate --editors
    if cfg["editors"] and cfg["editors"] != "all":
        for e in cfg["editors"].split(","):
            e = e.strip()
            if e and e not in ALL_EDITORS:
                errors.append(f"Unknown editor: '{e}' (valid: {', '.join(ALL_EDITORS)}, all)")

    # Validate --lang
    if cfg["lang"]:
        for l in cfg["lang"].split(","):
            l = l.strip()
            if l and l.lower() not in VALID_LANGS:
                errors.append(f"Unknown language: '{l}' (valid: {', '.join(sorted(VALID_LANGS - {'c++', 'c#', 'cs', 'go', 'common'}))})")

    if errors:
        for e in errors:
            print(f"Error: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------

def check_dependencies() -> None:
    """Run check_deps and abort if any required dep is missing."""
    from check_deps import check_deps

    results = check_deps(verbose=False)
    if not results["all_ok"]:
        from check_deps import print_report
        print_report(results)
        print("Aborting install: missing required dependencies.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Profile / Banner / Summary
# ---------------------------------------------------------------------------

def resolve_profile(profile: str, only: str) -> str:
    if profile == "minimal":
        if not only:
            return "agents,skills"
    elif profile in ("standard", ""):
        pass
    elif profile == "strict":
        pass
    else:
        print(f"Unknown profile: {profile} (valid: minimal, standard, strict)")
        sys.exit(1)
    return only


def print_banner(target_dir: Path, rules_dir: Path, profile: str,
                 only: str, skip: str, dry_run: bool,
                 modules: list[str] | None = None) -> None:
    print("AI Toolkit Installer")
    print("========================")
    print(f"Toolkit:   {toolkit_dir}")
    print(f"Target:    {target_dir.resolve()}")
    print(f"Rules:     {rules_dir}")
    if profile:
        print(f"Profile:   {profile}")
    if modules is not None:
        print(f"Modules:   {', '.join(modules)}")
    if only:
        print(f"Only:      {only}")
    if skip:
        print(f"Skip:      {skip}")
    if dry_run:
        print("Mode:      DRY-RUN (no changes)")
    print()


def print_summary(local: bool = False) -> None:
    print()
    print("Done.")
    if local:
        print()
        print("Next steps:")
        print("  1. Edit CLAUDE.md -- add your project-specific rules")
        print("  2. Add more editors: ai-toolkit install --local --editors cursor,aider")
        print("  3. Update project configs: ai-toolkit update --local")
    else:
        print()
        print("Next steps:")
        print("  1. Edit ~/.claude/CLAUDE.md -- add your global rules above the toolkit sections")
        print("  2. Per project: ai-toolkit install --local --editors all")
        print("  3. To update: npm install -g @softspark/ai-toolkit@latest && ai-toolkit update")
        print("  4. To register rules from other tools: ai-toolkit add-rule <rule.md>")
        print("  5. Check install state: ai-toolkit status")


# ---------------------------------------------------------------------------
# Install Claude Code (orchestrator)
# ---------------------------------------------------------------------------

def install_claude_code(target_dir: Path, hooks_scripts_dir: Path,
                        rules_dir: Path, only: str, skip: str,
                        dry_run: bool) -> None:
    print("## Claude Code (~/.claude/)")
    print()

    claude_dir = target_dir / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    install_agents(claude_dir, only, skip, dry_run)
    install_skills(claude_dir, only, skip, dry_run)
    clean_legacy_commands(claude_dir, dry_run)
    install_hooks(claude_dir, hooks_scripts_dir, only, skip, dry_run)
    install_marker_files(claude_dir, only, skip, dry_run)

    if not dry_run:
        print("  Note: settings.local.json is project-specific -- use 'ai-toolkit install --local' per project")

    print()
    print(f"  Available: {count_agents()} agents, {count_skills()} skills")

    inject_rules(claude_dir, target_dir, rules_dir, only, skip, dry_run,
                 refresh_urls=True)

    if not dry_run:
        refresh_url_hooks(str(target_dir))

    _sync_mcp_templates(dry_run)


def _sync_mcp_templates(dry_run: bool) -> None:
    """Re-install tracked MCP templates into Claude global config."""
    from install_steps.install_state import get_mcp_templates

    templates = get_mcp_templates()
    if not templates:
        return

    if dry_run:
        print(f"  Would sync MCP templates: {', '.join(templates)}")
        return

    from mcp_editors import install_servers

    servers: dict = {}
    for name in templates:
        try:
            tpl_path = app_dir / "mcp-templates" / f"{name}.json"
            if tpl_path.is_file():
                import json as _json
                data = _json.loads(tpl_path.read_text(encoding="utf-8"))
                servers.update(data.get("mcpServers", {}))
        except Exception:
            pass  # Skip broken templates silently

    if servers:
        install_servers(["claude"], servers, scope="global")
        print(f"  MCP synced: {', '.join(templates)}")


VALID_PERSONAS = ("backend-lead", "frontend-lead", "devops-eng", "junior-dev")


def install_persona(target_dir: Path, persona: str, dry_run: bool) -> None:
    """Inject a persona rule into CLAUDE.md."""
    if not persona:
        return
    if persona not in VALID_PERSONAS:
        print(f"Unknown persona: {persona} (valid: {', '.join(VALID_PERSONAS)})")
        sys.exit(1)
    persona_file = app_dir / "personas" / f"{persona}.md"
    if not persona_file.is_file():
        print(f"  Persona file not found: {persona_file}")
        return
    if dry_run:
        print(f"  Would inject persona: {persona}")
        return
    inject_rule(persona_file, target_dir)
    print(f"  Persona applied: {persona}")


def install_strict_git_hooks(profile: str, local: bool, dry_run: bool) -> None:
    if profile == "strict" and not local and not dry_run:
        cwd = Path.cwd()
        if (cwd / ".git").is_dir():
            run_script("install-git-hooks.sh", str(cwd))
            print(f"  Strict profile: git hooks installed in {cwd}")


# ---------------------------------------------------------------------------
# Version helper
# ---------------------------------------------------------------------------

def resolve_extends_config(
    project_dir: Path,
    config_path: str = "",
    refresh: bool = False,
) -> dict | None:
    """Resolve .softspark-toolkit.json extends and return merged config.

    Returns None if no .softspark-toolkit.json or no extends field.
    Prints warnings/errors and exits on fatal errors.
    """
    if config_path:
        config_file = Path(config_path)
        if not config_file.is_file():
            print(f"  Error: config file not found: {config_path}")
            sys.exit(1)
        import json as _json
        with open(config_file, encoding="utf-8") as f:
            project_config = _json.load(f)
        config_root = config_file.parent
    else:
        project_config = load_project_config(project_dir)
        config_root = project_dir

    if project_config is None:
        return None

    # Validate project config schema
    errors = validate_project_config(project_config, config_root)
    if errors:
        print("  Config validation errors:")
        for e in errors:
            print(f"    ✗ {e}")
        sys.exit(1)

    extends = project_config.get("extends")
    if not extends:
        # Config without extends — just use its settings directly
        return project_config

    print(f"  Resolving extends: {extends}...")

    try:
        result = resolve_extends(extends, config_root, refresh=refresh)
    except ConfigResolverError as e:
        print(f"  ✗ Resolution failed: {e}")
        sys.exit(1)

    for w in result.warnings:
        print(f"  ⚠ {w}")

    # Merge
    try:
        base_datas = [c.data for c in result.configs]
        merge_result = merge_config_chain(base_datas, project_config)
    except ConfigMergeError as e:
        print(f"  ✗ Merge failed: {e}")
        sys.exit(1)

    for c in result.configs:
        version_str = f" v{c.version}" if c.version else ""
        print(f"  ✓ Resolved: {c.name}{version_str}")

    # Attach resolution metadata for state.json recording
    config_metas = [
        {
            "source": c.source,
            "name": c.name,
            "version": c.version,
            "integrity": c.integrity,
            "root": str(c.root),
        }
        for c in result.configs
    ]
    merge_result.merged["_extends_meta"] = {
        "source": extends,
        "configs": config_metas,
        "overrides_applied": merge_result.overrides_applied,
    }

    # Generate lock file
    lock_path = save_lock_file(
        config_root,
        config_metas,
        ai_toolkit_version=_get_toolkit_version(),
    )
    print(f"  Saved: {lock_path.name}")

    return merge_result.merged


def _apply_merged_config(
    merged: dict,
    cfg: dict,
) -> dict:
    """Apply merged config settings back into the install cfg dict.

    Overrides profile and modules based on merged config.
    Returns the modified cfg.
    """
    # Profile from merged config
    merged_profile = merged.get("profile")
    if merged_profile and not cfg["profile"]:
        cfg["profile"] = merged_profile

    # Agents: filter based on merged enabled/disabled lists
    # (stored for use by install_local_project)
    cfg["_merged_config"] = merged

    return cfg


def _get_toolkit_version() -> str:
    """Read version from package.json."""
    pkg = toolkit_dir / "package.json"
    if pkg.is_file():
        with open(pkg, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("version", "unknown")
    return "unknown"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = parse_args(sys.argv[1:])
    validate_args(cfg)

    # Handle --status early exit
    if cfg["status"]:
        print_status()
        sys.exit(0)

    # Auto-migrate from legacy ~/.ai-toolkit if needed
    from migrate import run_full_migration
    run_full_migration(dry_run=cfg.get("dry_run", False))

    target_dir: Path = cfg["target_dir"]
    only: str = cfg["only"]
    skip: str = cfg["skip"]
    dry_run: bool = cfg["dry_run"]
    local: bool = cfg["local"]
    reset: bool = cfg["reset"]
    profile: str = cfg["profile"]
    persona: str = cfg["persona"]
    modules_arg: str = cfg["modules"]
    auto_detect: bool = cfg["auto_detect"]
    lang_arg: str = cfg["lang"]

    # --lang <list> → merge into --modules as rules-<lang> entries
    _LANG_ALIASES = {"go": "golang", "c++": "cpp", "c#": "csharp", "cs": "csharp"}
    if lang_arg:
        langs = [_LANG_ALIASES.get(l.strip(), l.strip()) for l in lang_arg.split(",") if l.strip()]
        lang_modules = ",".join(f"rules-{l}" for l in langs)
        modules_arg = f"{modules_arg},{lang_modules}" if modules_arg else lang_modules
        auto_detect = False  # explicit --lang overrides auto-detect
        if not local:
            local = True  # language rules are project-local

    from paths import RULES_DIR, HOOKS_DIR, TOOLKIT_DATA_DIR
    rules_dir = RULES_DIR
    hooks_scripts_dir = HOOKS_DIR

    # --local always implies --auto-detect (why install locally without language rules?)
    if local and not auto_detect and not modules_arg:
        auto_detect = True

    # --auto-detect only makes sense with --local (language rules are project-specific)
    if auto_detect and not local:
        print("Warning: --auto-detect requires --local (language rules are project-specific). Adding --local.")
        local = True

    project_dir = Path.cwd() if local else target_dir
    resolved_modules = resolve_requested_modules(
        modules_arg, profile, auto_detect, project_dir,
    )

    # If module-level flags produced a module list, bridge to legacy --only
    if resolved_modules is not None:
        component_filter = modules_to_component_filter(resolved_modules)
        if component_filter and not only:
            only = component_filter

    # Legacy profile resolution (only when no module-level override)
    if resolved_modules is None:
        only = resolve_profile(profile, only)

    check_dependencies()

    if not dry_run:
        rules_dir.mkdir(parents=True, exist_ok=True)
        hooks_scripts_dir.mkdir(parents=True, exist_ok=True)

    if local:
        # --local: project-local only, no global install
        # Check for .softspark-toolkit.json extends system
        config_path_arg: str = cfg["config"]
        refresh_base: bool = cfg["refresh_base"]
        merged_config = resolve_extends_config(
            project_dir, config_path=config_path_arg, refresh=refresh_base,
        )
        if merged_config:
            cfg = _apply_merged_config(merged_config, cfg)
            profile = cfg["profile"]

        lang_modules = [m for m in (resolved_modules or []) if m.startswith("rules-")]
        local_editors_arg: str = cfg["editors"]
        install_local_project(rules_dir, dry_run, reset, lang_modules or None,
                              editors=local_editors_arg,
                              merged_config=merged_config)
        installed_eds: list[str] = []  # local install doesn't track global editors
        install_strict_git_hooks(profile, local, dry_run)
    else:
        # Global install
        print_banner(target_dir, rules_dir, profile, only, skip, dry_run,
                     modules=resolved_modules)
        install_claude_code(target_dir, hooks_scripts_dir, rules_dir, only, skip, dry_run)

        # Determine global editors: --editors flag > state > default (none)
        editors_arg: str = cfg["editors"]
        if editors_arg:
            if editors_arg == "all":
                global_eds = list(GLOBAL_CAPABLE_EDITORS)
            else:
                global_eds = [e.strip() for e in editors_arg.split(",") if e.strip()]
        else:
            # On update: use editors from state; on fresh install: none
            global_eds = get_global_editors() or None

        installed_eds = install_ai_tools(target_dir, rules_dir, dry_run,
                                         editors=global_eds)
        install_persona(target_dir, persona, dry_run)
        install_strict_git_hooks(profile, local, dry_run)

    # Record install state (skip for dry-run)
    if not dry_run:
        auto_detected = None
        if auto_detect:
            auto_detected = detect_languages(project_dir, toolkit_dir)

        # Determine what modules to record
        if resolved_modules is not None:
            record_modules = resolved_modules
        else:
            # Legacy mode: infer modules from profile/only
            record_modules = _infer_modules_from_legacy(profile, only)

        # Extract extends metadata if available
        extends_info = None
        merged = cfg.get("_merged_config")
        if merged and merged.get("_extends_meta"):
            extends_info = merged["_extends_meta"]

        record_install(
            version=_get_toolkit_version(),
            modules=record_modules,
            profile=profile or "standard",
            auto_detected=auto_detected,
            extends_info=extends_info,
        )

        # Record global editors (only for global install, not --local)
        if not local and installed_eds:
            record_global_editors(installed_eds)

        # Register project in global registry (for `ai-toolkit update` propagation)
        # Skipped when called from update_projects.py (--skip-register) to avoid
        # concurrent writes to projects.json during parallel updates.
        if local and not cfg.get("skip_register"):
            extends_source = ""
            if extends_info:
                extends_source = extends_info.get("source", "")
            # Determine editors to record for this project
            local_eds_for_registry: list[str] | None = None
            if local and local_editors_arg:
                if local_editors_arg == "all":
                    from install_steps.ai_tools import ALL_EDITORS
                    local_eds_for_registry = list(ALL_EDITORS)
                else:
                    local_eds_for_registry = [e.strip() for e in local_editors_arg.split(",") if e.strip()]

            is_new = register_project(
                project_dir,
                profile=profile or "standard",
                extends=extends_source,
                editors=local_eds_for_registry,
            )
            if is_new:
                print(f"  Registered project in {TOOLKIT_DATA_DIR / 'projects.json'}")

    print_summary(local=local)


def _infer_modules_from_legacy(profile: str, only: str) -> list[str]:
    """Best-effort inference of module names from legacy flags.

    Used when the user did not pass --modules or a manifest-aware
    --profile, so we approximate from what was actually installed.
    """
    modules: set[str] = {"core"}  # core is always installed

    if only:
        components = {c.strip() for c in only.split(",")}
    else:
        # Standard install: all main components
        components = {"agents", "skills", "hooks", "constitution",
                      "architecture", "rules"}

    if "agents" in components:
        modules.add("agents")
    if "skills" in components:
        modules.add("skills")
    if "rules" in components:
        modules.add("rules-common")

    return sorted(modules)


if __name__ == "__main__":
    main()
