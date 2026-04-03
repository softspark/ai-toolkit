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

Registered rules (~/.ai-toolkit/rules/*.md) are also injected into
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

Components: agents, skills, hooks, constitution, architecture, rules,
            cursor, windsurf, gemini, augment
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir, app_dir, inject_rule
from emission import agent_count as count_agents, skill_count as count_skills

# Step modules
from install_steps.symlinks import install_agents, install_skills, clean_legacy_commands
from install_steps.hooks import install_hooks
from install_steps.markers import install_marker_files, inject_rules
from install_steps.ai_tools import install_ai_tools, install_local_project, run_script


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
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}")
            sys.exit(1)
        else:
            cfg["target_dir"] = Path(arg)
        i += 1
    return cfg


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
                 only: str, skip: str, dry_run: bool) -> None:
    print("AI Toolkit Installer")
    print("========================")
    print(f"Toolkit:   {toolkit_dir}")
    print(f"Target:    {target_dir.resolve()}")
    print(f"Rules:     {rules_dir}")
    if profile:
        print(f"Profile:   {profile}")
    if only:
        print(f"Only:      {only}")
    if skip:
        print(f"Skip:      {skip}")
    if dry_run:
        print("Mode:      DRY-RUN (no changes)")
    print()


def print_summary() -> None:
    print()
    print("Done.")
    print()
    print("Next steps:")
    print("  1. Edit ~/.claude/CLAUDE.md -- add your global rules above the toolkit sections")
    print("  2. Per project: ai-toolkit install --local (or: ai-toolkit update --local)")
    print("  3. To update: npm install -g @softspark/ai-toolkit@latest && ai-toolkit update")
    print("  4. To register rules from other tools: ai-toolkit add-rule <rule.md>")


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

    inject_rules(claude_dir, target_dir, rules_dir, only, skip, dry_run)


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
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cfg = parse_args(sys.argv[1:])

    target_dir: Path = cfg["target_dir"]
    only: str = cfg["only"]
    skip: str = cfg["skip"]
    dry_run: bool = cfg["dry_run"]
    local: bool = cfg["local"]
    reset: bool = cfg["reset"]
    profile: str = cfg["profile"]
    persona: str = cfg["persona"]

    rules_dir = Path.home() / ".ai-toolkit" / "rules"
    hooks_scripts_dir = Path.home() / ".ai-toolkit" / "hooks"

    only = resolve_profile(profile, only)
    check_dependencies()
    print_banner(target_dir, rules_dir, profile, only, skip, dry_run)

    if not dry_run:
        rules_dir.mkdir(parents=True, exist_ok=True)
        hooks_scripts_dir.mkdir(parents=True, exist_ok=True)

    install_claude_code(target_dir, hooks_scripts_dir, rules_dir, only, skip, dry_run)
    install_ai_tools(target_dir, rules_dir, only, skip, dry_run)

    if local:
        install_local_project(rules_dir, dry_run, reset)

    install_persona(target_dir, persona, dry_run)
    install_strict_git_hooks(profile, local, dry_run)
    print_summary()


if __name__ == "__main__":
    main()
