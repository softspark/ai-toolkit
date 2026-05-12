#!/usr/bin/env python3
"""Inject external MCP server templates into .mcp.json and all editor configs.

Allows external tools (MCP servers, plugins) to register their own MCP server
templates alongside ai-toolkit's built-in templates. Each injected template is
tagged with ``_source`` derived from the filename stem (or URL last segment)
so that re-running is idempotent and removal is safe.

Usage:
    inject_mcp_cli.py <template-file-or-url> [target-dir] [--name <name>] [--force]
    inject_mcp_cli.py <url> [template-name] [target-dir] [--force]   # URL-only legacy form
    inject_mcp_cli.py --remove <template-source-name> [target-dir]

Arguments:
    template-file-or-url  Path to a JSON file or HTTPS URL with
                          ``{"mcpServers": {...}}`` block (toolkit template format).
    target-dir            Directory containing ``.mcp.json``
                          (default: $HOME -- writes to ~/.mcp.json and propagates
                          to ~/.claude.json, ~/.cursor/mcp.json, ~/.codex/config.toml, ...).

Flags:
    --name <name>  Explicit source name. Default: filename stem or URL last segment.
                   Works for both local files and URLs. Preferred over positional
                   template-name (which only works for URL sources for backward
                   compatibility with the inject-hook positional grammar).
    --force        Overwrite servers that already exist under a different
                   ``_source`` tag. Without --force, collisions are rejected.
    --remove       Remove all server entries tagged with the given source name
                   (also unregisters URL source and removes cached template file).

The source name is derived from the filename stem (e.g.,
``rag-mcp-template.json`` becomes ``"rag-mcp-template"``). Every server in the
template is tagged with ``"_source": "<source-name>"`` inside ``.mcp.json``
(toolkit source-of-truth). Native editor configs receive the same servers
without ``_source`` (some editors reject unknown fields).

Servers tagged with ``_source: "ai-toolkit"`` are **never** modified -- those
are managed exclusively by the toolkit itself.

Propagation: every supported editor with a `global_path` in EDITOR_SPECS is
updated. Project-scoped editors are skipped (use ``ai-toolkit mcp install`` for
project scope).

Exit codes:
    0  success
    1  usage / argument error
    2  JSON parse error
    3  collision rejected (use --force)
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROTECTED_SOURCE = "ai-toolkit"


def load_json(path: str) -> dict:
    """Load and parse a JSON file."""
    with open(path) as f:
        return json.load(f)


def save_json(path: str, data: dict, indent: int = 2) -> None:
    """Write a dictionary to a JSON file with trailing newline."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write("\n")


def _is_url(source: str) -> bool:
    """Check if source looks like an HTTP(S) URL."""
    return source.startswith("https://") or source.startswith("http://")


def _name_from_url(url: str) -> str:
    """Derive a template source name from a URL's last path segment."""
    parsed = urllib.parse.urlparse(url)
    filename = parsed.path.rstrip("/").split("/")[-1]
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return re.sub(r"[^a-zA-Z0-9_-]", "", stem)


def _server_source(server: dict) -> str | None:
    """Return the ``_source`` tag of a server entry, or None if untagged."""
    if isinstance(server, dict):
        return server.get("_source")
    return None


def _strip_source_tag(server: dict) -> dict:
    """Return a copy of *server* with ``_source`` removed (for native editors)."""
    clean = copy.deepcopy(server)
    clean.pop("_source", None)
    return clean


def _tag_servers(servers: dict, source: str) -> dict:
    """Return a copy of *servers* with every entry tagged ``_source: <source>``."""
    result: dict = {}
    for name, server in servers.items():
        if not isinstance(server, dict):
            result[name] = server
            continue
        tagged = copy.deepcopy(server)
        tagged["_source"] = source
        result[name] = tagged
    return result


def _strip_servers_by_source(servers: dict, source: str) -> dict:
    """Return a copy of *servers* with entries matching ``_source`` removed."""
    return {
        name: server for name, server in servers.items()
        if _server_source(server) != source
    }


def _server_names_for_source(servers: dict, source: str) -> list[str]:
    """Return server names tagged with the given ``_source``."""
    return [name for name, server in servers.items()
            if _server_source(server) == source]


def _check_collisions(
    existing: dict, new_servers: dict, source: str, force: bool
) -> None:
    """Reject when an existing server has a different ``_source``.

    Same-source overwrite is always allowed (idempotent re-inject).
    PROTECTED_SOURCE entries are protected even with --force.
    """
    collisions = []
    for name in new_servers:
        if name not in existing:
            continue
        existing_source = _server_source(existing[name])
        if existing_source == source:
            continue
        if existing_source == PROTECTED_SOURCE:
            print(
                f"Error: server '{name}' is managed by '{PROTECTED_SOURCE}' "
                "and cannot be overwritten.",
                file=sys.stderr,
            )
            sys.exit(3)
        collisions.append((name, existing_source))

    if not collisions:
        return

    if not force:
        print(
            f"Error: server name collision(s) in .mcp.json (re-run with --force):",
            file=sys.stderr,
        )
        for name, other_source in collisions:
            src_label = other_source or "(untagged)"
            print(f"  - {name} already exists under _source={src_label}", file=sys.stderr)
        sys.exit(3)

    for name, other_source in collisions:
        src_label = other_source or "(untagged)"
        print(f"  Overwriting '{name}' (was _source={src_label})")


def _fetch_and_cache(url: str, source: str) -> str:
    """Fetch template JSON from URL, cache locally, register source.

    Returns:
        Path to the cached template JSON file.
    """
    from url_fetch import fetch_url
    from mcp_sources import register_url_source
    from paths import EXTERNAL_MCP_DIR

    EXTERNAL_MCP_DIR.mkdir(parents=True, exist_ok=True)

    try:
        data = fetch_url(url)
    except Exception as exc:
        print(f"Error fetching URL: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        print(f"Error: URL returned invalid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    if "mcpServers" not in parsed:
        print("Warning: no 'mcpServers' key found in URL response", file=sys.stderr)

    cached_path = EXTERNAL_MCP_DIR / f"{source}.json"
    cached_path.write_bytes(data)
    register_url_source(None, source, url, content=data)

    return str(cached_path)


def _propagate_to_editors(
    servers_clean: dict, source: str, target_dir: str, force: bool
) -> None:
    """Mirror servers to every editor that has a global_path in EDITOR_SPECS.

    Servers are written without the ``_source`` tag (native editor configs do
    not need it). Per-editor failures are non-fatal -- we report and continue.
    """
    from mcp_editors import EDITOR_SPECS, install_servers

    home = Path(target_dir)
    editors_with_global = [
        name for name, spec in EDITOR_SPECS.items()
        if spec.get("global_path")
    ]

    for editor in sorted(editors_with_global):
        try:
            updated = install_servers(
                [editor], servers_clean, scope="global", home=home,
            )
            for path in updated:
                print(f"  Propagated to {editor}: {path}")
        except Exception as exc:
            print(
                f"  Warning: {editor} propagation failed: {exc}",
                file=sys.stderr,
            )


def _remove_from_editors(server_names: list[str], target_dir: str) -> None:
    """Remove servers from every editor with a global_path."""
    from mcp_editors import EDITOR_SPECS, remove_servers

    home = Path(target_dir)
    editors_with_global = [
        name for name, spec in EDITOR_SPECS.items()
        if spec.get("global_path")
    ]

    for editor in sorted(editors_with_global):
        try:
            updated = remove_servers(
                [editor], server_names, scope="global", home=home,
            )
            for path in updated:
                print(f"  Cleaned {editor}: {path}")
        except Exception as exc:
            print(
                f"  Warning: {editor} cleanup failed: {exc}",
                file=sys.stderr,
            )


def inject(
    template_file: str,
    target_dir: str,
    source_override: str = "",
    force: bool = False,
) -> None:
    """Inject an MCP template into .mcp.json + propagate to all editors.

    Args:
        template_file: Path to the template JSON file, or an HTTPS URL.
        target_dir: Directory used as $HOME for editor config resolution.
            ``.mcp.json`` is written to ``<target_dir>/.mcp.json``.
        source_override: Explicit source name (overrides filename-derived).
        force: Overwrite servers tagged with a different ``_source``.
    """
    is_url = _is_url(template_file)

    if is_url:
        if template_file.startswith("http://"):
            print(
                "Error: only HTTPS URLs are supported. Use https:// for security.",
                file=sys.stderr,
            )
            sys.exit(1)

        source = source_override or _name_from_url(template_file)
        source = re.sub(r"[^a-zA-Z0-9_-]", "", source)
        if not source:
            print(
                "Error: could not derive template name from URL. "
                "Provide one explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

        if source == PROTECTED_SOURCE:
            print(
                f"Error: source name '{PROTECTED_SOURCE}' is reserved.",
                file=sys.stderr,
            )
            sys.exit(1)

        template_file = _fetch_and_cache(template_file, source)
        print(f"Fetched template from URL (source: '{source}')")
    else:
        source = source_override or Path(template_file).stem
        if source == PROTECTED_SOURCE:
            print(
                f"Error: source name '{PROTECTED_SOURCE}' is reserved. "
                "Rename your template file.",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        template_data = load_json(template_file)
    except json.JSONDecodeError as exc:
        print(f"Error: malformed JSON in {template_file}: {exc}", file=sys.stderr)
        sys.exit(2)
    except OSError as exc:
        print(f"Error reading template file: {exc}", file=sys.stderr)
        sys.exit(1)

    new_servers = template_data.get("mcpServers", {})
    if not new_servers:
        print(f"Warning: no 'mcpServers' key found in {template_file}", file=sys.stderr)
        return

    mcp_path = Path(target_dir) / ".mcp.json"
    config: dict = {"mcpServers": {}}
    if mcp_path.is_file():
        try:
            config = load_json(str(mcp_path))
        except json.JSONDecodeError as exc:
            print(f"Error: malformed JSON in {mcp_path}: {exc}", file=sys.stderr)
            sys.exit(2)

    if "mcpServers" not in config or not isinstance(config["mcpServers"], dict):
        config["mcpServers"] = {}

    _check_collisions(config["mcpServers"], new_servers, source, force)

    tagged = _tag_servers(new_servers, source)
    stripped = _strip_servers_by_source(config["mcpServers"], source)
    stripped.update(tagged)
    config["mcpServers"] = stripped

    save_json(str(mcp_path), config)
    print(f"Injected MCP template '{source}' into {mcp_path}")
    print(f"  Servers: {', '.join(sorted(new_servers.keys()))}")

    if not is_url:
        try:
            from mcp_sources import register_path_source
            register_path_source(
                None, source, Path(template_file),
                content=Path(template_file).read_bytes(),
            )
        except Exception as exc:
            print(f"Warning: could not register local source: {exc}", file=sys.stderr)

    servers_clean = {name: _strip_source_tag(s) for name, s in new_servers.items()}
    _propagate_to_editors(servers_clean, source, target_dir, force)


def remove(source_name: str, target_dir: str) -> None:
    """Remove all server entries tagged with *source_name*.

    Also unregisters the URL source if it was URL-sourced, removes cached file,
    and cleans matching server names from every global editor config.
    """
    if source_name == PROTECTED_SOURCE:
        print(
            f"Error: cannot remove '{PROTECTED_SOURCE}' entries. "
            "Use 'ai-toolkit uninstall' instead.",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp_path = Path(target_dir) / ".mcp.json"

    server_names: list[str] = []
    if mcp_path.is_file():
        try:
            config = load_json(str(mcp_path))
        except json.JSONDecodeError as exc:
            print(f"Error: malformed JSON in {mcp_path}: {exc}", file=sys.stderr)
            sys.exit(2)

        servers = config.get("mcpServers", {})
        if isinstance(servers, dict):
            server_names = _server_names_for_source(servers, source_name)
            config["mcpServers"] = _strip_servers_by_source(servers, source_name)
            save_json(str(mcp_path), config)
            if server_names:
                print(
                    f"Removed source '{source_name}' from {mcp_path} "
                    f"(servers: {', '.join(server_names)})"
                )

    if server_names:
        _remove_from_editors(server_names, target_dir)

    try:
        from mcp_sources import unregister_source
        from paths import EXTERNAL_MCP_DIR

        if unregister_source(None, source_name):
            print(f"Unregistered MCP source '{source_name}'")

        cached = EXTERNAL_MCP_DIR / f"{source_name}.json"
        if cached.is_file():
            cached.unlink()
    except ImportError:
        pass

    if not server_names:
        print(f"No entries with source '{source_name}' found.")


def _parse_args(argv: list[str]) -> dict:
    """Parse CLI arguments."""
    result: dict = {
        "remove_mode": False,
        "remove_name": "",
        "source_file": "",
        "template_name": "",
        "target_dir": str(Path.home()),
        "force": False,
    }

    i = 0
    positional = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--remove":
            result["remove_mode"] = True
            i += 1
            if i >= len(argv):
                print("--remove requires a template source name", file=sys.stderr)
                sys.exit(1)
            result["remove_name"] = argv[i]
        elif arg == "--name":
            i += 1
            if i >= len(argv):
                print("--name requires a template source name", file=sys.stderr)
                sys.exit(1)
            result["template_name"] = argv[i]
        elif arg == "--force":
            result["force"] = True
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            if positional == 0:
                if not result["remove_mode"]:
                    result["source_file"] = arg
                else:
                    result["target_dir"] = arg
            elif positional == 1:
                if _is_url(result["source_file"]):
                    if arg.startswith(("/", "~", ".")):
                        result["target_dir"] = arg
                    else:
                        result["template_name"] = arg
                else:
                    result["target_dir"] = arg
            elif positional == 2:
                result["target_dir"] = arg
            positional += 1
        i += 1

    return result


def main() -> None:
    """Inject or remove external MCP templates."""
    args = _parse_args(sys.argv[1:])

    if args["remove_mode"]:
        remove(args["remove_name"], args["target_dir"])
        return

    source_file = args["source_file"]
    if not source_file:
        print(
            "Usage: inject_mcp_cli.py <template-file-or-url> [template-name] "
            "[target-dir] [--force]",
            file=sys.stderr,
        )
        print(
            "       inject_mcp_cli.py --remove <template-source-name> [target-dir]",
            file=sys.stderr,
        )
        sys.exit(1)

    if not _is_url(source_file):
        source_path = Path(source_file)
        if not source_path.is_file():
            print(f"Template file not found: {source_path}", file=sys.stderr)
            sys.exit(1)

    inject(
        source_file,
        args["target_dir"],
        source_override=args["template_name"],
        force=args["force"],
    )


if __name__ == "__main__":
    main()
