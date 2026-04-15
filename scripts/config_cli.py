#!/usr/bin/env python3
"""CLI dispatcher for ai-toolkit config subcommands.

Usage:
    ai-toolkit config validate [path]     — Validate .softspark-toolkit.json
    ai-toolkit config diff [path]         — Show project vs base differences
    ai-toolkit config init                — Interactive config setup (MVP Phase 3)
    ai-toolkit config create-base <name>  — Scaffold base config package (MVP Phase 3)
    ai-toolkit config check               — CI enforcement check (MVP Phase 4)

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure scripts/ is on the path for sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config_resolver import (
    ConfigResolverError,
    load_project_config,
    resolve_extends,
)
from config_merger import ConfigMergeError, merge_config_chain
from config_validator import (
    validate_merged_config,
    validate_project_config,
)
from config_scaffold import create_base_package, create_project_config
from config_lock import check_lock_staleness


from paths import PROJECT_CONFIG_FILENAME


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_validate(args: list[str]) -> int:
    """Validate .softspark-toolkit.json schema and extends resolution."""
    project_dir = Path(args[0]) if args else Path.cwd()

    try:
        config = load_project_config(project_dir)
    except ConfigResolverError as e:
        print(f"  ✗ {e}")
        return 1
    if config is None:
        print(f"  ✗ No {PROJECT_CONFIG_FILENAME} found in {project_dir}")
        return 2

    print(f"  Validating {project_dir / PROJECT_CONFIG_FILENAME}...")
    errors = validate_project_config(config, project_dir)

    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    # If extends, try to resolve and validate merged config
    extends = config.get("extends")
    if extends:
        print(f"  Resolving extends: {extends}...")
        try:
            result = resolve_extends(extends, project_dir)
            for w in result.warnings:
                print(f"  ⚠ {w}")

            # Merge and validate
            base_datas = [c.data for c in result.configs]
            merge_result = merge_config_chain(base_datas, config)

            # Post-merge enforcement validation
            if base_datas:
                merged_errors = validate_merged_config(
                    merge_result.merged, base_datas[-1]
                )
                if merged_errors:
                    for e in merged_errors:
                        print(f"  ✗ {e}")
                    return 1

            print(f"  ✓ extends resolved: {len(result.configs)} base config(s)")
            for c in result.configs:
                version_str = f" v{c.version}" if c.version else ""
                print(f"    - {c.name}{version_str}")

        except ConfigResolverError as e:
            print(f"  ✗ Resolution failed: {e}")
            return 1
        except ConfigMergeError as e:
            print(f"  ✗ Merge failed: {e}")
            return 1

    # Summary — these passed because validation above would have returned 1
    print(f"  ✓ schema valid")
    print(f"  ✓ no forbidden overrides")
    if extends:
        print(f"  ✓ extends resolved")

    print("\n  Config valid ✓")
    return 0


def cmd_diff(args: list[str]) -> int:
    """Show differences between project config and base config."""
    project_dir = Path(args[0]) if args else Path.cwd()

    try:
        config = load_project_config(project_dir)
    except ConfigResolverError as e:
        print(f"  ✗ {e}")
        return 1
    if config is None:
        print(f"  ✗ No {PROJECT_CONFIG_FILENAME} found in {project_dir}")
        return 2

    extends = config.get("extends")
    if not extends:
        print("  No 'extends' field — nothing to diff against.")
        return 0

    try:
        result = resolve_extends(extends, project_dir)
    except ConfigResolverError as e:
        print(f"  ✗ Cannot resolve extends: {e}")
        return 1

    if not result.configs:
        print("  No base configs resolved.")
        return 0

    base = result.configs[-1]  # most immediate parent
    base_data = base.data

    print(f"  Base: {base.name}" + (f"@{base.version}" if base.version else ""))
    print()

    # Profile
    base_profile = base_data.get("profile", "standard")
    proj_profile = config.get("profile", base_profile)
    if proj_profile != base_profile:
        print(f"  Profile:     {base_profile} (base) → {proj_profile} (project) ⚠ OVERRIDE")
    else:
        print(f"  Profile:     {proj_profile} (inherited)")

    # Agents
    _diff_agents(base_data.get("agents", {}), config.get("agents", {}), base_data)

    # Rules
    _diff_rules(base_data.get("rules", {}), config.get("rules", {}))

    # Constitution
    _diff_constitution(base_data.get("constitution", {}), config.get("constitution", {}))

    # Overrides
    _diff_overrides(config.get("overrides", {}))

    return 0


def _diff_agents(
    base: dict, project: dict, full_base: dict
) -> None:
    """Print agent diff."""
    base_enabled = set(base.get("enabled", []))
    proj_enabled = set(project.get("enabled", []))
    proj_disabled = set(project.get("disabled", []))
    required = set(full_base.get("enforce", {}).get("requiredAgents", []))

    added = proj_enabled - base_enabled
    removed = proj_disabled & base_enabled

    if added or removed or required:
        print()
        print("  Agents:")
        for a in sorted(added):
            print(f"    + {a}     (project adds)")
        for a in sorted(removed):
            print(f"    - {a}     (project disables)")
        for a in sorted(required):
            print(f"    = {a}     (base requires, cannot disable)")
        for a in sorted(base_enabled - removed - required):
            if a not in added:
                print(f"      {a}     (inherited)")


def _diff_rules(base: dict, project: dict) -> None:
    """Print rules diff."""
    base_inject = set(base.get("inject", []))
    proj_inject = set(project.get("inject", []))
    proj_remove = set(project.get("remove", []))

    added = proj_inject - base_inject
    removed = proj_remove

    if added or removed:
        print()
        print("  Rules:")
        for r in sorted(added):
            print(f"    + {r}  (project adds)")
        for r in sorted(removed):
            print(f"    - {r}  (project removes)")
        for r in sorted(base_inject - removed):
            print(f"    = {r}  (inherited)")


def _diff_constitution(base: dict, project: dict) -> None:
    """Print constitution diff."""
    base_articles = {a["article"]: a for a in base.get("amendments", [])}
    proj_articles = {a["article"]: a for a in project.get("amendments", [])}

    if base_articles or proj_articles:
        print()
        print("  Constitution:")
        print("    = Articles I-V              (immutable)")
        for num, art in sorted(base_articles.items()):
            print(f"    = Article {num}: {art['title']}  (inherited from base)")
        for num, art in sorted(proj_articles.items()):
            if num not in base_articles:
                print(f"    + Article {num}: {art['title']}  (project adds)")


def _diff_overrides(overrides: dict) -> None:
    """Print override diff."""
    if overrides:
        print()
        print("  Overrides:")
        for key, ov in overrides.items():
            action = ov.get("replacement", "custom")
            justification = ov.get("justification", "")
            print(f"    {key}: {action.upper()} (justification: \"{justification}\")")


def cmd_init(args: list[str]) -> int:
    """Interactive (or flag-driven) project config setup."""
    project_dir = Path.cwd()
    config_path = project_dir / PROJECT_CONFIG_FILENAME

    if config_path.is_file() and "--force" not in args:
        print(f"  {PROJECT_CONFIG_FILENAME} already exists. Use --force to overwrite.")
        return 1

    extends = ""
    profile = "standard"

    # Parse flags for non-interactive mode
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--extends":
            i += 1
            extends = args[i] if i < len(args) else ""
        elif arg.startswith("--extends="):
            extends = arg.split("=", 1)[1]
        elif arg == "--profile":
            i += 1
            profile = args[i] if i < len(args) else "standard"
        elif arg.startswith("--profile="):
            profile = arg.split("=", 1)[1]
        elif arg == "--no-extends":
            extends = ""
        elif arg == "--force":
            pass  # handled above
        i += 1

    # If no flags provided and stdin is a TTY, do interactive mode
    if not extends and not any(a.startswith("--") for a in args):
        if sys.stdin.isatty():
            try:
                answer = input("  Does your organization have a shared ai-toolkit config? [y/n] ").strip().lower()
                if answer in ("y", "yes"):
                    extends = input("  npm package name, git URL, or local path: ").strip()
                profile_input = input("  Which profile? [minimal/standard/strict] (default: standard) ").strip()
                if profile_input in ("minimal", "standard", "strict"):
                    profile = profile_input
            except (EOFError, KeyboardInterrupt):
                print("\n  Cancelled.")
                return 1
        else:
            # Non-interactive, no flags: create minimal config
            pass

    # Validate extends if provided
    if extends:
        print(f"  Validating extends: {extends}...")
        try:
            result = resolve_extends(extends, project_dir)
            for c in result.configs:
                version_str = f" v{c.version}" if c.version else ""
                print(f"  ✓ Resolved: {c.name}{version_str}")
        except ConfigResolverError as e:
            print(f"  ✗ Cannot resolve: {e}")
            return 1

    # Write config
    config_path = create_project_config(project_dir, extends=extends, profile=profile)
    print(f"  Created: {config_path.name}")

    # Suggest next step
    print()
    print("  Next: ai-toolkit install --local")

    return 0


def cmd_create_base(args: list[str]) -> int:
    """Scaffold a base config npm package."""
    if not args or args[0].startswith("-"):
        print("Usage: ai-toolkit config create-base <package-name> [output-dir]")
        print()
        print("Examples:")
        print("  ai-toolkit config create-base @mycompany/ai-toolkit-config")
        print("  ai-toolkit config create-base @mycompany/ai-toolkit-config ./packages")
        return 1

    name = args[0]
    output_dir = Path(args[1]) if len(args) > 1 else None

    print(f"  Scaffolding base config: {name}...")
    pkg_dir = create_base_package(name, output_dir)

    files = sorted(p.relative_to(pkg_dir) for p in pkg_dir.rglob("*") if p.is_file())
    print(f"  Created: {pkg_dir}")
    for f in files:
        print(f"    {f}")

    print()
    print("  Next steps:")
    print(f"    1. cd {pkg_dir.name}")
    print("    2. Edit ai-toolkit.config.json — add your org's rules and agents")
    print("    3. npm publish")

    return 0


def cmd_check(args: list[str]) -> int:
    """CI enforcement check — verify project adheres to base config.

    Exit codes:
      0 — project complies with base config
      1 — violations found
      2 — .softspark-toolkit.json not found
    """
    project_dir = Path(args[0]) if args and not args[0].startswith("-") else Path.cwd()
    json_output = "--json" in args

    try:
        config = load_project_config(project_dir)
    except ConfigResolverError as e:
        if json_output:
            print(json.dumps({"status": "error", "code": 1, "message": str(e)}))
        else:
            print(f"  ✗ {e}")
        return 1
    if config is None:
        if json_output:
            print(json.dumps({"status": "error", "code": 2, "message": "No .softspark-toolkit.json found"}))
        else:
            print(f"  ✗ No {PROJECT_CONFIG_FILENAME} found in {project_dir}")
        return 2

    checks: list[dict] = []
    all_pass = True

    # 1. Schema validation
    errors = validate_project_config(config, project_dir)
    checks.append({
        "name": "schema_valid",
        "label": "Schema valid",
        "pass": len(errors) == 0,
        "errors": errors,
    })
    if errors:
        all_pass = False

    # 2. Extends resolution + merge
    extends = config.get("extends")
    base_data: dict = {}
    if extends:
        try:
            result = resolve_extends(extends, project_dir)
            base_datas = [c.data for c in result.configs]
            if base_datas:
                base_data = base_datas[-1]
            merge_result = merge_config_chain(base_datas, config)

            checks.append({
                "name": "extends_resolved",
                "label": f"Extends resolved ({len(result.configs)} base config(s))",
                "pass": True,
                "errors": [],
            })

            # 3. Post-merge enforcement
            merged_errors = validate_merged_config(merge_result.merged, base_data)
            checks.append({
                "name": "enforce_constraints",
                "label": "Enforce constraints met",
                "pass": len(merged_errors) == 0,
                "errors": merged_errors,
            })
            if merged_errors:
                all_pass = False

        except ConfigResolverError as e:
            checks.append({
                "name": "extends_resolved",
                "label": "Extends resolved",
                "pass": False,
                "errors": [str(e)],
            })
            all_pass = False
        except ConfigMergeError as e:
            checks.append({
                "name": "merge_valid",
                "label": "Config merge valid",
                "pass": False,
                "errors": [str(e)],
            })
            all_pass = False

    # 4. Required agents
    enforce = base_data.get("enforce", {})
    required_agents = set(enforce.get("requiredAgents", []))
    if required_agents:
        disabled = set(config.get("agents", {}).get("disabled", []))
        blocked = required_agents & disabled
        checks.append({
            "name": "required_agents",
            "label": f"Required agents enabled ({', '.join(sorted(required_agents))})",
            "pass": len(blocked) == 0,
            "errors": [f"Cannot disable required agent: {a}" for a in sorted(blocked)],
        })
        if blocked:
            all_pass = False

    # 5. Constitution integrity
    base_amendments = {a["article"] for a in base_data.get("constitution", {}).get("amendments", [])}
    proj_amendments = {a["article"] for a in config.get("constitution", {}).get("amendments", [])}
    conflicts = base_amendments & proj_amendments
    checks.append({
        "name": "constitution_intact",
        "label": "Constitution articles intact",
        "pass": len(conflicts) == 0,
        "errors": [f"Article {a} conflicts with base" for a in sorted(conflicts)],
    })
    if conflicts:
        all_pass = False

    # 6. Lock file staleness
    lock_status = check_lock_staleness(project_dir)
    if lock_status:
        checks.append({
            "name": "lock_file",
            "label": "Lock file up-to-date",
            "pass": lock_status == "ok",
            "errors": [] if lock_status == "ok" else [lock_status],
        })
        if lock_status != "ok":
            # Lock staleness is a warning, not a failure
            pass

    # Output
    if json_output:
        print(json.dumps({
            "status": "pass" if all_pass else "fail",
            "code": 0 if all_pass else 1,
            "checks": checks,
        }, indent=2))
    else:
        for check in checks:
            symbol = "✓" if check["pass"] else "✗"
            print(f"  {symbol} {check['label']}")
            for err in check.get("errors", []):
                print(f"      {err}")

        print()
        if all_pass:
            print("  Governance check passed ✓")
        else:
            print("  Governance check FAILED ✗")

    return 0 if all_pass else 1


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

SUBCOMMANDS = {
    "validate": cmd_validate,
    "diff": cmd_diff,
    "init": cmd_init,
    "create-base": cmd_create_base,
    "check": cmd_check,
}


def main() -> None:
    """Dispatch config subcommand."""
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h", "help"):
        print("Usage: ai-toolkit config <subcommand> [args...]")
        print()
        print("Subcommands:")
        print("  validate [path]      Validate .softspark-toolkit.json schema + extends")
        print("  diff [path]          Show project vs base config differences")
        print("  init [flags]         Create .softspark-toolkit.json (--extends, --profile, --no-extends)")
        print("  create-base <name>   Scaffold base config npm package")
        print("  check [path]         CI enforcement check (exit 0=pass, 1=fail, 2=no config)")
        sys.exit(0)

    subcmd = sys.argv[1]
    args = sys.argv[2:]

    handler = SUBCOMMANDS.get(subcmd)
    if not handler:
        print(f"Unknown config subcommand: {subcmd}", file=sys.stderr)
        print(f"Valid: {', '.join(sorted(SUBCOMMANDS))}", file=sys.stderr)
        sys.exit(1)

    exit_code = handler(args)
    sys.exit(exit_code or 0)


if __name__ == "__main__":
    main()
