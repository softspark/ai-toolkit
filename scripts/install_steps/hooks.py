"""Hook installation: copy scripts, merge JSON, output styles."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from _common import app_dir, should_install, toolkit_dir


def install_hooks(claude_dir: Path, hooks_scripts_dir: Path,
                  only: str, skip: str, dry_run: bool) -> None:
    """Install hooks: copy scripts, merge JSON, install output styles."""
    if not should_install("hooks", only, skip):
        print("  Skipped: hooks")
        return

    hooks_json = app_dir / "hooks.json"
    if not hooks_json.is_file():
        return

    if dry_run:
        print("  Would merge: .claude/settings.json hooks (toolkit entries into user settings)")
        output_styles_dir = app_dir / "output-styles"
        if output_styles_dir.is_dir():
            print("  Would install: output styles to ~/.claude/output-styles/ + set outputStyle in settings.json")
        print("  Would set: env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in settings.json")
        return

    _copy_hook_scripts(claude_dir, hooks_scripts_dir)
    _copy_hook_runtime_scripts(hooks_scripts_dir.parent / "scripts")
    _run_merge_hooks(
        "inject",
        str(hooks_json),
        str(claude_dir / "settings.json"),
    )
    print("  Merged: .claude/settings.json (hooks)")

    legacy_hooks_json = claude_dir / "hooks.json"
    if legacy_hooks_json.is_file():
        legacy_hooks_json.unlink()
        print("  Removed: .claude/hooks.json (legacy)")

    _install_output_styles(claude_dir)
    _install_env_vars(claude_dir)


def _copy_hook_scripts(claude_dir: Path, hooks_scripts_dir: Path) -> None:
    hooks_src = app_dir / "hooks"
    if not hooks_src.is_dir():
        return
    copied = 0
    for hook_file in sorted(hooks_src.glob("*.sh")):
        dst = hooks_scripts_dir / hook_file.name
        shutil.copy2(hook_file, dst)
        dst.chmod(dst.stat().st_mode | 0o111)
        copied += 1
    print(f"  Copied: {copied} hook scripts to ~/.softspark/ai-toolkit/hooks/")
    legacy_hooks = claude_dir / "hooks"
    if legacy_hooks.is_symlink():
        legacy_hooks.unlink()
        print("  Removed: .claude/hooks (legacy symlink)")


# Python helpers that hooks invoke at runtime. Kept narrow on purpose — only
# scripts that a deployed hook actually executes belong here.
HOOK_RUNTIME_SCRIPTS: tuple[str, ...] = (
    "session_token_stats.py",
    "version_check.py",
)


def _copy_hook_runtime_scripts(scripts_dst: Path) -> None:
    """Copy the small set of Python helpers that deployed hooks invoke.

    Without this, hooks that call e.g. session_token_stats.py only work when
    the npm-global @softspark/ai-toolkit package is up to date. Shipping these
    alongside the hooks means ~/.softspark/ai-toolkit/ is self-sufficient.
    """
    scripts_src = toolkit_dir / "scripts"
    if not scripts_src.is_dir():
        return
    scripts_dst.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in HOOK_RUNTIME_SCRIPTS:
        src = scripts_src / name
        if not src.is_file():
            continue
        dst = scripts_dst / name
        shutil.copy2(src, dst)
        dst.chmod(dst.stat().st_mode | 0o111)
        copied += 1
    if copied:
        print(f"  Copied: {copied} hook runtime scripts to ~/.softspark/ai-toolkit/scripts/")


def _run_merge_hooks(action: str, *args: str) -> None:
    cmd = ["python3", str(toolkit_dir / "scripts" / "merge-hooks.py"), action, *args]
    subprocess.run(cmd, check=True, timeout=120)


def _install_output_styles(claude_dir: Path) -> None:
    output_styles_src = app_dir / "output-styles"
    if not output_styles_src.is_dir():
        return
    output_styles_dst = claude_dir / "output-styles"
    output_styles_dst.mkdir(parents=True, exist_ok=True)
    styles_copied = 0
    for style_file in sorted(output_styles_src.glob("*.md")):
        shutil.copy2(style_file, output_styles_dst / style_file.name)
        styles_copied += 1
    if styles_copied > 0:
        print(f"  Copied: {styles_copied} output style(s) to ~/.claude/output-styles/")
        settings_path = claude_dir / "settings.json"
        if settings_path.is_file():
            with open(settings_path, encoding="utf-8") as f:
                settings_data = json.load(f)
        else:
            settings_data = {}
        if "outputStyle" not in settings_data:
            settings_data["outputStyle"] = "Golden Rules"
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=4)
            print("  Set: outputStyle = 'Golden Rules' in settings.json")


# Toolkit env vars injected into settings.json
TOOLKIT_ENV_VARS = {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
}


def _install_env_vars(claude_dir: Path) -> None:
    """Ensure toolkit env vars are set in settings.json."""
    settings_path = claude_dir / "settings.json"
    if settings_path.is_file():
        with open(settings_path, encoding="utf-8") as f:
            settings_data = json.load(f)
    else:
        settings_data = {}

    env = settings_data.setdefault("env", {})
    changed = False
    for key, value in TOOLKIT_ENV_VARS.items():
        if env.get(key) != value:
            env[key] = value
            changed = True

    if changed:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=4)
        print("  Set: env vars in settings.json (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)")
