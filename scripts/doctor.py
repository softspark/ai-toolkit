#!/usr/bin/env python3
"""ai-toolkit doctor -- Installation health and configuration diagnostics.

Checks:
  1. Environment prerequisites (node, bash, python3, bats) + check_deps
  2. Global install integrity (symlinks, settings.json hooks)
  3. Hook scripts (existence, executable)
  4. Hook configuration (valid event names)
  5. Generated artifacts (AGENTS.md, llms.txt staleness)
  6. Planned assets
  7. Benchmark freshness
  8. Stale rules
  9. URL hook sources

Exit codes:
  0  all checks pass
  1  one or more checks failed
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir
from paths import HOOKS_DIR as _HOOKS_DIR, RULES_DIR as _RULES_DIR, EXTERNAL_HOOKS_DIR as _EXTERNAL_HOOKS_DIR


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLAUDE_DIR = Path.home() / ".claude"
HOOKS_DIR = _HOOKS_DIR
RULES_DIR = _RULES_DIR
EXTERNAL_HOOKS_DIR = _EXTERNAL_HOOKS_DIR
BENCHMARK_DASHBOARD = toolkit_dir / "benchmarks" / "ecosystem-dashboard.json"

VALID_EVENTS = frozenset({
    "SessionStart", "Notification", "PreToolUse", "PostToolUse", "Stop",
    "PreCompact", "SubagentStop", "UserPromptSubmit", "TaskCompleted",
    "TeammateIdle", "SubagentStart", "SessionEnd", "PermissionRequest", "Setup",
})

EXPECTED_HOOKS = [
    "guard-destructive.sh",
    "guard-path.sh",
    "post-tool-use.sh",
    "quality-check.sh",
    "quality-gate.sh",
    "save-session.sh",
    "session-start.sh",
    "pre-compact.sh",
    "user-prompt-submit.sh",
    "track-usage.sh",
    "subagent-start.sh",
    "subagent-stop.sh",
    "session-end.sh",
]

PLANNED_ASSETS = [
    toolkit_dir / "app" / ".claude-plugin" / "plugin.json",
    toolkit_dir / "scripts" / "benchmark_ecosystem.py",
    toolkit_dir / "scripts" / "harvest_ecosystem.py",
    toolkit_dir / "kb" / "reference" / "claude-ecosystem-benchmark-snapshot.md",
    toolkit_dir / "kb" / "reference" / "plugin-pack-conventions.md",
    toolkit_dir / "app" / "skills" / "plugin-creator" / "SKILL.md",
    toolkit_dir / "app" / "skills" / "hook-creator" / "SKILL.md",
    toolkit_dir / "app" / "skills" / "command-creator" / "SKILL.md",
    toolkit_dir / "app" / "skills" / "agent-creator" / "SKILL.md",
]


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

class DiagResult:
    """Accumulates pass/fail/warn/fix/skip counts."""

    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def ok(self, msg: str) -> None:
        print(f"  OK: {msg}")

    def fail(self, msg: str) -> None:
        print(f"  FAIL: {msg}")
        self.errors += 1

    def warn(self, msg: str) -> None:
        print(f"  WARN: {msg}")
        self.warnings += 1

    def skip(self, msg: str) -> None:
        print(f"  SKIP: {msg}")

    def fixed(self, msg: str) -> None:
        print(f"  FIXED: {msg}")


# ---------------------------------------------------------------------------
# Version extraction
# ---------------------------------------------------------------------------

def _get_version(binary: str) -> str:
    """Get a version string from a binary."""
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip() or result.stderr.strip()
        m = re.search(r"(\d+\.\d+\.\d+)", output)
        return m.group(1) if m else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


# ---------------------------------------------------------------------------
# Check 1: Environment
# ---------------------------------------------------------------------------

def check_environment(dr: DiagResult, fix_mode: bool) -> None:
    """Check that required and optional binaries are present."""
    print("## Environment")

    # Basic binary checks (matching original bash behavior)
    for binary, label, required in [
        ("node", "node", True),
        ("bash", "bash", True),
        ("python3", "python3", False),
        ("bats", "bats", False),
    ]:
        if shutil.which(binary):
            version = _get_version(binary)
            ver_str = f" {version}" if version else ""
            dr.ok(f"{label}{ver_str}")
        else:
            if required:
                dr.fail(f"{label} not found")
            else:
                dr.warn(f"{label} not found" + (" (needed for hook merge)" if binary == "python3" else " (needed for tests)"))

    # Enhanced: also run check_deps logic
    try:
        from check_deps import check_deps as run_check_deps

        results = run_check_deps(verbose=False)
        if not results["all_ok"]:
            for dep in results["required"]:
                if not dep["found"] or not dep["version_ok"]:
                    hint = f" (fix: {dep['install_hint']})" if dep["install_hint"] else ""
                    dr.warn(f"check_deps: {dep['name']} -- {dep['reason']}{hint}")
    except ImportError:
        dr.warn("check_deps.py not available for enhanced dependency check")

    print()


# ---------------------------------------------------------------------------
# Check 2: Global Install
# ---------------------------------------------------------------------------

def _check_symlinks(dr: DiagResult, fix_mode: bool, directory: Path,
                    source_subdir: str, label: str, glob_pattern: str,
                    is_file_check: bool) -> None:
    """Check symlinks in a directory, optionally fixing broken ones."""
    if not directory.is_dir():
        dr.fail(f"{label} directory missing")
        return

    link_count = 0
    broken_count = 0
    for item in sorted(directory.glob(glob_pattern) if glob_pattern != "*" else directory.iterdir()):
        if not item.is_symlink():
            continue
        link_count += 1
        if not item.exists():
            if fix_mode:
                item.unlink()
                source = toolkit_dir / "app" / source_subdir / item.name
                check_fn = source.is_file if is_file_check else source.is_dir
                if check_fn():
                    item.symlink_to(source)
                    dr.fixed(f"re-linked {label[:-1]}: {item.name}")
                else:
                    dr.fixed(f"removed broken {label[:-1]} symlink: {item.name}")
            else:
                broken_count += 1
                dr.warn(f"broken symlink: {item}")

    if link_count > 0 and broken_count == 0:
        dr.ok(f"{label}: {link_count} symlinks (0 broken)")
    elif link_count == 0:
        dr.fail(f"{label}: no symlinks found")


def _check_settings_json(dr: DiagResult) -> None:
    """Check settings.json hooks and legacy hooks.json."""
    settings_json = CLAUDE_DIR / "settings.json"
    if settings_json.is_file():
        content = settings_json.read_text(encoding="utf-8")
        if '"_source"' in content and '"ai-toolkit"' in content:
            hook_count = content.count('"ai-toolkit"')
            dr.ok(f"settings.json: {hook_count} toolkit hook entries")
        else:
            dr.warn("settings.json exists but has no toolkit hooks")
    else:
        dr.fail("settings.json not found")

    legacy_hooks = CLAUDE_DIR / "hooks.json"
    if legacy_hooks.is_file():
        dr.warn("legacy hooks.json still exists (run: ai-toolkit update)")


def check_global_install(dr: DiagResult, fix_mode: bool) -> None:
    """Check symlinks and settings.json in ~/.claude/."""
    print("## Global Install")

    if CLAUDE_DIR.is_dir():
        dr.ok(f"{CLAUDE_DIR} exists")
    else:
        dr.fail(f"{CLAUDE_DIR} not found (run: ai-toolkit install)")
        print()
        return

    _check_symlinks(dr, fix_mode, CLAUDE_DIR / "agents", "agents", "agents", "*.md", True)
    _check_symlinks(dr, fix_mode, CLAUDE_DIR / "skills", "skills", "skills", "*", False)
    _check_settings_json(dr)

    print()


# ---------------------------------------------------------------------------
# Check 3: Hook Scripts
# ---------------------------------------------------------------------------

def check_hook_scripts(dr: DiagResult, fix_mode: bool) -> None:
    """Check that expected hook scripts exist and are executable."""
    print("## Hook Scripts")

    if not HOOKS_DIR.is_dir():
        dr.fail(f"hook scripts directory missing: {HOOKS_DIR}")
        print()
        return

    for hook in EXPECTED_HOOKS:
        hook_path = HOOKS_DIR / hook
        source_path = toolkit_dir / "app" / "hooks" / hook

        if hook_path.is_file() and os.access(hook_path, os.X_OK):
            dr.ok(hook)
        elif hook_path.is_file():
            if fix_mode:
                hook_path.chmod(hook_path.stat().st_mode | 0o111)
                dr.fixed(f"{hook} made executable")
            else:
                dr.warn(f"{hook} exists but is not executable")
        else:
            if fix_mode and source_path.is_file():
                HOOKS_DIR.mkdir(parents=True, exist_ok=True)
                import shutil as _shutil
                _shutil.copy2(source_path, hook_path)
                hook_path.chmod(hook_path.stat().st_mode | 0o111)
                dr.fixed(f"restored {hook}")
            else:
                dr.fail(f"{hook} missing from {HOOKS_DIR}")

    print()


# ---------------------------------------------------------------------------
# Check 4: Hook Configuration
# ---------------------------------------------------------------------------

def check_hook_configuration(dr: DiagResult) -> None:
    """Validate event names in app/hooks.json."""
    print("## Hook Configuration")

    hooks_file = toolkit_dir / "app" / "hooks.json"
    if not hooks_file.is_file():
        dr.fail("app/hooks.json not found")
        print()
        return

    try:
        with open(hooks_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        dr.warn("could not parse hook events from app/hooks.json")
        print()
        return

    hooks = data.get("hooks", {})
    if not hooks:
        dr.warn("could not parse hook events from app/hooks.json")
    else:
        for event in hooks:
            if event in VALID_EVENTS:
                dr.ok(f"event: {event}")
            else:
                dr.fail(f"unknown hook event: {event}")

    print()


# ---------------------------------------------------------------------------
# Check 5: Generated Artifacts
# ---------------------------------------------------------------------------

def check_generated_artifacts(dr: DiagResult, fix_mode: bool) -> None:
    """Check existence and staleness of generated artifacts."""
    print("## Generated Artifacts")

    artifacts = {
        "AGENTS.md": ("generate_agents_md.py", []),
        "llms.txt": ("generate_llms_txt.py", []),
        "llms-full.txt": ("generate_llms_txt.py", ["--full"]),
    }

    for artifact, (gen_script, gen_args) in artifacts.items():
        path = toolkit_dir / artifact
        if path.is_file():
            dr.ok(f"{artifact} exists")
        else:
            if fix_mode:
                result = subprocess.run(
                    ["python3", str(toolkit_dir / "scripts" / gen_script)] + gen_args,
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    path.write_text(result.stdout, encoding="utf-8")
                    dr.fixed(f"regenerated {artifact}")
                else:
                    dr.fail(f"could not regenerate {artifact}")
            else:
                dr.warn(f"{artifact} missing (run: ai-toolkit generate-all)")

    # Check if AGENTS.md is stale (agents added/removed since generation)
    agents_md = toolkit_dir / "AGENTS.md"
    if agents_md.is_file():
        agents_dir = toolkit_dir / "app" / "agents"
        actual_agents = sum(1 for f in agents_dir.glob("*.md") if f.is_file()) if agents_dir.is_dir() else 0
        content = agents_md.read_text(encoding="utf-8")
        mentioned_agents = len(re.findall(r"^### `", content, re.MULTILINE))
        if actual_agents != mentioned_agents:
            if fix_mode:
                result = subprocess.run(
                    ["python3", str(toolkit_dir / "scripts" / "generate_agents_md.py")],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    agents_md.write_text(result.stdout, encoding="utf-8")
                    dr.fixed(f"regenerated stale AGENTS.md ({mentioned_agents} -> {actual_agents} entries)")
            else:
                dr.warn(f"AGENTS.md may be stale: {mentioned_agents} entries vs {actual_agents} agent files")

    print()


# ---------------------------------------------------------------------------
# Check 6: Planned Assets
# ---------------------------------------------------------------------------

def check_planned_assets(dr: DiagResult) -> None:
    """Check that planned assets exist and are non-empty."""
    print("## Planned Assets")

    for asset in PLANNED_ASSETS:
        if asset.is_file() and asset.stat().st_size > 0:
            dr.ok(f"{asset.name} present")
        else:
            rel = str(asset.relative_to(toolkit_dir))
            dr.fail(f"missing or empty asset: {rel}")

    # Plugin pack count
    plugins_dir = toolkit_dir / "app" / "plugins"
    if plugins_dir.is_dir():
        pack_count = sum(1 for d in plugins_dir.iterdir() if d.is_dir())
        if pack_count > 0:
            dr.ok(f"plugin packs: {pack_count} experimental pack(s) present")
        else:
            dr.warn("no plugin packs found in app/plugins")
    else:
        dr.warn("no plugin packs found in app/plugins")

    print()


# ---------------------------------------------------------------------------
# Check 7: Benchmark Freshness
# ---------------------------------------------------------------------------

def check_benchmark_freshness(dr: DiagResult) -> None:
    """Check benchmark dashboard freshness."""
    print("## Benchmark Freshness")

    if BENCHMARK_DASHBOARD.is_file():
        try:
            with open(BENCHMARK_DASHBOARD, encoding="utf-8") as f:
                data = json.load(f)
            freshness = data.get("freshness", {})
            status = freshness.get("status", "unknown")
            age = freshness.get("age_days", "?")
            threshold = freshness.get("stale_threshold_days", "?")

            if status == "fresh":
                dr.ok(f"benchmark dashboard is fresh ({age} day(s) old, threshold {threshold})")
            elif status == "aging":
                dr.warn(f"benchmark dashboard is aging ({age} day(s) old, threshold {threshold})")
            elif status == "stale":
                dr.warn(f"benchmark dashboard is stale ({age} day(s) old, threshold {threshold}) -- run: python3 scripts/harvest_ecosystem.py")
            else:
                dr.warn("benchmark dashboard freshness unknown")
        except (json.JSONDecodeError, OSError):
            dr.warn("could not parse benchmark dashboard freshness")
    else:
        dr.fail("benchmark dashboard missing: benchmarks/ecosystem-dashboard.json")

    harvest = toolkit_dir / "benchmarks" / "ecosystem-harvest.json"
    if harvest.is_file():
        dr.ok("ecosystem-harvest.json present")
    else:
        dr.warn("ecosystem-harvest.json missing (run: python3 scripts/harvest_ecosystem.py)")

    print()


# ---------------------------------------------------------------------------
# Check 8: Stale Rules
# ---------------------------------------------------------------------------

def check_stale_rules(dr: DiagResult, fix_mode: bool) -> None:
    """Check for stale symlinks and empty rule files."""
    print()
    print("## 8. Stale Rules")

    if not RULES_DIR.is_dir():
        dr.skip("No rules directory")
        return

    stale = 0
    for rule_file in sorted(RULES_DIR.iterdir()):
        # Check for stale symlinks
        if rule_file.is_symlink() and not rule_file.exists():
            print(f"  WARNING: Stale symlink: {rule_file}")
            stale += 1
            if fix_mode:
                rule_file.unlink()
                print("    FIXED: removed stale symlink")
        elif rule_file.is_file() and rule_file.stat().st_size == 0:
            print(f"  WARNING: Empty rule file: {rule_file}")
            stale += 1

    if stale == 0:
        dr.ok("All rules healthy")


# ---------------------------------------------------------------------------
# Check 9: URL Hook Sources
# ---------------------------------------------------------------------------

def check_url_hooks(dr: DiagResult, fix_mode: bool) -> None:
    """Check URL-sourced hook cache integrity."""
    print()
    print("## 9. URL Hook Sources")

    sources_file = EXTERNAL_HOOKS_DIR / "sources.json"
    if not sources_file.is_file():
        dr.skip("No URL hook sources registered")
        return

    try:
        with open(sources_file, encoding="utf-8") as f:
            data = json.load(f)
        sources = data.get("hooks", {})
    except (json.JSONDecodeError, OSError) as exc:
        dr.fail(f"Corrupt sources.json: {exc}")
        return

    if not sources:
        dr.ok("No URL hook sources registered")
        return

    issues = 0
    for name, entry in sources.items():
        cached = EXTERNAL_HOOKS_DIR / f"{name}.json"
        url = entry.get("url", "")

        if not cached.is_file():
            dr.warn(f"Missing cached file for '{name}' ({url})")
            issues += 1
            if fix_mode:
                try:
                    from url_fetch import fetch_url
                    content = fetch_url(url)
                    json.loads(content)  # validate
                    EXTERNAL_HOOKS_DIR.mkdir(parents=True, exist_ok=True)
                    cached.write_bytes(content)
                    print(f"    FIXED: re-fetched {name}")
                except Exception as exc:
                    print(f"    Could not re-fetch: {exc}")
            continue

        # Validate cached file is valid JSON with hooks key
        try:
            with open(cached, encoding="utf-8") as f:
                hook_data = json.load(f)
            if "hooks" not in hook_data:
                dr.warn(f"Cached file '{name}' missing 'hooks' key")
                issues += 1
            else:
                dr.ok(f"{name} ({url})")
        except json.JSONDecodeError:
            dr.warn(f"Corrupt cached file: {cached}")
            issues += 1
            if fix_mode:
                try:
                    from url_fetch import fetch_url
                    content = fetch_url(url)
                    json.loads(content)
                    cached.write_bytes(content)
                    print(f"    FIXED: re-fetched {name}")
                except Exception as exc:
                    print(f"    Could not re-fetch: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    fix_mode = "--fix" in sys.argv[1:]

    print("ai-toolkit doctor")
    print("========================")
    print()

    dr = DiagResult()

    check_environment(dr, fix_mode)
    check_global_install(dr, fix_mode)
    check_hook_scripts(dr, fix_mode)
    check_hook_configuration(dr)
    check_generated_artifacts(dr, fix_mode)
    check_planned_assets(dr)
    check_benchmark_freshness(dr)
    check_stale_rules(dr, fix_mode)
    check_url_hooks(dr, fix_mode)

    # Summary
    print("========================")
    if fix_mode:
        print("Mode: --fix (auto-repair enabled)")
    print(f"Errors: {dr.errors} | Warnings: {dr.warnings}")

    if dr.errors > 0:
        print("HEALTH CHECK FAILED")
        sys.exit(1)
    else:
        print("HEALTH CHECK PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
