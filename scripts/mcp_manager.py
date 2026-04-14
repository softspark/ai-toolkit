#!/usr/bin/env python3
"""MCP template manager -- add, remove, inspect, and install MCP configs.

Usage:
  mcp_manager.py list                           List available templates
  mcp_manager.py editors                        List native editor MCP adapters
  mcp_manager.py show <name>                    Show template details
  mcp_manager.py add <name> [names..] [--target <path>]  Add to .mcp.json
  mcp_manager.py install --editor <name[,..]> [--scope project|global] [--target <path>] [name..]
  mcp_manager.py remove <name>                  Remove from .mcp.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp_editors import (
    editor_rows,
    install_servers,
    load_project_mcp_servers,
    remove_servers,
    supported_editors,
)

TOOLKIT_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = TOOLKIT_DIR / "app" / "mcp-templates"
MCP_CONFIG_NAME = ".mcp.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_template(name: str) -> dict:
    """Load a template JSON by name. Exits on error."""
    template_path = TEMPLATES_DIR / f"{name}.json"
    if not template_path.is_file():
        print(f"Error: template '{name}' not found at {template_path}", file=sys.stderr)
        print(f"Run 'ai-toolkit mcp list' to see available templates.", file=sys.stderr)
        sys.exit(1)
    with open(template_path, encoding="utf-8") as f:
        return json.load(f)


def available_templates() -> list[dict]:
    """Return sorted list of all template metadata."""
    templates = []
    for p in sorted(TEMPLATES_DIR.glob("*.json")):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        templates.append({
            "name": data.get("name", p.stem),
            "description": data.get("description", ""),
            "file": p.name,
        })
    return templates


def load_mcp_config(target_dir: Path) -> dict:
    """Load existing .mcp.json or return empty structure."""
    config_path = target_dir / MCP_CONFIG_NAME
    if config_path.is_file():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {"mcpServers": {}}


def write_mcp_config(target_dir: Path, config: dict) -> None:
    """Write .mcp.json with pretty formatting."""
    config_path = target_dir / MCP_CONFIG_NAME
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    print(f"Updated: {config_path}")


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list() -> None:
    """List all available MCP templates."""
    templates = available_templates()
    if not templates:
        print("No templates found.")
        return

    print(f"{'Name':<25} Description")
    print("-" * 70)
    for t in templates:
        print(f"{t['name']:<25} {t['description']}")
    print()
    print(f"{len(templates)} templates available")
    print(f"Add with: ai-toolkit mcp add <name>")


def cmd_editors() -> None:
    """List editors with native MCP config adapters."""
    rows = editor_rows()
    print(f"{'Editor':<12} {'Scope':<18} {'Project Path':<28} {'Global Path'}")
    print("-" * 110)
    for row in rows:
        print(
            f"{row['name']:<12} {row['scope']:<18} "
            f"{row['project_path']:<28} {row['global_path']}"
        )
    print()
    print(f"{len(rows)} editors supported")


def cmd_show(name: str) -> None:
    """Show details of a specific template."""
    data = load_template(name)
    print(f"Name:        {data.get('name', name)}")
    print(f"Description: {data.get('description', '')}")
    print()
    print("mcpServers config:")
    print(json.dumps(data.get("mcpServers", {}), indent=2))

    # Show required env vars
    env_vars = []
    for server in data.get("mcpServers", {}).values():
        for key, val in server.get("env", {}).items():
            env_vars.append((key, val))

    if env_vars:
        print()
        print("Required environment variables:")
        for key, val in env_vars:
            print(f"  {key} = {val}")

    post_install = data.get("postInstall")
    if post_install:
        print()
        print(f"Setup: {post_install}")


def cmd_add(names: list[str], target_dir: Path) -> None:
    """Add one or more MCP templates to .mcp.json."""
    if not names:
        print("Error: provide at least one template name.", file=sys.stderr)
        print("Usage: ai-toolkit mcp add <name> [names..]", file=sys.stderr)
        sys.exit(1)

    config = load_mcp_config(target_dir)
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    added = []
    for name in names:
        data = load_template(name)
        servers = data.get("mcpServers", {})
        for key, value in servers.items():
            if key in config["mcpServers"]:
                print(f"  Overwriting existing server: {key}")
            config["mcpServers"][key] = value
            added.append(key)

    write_mcp_config(target_dir, config)
    print(f"Added: {', '.join(added)}")

    # Show postInstall hints from added templates
    for name in names:
        data = load_template(name)
        post_install = data.get("postInstall")
        if post_install:
            print(f"\n  Note ({name}): {post_install}")


def cmd_install(
    names: list[str],
    editors: list[str],
    *,
    target_dir: Path | None,
    scope: str | None,
) -> None:
    """Install MCP templates into native editor config files."""
    if not editors:
        print("Error: install requires --editor <name[,..]>", file=sys.stderr)
        print(
            f"Supported editors: {', '.join(supported_editors())}",
            file=sys.stderr,
        )
        sys.exit(1)

    eff_scope = scope or ("project" if target_dir is not None or not names else "global")
    if eff_scope == "project":
        project_dir = target_dir or Path.cwd()
        if names:
            cmd_add(names, project_dir)
            servers = {}
            for name in names:
                servers.update(load_template(name).get("mcpServers", {}))
        else:
            servers = load_project_mcp_servers(project_dir)
        updated = install_servers(
            editors,
            servers,
            scope="project",
            project_dir=project_dir,
        )
    else:
        if not names:
            print(
                "Error: global install requires at least one template name.",
                file=sys.stderr,
            )
            sys.exit(1)
        servers = {}
        for name in names:
            servers.update(load_template(name).get("mcpServers", {}))
        updated = install_servers(editors, servers, scope="global")

    for path in updated:
        print(f"Updated: {path}")

    # Track globally installed templates in state.json
    if eff_scope == "global" and names:
        from install_steps.install_state import record_mcp_template
        for name in names:
            record_mcp_template(name)

    # Show postInstall hints from installed templates
    if names:
        for name in names:
            data = load_template(name)
            post_install = data.get("postInstall")
            if post_install:
                print(f"\n  Note ({name}): {post_install}")


def cmd_remove(name: str, target_dir: Path | None, *, editors: list[str], scope: str | None) -> None:
    """Remove an MCP server from .mcp.json."""
    if editors:
        eff_scope = scope or ("project" if target_dir else "global")
        if eff_scope == "project":
            project_dir = target_dir or Path.cwd()
            config_path = project_dir / MCP_CONFIG_NAME
            if config_path.is_file():
                config = load_mcp_config(project_dir)
                config.get("mcpServers", {}).pop(name, None)
                write_mcp_config(project_dir, config)
            updated = remove_servers(
                editors,
                [name],
                scope="project",
                project_dir=project_dir,
            )
        else:
            updated = remove_servers(editors, [name], scope="global")
            # Untrack globally removed template from state.json
            from install_steps.install_state import remove_mcp_template
            remove_mcp_template(name)
        for path in updated:
            print(f"Updated: {path}")
        print(f"Removed: {name}")
        return

    config_path = (target_dir or Path.cwd()) / MCP_CONFIG_NAME
    if not config_path.is_file():
        print(f"Error: {config_path} not found.", file=sys.stderr)
        sys.exit(1)

    config = load_mcp_config(target_dir or Path.cwd())
    servers = config.get("mcpServers", {})

    if name not in servers:
        print(f"Error: server '{name}' not found in {config_path}.", file=sys.stderr)
        print(f"Available servers: {', '.join(servers.keys()) or '(none)'}", file=sys.stderr)
        sys.exit(1)

    del servers[name]
    write_mcp_config(target_dir or Path.cwd(), config)
    print(f"Removed: {name}")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_options(args: list[str]) -> tuple[list[str], Path | None, list[str], str | None]:
    """Extract common MCP CLI options."""
    target_dir: Path | None = None
    editors: list[str] = []
    scope: str | None = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == "--target" and i + 1 < len(args):
            target_dir = Path(args[i + 1]).resolve()
            i += 2
        elif args[i] == "--editor" and i + 1 < len(args):
            editors = [e.strip() for e in args[i + 1].split(",") if e.strip()]
            i += 2
        elif args[i] == "--scope" and i + 1 < len(args):
            scope = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return remaining, target_dir, editors, scope


def main() -> None:
    """Entry point for MCP template manager."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    subcmd = sys.argv[1]
    rest = sys.argv[2:]

    if subcmd == "list":
        cmd_list()
    elif subcmd == "editors":
        cmd_editors()
    elif subcmd == "show":
        if not rest:
            print("Usage: ai-toolkit mcp show <name>", file=sys.stderr)
            sys.exit(1)
        cmd_show(rest[0])
    elif subcmd == "add":
        names, target_dir, _editors, _scope = parse_options(rest)
        cmd_add(names, target_dir or Path.cwd())
    elif subcmd == "install":
        names, target_dir, editors, scope = parse_options(rest)
        cmd_install(names, editors, target_dir=target_dir, scope=scope)
    elif subcmd == "remove":
        names, target_dir, editors, scope = parse_options(rest)
        if not names:
            print("Usage: ai-toolkit mcp remove <name>", file=sys.stderr)
            sys.exit(1)
        cmd_remove(
            names[0],
            target_dir if editors else (target_dir or Path.cwd()),
            editors=editors,
            scope=scope,
        )
    else:
        print(f"Unknown subcommand: {subcmd}", file=sys.stderr)
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
