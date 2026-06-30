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


GLOBAL_RULES_SECTION = "global-rules"


def install_marker_files(claude_dir: Path, only: str, skip: str,
                         dry_run: bool) -> None:
    """Inject constitution.md, ARCHITECTURE.md via markers."""
    marker_files = [
        ("constitution.md", "constitution", "constitution"),
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


def inject_rules(claude_dir: Path, target_dir: Path, rules_dir: Path,
                 only: str, skip: str, dry_run: bool,
                 refresh_urls: bool = False) -> None:
    """Install Claude Code user-level rules.

    When refresh_urls is True, re-fetches URL-sourced rules before injection.
    Only the global install path should set this to True (once per update).
    """
    claude_md = claude_dir / "CLAUDE.md"

    if dry_run:
        _inject_rules_dry_run(rules_dir)
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

    if not install_toolkit_rules and not rules_synced:
        return

    removed = _cleanup_managed_claude_rules(
        claude_dir,
        expected,
        cleanup_toolkit_rules=install_toolkit_rules,
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
    rules_root = claude_dir / "rules"
    rules_root.mkdir(parents=True, exist_ok=True)
    dst = rules_root / f"{output_name}.md"
    content = source_file.read_text(encoding="utf-8").rstrip() + "\n"
    dst.write_text(content, encoding="utf-8")


def _remove_legacy_rule_marker(target_dir: Path, rule_name: str) -> None:
    """Remove old CLAUDE.md marker sections for rules now stored as files."""
    remove_rule_section(_safe_rule_name(rule_name), target_dir)


def _cleanup_managed_claude_rules(
    claude_dir: Path,
    expected: set[str],
    *,
    cleanup_toolkit_rules: bool,
) -> int:
    """Remove stale ai-toolkit-managed user-level rule files only."""
    rules_root = claude_dir / "rules"
    if not rules_root.is_dir():
        return 0

    removed = 0
    for path in sorted(rules_root.glob("ai-toolkit-*.md")):
        if path.stem in expected:
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
                print(f"           Using cached version.")
            else:
                print(f"  Warning: could not fetch '{rule_name}' from {url}: {exc}")
                print(f"           No cached version — rule will be skipped.")


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
                print(f"           Using cached version.")
            else:
                print(f"  Warning: could not fetch '{hook_name}' from {url}: {exc}")
                print(f"           No cached version — hook will be skipped.")
                continue

        # Re-inject from cached file
        if cached_file.is_file():
            from inject_hook_cli import inject
            inject(str(cached_file), target, source_override=hook_name)


def refresh_url_mcp(target_dir: str | None = None) -> None:
    """Re-fetch all URL-sourced MCP templates and re-inject them.

    Called during ``ai-toolkit update`` to keep URL-sourced MCP templates
    current. On fetch failure, warns and keeps the cached version.
    """
    from mcp_sources import get_url_templates, register_url_source
    from paths import EXTERNAL_MCP_DIR
    from url_fetch import fetch_url
    import json

    url_templates = get_url_templates()
    if not url_templates:
        return

    print("  Refreshing URL-sourced MCP templates...")
    target = target_dir or str(Path.home())

    for template_name, url in url_templates.items():
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
                print(f"           Using cached version.")
            else:
                print(f"  Warning: could not fetch '{template_name}' from {url}: {exc}")
                print(f"           No cached version — template will be skipped.")
                continue

        if cached_file.is_file():
            from inject_mcp_cli import inject
            inject(str(cached_file), target, source_override=template_name, force=True)


def _inject_rules_dry_run(rules_dir: Path) -> None:
    rules_src = app_dir / "rules"
    rule_names = " ".join(
        f.stem for f in sorted(rules_src.glob("*.md"))
    ) if rules_src.is_dir() else ""
    print(f"  Would generate: ~/.claude/rules/ai-toolkit-*.md ({rule_names})")
    if rules_dir.is_dir():
        registered = list(rules_dir.glob("*.md"))
        if registered:
            reg_names = " ".join(f.stem for f in sorted(registered))
            print(f"  Would generate: ~/.claude/rules/ai-toolkit-registered-*.md ({reg_names})")
    print("  Would update: ~/.claude/CLAUDE.md global rules index")
