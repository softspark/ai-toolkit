# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Marker file injection and rule installation."""
from __future__ import annotations

import re
from pathlib import Path

from _common import (
    app_dir,
    inject_section,
    remove_rule_section,
    should_install,
    _collapse_blank_runs,
    _strip_section,
    _trim_trailing_blanks,
)
from frontmatter import split_frontmatter
from install_steps.ai_tools import (
    CONSTITUTION_RULE,
    common_rule_sources,
    render_common_rule,
)


GLOBAL_RULES_SECTION = "global-rules"


def install_marker_files(claude_dir: Path, only: str, skip: str,
                         dry_run: bool) -> None:
    """Inject ARCHITECTURE.md via markers.

    The constitution is a user-level rule now (``inject_rules``); nothing
    imported ``~/.claude/constitution.md``, so it never loaded from there.
    """
    if not dry_run:
        _retire_global_constitution_file(claude_dir)
    marker_files = [
        ("ARCHITECTURE.md", "architecture", "architecture"),
    ]
    for filename, component, section in marker_files:
        if not should_install(component, only, skip):
            print(f"  Skipped: .claude/{filename}")
            continue
        src = app_dir / filename
        if not src.is_file():
            continue
        if dry_run:
            print(f"  Would inject: .claude/{filename} (marker-based, preserves user content)")
            continue
        dst = claude_dir / filename
        if dst.is_symlink():
            dst.unlink()
            print(f"  Upgraded: .claude/{filename} (symlink -> marker injection)")
        inject_section(src, dst, section)
        print(f"  Injected: .claude/{filename}")


def _retire_global_constitution_file(claude_dir: Path) -> None:
    """Strip the toolkit section from the old ``~/.claude/constitution.md``."""
    legacy = claude_dir / "constitution.md"
    if legacy.is_symlink():
        legacy.unlink()
        print("  Removed: .claude/constitution.md (legacy symlink)")
        return
    if not legacy.is_file():
        return
    original = legacy.read_text(encoding="utf-8")
    stripped = _strip_section(original, "constitution")
    if stripped == original:
        return
    if stripped.strip():
        legacy.write_text(stripped, encoding="utf-8")
        print("  Stripped: .claude/constitution.md (user content preserved)")
    else:
        legacy.unlink()
        print("  Removed: .claude/constitution.md (now rules/ai-toolkit-constitution.md)")


def inject_rules(claude_dir: Path, target_dir: Path, rules_dir: Path,
                 only: str, skip: str, dry_run: bool,
                 refresh_urls: bool = False,
                 profile: str = "standard") -> None:
    """Install Claude Code user-level rules.

    Besides the standalone toolkit rules and registered rules, the common
    rules (``app/rules/common``) and the constitution are user-level rules:
    they apply to every project, and Claude Code also loads project
    ``.claude/rules/`` from parent directories, so project copies would load
    them twice or more.

    When refresh_urls is True, re-fetches URL-sourced rules before injection.
    Only the global install path should set this to True (once per update).
    """
    claude_md = claude_dir / "CLAUDE.md"

    if dry_run:
        _inject_rules_dry_run(rules_dir, profile, only, skip)
        return

    # Refresh URL-sourced rules before injection (global update only)
    if refresh_urls:
        _refresh_url_rules(rules_dir)

    if not claude_md.is_file():
        claude_md.touch()
        print("  Created: ~/.claude/CLAUDE.md")

    install_toolkit_rules = should_install("rules", only, skip)
    if not install_toolkit_rules:
        print("  Skipped: toolkit rule files")

    expected: set[str] = set()
    rules_synced: list[str] = []

    if rules_dir.is_dir():
        for rule_file in sorted(rules_dir.glob("*.md")):
            rule_name = rule_file.stem
            output_name = f"ai-toolkit-registered-{_safe_rule_name(rule_name)}"
            _write_claude_rule_file(claude_dir, rule_file, output_name)
            _remove_legacy_rule_marker(target_dir, rule_name)
            expected.add(output_name)
            rules_synced.append(rule_name)

    if install_toolkit_rules:
        rules_src = app_dir / "rules"
        if rules_src.is_dir():
            for source_file in sorted(rules_src.glob("*.md")):
                rule_name = source_file.stem
                output_name = f"ai-toolkit-{_safe_rule_name(rule_name)}"
                _write_claude_rule_file(claude_dir, source_file, output_name)
                _remove_legacy_rule_marker(target_dir, rule_name)
                expected.add(output_name)
                rules_synced.append(rule_name)
        for stem, body, paths in common_rule_sources(profile):
            output_name = f"ai-toolkit-{_safe_rule_name(stem)}"
            _write_rule_text(claude_dir, output_name, render_common_rule(body, paths))
            expected.add(output_name)
            rules_synced.append(stem)

    install_constitution = should_install("constitution", only, skip)
    constitution_src = app_dir / "constitution.md"
    if install_constitution and constitution_src.is_file():
        _, body = split_frontmatter(constitution_src.read_text(encoding="utf-8"))
        _write_rule_text(claude_dir, CONSTITUTION_RULE, body.lstrip("\n").rstrip() + "\n")
        expected.add(CONSTITUTION_RULE)

    # `--skip rules` leaves the rule files and their index alone; the
    # constitution is its own component and is written either way.
    if not install_toolkit_rules and not rules_synced:
        return
    if install_constitution and constitution_src.is_file():
        rules_synced.append("constitution")

    removed = _cleanup_managed_claude_rules(
        claude_dir,
        expected,
        cleanup_toolkit_rules=install_toolkit_rules,
        keep_constitution=not install_constitution,
    )
    _inject_global_rules_index(claude_md, sorted(expected), rules_synced)

    print(f"  Rules synced: {' '.join(rules_synced)}")
    if removed:
        print(f"  Cleaned: {removed} stale .claude/rules/ai-toolkit-*.md file(s)")


def _safe_rule_name(name: str) -> str:
    """Return a Claude-safe filename/marker stem."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)


def _write_claude_rule_file(
    claude_dir: Path,
    source_file: Path,
    output_name: str,
) -> None:
    """Write a managed user-level rule under ``~/.claude/rules``."""
    _write_rule_text(
        claude_dir,
        output_name,
        source_file.read_text(encoding="utf-8").rstrip() + "\n",
    )


def _write_rule_text(claude_dir: Path, output_name: str, content: str) -> None:
    rules_root = claude_dir / "rules"
    rules_root.mkdir(parents=True, exist_ok=True)
    (rules_root / f"{output_name}.md").write_text(content, encoding="utf-8")


def _remove_legacy_rule_marker(target_dir: Path, rule_name: str) -> None:
    """Remove old CLAUDE.md marker sections for rules now stored as files."""
    remove_rule_section(_safe_rule_name(rule_name), target_dir)


def _cleanup_managed_claude_rules(
    claude_dir: Path,
    expected: set[str],
    *,
    cleanup_toolkit_rules: bool,
    keep_constitution: bool = False,
) -> int:
    """Remove stale ai-toolkit-managed user-level rule files only."""
    rules_root = claude_dir / "rules"
    if not rules_root.is_dir():
        return 0

    removed = 0
    for path in sorted(rules_root.glob("ai-toolkit-*.md")):
        if path.stem in expected:
            continue
        if keep_constitution and path.stem == CONSTITUTION_RULE:
            continue
        if not cleanup_toolkit_rules and not path.stem.startswith("ai-toolkit-registered-"):
            continue
        path.unlink()
        removed += 1
    return removed


def _inject_global_rules_index(
    claude_md: Path,
    managed_rule_names: list[str],
    display_names: list[str],
) -> None:
    """Keep CLAUDE.md as a compact pointer to user-level rule files."""
    existing = claude_md.read_text(encoding="utf-8") if claude_md.is_file() else ""
    existing = _trim_trailing_blanks(_strip_section(existing, GLOBAL_RULES_SECTION))

    lines = [
        "# Global ai-toolkit Rules",
        "",
        "ai-toolkit rules live in `~/.claude/rules/ai-toolkit-*.md` as Claude Code user-level rules.",
        "They are intentionally not inlined into this `CLAUDE.md`; use `/memory` to inspect loaded rule files.",
    ]
    if display_names:
        names = ", ".join(f"`{name}`" for name in display_names)
        lines.extend(["", f"Rules: {names}"])
    if managed_rule_names:
        files = ", ".join(f"`~/.claude/rules/{name}.md`" for name in managed_rule_names)
        lines.extend(["", f"Files: {files}"])

    parts: list[str] = []
    if existing.strip():
        parts.append(existing)
        parts.append("")
    parts.extend([
        f"<!-- TOOLKIT:{GLOBAL_RULES_SECTION} START -->",
        "<!-- Auto-injected by ai-toolkit. Re-run to update. -->",
        "",
        "\n".join(lines),
        "",
        f"<!-- TOOLKIT:{GLOBAL_RULES_SECTION} END -->",
    ])

    output = _collapse_blank_runs("\n".join(parts) + "\n").lstrip("\n")
    claude_md.parent.mkdir(parents=True, exist_ok=True)
    claude_md.write_text(output, encoding="utf-8")


def _refresh_url_rules(rules_dir: Path) -> None:
    """Re-fetch all URL-sourced rules. Warn on failure, use cached copy."""
    from rule_sources import get_url_rules, fetch_url, register_url_source

    url_rules = get_url_rules(rules_dir)
    if not url_rules:
        return

    for rule_name, url in url_rules.items():
        rule_file = rules_dir / f"{rule_name}.md"
        try:
            data = fetch_url(url)
            rule_file.write_bytes(data)
            register_url_source(rules_dir, rule_name, url, content=data)
            print(f"  Refreshed: {rule_name} (from {url})")
        except Exception as exc:
            if rule_file.is_file():
                print(f"  Warning: could not refresh '{rule_name}' from {url}: {exc}")
                print("           Using cached version.")
            else:
                print(f"  Warning: could not fetch '{rule_name}' from {url}: {exc}")
                print("           No cached version — rule will be skipped.")


def refresh_url_hooks(target_dir: str | None = None) -> None:
    """Re-fetch all URL-sourced hooks and re-inject them.

    Called during ``ai-toolkit update`` to keep URL-sourced hooks current.
    On fetch failure, warns and keeps the cached version.
    """
    from hook_sources import get_url_hooks, register_url_source
    from paths import EXTERNAL_HOOKS_DIR
    from url_fetch import fetch_url
    import json

    url_hooks = get_url_hooks()
    if not url_hooks:
        return

    print("  Refreshing URL-sourced hooks...")
    target = target_dir or str(Path.home())

    for hook_name, url in url_hooks.items():
        cached_file = EXTERNAL_HOOKS_DIR / f"{hook_name}.json"
        try:
            data = fetch_url(url)
            # Validate JSON before caching
            json.loads(data)
            cached_file.write_bytes(data)
            register_url_source(None, hook_name, url, content=data)
            print(f"  Refreshed: {hook_name} (from {url})")
        except Exception as exc:
            if cached_file.is_file():
                print(f"  Warning: could not refresh '{hook_name}' from {url}: {exc}")
                print("           Using cached version.")
            else:
                print(f"  Warning: could not fetch '{hook_name}' from {url}: {exc}")
                print("           No cached version — hook will be skipped.")
                continue

        # Re-inject from cached file
        if cached_file.is_file():
            from inject_hook_cli import inject
            inject(str(cached_file), target, source_override=hook_name)


def refresh_mcp_templates(target_dir: str | None = None) -> None:
    """Re-read registered local and URL MCP templates and re-inject them.

    Called during ``ai-toolkit update``. URL fetch failures use the cached
    version; missing local sources leave their installed config in place.
    """
    from mcp_sources import load_sources, register_url_source
    from paths import EXTERNAL_MCP_DIR
    from url_fetch import fetch_url
    import json

    sources = load_sources()
    if not sources:
        return

    print("  Refreshing external MCP templates...")
    target = target_dir or str(Path.home())

    for template_name, source in sources.items():
        if "url" not in source:
            _refresh_local_mcp_template(template_name, source, target)
            continue
        url = source["url"]
        cached_file = EXTERNAL_MCP_DIR / f"{template_name}.json"
        try:
            data = fetch_url(url)
            json.loads(data)
            cached_file.write_bytes(data)
            register_url_source(None, template_name, url, content=data)
            print(f"  Refreshed: {template_name} (from {url})")
        except Exception as exc:
            if cached_file.is_file():
                print(f"  Warning: could not refresh '{template_name}' from {url}: {exc}")
                print("           Using cached version.")
            else:
                print(f"  Warning: could not fetch '{template_name}' from {url}: {exc}")
                print("           No cached version — template will be skipped.")
                continue

        if cached_file.is_file():
            from inject_mcp_cli import inject
            inject(str(cached_file), target, source_override=template_name, force=True)


def _refresh_local_mcp_template(name: str, source: dict, target: str) -> None:
    """Refresh a local source while preserving ownership and missing files."""
    from inject_mcp_cli import inject

    path = source.get("path")
    if not isinstance(path, str) or not Path(path).is_file():
        print(f"  Warning: local MCP template '{name}' is missing; keeping installed config.")
        return
    try:
        inject(path, target, source_override=name, force=False)
    except (Exception, SystemExit) as exc:
        print(f"  Warning: could not refresh local MCP template '{name}': {exc}")


def _inject_rules_dry_run(rules_dir: Path, profile: str = "standard",
                          only: str = "", skip: str = "") -> None:
    rules_src = app_dir / "rules"
    names = [f.stem for f in sorted(rules_src.glob("*.md"))] if rules_src.is_dir() else []
    if should_install("rules", only, skip):
        names += [stem for stem, _, _ in common_rule_sources(profile)]
    if should_install("constitution", only, skip):
        names.append("constitution")
    print(f"  Would generate: ~/.claude/rules/ai-toolkit-*.md ({' '.join(names)})")
    if rules_dir.is_dir():
        registered = list(rules_dir.glob("*.md"))
        if registered:
            reg_names = " ".join(f.stem for f in sorted(registered))
            print(f"  Would generate: ~/.claude/rules/ai-toolkit-registered-*.md ({reg_names})")
    print("  Would update: ~/.claude/CLAUDE.md global rules index")
