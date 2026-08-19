#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Build and verify the native ai-toolkit plugin for Codex.

Usage:
    codex_plugin.py export [--output FILE]
    codex_plugin.py verify
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from codex_skill_adapter import build_codex_skill_text
from generate_codex_hooks import (
    CODEX_HOOKS,
    _asset_names,
    _managed_asset_content,
    validate_hooks_document,
)
from secure_fs import SecureDestination, lexical_absolute, run_secure_transaction


TOOLKIT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = TOOLKIT_DIR / "app"
PLUGIN_NAME = "ai-toolkit"
FIXED_ZIP_TIME = (2026, 1, 1, 0, 0, 0)
SKIP_NAMES = frozenset({"__pycache__", ".DS_Store"})
_TASK_ONLY_FRONTMATTER_RE = re.compile(
    r"^(?:disable-model-invocation|disable_model_invocation):\s*true\s*$\n?",
    re.MULTILINE,
)
_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_PLUGIN_ASSET_RE = re.compile(r"\$\{PLUGIN_ROOT\}/hooks/([A-Za-z0-9._-]+)")
_SKILL_TEXT_REWRITES = {
    "briefing": (
        ("scripts/session_token_stats.py", "./scripts/session_token_stats.py"),
        (
            "app/hooks/ai-toolkit-statusline.sh",
            "the core-install statusline hook",
        ),
    ),
    "docs": (
        (
            "app/skills/documentation-standards/SKILL.md",
            "../documentation-standards/SKILL.md",
        ),
    ),
    "persona": (
        (
            "If file not found, try the installed location: "
            "`~/.claude/skills/persona/../../../app/personas/{name}.md`",
            "If the file is missing, report the available filenames from "
            "`./personas/`; do not search global paths",
        ),
        (
            "relative to the toolkit root. When the toolkit is globally "
            "installed, that root is at "
            "`~/.claude/skills/persona/../../../app/personas/` — fallback "
            "paths matter.",
            "relative to this installed skill directory.",
        ),
        (
            "(relative to toolkit root)",
            "(relative to this installed skill directory)",
        ),
        (
            "~/.claude/skills/persona/../../../app/personas/",
            "./personas/",
        ),
        ("app/personas/", "./personas/"),
    ),
}
_SKILL_RESOURCE_SOURCES = {
    "briefing": (
        (
            TOOLKIT_DIR / "scripts" / "session_token_stats.py",
            Path("scripts/session_token_stats.py"),
        ),
    ),
    "persona": ((APP_DIR / "personas", Path("personas")),),
}
# Full-catalog audit: source-workspace paths in authoring/audit skills operate on
# the user's current checkout. These are the package-owned cross-resource paths
# that must resolve inside the exported plugin itself.
_SKILL_RUNTIME_REFERENCES = {
    "briefing": ("scripts/session_token_stats.py",),
    "docs": ("../documentation-standards/SKILL.md",),
    "persona": (
        "personas/backend-lead.md",
        "personas/devops-eng.md",
        "personas/frontend-lead.md",
        "personas/junior-dev.md",
    ),
}


def _package_metadata() -> dict[str, Any]:
    payload = json.loads((TOOLKIT_DIR / "package.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("package.json must contain an object")
    return payload


def _repository_url(package: dict[str, Any]) -> str:
    repository = package.get("repository")
    if isinstance(repository, dict):
        repository = repository.get("url")
    if not isinstance(repository, str) or not repository:
        raise ValueError("package.json repository URL is required")
    return repository.removeprefix("git+").removesuffix(".git")


def render_manifest() -> str:
    """Render stable plugin metadata from package.json."""
    package = _package_metadata()
    homepage = package.get("homepage")
    version = package.get("version")
    license_name = package.get("license")
    if not isinstance(homepage, str) or not homepage.startswith("https://"):
        raise ValueError("package.json homepage must be an HTTPS URL")
    if not isinstance(version, str) or not version:
        raise ValueError("package.json version is required")
    if not isinstance(license_name, str) or not license_name:
        raise ValueError("package.json license is required")

    manifest = {
        "name": PLUGIN_NAME,
        "version": version,
        "description": (
            "AI engineering skills and lifecycle guardrails for Codex CLI."
        ),
        "author": {
            "name": "SoftSpark",
            "email": "biuro@softspark.eu",
            "url": "https://github.com/softspark",
        },
        "homepage": homepage,
        "repository": _repository_url(package),
        "license": license_name,
        "keywords": [
            "ai-toolkit",
            "codex",
            "developer-tools",
            "skills",
            "hooks",
        ],
        "skills": "./skills/",
        "interface": {
            "displayName": "AI Toolkit",
            "shortDescription": "Engineering skills and lifecycle guardrails",
            "longDescription": (
                "Use AI Toolkit workflows for implementation, testing, review, "
                "security, architecture, and delivery in Codex CLI."
            ),
            "developerName": "SoftSpark",
            "category": "Developer Tools",
            "capabilities": ["Skills", "Lifecycle hooks", "Developer workflows"],
            "websiteURL": homepage,
            "defaultPrompt": [
                "Use AI Toolkit to implement this change with tests.",
                "Review this code with the relevant AI Toolkit skills.",
                "Verify this repository before claiming the task is complete.",
            ],
            "brandColor": "#2563EB",
        },
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def _plugin_skill_text(source: Path) -> str:
    """Render a Codex-adapted skill accepted by plugin ingestion."""
    rendered = build_codex_skill_text(source)
    rendered = _TASK_ONLY_FRONTMATTER_RE.sub("", rendered)
    for source_path, plugin_path in _SKILL_TEXT_REWRITES.get(
        source.parent.name,
        (),
    ):
        rendered = rendered.replace(source_path, plugin_path)
    return rendered


def _copy_file_strict(source: Path, destination: Path) -> None:
    """Copy one regular source file without following links."""
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"unsafe source file: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())
    os.chmod(destination, stat.S_IMODE(source.stat().st_mode))


def _copy_tree_strict(source: Path, destination: Path) -> None:
    """Copy a source tree while rejecting links and non-regular entries."""
    if source.is_symlink() or not source.is_dir():
        raise ValueError(f"unsafe source directory: {source}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(
            part in SKIP_NAMES or part.endswith(".pyc")
            for part in relative.parts
        ):
            continue
        if path.is_symlink():
            raise ValueError(f"source symlink is not allowed: {path}")
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif path.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            os.chmod(target, stat.S_IMODE(path.stat().st_mode))
        else:
            raise ValueError(f"unsupported source entry: {path}")


def _stage_skills(destination: Path) -> None:
    skills_source = APP_DIR / "skills"
    for skill_dir in sorted(skills_source.iterdir()):
        if skill_dir.name.startswith((".", "_")) or not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_symlink() or not skill_file.is_file():
            raise ValueError(f"invalid skill source: {skill_file}")
        target = destination / skill_dir.name
        _copy_tree_strict(skill_dir, target)
        (target / "SKILL.md").write_text(
            _plugin_skill_text(skill_file),
            encoding="utf-8",
        )
        for source, relative_target in _SKILL_RESOURCE_SOURCES.get(
            skill_dir.name,
            (),
        ):
            destination_path = target / relative_target
            if source.is_dir() and not source.is_symlink():
                _copy_tree_strict(source, destination_path)
            else:
                _copy_file_strict(source, destination_path)


def build_plugin_hooks() -> dict[str, Any]:
    """Build native command hooks rooted inside the installed plugin."""
    hooks: dict[str, list[dict[str, Any]]] = {}
    for event, entries in CODEX_HOOKS.items():
        groups: list[dict[str, Any]] = []
        for matcher, script in entries:
            handler: dict[str, Any] = {
                "type": "command",
                "command": (
                    "AI_TOOLKIT_HOOK_QUIET=1 "
                    "AI_TOOLKIT_HOOK_OWNER=ai-toolkit "
                    f'"${{PLUGIN_ROOT}}/hooks/{script}"'
                ),
            }
            if event == "SessionEnd":
                handler["timeout"] = 3
            group: dict[str, Any] = {"hooks": [handler]}
            if matcher:
                group["matcher"] = matcher
            groups.append(group)
        hooks[event] = groups
    document = {"hooks": hooks}
    validate_hooks_document(document)
    return document


def stage_plugin(destination: Path) -> None:
    """Create a self-contained native Codex plugin tree."""
    if destination.is_symlink():
        raise ValueError(f"refusing symlinked staging directory: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    manifest_path = destination / ".codex-plugin" / "plugin.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(render_manifest(), encoding="utf-8")

    _stage_skills(destination / "skills")

    hooks_dir = destination / "hooks"
    hooks_dir.mkdir()
    hooks_document = build_plugin_hooks()
    (hooks_dir / "hooks.json").write_text(
        json.dumps(hooks_document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for name in sorted(_asset_names()):
        asset = hooks_dir / name
        asset.write_bytes(_managed_asset_content(name))
        os.chmod(asset, 0o755)

    license_source = TOOLKIT_DIR / "LICENSE"
    if license_source.is_symlink() or not license_source.is_file():
        raise ValueError("LICENSE must be a regular source file")
    (destination / "LICENSE").write_bytes(license_source.read_bytes())
    _copy_file_strict(
        APP_DIR / "constitution.md",
        destination / "constitution.md",
    )


def _load_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if path.is_symlink() or not path.is_file():
        errors.append(f"missing regular {label}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"invalid {label}: {error}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain an object")
        return None
    return payload


def _validate_manifest(plugin_dir: Path, errors: list[str]) -> None:
    manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
    manifest = _load_json_object(manifest_path, "plugin manifest", errors)
    if manifest is None:
        return
    extra_manifest_files = [
        path
        for path in (plugin_dir / ".codex-plugin").iterdir()
        if path.name != "plugin.json"
    ]
    if extra_manifest_files:
        errors.append("only plugin.json may appear in .codex-plugin")

    allowed = {
        "name",
        "version",
        "description",
        "author",
        "homepage",
        "repository",
        "license",
        "keywords",
        "skills",
        "interface",
    }
    unknown = sorted(set(manifest) - allowed)
    if unknown:
        errors.append(f"unsupported plugin manifest fields: {unknown}")
    if "hooks" in manifest:
        errors.append("plugin manifest must rely on default hooks/hooks.json discovery")
    if manifest.get("name") != PLUGIN_NAME:
        errors.append(f"plugin manifest name must be {PLUGIN_NAME}")
    version = manifest.get("version")
    if not isinstance(version, str) or _SEMVER_RE.fullmatch(version) is None:
        errors.append("plugin manifest version must be strict semver")
    if manifest.get("skills") != "./skills/":
        errors.append("plugin manifest skills must be ./skills/")
    if not (plugin_dir / "skills").is_dir():
        errors.append("plugin skills directory is missing")
    for field in ("description", "homepage", "repository", "license"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"plugin manifest {field} must be a non-empty string")
    author = manifest.get("author")
    if not isinstance(author, dict) or not isinstance(author.get("name"), str):
        errors.append("plugin manifest author.name is required")
    interface = manifest.get("interface")
    required_interface = {
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "capabilities",
        "websiteURL",
        "defaultPrompt",
    }
    if not isinstance(interface, dict):
        errors.append("plugin manifest interface must be an object")
    else:
        missing = sorted(required_interface - set(interface))
        if missing:
            errors.append(f"plugin manifest interface fields are missing: {missing}")


def _validate_skills(plugin_dir: Path, errors: list[str]) -> None:
    skills_dir = plugin_dir / "skills"
    if skills_dir.is_symlink() or not skills_dir.is_dir():
        errors.append("plugin skills must be a regular directory")
        return
    skills = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if not skills:
        errors.append("plugin must contain at least one skill")
    for skill in skills:
        skill_file = skill / "SKILL.md"
        if skill.is_symlink() or skill_file.is_symlink() or not skill_file.is_file():
            errors.append(f"invalid plugin skill: {skill.name}")
            continue
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\nname:" not in text or "\ndescription:" not in text:
            errors.append(f"invalid plugin skill frontmatter: {skill.name}")
        if _TASK_ONLY_FRONTMATTER_RE.search(text):
            errors.append(f"plugin skill disables model invocation: {skill.name}")


def _validate_skill_runtime_dependencies(
    plugin_dir: Path,
    errors: list[str],
) -> None:
    """Check every declared cross-resource dependency in bundled skills."""
    for skill_name, relative_paths in _SKILL_RUNTIME_REFERENCES.items():
        skill_dir = plugin_dir / "skills" / skill_name
        for relative_path in relative_paths:
            resource = skill_dir / relative_path
            if resource.is_symlink() or not resource.is_file():
                errors.append(
                    f"{skill_name} runtime resource is missing: {relative_path}"
                )

        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_symlink() or not skill_file.is_file():
            continue
        text = skill_file.read_text(encoding="utf-8")
        for source_path, _plugin_path in _SKILL_TEXT_REWRITES[skill_name]:
            source_reference = re.compile(
                rf"(?<![./A-Za-z0-9_-]){re.escape(source_path)}"
            )
            if source_reference.search(text):
                errors.append(
                    f"{skill_name} contains a source-root runtime reference: "
                    f"{source_path}"
                )


def _validate_hooks(plugin_dir: Path, errors: list[str]) -> None:
    hooks_path = plugin_dir / "hooks" / "hooks.json"
    hooks = _load_json_object(hooks_path, "hooks/hooks.json", errors)
    if hooks is None:
        return
    try:
        validate_hooks_document(hooks)
    except ValueError as error:
        errors.append(str(error))
        return
    expected_events = set(CODEX_HOOKS)
    actual_events = set(hooks.get("hooks", {}))
    if actual_events != expected_events:
        errors.append(
            f"plugin hook events differ from the wired Codex events: {sorted(actual_events)}"
        )

    referenced: set[str] = set()
    for event, groups in hooks.get("hooks", {}).items():
        for group in groups:
            for handler in group["hooks"]:
                command = handler["command"]
                if any(
                    forbidden in command
                    for forbidden in (
                        "git rev-parse",
                        "CODEX_HOME",
                        ".softspark/ai-toolkit/hooks",
                    )
                ):
                    errors.append(f"plugin {event} command is not self-contained")
                match = _PLUGIN_ASSET_RE.search(command)
                if match is None:
                    errors.append(f"plugin {event} command must use PLUGIN_ROOT")
                    continue
                referenced.add(match.group(1))
                if event == "SessionEnd" and handler.get("timeout", 0) > 3:
                    errors.append("plugin SessionEnd timeout cannot exceed 3 seconds")

    hooks_dir = plugin_dir / "hooks"
    for name in sorted(_asset_names() | referenced):
        asset = hooks_dir / name
        if asset.is_symlink() or not asset.is_file():
            errors.append(f"missing regular plugin hook asset: {name}")
        elif not asset.stat().st_mode & stat.S_IXUSR:
            errors.append(f"plugin hook asset is not executable: {name}")


def validate_staged_plugin(plugin_dir: Path) -> list[str]:
    """Validate plugin structure, schema, paths, and self-containment."""
    errors: list[str] = []
    if plugin_dir.is_symlink() or not plugin_dir.is_dir():
        return ["plugin root must be a regular directory"]
    for path in plugin_dir.rglob("*"):
        if path.is_symlink():
            errors.append(f"plugin contains a symlink: {path.relative_to(plugin_dir)}")
    _validate_manifest(plugin_dir, errors)
    _validate_skills(plugin_dir, errors)
    _validate_skill_runtime_dependencies(plugin_dir, errors)
    _validate_hooks(plugin_dir, errors)
    license_path = plugin_dir / "LICENSE"
    if license_path.is_symlink() or not license_path.is_file():
        errors.append("plugin LICENSE is missing")
    constitution = plugin_dir / "constitution.md"
    if constitution.is_symlink() or not constitution.is_file():
        errors.append("plugin constitution runtime resource is missing")
    return errors


def _shared_validator_path() -> Path | None:
    override = os.environ.get("CODEX_PLUGIN_VALIDATOR")
    candidates = []
    if override:
        candidates.append(Path(override).expanduser())
    candidates.append(
        Path.home()
        / ".codex"
        / "skills"
        / ".system"
        / "plugin-creator"
        / "scripts"
        / "validate_plugin.py"
    )
    for candidate in candidates:
        if not candidate.is_symlink() and candidate.is_file():
            return candidate
    return None


def _run_shared_validator(plugin_dir: Path) -> bool:
    validator = _shared_validator_path()
    if validator is None:
        return True
    result = subprocess.run(
        [sys.executable, str(validator), str(plugin_dir)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stdout.rstrip(), file=sys.stderr)
        print(result.stderr.rstrip(), file=sys.stderr)
        return False
    print("Shared Codex plugin validator passed")
    return True


def verify_plugin() -> bool:
    with tempfile.TemporaryDirectory(prefix="ai-toolkit-codex-plugin-") as tmp:
        staged = Path(tmp) / PLUGIN_NAME
        stage_plugin(staged)
        errors = validate_staged_plugin(staged)
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if errors or not _run_shared_validator(staged):
            return False
    print("Codex plugin validation passed")
    return True


def _archive_file(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    mode = stat.S_IMODE(path.stat().st_mode)
    permissions = 0o755 if mode & 0o111 else 0o644
    info = zipfile.ZipInfo(arcname, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | permissions) << 16
    archive.writestr(info, path.read_bytes())


def _absolute_output(output: Path) -> Path:
    return lexical_absolute(output)


def _assert_no_symlinked_output_ancestors(output: Path) -> None:
    current = Path(output.anchor)
    for part in output.parts[1:-1]:
        current /= part
        if current.is_symlink():
            raise ValueError(f"refusing symlinked output ancestor: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"refusing non-directory output ancestor: {current}")


def _assert_safe_output(output: Path) -> None:
    _assert_no_symlinked_output_ancestors(output)
    if output.exists() and (output.is_symlink() or not output.is_file()):
        raise ValueError(f"refusing unsafe output path: {output}")
    if output.is_symlink():
        raise ValueError(f"refusing symlinked output path: {output}")


def _archive_bytes(staged: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        staged_paths = sorted(
            staged.rglob("*"),
            key=lambda path: path.relative_to(staged).as_posix(),
        )
        for path in staged_paths:
            if path.is_symlink():
                raise ValueError(f"staged symlink is not allowed: {path}")
            if path.is_file():
                _archive_file(
                    archive,
                    path,
                    path.relative_to(staged).as_posix(),
                )
    return buffer.getvalue()


def export_plugin(output: Path) -> bool:
    output = _absolute_output(output)
    _assert_safe_output(output)
    with tempfile.TemporaryDirectory(prefix="ai-toolkit-codex-plugin-") as tmp:
        staged = Path(tmp) / PLUGIN_NAME
        stage_plugin(staged)
        archive_content = _archive_bytes(staged)

    destination = SecureDestination(
        path=output,
        trusted_root=Path(output.anchor),
        label="Codex plugin archive",
    )
    run_secure_transaction(
        [destination],
        lambda transaction: transaction.atomic_write(
            destination,
            archive_content,
            0o644,
        ),
    )

    print(f"Created: {output}")
    print(
        "Next: add the plugin to a local marketplace, install it from /plugins, "
        "then start a new Codex CLI session."
    )
    print("Codex IDE does not support plugins.")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    export = subparsers.add_parser("export", help="build a native Codex plugin ZIP")
    export.add_argument("--output", default="ai-toolkit-codex-plugin.zip")
    subparsers.add_parser("verify", help="validate a clean staged Codex plugin")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.action == "export":
        return 0 if export_plugin(Path(args.output)) else 1
    if args.action == "verify":
        return 0 if verify_plugin() else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
