#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate native OpenCode Agent Skills directories.

OpenCode discovers project skills under ``.opencode/skills/<name>/SKILL.md``.
This generator copies each complete ai-toolkit skill so its scripts,
references, templates, and other relative resources remain available.
"""
from __future__ import annotations

import json
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_skill_adapter import build_opencode_skill_text
from emission import skills_dir
from frontmatter import frontmatter_block, frontmatter_field, frontmatter_sections
from secure_fs import SecureDestination, SecureTransaction, nearest_existing_root


PORTABLE_FRONTMATTER = ("license", "compatibility")
SAFE_SKILL_NAME = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MANAGED_MARKER = "<!-- ai-toolkit-managed: opencode-skill -->"
MANAGED_MANIFEST = ".ai-toolkit-managed-files"
IGNORED_PARTS = frozenset({"__pycache__", ".DS_Store"})


@dataclass(frozen=True)
class PreparedSkill:
    name: str
    markdown: str
    files: dict[Path, tuple[bytes, int]]

    @property
    def managed_paths(self) -> set[Path]:
        return {Path("SKILL.md"), Path(MANAGED_MANIFEST), *self.files}


def _portable_body(skill_file: Path) -> str:
    rendered = build_opencode_skill_text(skill_file)
    if not rendered.startswith("---\n"):
        return rendered.rstrip()
    parts = rendered.split("---", 2)
    return (parts[2] if len(parts) == 3 else rendered).lstrip("\n").rstrip()


def _render_skill(skill_file: Path) -> str:
    name = frontmatter_field(skill_file, "name")
    description = frontmatter_field(skill_file, "description")
    sections = frontmatter_sections(frontmatter_block(skill_file))
    lines = [
        "---",
        f"name: {name}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
    ]
    for key in PORTABLE_FRONTMATTER:
        lines.extend(sections.get(key, []))
    if frontmatter_field(skill_file, "user-invocable").lower() == "false":
        lines.append("slash: false")
    metadata = list(sections.get("metadata", []))
    disable_model = (
        frontmatter_field(skill_file, "disable-model-invocation").lower()
        == "true"
    )
    if metadata or disable_model:
        if not metadata or metadata == ["metadata: {}"]:
            metadata = ["metadata:"]
        if disable_model and not any(
            line.strip().startswith("opencode/autoinvoke:") for line in metadata[1:]
        ):
            metadata.append("  opencode/autoinvoke: false")
        lines.extend(metadata)
    lines.extend(("---", "", MANAGED_MARKER, "", _portable_body(skill_file), ""))
    return "\n".join(lines)


def _is_managed_skill(path: Path) -> bool:
    skill_file = path / "SKILL.md"
    if path.is_symlink() or not path.is_dir() or skill_file.is_symlink():
        return False
    try:
        return MANAGED_MARKER in skill_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False


def _managed_paths(path: Path) -> set[Path] | None:
    manifest = path / MANAGED_MANIFEST
    if manifest.is_symlink() or not manifest.is_file():
        return None
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return None
    paths = {Path(item) for item in value}
    if any(item.is_absolute() or ".." in item.parts for item in paths):
        return None
    return paths | {Path(MANAGED_MANIFEST)}


def _managed_directories(managed: set[Path]) -> set[Path]:
    directories: set[Path] = set()
    for relative in managed:
        parent = relative.parent
        while parent != Path("."):
            directories.add(parent)
            parent = parent.parent
    return directories


def _has_user_extras(path: Path) -> bool:
    managed = _managed_paths(path)
    if managed is None:
        return True
    managed_directories = _managed_directories(managed)
    for item in path.rglob("*"):
        if item.is_symlink():
            return True
        relative = item.relative_to(path)
        if item.is_dir() and relative not in managed_directories:
            return True
        if item.is_file() and relative not in managed:
            return True
    return False


def _source_skills(source_root: Path) -> list[Path]:
    return [
        entry
        for entry in sorted(source_root.iterdir())
        if entry.is_dir()
        and not entry.name.startswith((".", "_"))
        and (entry / "SKILL.md").is_file()
    ]


def _is_ignored(relative: Path) -> bool:
    return bool(IGNORED_PARTS.intersection(relative.parts)) or relative.suffix in {
        ".pyc",
        ".pyo",
    }


def _source_files(source: Path) -> dict[Path, tuple[bytes, int]]:
    files: dict[Path, tuple[bytes, int]] = {}
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if _is_ignored(relative) or path.is_dir():
            continue
        if not path.is_file():
            raise RuntimeError(f"Unsupported OpenCode skill source: {path}")
        if relative == Path("SKILL.md"):
            continue
        mode = stat.S_IMODE(path.stat().st_mode) or 0o644
        files[relative] = (path.read_bytes(), mode)
    return files


def _prepare_sources(source_root: Path) -> list[PreparedSkill]:
    """Validate every source and render all SKILL.md files before writes."""
    if source_root.is_symlink() or not source_root.is_dir():
        raise RuntimeError(f"Invalid OpenCode skill source root: {source_root}")
    for path in sorted(source_root.rglob("*")):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked OpenCode skill source: {path}")
        if not path.is_dir() and not path.is_file():
            raise RuntimeError(f"Unsupported OpenCode skill source: {path}")

    prepared: list[PreparedSkill] = []
    names: set[str] = set()
    for source in _source_skills(source_root):
        skill_file = source / "SKILL.md"
        name = frontmatter_field(skill_file, "name")
        description = frontmatter_field(skill_file, "description")
        if len(name) > 64 or not SAFE_SKILL_NAME.fullmatch(name):
            raise ValueError(f"Invalid OpenCode skill name: {skill_file}")
        if not description or len(description) > 1024:
            raise ValueError(f"Invalid OpenCode skill description: {skill_file}")
        if name in names:
            raise ValueError(f"Duplicate OpenCode skill name: {name}")
        names.add(name)
        prepared.append(
            PreparedSkill(
                name=name,
                markdown=_render_skill(skill_file),
                files=_source_files(source),
            )
        )
    return prepared


def _assert_destination_roots(
    target_dir: Path, base: Path, destination_root: Path
) -> None:
    for path in (target_dir, base, destination_root):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked OpenCode destination: {path}")
        if path.exists() and not path.is_dir():
            raise RuntimeError(f"OpenCode destination is not a directory: {path}")


def _destination_transaction(
    target_dir: Path,
    base: Path,
    destination_root: Path,
) -> tuple[SecureTransaction, SecureDestination, SecureDestination, Path]:
    """Pin the base and skills roots for the complete operation."""
    trusted_root = nearest_existing_root(target_dir)
    base_probe = SecureDestination(
        base / MANAGED_MANIFEST,
        trusted_root,
        "OpenCode configuration ancestry",
    )
    skills_probe = SecureDestination(
        destination_root / MANAGED_MANIFEST,
        trusted_root,
        "OpenCode skills ancestry",
    )
    return (
        SecureTransaction([base_probe, skills_probe]),
        base_probe,
        skills_probe,
        trusted_root,
    )


def _user_extra_files(path: Path, managed: set[Path]) -> set[Path]:
    files: set[Path] = set()
    for item in sorted(path.rglob("*")):
        relative = item.relative_to(path)
        if item.is_symlink():
            raise RuntimeError(f"Refusing symlinked OpenCode destination: {item}")
        if item.is_dir():
            continue
        if not item.is_file():
            raise RuntimeError(f"Unsupported OpenCode destination entry: {item}")
        if relative in managed:
            continue
        files.add(relative)
    return files


def _user_skill_names(destination_root: Path) -> set[str]:
    if not destination_root.is_dir():
        return set()
    names: set[str] = set()
    for path in sorted(destination_root.iterdir()):
        if path.is_symlink():
            raise RuntimeError(f"Refusing symlinked OpenCode skill destination: {path}")
        if not path.is_dir() or _is_managed_skill(path):
            continue
        skill_file = path / "SKILL.md"
        if skill_file.is_symlink():
            raise RuntimeError(f"Refusing symlinked OpenCode skill destination: {skill_file}")
        if not skill_file.is_file():
            continue
        name = frontmatter_field(skill_file, "name")
        if name:
            names.add(name)
    return names


def _skill_writes(
    destination_root: Path,
    skill: PreparedSkill,
) -> dict[Path, tuple[bytes, int]]:
    skill_root = destination_root / skill.name
    writes = {
        skill_root / relative: value
        for relative, value in skill.files.items()
    }
    writes[skill_root / "SKILL.md"] = (skill.markdown.encode(), 0o644)
    manifest = (
        json.dumps(
            sorted(path.as_posix() for path in skill.managed_paths),
            indent=2,
        )
        + "\n"
    ).encode()
    writes[skill_root / MANAGED_MANIFEST] = (manifest, 0o644)
    return writes


def _secure_file_mutations(
    writes: dict[Path, tuple[bytes, int]],
    removals: set[Path],
    *,
    trusted_root: Path,
    ancestry: SecureTransaction,
    skills_probe: SecureDestination,
    prune: set[Path],
) -> None:
    mutation_paths = set(writes) | removals
    destinations = {
        path: SecureDestination(path, trusted_root, f"OpenCode skill file {path.name}")
        for path in mutation_paths
    }
    transaction = SecureTransaction(list(destinations.values()))
    try:
        transaction.materialize_parents()
        for path, (content, mode) in sorted(writes.items()):
            transaction.atomic_write(destinations[path], content, mode)
        for path in sorted(removals - set(writes), reverse=True):
            transaction.unlink(destinations[path])
        for relative in sorted(prune, key=lambda item: len(item.parts), reverse=True):
            ancestry.rmdir_empty(skills_probe, relative)
    except BaseException as error:
        try:
            transaction.rollback()
        except Exception as rollback_error:
            raise RuntimeError(
                "OpenCode skill mutation failed and rollback was incomplete: "
                f"{rollback_error}"
            ) from error
        raise
    finally:
        transaction.close()


def _rollback_ancestry(
    transaction: SecureTransaction,
    error: BaseException,
) -> None:
    try:
        transaction.rollback()
    except Exception as rollback_error:
        raise RuntimeError(
            "OpenCode ancestry rollback was incomplete: "
            f"{rollback_error}"
        ) from error


def cleanup(
    target_dir: Path,
    config_root: Path | None = None,
) -> tuple[int, int]:
    """Remove native managed skills and return ``(removed, preserved)``."""
    base = config_root if config_root is not None else target_dir / ".opencode"
    destination_root = base / "skills"
    ancestry, base_probe, skills_probe, trusted_root = _destination_transaction(
        target_dir,
        base,
        destination_root,
    )
    try:
        _assert_destination_roots(target_dir, base, destination_root)
        if not destination_root.is_dir():
            return 0, 0
        ancestry.materialize_parents()
        removals: set[Path] = set()
        prune: set[Path] = set()
        removed = 0
        preserved = 0
        for path in sorted(destination_root.iterdir()):
            managed = _managed_paths(path)
            if managed is None or not _is_managed_skill(path):
                if path.is_dir() or path.is_symlink():
                    preserved += 1
                continue
            if any(item.is_symlink() for item in path.rglob("*")):
                preserved += 1
                continue
            removed += 1
            removals.update(path / relative for relative in managed)
            prune.update(
                Path(path.name) / relative
                for relative in _managed_directories(managed)
            )
            prune.add(Path(path.name))
        if removals:
            _secure_file_mutations(
                {},
                removals,
                trusted_root=trusted_root,
                ancestry=ancestry,
                skills_probe=skills_probe,
                prune=prune,
            )
        ancestry.rmdir_empty(base_probe, Path("skills"))
        return removed, preserved
    except BaseException as error:
        _rollback_ancestry(ancestry, error)
        raise
    finally:
        ancestry.close()


def discover(
    target_dir: Path,
    config_root: Path | None = None,
) -> int:
    """Return the number of native toolkit-managed OpenCode skills."""
    base = config_root if config_root is not None else target_dir / ".opencode"
    destination_root = base / "skills"
    ancestry, _, _, _ = _destination_transaction(
        target_dir,
        base,
        destination_root,
    )
    try:
        _assert_destination_roots(target_dir, base, destination_root)
        if not destination_root.is_dir():
            return 0
        return sum(
            1 for path in destination_root.iterdir() if _is_managed_skill(path)
        )
    finally:
        ancestry.close()


def generate(
    target_dir: Path,
    config_root: Path | None = None,
    source_root: Path = skills_dir,
) -> tuple[int, int, int]:
    """Copy skills and return ``(written, removed_stale, preserved)``."""
    prepared = _prepare_sources(source_root)
    base = config_root if config_root is not None else target_dir / ".opencode"
    destination_root = base / "skills"
    ancestry, _, skills_probe, trusted_root = _destination_transaction(
        target_dir,
        base,
        destination_root,
    )
    try:
        ancestry.materialize_parents()
        _assert_destination_roots(target_dir, base, destination_root)
        user_names = _user_skill_names(destination_root)
        preserved = 0
        expected: set[str] = set()
        writes: dict[Path, tuple[bytes, int]] = {}
        removals: set[Path] = set()
        prune: set[Path] = set()
        for skill in prepared:
            destination = destination_root / skill.name
            if skill.name in user_names:
                preserved += 1
                continue
            if (
                destination.exists() or destination.is_symlink()
            ) and not _is_managed_skill(destination):
                preserved += 1
                continue
            managed: set[Path] = set()
            extras: set[Path] = set()
            if destination.exists():
                managed = _managed_paths(destination)
                if managed is None:
                    preserved += 1
                    continue
                extras = _user_extra_files(destination, managed)
            collisions = skill.managed_paths.intersection(extras)
            if collisions:
                joined = ", ".join(sorted(path.as_posix() for path in collisions))
                raise RuntimeError(
                    "OpenCode skill update would overwrite user-owned files: "
                    f"{joined}"
                )
            writes.update(_skill_writes(destination_root, skill))
            removals.update(
                destination / relative
                for relative in managed - skill.managed_paths
            )
            prune.update(
                Path(skill.name) / relative
                for relative in _managed_directories(managed)
            )
            expected.add(skill.name)

        stale = 0
        for path in sorted(destination_root.iterdir()):
            if path.name.startswith(".ai-toolkit-") or path.name in expected:
                continue
            if not _is_managed_skill(path):
                continue
            if _has_user_extras(path):
                preserved += 1
                continue
            managed = _managed_paths(path)
            if managed is None:
                preserved += 1
                continue
            stale += 1
            removals.update(path / relative for relative in managed)
            prune.update(
                Path(path.name) / relative
                for relative in _managed_directories(managed)
            )
            prune.add(Path(path.name))

        _secure_file_mutations(
            writes,
            removals,
            trusted_root=trusted_root,
            ancestry=ancestry,
            skills_probe=skills_probe,
            prune=prune,
        )
        return len(expected), stale, preserved
    except BaseException as error:
        _rollback_ancestry(ancestry, error)
        raise
    finally:
        ancestry.close()


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed, preserved = generate(target)
    print(
        f"Generated: .opencode/skills/ ({written} skills, "
        f"{removed} stale removed, {preserved} preserved)"
    )


if __name__ == "__main__":
    main()
