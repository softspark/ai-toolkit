#!/usr/bin/env python3
"""Build and verify the uploadable ai-toolkit plugin for the Claude app.

Claude Code reads ``~/.claude`` directly. Claude Chat and Cowork do not: they
load customizations through the Claude app plugin/skill UI. This command turns
the canonical ``app/`` sources into a self-contained plugin archive that can be
uploaded from Customize > Plugins.

Usage:
    claude_app.py sync
    claude_app.py export [--output FILE] [--no-custom-rules] [--verify]
    claude_app.py verify
"""
from __future__ import annotations

import argparse
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


TOOLKIT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = TOOLKIT_DIR / "app"
CLAUDE_APP_DIR = APP_DIR / "claude-app"
PLUGIN_HOOKS_PATH = CLAUDE_APP_DIR / "hooks" / "hooks.json"
PLUGIN_RULES_SKILL_PATH = CLAUDE_APP_DIR / "skills" / "ai-toolkit-rules" / "SKILL.md"
GLOBAL_INSTRUCTIONS_PATH = CLAUDE_APP_DIR / "global-instructions.md"
REGISTERED_RULES_DIR = Path.home() / ".softspark" / "ai-toolkit" / "rules"

PLUGIN_SCRIPT_FILES = (
    "paths.py",
    "session_state.py",
    "test_cohesion.py",
    "version_check.py",
)
CLAUDE_CODE_ONLY_HOOKS = frozenset({"filter-tool-output.sh"})
RULE_FILES = tuple(sorted((APP_DIR / "rules").glob("*.md"))) + tuple(
    sorted((APP_DIR / "rules" / "common").glob("*.md"))
)
SKIP_NAMES = {"__pycache__", ".DS_Store"}
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _strip_frontmatter(content: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content.strip()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return content.strip()


def render_plugin_hooks() -> str:
    """Render plugin-owned hooks from the global-install hook manifest."""
    source = json.loads((APP_DIR / "hooks.json").read_text(encoding="utf-8"))
    hooks = source.get("hooks", {})

    def supports_claude_app(handler: object) -> bool:
        if not isinstance(handler, dict):
            return True
        command = handler.get("command")
        if not isinstance(command, str):
            return True
        return not any(name in command for name in CLAUDE_CODE_ONLY_HOOKS)

    app_hooks = {}
    for event, groups in hooks.items():
        app_groups = []
        for group in groups:
            handlers = [
                handler
                for handler in group.get("hooks", [])
                if supports_claude_app(handler)
            ]
            if handlers:
                app_groups.append({**group, "hooks": handlers})
        if app_groups:
            app_hooks[event] = app_groups

    def adapt(value):
        if isinstance(value, dict):
            return {
                key: adapt(item)
                for key, item in value.items()
                if key != "_source"
            }
        if isinstance(value, list):
            return [adapt(item) for item in value]
        if isinstance(value, str):
            adapted = value.replace(
                "$HOME/.softspark/ai-toolkit/hooks/",
                "${CLAUDE_PLUGIN_ROOT}/hooks/",
            )
            if "${CLAUDE_PLUGIN_ROOT}/hooks/" in adapted:
                adapted = f'AI_TOOLKIT_DIR="${{CLAUDE_PLUGIN_ROOT}}" {adapted}'
            return adapted
        return value

    return json.dumps({"hooks": adapt(app_hooks)}, indent=2, ensure_ascii=False) + "\n"


def render_rules_skill(extra_rules: tuple[Path, ...] = ()) -> str:
    """Render always-relevant engineering rules as a Claude app skill."""
    parts = [
        "---",
        "name: ai-toolkit-rules",
        'description: "Mandatory engineering, security, testing, git, performance, quality, and response rules. Claude MUST load this skill for every technical, coding, debugging, review, architecture, DevOps, data, or file-editing task in Chat or Cowork."',
        "user-invocable: true",
        "---",
        "",
        "# AI Toolkit Rules",
        "",
        "Apply every relevant rule below before acting. Treat MUST/NEVER language as mandatory.",
    ]
    for rule_file in (*RULE_FILES, *extra_rules):
        try:
            label = rule_file.relative_to(TOOLKIT_DIR)
        except ValueError:
            label = Path("registered") / rule_file.name
        body = _strip_frontmatter(rule_file.read_text(encoding="utf-8"))
        parts.extend(("", f"## Source: `{label}`", "", body))
    return "\n".join(parts).rstrip() + "\n"


def render_global_instructions() -> str:
    return """# AI Toolkit — Claude app global instructions

For every technical, coding, debugging, review, architecture, DevOps, data,
or file-editing task, load and follow the installed `ai-toolkit-rules` skill
before acting. Load the relevant language-rule and workflow skills as needed.
Use ai-toolkit sub-agents for specialist work in Cowork. Before claiming a
task is complete, run fresh verification and report the evidence.

In regular Chat, hooks and sub-agents are unavailable; skills remain the
authoritative customization surface. In Cowork, also honor the plugin hooks.
"""


def sync_generated() -> None:
    """Refresh committed Claude app plugin assets from canonical sources."""
    _write_text(PLUGIN_HOOKS_PATH, render_plugin_hooks())
    _write_text(PLUGIN_RULES_SKILL_PATH, render_rules_skill())
    _write_text(GLOBAL_INSTRUCTIONS_PATH, render_global_instructions())
    print("Synced: app/claude-app/hooks/hooks.json")
    print("Synced: app/claude-app/skills/ai-toolkit-rules/SKILL.md")
    print("Synced: app/claude-app/global-instructions.md")


def _copy_tree(source: Path, destination: Path) -> None:
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(
            part in SKIP_NAMES
            or part in CLAUDE_CODE_ONLY_HOOKS
            or part.endswith(".pyc")
            for part in relative.parts
        ):
            continue
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def stage_plugin(destination: Path, include_custom_rules: bool = True) -> int:
    """Create a clean plugin tree and return the registered-rule count."""
    destination.mkdir(parents=True, exist_ok=True)
    (destination / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        APP_DIR / ".claude-plugin" / "plugin.json",
        destination / ".claude-plugin" / "plugin.json",
    )

    for dirname in ("skills", "hooks", "output-styles"):
        _copy_tree(APP_DIR / dirname, destination / dirname)

    agents_dir = destination / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for agent in sorted((APP_DIR / "agents").glob("*.md")):
        shutil.copy2(agent, agents_dir / agent.name)

    app_assets = destination / "claude-app"
    _write_text(app_assets / "hooks" / "hooks.json", render_plugin_hooks())
    _write_text(
        app_assets / "skills" / "ai-toolkit-rules" / "SKILL.md",
        render_rules_skill(),
    )
    _write_text(app_assets / "global-instructions.md", render_global_instructions())

    scripts_dir = destination / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for filename in PLUGIN_SCRIPT_FILES:
        shutil.copy2(TOOLKIT_DIR / "scripts" / filename, scripts_dir / filename)
    shutil.copy2(TOOLKIT_DIR / "package.json", destination / "package.json")
    shutil.copy2(TOOLKIT_DIR / "LICENSE", destination / "LICENSE")

    registered = ()
    if include_custom_rules and REGISTERED_RULES_DIR.is_dir():
        registered = tuple(sorted(REGISTERED_RULES_DIR.glob("*.md")))
    if registered:
        _write_text(
            app_assets / "skills" / "registered-rules" / "SKILL.md",
            render_registered_rules_skill(registered),
        )
    return len(registered)


def render_registered_rules_skill(rules: tuple[Path, ...]) -> str:
    parts = [
        "---",
        "name: registered-rules",
        'description: "User-registered ai-toolkit rules. Claude MUST load this skill for technical work when the installed bundle contains organization or personal standards."',
        "user-invocable: true",
        "---",
        "",
        "# Registered AI Toolkit Rules",
    ]
    for rule_file in rules:
        parts.extend(
            (
                "",
                f"## `{rule_file.name}`",
                "",
                _strip_frontmatter(rule_file.read_text(encoding="utf-8")),
            )
        )
    return "\n".join(parts).rstrip() + "\n"


def _validate_staged_plugin(plugin_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"invalid plugin manifest: {exc}"]

    if not isinstance(manifest.get("repository"), str):
        errors.append("plugin manifest repository must be a URL string")
    for field in ("npm", "install", "marketplace", "claude-code"):
        if field in manifest:
            errors.append(f"plugin manifest contains ignored field: {field}")

    hooks_path = plugin_dir / str(manifest.get("hooks", "")).removeprefix("./")
    skills_path = plugin_dir / str(manifest.get("skills", "")).removeprefix("./")
    if not hooks_path.is_file():
        errors.append(f"plugin hook config missing: {hooks_path.relative_to(plugin_dir)}")
    if not skills_path.is_dir():
        errors.append(f"plugin skill path missing: {skills_path.relative_to(plugin_dir)}")

    if hooks_path.is_file():
        hooks_text = hooks_path.read_text(encoding="utf-8")
        if "$HOME/.softspark/ai-toolkit/hooks/" in hooks_text:
            errors.append("plugin hooks still reference the Claude Code global install")
        if "${CLAUDE_PLUGIN_ROOT}/hooks/" not in hooks_text:
            errors.append("plugin hooks do not reference CLAUDE_PLUGIN_ROOT")
        try:
            json.loads(hooks_text)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid plugin hooks JSON: {exc}")

    for agent in (plugin_dir / "agents").glob("*.md"):
        if not agent.read_text(encoding="utf-8").startswith("---\n"):
            errors.append(f"agent lacks frontmatter: {agent.name}")
    return errors


def _run_claude_validator(plugin_dir: Path) -> bool:
    claude = shutil.which("claude")
    if not claude:
        print("ERROR: claude CLI not found; cannot run official plugin validator", file=sys.stderr)
        return False
    result = subprocess.run(
        [claude, "plugin", "validate", str(plugin_dir), "--strict"]
    )
    return result.returncode == 0


def verify_plugin() -> bool:
    with tempfile.TemporaryDirectory(prefix="ai-toolkit-claude-app-") as tmp:
        staged = Path(tmp) / "ai-toolkit"
        stage_plugin(staged, include_custom_rules=False)
        errors = _validate_staged_plugin(staged)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if errors:
            return False
        if not _run_claude_validator(staged):
            return False
    print("Claude app plugin validation passed")
    return True


def _archive_file(zip_file: zipfile.ZipFile, path: Path, arcname: str) -> None:
    data = path.read_bytes()
    mode = path.stat().st_mode
    permissions = 0o755 if mode & stat.S_IXUSR else 0o644
    info = zipfile.ZipInfo(arcname, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | permissions) << 16
    zip_file.writestr(info, data)


def export_plugin(output: Path, include_custom_rules: bool, verify: bool) -> bool:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ai-toolkit-claude-app-") as tmp:
        staged = Path(tmp) / "ai-toolkit"
        registered_count = stage_plugin(staged, include_custom_rules=include_custom_rules)
        errors = _validate_staged_plugin(staged)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return False
        if verify and not _run_claude_validator(staged):
            return False
        with zipfile.ZipFile(output, "w") as archive:
            for path in sorted(staged.rglob("*")):
                if path.is_file():
                    _archive_file(archive, path, path.relative_to(staged).as_posix())

    instructions = output.with_name(f"{output.stem}-global-instructions.md")
    _write_text(instructions, render_global_instructions())
    print(f"Created: {output}")
    print(f"Created: {instructions}")
    if registered_count:
        print(f"Included registered rules: {registered_count} (local bundle; review before sharing)")
    print("Next: Claude > Customize > Plugins > + > Upload plugin")
    print("Then paste the instructions file into Settings > Cowork > Global instructions")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("sync", help="refresh committed Claude app plugin assets")
    subparsers.add_parser("verify", help="run structural and official plugin validation")
    export = subparsers.add_parser("export", help="build an uploadable Claude app plugin ZIP")
    export.add_argument("--output", default="ai-toolkit-claude-app.zip")
    export.add_argument("--no-custom-rules", action="store_true")
    export.add_argument("--verify", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.action == "sync":
        sync_generated()
        return 0
    if args.action == "verify":
        return 0 if verify_plugin() else 1
    if args.action == "export":
        return 0 if export_plugin(
            Path(args.output),
            include_custom_rules=not args.no_custom_rules,
            verify=args.verify,
        ) else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
