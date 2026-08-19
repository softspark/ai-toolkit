#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Export and verify the opt-in native Google Antigravity plugin package."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dir_rules_shared import STANDARD_RULES
from emission import agents_dir
from generate_antigravity_agents import render_agent
from generate_antigravity_hooks import (
    RUNTIME_NAME,
    RUNTIME_SOURCE,
    build_document,
    validate_document,
)
from secure_fs import SecureDestination, lexical_absolute, run_secure_transaction


TOOLKIT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = TOOLKIT_DIR / "app"
PLUGIN_NAME = "ai-toolkit"
PLUGIN_SCHEMA = "https://antigravity.google/schemas/v1/plugin.json"
PLUGIN_HOOK_COMMAND = f'python3 "${{extensionPath}}/runtime/{RUNTIME_NAME}"'
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
SKIP_NAMES = frozenset({"__pycache__", ".DS_Store"})
ABSOLUTE_HOST_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\\\Users\\\\)")
PLUGIN_SCRIPT_NAMES = (
    "_common.py",
    "audit_skills.py",
    "emission.py",
    "frontmatter.py",
    "injection.py",
    "instruction_core.py",
)


def render_manifest() -> str:
    manifest = {
        "$schema": PLUGIN_SCHEMA,
        "name": PLUGIN_NAME,
        "description": (
            "AI engineering rules, skills, agents, and lifecycle guardrails."
        ),
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def _collect_tree(source: Path, prefix: str) -> list[tuple[str, bytes, int]]:
    """Collect regular files without following links or special entries."""
    source = lexical_absolute(source)
    if source.is_symlink() or not source.is_dir():
        raise RuntimeError(f"unsafe plugin source directory: {source}")
    collected: list[tuple[str, bytes, int]] = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(
            part in SKIP_NAMES or part.endswith(".pyc")
            for part in relative.parts
        ):
            continue
        if path.is_symlink():
            raise RuntimeError(f"plugin source symlink is not allowed: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(f"unsupported plugin source entry: {path}")
        mode = 0o755 if stat.S_IMODE(path.stat().st_mode) & 0o111 else 0o644
        collected.append(
            ((Path(prefix) / relative).as_posix(), path.read_bytes(), mode)
        )
    return collected


def _adapt_skill_files(
    files: list[tuple[str, bytes, int]],
) -> list[tuple[str, bytes, int]]:
    """Rewrite source-checkout paths to resources bundled in the plugin."""
    adapted: list[tuple[str, bytes, int]] = []
    for relative, content, mode in files:
        path = Path(relative)
        if path.name != "SKILL.md" or len(path.parts) < 3:
            adapted.append((relative, content, mode))
            continue
        skill_name = path.parts[1]
        text = content.decode("utf-8")
        skill_root = f"${{extensionPath}}/skills/{skill_name}"
        text = text.replace("${CLAUDE_SKILL_DIR}", skill_root)
        if skill_name == "persona":
            installed_personas = (
                "~/.claude/skills/persona/../../../app/personas/"
            )
            text = text.replace(
                installed_personas,
                "${extensionPath}/resources/personas/",
            )
            text = text.replace(
                "app/personas/",
                "${extensionPath}/resources/personas/",
            )
        elif skill_name == "docs":
            text = text.replace(
                "app/skills/documentation-standards/SKILL.md",
                "${extensionPath}/skills/documentation-standards/SKILL.md",
            )
        elif skill_name == "briefing":
            text = text.replace(
                "scripts/session_token_stats.py",
                "${extensionPath}/skills/briefing/scripts/"
                "session_token_stats.py",
            )
        elif skill_name == "skill-audit":
            text = text.replace(
                "scripts/audit_skills.py",
                "${extensionPath}/scripts/audit_skills.py",
            )
        adapted.append((relative, text.encode("utf-8"), mode))
    return adapted


def _plugin_audit_helper_content(source: Path) -> bytes:
    """Adapt the security auditor to the native plugin directory layout."""
    text = source.read_text(encoding="utf-8")
    replacements = {
        'skills = toolkit_root / "app" / "skills"': (
            'skills = toolkit_root / "skills"'
        ),
        'skills = app / "skills"': 'skills = toolkit_root / "skills"',
        'agents = app / "agents"': 'agents = toolkit_root / "agents"',
        'agents.glob("*.md")': 'agents.glob("*/agent.md")',
    }
    for original, replacement in replacements.items():
        if text.count(original) != 1:
            raise RuntimeError(
                f"audit_skills.py layout marker changed: {original}"
            )
        text = text.replace(original, replacement, 1)
    return text.encode("utf-8")


def _plugin_agent_text(rendered: str) -> str:
    """Point agent runtime commands at resources inside this plugin."""
    return rendered.replace(
        "${SKILL_DIR}/cve-scan/scripts/cve_scan.py",
        "${extensionPath}/skills/cve-scan/scripts/cve_scan.py",
    ).replace(
        "app/skills/cve-scan/scripts/cve_scan.py",
        "${extensionPath}/skills/cve-scan/scripts/cve_scan.py",
    )


def _plugin_files() -> list[tuple[str, bytes, int]]:
    """Build the complete package in memory before touching the destination."""
    files: list[tuple[str, bytes, int]] = [
        ("plugin.json", render_manifest().encode(), 0o644),
        (
            "hooks.json",
            (
                json.dumps(
                    build_document(PLUGIN_HOOK_COMMAND),
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            ).encode(),
            0o644,
        ),
        (f"runtime/{RUNTIME_NAME}", RUNTIME_SOURCE.encode(), 0o755),
    ]
    for filename, builder in sorted(STANDARD_RULES.items()):
        files.append((f"rules/{filename}", builder().encode(), 0o644))
    files.extend(
        _adapt_skill_files(_collect_tree(APP_DIR / "skills", "skills"))
    )
    files.extend(_collect_tree(APP_DIR / "personas", "resources/personas"))
    token_stats = TOOLKIT_DIR / "scripts" / "session_token_stats.py"
    if token_stats.is_symlink() or not token_stats.is_file():
        raise RuntimeError("briefing runtime source must be a regular file")
    files.append(
        (
            "skills/briefing/scripts/session_token_stats.py",
            token_stats.read_bytes(),
            0o755,
        )
    )
    for script_name in PLUGIN_SCRIPT_NAMES:
        source = TOOLKIT_DIR / "scripts" / script_name
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"unsafe plugin script source: {source}")
        content = (
            _plugin_audit_helper_content(source)
            if script_name == "audit_skills.py"
            else source.read_bytes()
        )
        mode = 0o755 if script_name == "audit_skills.py" else 0o644
        files.append((f"scripts/{script_name}", content, mode))
    for source in sorted(agents_dir.glob("*.md")):
        name, rendered = render_agent(source)
        files.append(
            (
                f"agents/ai-toolkit-{name}/agent.md",
                _plugin_agent_text(rendered).encode(),
                0o644,
            )
        )
    license_path = TOOLKIT_DIR / "LICENSE"
    if license_path.is_symlink() or not license_path.is_file():
        raise RuntimeError("plugin LICENSE source must be a regular file")
    files.append(("LICENSE", license_path.read_bytes(), 0o644))
    names = [name for name, _, _ in files]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate Antigravity plugin resource")
    return sorted(files, key=lambda item: item[0])


def _zip_bytes(files: list[tuple[str, bytes, int]]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for relative, content, mode in files:
            info = zipfile.ZipInfo(f"{PLUGIN_NAME}/{relative}", FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | mode) << 16
            archive.writestr(info, content)
    return output.getvalue()


def _assert_safe_output(output: Path) -> None:
    current = Path(output.anchor)
    for part in output.parts[1:-1]:
        current /= part
        if current.is_symlink():
            raise RuntimeError(f"refusing symlinked output ancestor: {current}")
        if current.exists() and not current.is_dir():
            raise RuntimeError(f"refusing non-directory output ancestor: {current}")
    if output.is_symlink() or (output.exists() and not output.is_file()):
        raise RuntimeError(f"refusing unsafe plugin output: {output}")


def _normalize_macos_var_alias(output: Path) -> Path:
    """Use macOS' real ``/private/var`` path without blessing other symlinks."""
    var_root = Path("/var")
    if (
        output.parts[:2] == ("/", "var")
        and var_root.is_symlink()
        and var_root.resolve() == Path("/private/var")
    ):
        return Path("/private/var", *output.parts[2:])
    return output


def export(output: str | os.PathLike[str]) -> Path:
    """Create a deterministic ZIP with transactional destination replacement."""
    destination_path = _normalize_macos_var_alias(lexical_absolute(output))
    _assert_safe_output(destination_path)
    archive = _zip_bytes(_plugin_files())
    if os.environ.get("AI_TOOLKIT_ANTIGRAVITY_PLUGIN_INJECT_FAILURE") == "1":
        raise RuntimeError("injected Antigravity plugin export failure")
    destination = SecureDestination(
        destination_path,
        Path(destination_path.anchor),
        "Antigravity plugin archive",
    )
    run_secure_transaction(
        [destination],
        lambda transaction: transaction.atomic_write(
            destination, archive, 0o644
        ),
    )
    return destination_path


def _safe_zip_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = archive.infolist()
    names = [member.filename for member in members]
    if len(names) != len(set(names)):
        raise ValueError("plugin archive contains duplicate entries")
    for member in members:
        path = Path(member.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"plugin archive path traversal: {member.filename}")
        mode = member.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
            raise ValueError(f"plugin archive special entry: {member.filename}")
        if stat.S_ISLNK(mode):
            raise ValueError(f"plugin archive symlink: {member.filename}")
        permissions = stat.S_IMODE(mode)
        if permissions & 0o022:
            raise ValueError(f"plugin archive unsafe mode: {member.filename}")
    return members


def _extract_archive(archive_path: Path, destination: Path) -> Path:
    with zipfile.ZipFile(archive_path) as archive:
        members = _safe_zip_members(archive)
        for member in members:
            relative = Path(member.filename)
            target = destination / relative
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
            mode = stat.S_IMODE(member.external_attr >> 16) or 0o644
            target.chmod(mode)
    return destination / PLUGIN_NAME


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        errors.append(f"missing regular {label}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"invalid {label}: {error}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must contain an object")
        return None
    return value


def validate_plugin(plugin_dir: Path) -> list[str]:
    """Return structural, schema, safety, and self-containment errors."""
    errors: list[str] = []
    if plugin_dir.is_symlink() or not plugin_dir.is_dir():
        return ["plugin root must be a regular directory"]
    for path in sorted(plugin_dir.rglob("*")):
        relative = path.relative_to(plugin_dir)
        if path.is_symlink():
            errors.append(f"plugin contains a symlink: {relative}")
            continue
        mode = stat.S_IMODE(path.stat().st_mode)
        if mode & 0o022:
            errors.append(f"plugin contains unsafe mode: {relative}")
        if not path.is_dir() and not path.is_file():
            errors.append(f"plugin contains a special entry: {relative}")

    manifest = _load_json(plugin_dir / "plugin.json", "plugin.json", errors)
    expected_manifest = json.loads(render_manifest())
    if manifest is not None and manifest != expected_manifest:
        errors.append("plugin.json differs from the exact official schema")

    hooks = _load_json(plugin_dir / "hooks.json", "hooks.json", errors)
    expected_hooks = build_document(PLUGIN_HOOK_COMMAND)
    if hooks is not None:
        try:
            validate_document(hooks, PLUGIN_HOOK_COMMAND)
        except ValueError as error:
            errors.append(str(error))
        if hooks != expected_hooks:
            errors.append("plugin hooks differ from the canonical definition")

    required = {
        "runtime": f"runtime/{RUNTIME_NAME}",
        "LICENSE": "LICENSE",
        "persona resource": "resources/personas/backend-lead.md",
        "briefing runtime": "skills/briefing/scripts/session_token_stats.py",
        "skill audit runtime": "scripts/audit_skills.py",
    }
    for label, relative in required.items():
        path = plugin_dir / relative
        if path.is_symlink() or not path.is_file():
            errors.append(f"plugin {label} is missing")
    runtime = plugin_dir / "runtime" / RUNTIME_NAME
    if runtime.is_file() and not runtime.stat().st_mode & stat.S_IXUSR:
        errors.append("plugin hook runtime must be executable")

    for directory, required_file in (
        ("rules", None),
        ("skills", "SKILL.md"),
        ("agents", "agent.md"),
    ):
        root = plugin_dir / directory
        if root.is_symlink() or not root.is_dir():
            errors.append(f"plugin {directory} directory is missing")
            continue
        files = list(root.rglob(required_file or "*.md"))
        if not files:
            errors.append(f"plugin {directory} directory is empty")

    for path in sorted(plugin_dir.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if ABSOLUTE_HOST_PATH.search(text):
            errors.append(
                "plugin contains an absolute host path: "
                f"{path.relative_to(plugin_dir)}"
            )
        if str(TOOLKIT_DIR) in text:
            errors.append(
                "plugin contains a source-root reference: "
                f"{path.relative_to(plugin_dir)}"
            )
        if "${CLAUDE_SKILL_DIR}" in text:
            errors.append(
                "plugin contains a Claude-only skill path: "
                f"{path.relative_to(plugin_dir)}"
            )
    return errors


def verify(source: str | os.PathLike[str]) -> bool:
    path = lexical_absolute(source)
    if path.is_symlink():
        raise ValueError(f"refusing symlinked plugin input: {path}")
    if path.is_dir():
        errors = validate_plugin(path)
    elif path.is_file():
        with tempfile.TemporaryDirectory(prefix="ai-toolkit-antigravity-verify-") as tmp:
            staged = _extract_archive(path, Path(tmp))
            errors = validate_plugin(staged)
    else:
        raise FileNotFoundError(path)
    if errors:
        raise ValueError("; ".join(errors))
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    export_parser = subparsers.add_parser("export", help="build plugin ZIP")
    export_parser.add_argument("output_path", nargs="?")
    export_parser.add_argument(
        "--output", dest="output_option", default=None
    )
    verify_parser = subparsers.add_parser("verify", help="verify archive or directory")
    verify_parser.add_argument("source")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.action == "export":
            output = (
                args.output_option
                or args.output_path
                or "ai-toolkit-antigravity-plugin.zip"
            )
            path = export(output)
            print(f"Created: {path}")
            print("Install under .agents/plugins/ or ~/.gemini/config/plugins/.")
        else:
            verify(args.source)
            print("Antigravity plugin validation passed")
        return 0
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
