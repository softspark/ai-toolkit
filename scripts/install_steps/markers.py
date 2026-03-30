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
                 only: str, skip: str, dry_run: bool) -> None:
    """Inject rules into CLAUDE.md."""
    claude_md = claude_dir / "CLAUDE.md"

    if dry_run:
        _inject_rules_dry_run(rules_dir)
        return

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
