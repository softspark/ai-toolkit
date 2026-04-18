"""Marker file injection and rule injection."""
from __future__ import annotations

from pathlib import Path

from _common import app_dir, inject_rule, inject_section, should_install


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
    """Inject rules into CLAUDE.md.

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

    if not should_install("rules", only, skip):
        print("  Skipped: rules injection")

    rules_injected: list[str] = []

    if rules_dir.is_dir():
        for rule_file in sorted(rules_dir.glob("*.md")):
            rule_name = rule_file.stem
            inject_rule(rule_file, target_dir)
            rules_injected.append(rule_name)

    if should_install("rules", only, skip):
        rules_src = app_dir / "rules"
        if rules_src.is_dir():
            for source_file in sorted(rules_src.glob("*.md")):
                rule_name = source_file.stem
                inject_rule(source_file, target_dir)
                rules_injected.append(rule_name)

    print(f"  Rules injected: {' '.join(rules_injected)}")


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


def _inject_rules_dry_run(rules_dir: Path) -> None:
    rules_src = app_dir / "rules"
    rule_names = " ".join(
        f.stem for f in sorted(rules_src.glob("*.md"))
    ) if rules_src.is_dir() else ""
    print(f"  Would inject rules: {rule_names}")
    if rules_dir.is_dir():
        registered = list(rules_dir.glob("*.md"))
        if registered:
            reg_names = " ".join(f.stem for f in sorted(registered))
            print(f"  Would inject registered rules: {reg_names}")
