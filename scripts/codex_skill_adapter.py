# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Adapt ai-toolkit skills for clients sharing ``.agents/skills``.

Compatible skills are symlinked as-is. Skills that rely on Claude-only
delegation primitives are rendered into Codex-specific or portable DSH
wrappers. Generated variants retain shared references and assets while using
guidance appropriate for the selected discovery-surface owners.
"""
from __future__ import annotations

import errno
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

try:
    from frontmatter import frontmatter_field
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from frontmatter import frontmatter_field


CLAUDE_ONLY_TOOLS = frozenset({
    "Agent", "TeamCreate", "TeamDelete", "SendMessage",
    "TaskCreate", "TaskList", "TaskUpdate", "TaskGet", "TaskOutput", "TaskStop",
    "Skill", "EnterPlanMode", "ExitPlanMode",
})

ADAPTED_MARKER = ".ai-toolkit-codex-adapted"
DSH_ADAPTED_MARKER = ".ai-toolkit-dsh-adapted"
SHARED_ADAPTED_MARKER = ".ai-toolkit-shared-adapted"
SKILL_SURFACE_OWNERS_MARKER = ".ai-toolkit-skill-owners"
ADAPTED_MARKERS = frozenset({
    ADAPTED_MARKER,
    DSH_ADAPTED_MARKER,
    SHARED_ADAPTED_MARKER,
})
SKILL_SURFACE_OWNERS = frozenset({"codex", "dsh"})

_FRONTMATTER_RE = re.compile(r"\A---\n(?P<frontmatter>.*?)\n---\n?(?P<body>.*)\Z", re.S)
_AGENT_START_RE = re.compile(r"\bAgent\s*\(")
_TASK_API_RE = re.compile(r"\bTask(?:Create|List|Update|Get|Output|Stop)\b")
_POSITIONAL_ARGUMENT_RE = re.compile(r"\$([1-9])\b")
_PLATFORM_LABELS = {"codex": "Codex", "opencode": "OpenCode"}
_UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS = frozenset({
    errno.EBADF,
    errno.EINVAL,
    getattr(errno, "ENOTSUP", errno.EINVAL),
    getattr(errno, "EOPNOTSUPP", errno.EINVAL),
})
_ADAPTATION_BODY_TOKENS = frozenset({
    "$ARGUMENTS",
    "CLAUDE_SKILL_DIR",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
    "spawn_agent",
    "send_input",
    "wait_agent",
    "close_agent",
    "update_plan",
    "fork_context",
    "agent_type=",
    "TeamCreate",
    "TeamDelete",
    "SendMessage",
})


class _OwnerMarkerState(NamedTuple):
    data: bytes | None
    signature: tuple[int, int, int, int, int] | None


class _ManagedChildState(NamedTuple):
    kind: str
    content: bytes | str
    permissions: int = 0


class _ManagedEntryState(NamedTuple):
    kind: str
    content: str | dict[str, _ManagedChildState]


class _RegularFileState(NamedTuple):
    data: bytes
    signature: tuple[int, int, int, int, int]
    permissions: int


def _translation_note(platform: str) -> str:
    if platform == "dsh":
        return """
## Portable Translation Layer

This generated variant preserves the workflow intent using durable,
client-independent guidance:

- Use available subagents when delegation materially improves speed or quality.
- Give delegated work a narrow objective, relevant context, explicit file
  ownership, and a clear expected result.
- Use the controls available in the current client to steer or stop delegated
  work without assuming a particular tool signature.
- Wait for delegated results only when the next critical-path step depends on
  them, then integrate the results in the parent task.
- Track progress using the planning mechanism available in the current client
  or an explicit local checklist.
- Resolve `./` paths in command examples from the installed skill directory
  that contains this `SKILL.md` file.
"""
    label = _PLATFORM_LABELS[platform]
    return f"""
## {label} Translation Layer

This generated {label} variant preserves the workflow intent using durable,
client-independent guidance:

- Use {label}-native subagents to delegate independent work when parallelism
  materially improves speed or quality.
- Give each delegated task a narrow objective, relevant context, explicit file
  ownership, and a clear expected result.
- Use the subagent controls available in the current client to steer or stop
  delegated work without assuming a particular tool signature.
- Wait for delegated results only when the next critical-path step depends on
  them, then integrate the results in the parent task.
- Track progress using the planning mechanism available in the current client
  or an explicit local checklist.
- Treat a team as coordinated {label}-native subagents with non-overlapping work.
- Resolve `./` paths in command examples from the installed skill directory
  that contains this `SKILL.md` file.
"""


def _semantic_replacements(platform: str) -> dict[str, str]:
    if platform == "dsh":
        return {
            "${CLAUDE_SKILL_DIR}/": "./",
            "$CLAUDE_SKILL_DIR/": "./",
            "${CLAUDE_SKILL_DIR}": "the installed skill directory",
            "CLAUDE_SKILL_DIR": "the installed skill directory",
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "subagent support",
            "spawn_agent": "delegate independent work to an available subagent",
            "send_input": "steer a running subagent",
            "wait_agent": "wait for delegated results",
            "close_agent": "stop or finish delegated work",
            "update_plan": "the planning mechanism available in the current client",
            "fork_context": "appropriate inherited task context",
            "agent_type=": "a suitable subagent role",
            "TeamCreate": "coordinate available subagents",
            "TeamDelete": "finish coordinated subagent work",
            "SendMessage": "steer a running subagent",
            "TaskCreate": "the available planning mechanism",
            "TaskList": "the available planning mechanism",
            "TaskUpdate": "the available planning mechanism",
            "TaskGet": "review delegated progress",
            "TaskOutput": "collect delegated results",
            "TaskStop": "stop delegated work",
            "$ARGUMENTS": "the user-supplied task details",
        }
    label = _PLATFORM_LABELS[platform]
    native_subagent = f"{label}-native subagent"
    replacements = {
        "${CLAUDE_SKILL_DIR}/": "./",
        "$CLAUDE_SKILL_DIR/": "./",
        "${CLAUDE_SKILL_DIR}": "the installed skill directory",
        "CLAUDE_SKILL_DIR": "the installed skill directory",
        "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": f"{label} subagent support",
        "spawn_agent": f"delegate independent work to a {native_subagent}",
        "send_input": "steer a running subagent",
        "wait_agent": "wait for delegated results",
        "close_agent": "stop or finish delegated work",
        "update_plan": "the planning mechanism available in the current client",
        "fork_context": "appropriate inherited task context",
        "agent_type=": "a suitable subagent role",
        "TeamCreate": f"coordinate {label}-native subagents",
        "TeamDelete": "finish coordinated subagent work",
        "SendMessage": "steer a running subagent",
        "TaskCreate": "the available planning mechanism",
        "TaskList": "the available planning mechanism",
        "TaskUpdate": "the available planning mechanism",
        "TaskGet": "review delegated progress",
        "TaskOutput": "collect delegated results",
        "TaskStop": "stop delegated work",
    }
    if platform == "codex":
        replacements["$ARGUMENTS"] = "the user-supplied task details"
    return replacements


def skill_tools(skill_file: Path) -> list[str]:
    """Return ordered allowed-tools entries from a skill frontmatter block."""
    tools_str = frontmatter_field(skill_file, "allowed-tools") or ""
    return [tool.strip() for tool in tools_str.split(",") if tool.strip()]


def is_codex_adapted_skill(skill_file: Path) -> bool:
    """Return True when a source skill needs portable client adaptation."""
    if set(skill_tools(skill_file)) & CLAUDE_ONLY_TOOLS:
        return True
    text = skill_file.read_text(encoding="utf-8")
    if any(token in text for token in _ADAPTATION_BODY_TOKENS):
        return True
    if _AGENT_START_RE.search(text) or _TASK_API_RE.search(text):
        return True
    is_user_invocable = frontmatter_field(skill_file, "user-invocable") != "false"
    return is_user_invocable and bool(_POSITIONAL_ARGUMENT_RE.search(text))


def codex_skill_description(skill_file: Path) -> str:
    """Return the skill description shown in Codex-facing generators."""
    description = frontmatter_field(skill_file, "description")
    if not description:
        return ""
    if is_codex_adapted_skill(skill_file):
        return (
            f"{description} Codex-adapted: uses Codex-native subagents and "
            "current-client planning controls."
        )
    return description


def build_codex_skill_text(skill_file: Path) -> str:
    """Render the Codex-facing SKILL.md contents for a source skill."""
    return _build_portable_skill_text(skill_file, "codex")


def build_opencode_skill_text(skill_file: Path) -> str:
    """Render an OpenCode-facing skill without leaking Codex branding."""
    return _build_portable_skill_text(skill_file, "opencode")


def build_dsh_skill_text(skill_file: Path) -> str:
    """Render a platform-neutral DSH skill with invocation metadata intact."""
    return _build_portable_skill_text(skill_file, "dsh")


def _build_managed_skill_text(skill_file: Path, platform: str) -> str:
    """Dispatch managed wrapper rendering without changing legacy APIs."""
    if platform == "codex":
        return build_codex_skill_text(skill_file)
    if platform == "dsh":
        return build_dsh_skill_text(skill_file)
    raise ValueError(f"Unsupported managed skill platform: {platform}")


def _build_portable_skill_text(skill_file: Path, platform: str) -> str:
    """Render a client-specific skill using semantic, signature-free guidance."""
    if platform not in {*_PLATFORM_LABELS, "dsh"}:
        raise ValueError(f"Unsupported skill adaptation platform: {platform}")
    text = skill_file.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return _adapt_body(text, platform) if is_codex_adapted_skill(skill_file) else text

    body = match.group("body")
    adapted = is_codex_adapted_skill(skill_file)

    if adapted:
        body = _adapt_body(body, platform)
        name = frontmatter_field(skill_file, "name")
        description = (
            codex_skill_description(skill_file)
            if platform == "codex"
            else frontmatter_field(skill_file, "description")
        )
        rendered_entries = [
            ("name", str(name)),
            ("description", json.dumps(description, ensure_ascii=False)),
        ]
        rendered_frontmatter = _render_frontmatter(rendered_entries)
        if platform == "dsh":
            invocation_lines = _invocation_metadata_lines(match.group("frontmatter"))
            if invocation_lines:
                rendered_frontmatter += "\n" + "\n".join(invocation_lines)
    else:
        # Native skills pass their frontmatter through untouched. The old
        # line-by-line re-render flattened nested keys (`hooks:` blocks) into
        # top-level `key: ` lines, which is not the document the author wrote.
        rendered_frontmatter = match.group("frontmatter").strip("\n")

    return f"---\n{rendered_frontmatter}\n---\n{body.rstrip()}\n"


def sync_codex_skill(skill_dir: Path, skills_dst: Path) -> str:
    """Install one skill into `.agents/skills/` and return its mode."""
    skill_file = skill_dir / "SKILL.md"
    adapted = is_codex_adapted_skill(skill_file)

    if adapted:
        return _sync_adapted_skill(skill_dir, skills_dst)
    return _sync_native_skill(skill_dir, skills_dst)


def sync_dsh_skill(skill_dir: Path, skills_dst: Path, *, shared: bool = False) -> str:
    """Install one skill for DSH, optionally on a Codex-shared surface."""
    skill_file = skill_dir / "SKILL.md"
    if not is_codex_adapted_skill(skill_file):
        return _sync_native_skill(skill_dir, skills_dst)
    marker = SHARED_ADAPTED_MARKER if shared else DSH_ADAPTED_MARKER
    return _sync_adapted_skill(
        skill_dir,
        skills_dst,
        platform="dsh",
        marker_name=marker,
    )


def prepare_codex_skills_dir(target_dir: Path) -> Path:
    """Create the documented Codex skill root without following symlinks."""
    _preflight_skill_surface_owner_marker(target_dir)
    if target_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked Codex target directory: {target_dir}")
    agents_dir = target_dir / ".agents"
    skills_dst = agents_dir / "skills"
    _assert_safe_skill_roots(agents_dir, skills_dst)
    skills_dst.mkdir(parents=True, exist_ok=True)
    _assert_safe_skill_roots(agents_dir, skills_dst)
    return skills_dst


def _preflight_skill_surface_owner_marker(target_dir: Path) -> _OwnerMarkerState:
    """Validate and snapshot ownership before any skill-root mutation."""
    return _read_owner_marker_state(
        target_dir / ".agents" / SKILL_SURFACE_OWNERS_MARKER
    )


def _read_owner_marker_state(marker: Path) -> _OwnerMarkerState:
    """Return the exact valid marker state, rejecting every unsafe collision."""
    if marker.is_symlink():
        raise RuntimeError(
            f"Refusing invalid skill-surface owner marker {marker}: "
            "symlinks are not managed owner markers"
        )
    if not marker.exists():
        return _OwnerMarkerState(data=None, signature=None)
    try:
        metadata = marker.lstat()
    except OSError as error:
        raise RuntimeError(
            f"Refusing invalid skill-surface owner marker {marker}: "
            f"cannot inspect marker ({error})"
        ) from error
    if stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(
            f"Refusing invalid skill-surface owner marker {marker}: "
            "directory found where a regular marker file is required"
        )
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(
            f"Refusing invalid skill-surface owner marker {marker}: "
            "only a regular non-symlink marker file is supported"
        )
    try:
        data = marker.read_bytes()
    except (OSError, UnicodeError) as error:
        raise RuntimeError(
            f"Refusing invalid skill-surface owner marker {marker}: "
            f"cannot read regular marker ({error})"
        ) from error
    if parse_skill_surface_owners(data) is None:
        raise RuntimeError(
            f"Refusing invalid skill-surface owner marker {marker}: expected "
            "one canonical owner per line (codex and/or dsh)"
        )
    signature = (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
    )
    return _OwnerMarkerState(data=data, signature=signature)


def serialize_skill_surface_owners(owners: set[str]) -> bytes:
    """Serialize one non-empty known owner set into its only managed form."""
    if not owners or not owners <= SKILL_SURFACE_OWNERS:
        raise ValueError(f"Invalid .agents/skills owners: {sorted(owners)}")
    return ("\n".join(sorted(owners)) + "\n").encode("utf-8")


def parse_skill_surface_owners(data: bytes) -> set[str] | None:
    """Return owners only when bytes exactly match the canonical serialization."""
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError:
        return None
    owners = set(lines)
    if len(lines) != len(owners):
        return None
    try:
        canonical = serialize_skill_surface_owners(owners)
    except ValueError:
        return None
    return owners if data == canonical else None


def _assert_owner_marker_state(marker: Path, expected: _OwnerMarkerState) -> None:
    try:
        actual = _read_owner_marker_state(marker)
    except RuntimeError as error:
        raise RuntimeError(
            f"Skill-surface owner marker changed before atomic replacement: {marker}"
        ) from error
    if actual != expected:
        raise RuntimeError(
            f"Skill-surface owner marker changed before atomic replacement: {marker}"
        )


def _restore_owner_marker(marker: Path, expected: _OwnerMarkerState) -> None:
    try:
        actual = _read_owner_marker_state(marker)
    except RuntimeError as error:
        raise RuntimeError(
            f"Cannot restore changed skill-surface owner marker: {marker}"
        ) from error
    if actual == expected:
        return
    if expected.data is None:
        if actual.data is None:
            return
        marker.unlink()
        _fsync_directory(marker.parent)
        return
    temp_path = _stage_bytes(marker, expected.data)
    try:
        os.replace(temp_path, marker)
        _fsync_directory(marker.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def _directory_entry_names(path: Path) -> set[str]:
    if not path.is_dir() or path.is_symlink():
        return set()
    return {entry.name for entry in path.iterdir()}


def _snapshot_managed_entries(
    skills_dst: Path,
    skills_src: Path,
) -> dict[str, _ManagedEntryState]:
    if not skills_dst.is_dir() or skills_dst.is_symlink():
        return {}
    source_root = skills_src.resolve()
    snapshots: dict[str, _ManagedEntryState] = {}
    for entry in skills_dst.iterdir():
        if entry.is_symlink():
            if _is_relative_to(_symlink_target(entry), source_root):
                snapshots[entry.name] = _ManagedEntryState(
                    kind="link",
                    content=os.readlink(entry),
                )
            continue
        marker_name = _validated_wrapper_marker(entry)
        if marker_name is None:
            continue
        children: dict[str, _ManagedChildState] = {}
        for child in entry.iterdir():
            if child.name == "SKILL.md" or child.name in ADAPTED_MARKERS:
                if child.is_symlink() or not child.is_file():
                    raise RuntimeError(
                        f"Cannot transactionally manage malformed skill wrapper: {child}"
                    )
                metadata = child.stat()
                children[child.name] = _ManagedChildState(
                    kind="file",
                    content=child.read_bytes(),
                    permissions=stat.S_IMODE(metadata.st_mode),
                )
                continue
            if child.is_symlink() and _is_relative_to(
                _symlink_target(child), source_root
            ):
                children[child.name] = _ManagedChildState(
                    kind="link",
                    content=os.readlink(child),
                )
        if "SKILL.md" not in children or marker_name not in children:
            raise RuntimeError(f"Cannot snapshot incomplete skill wrapper: {entry}")
        snapshots[entry.name] = _ManagedEntryState(
            kind="wrapper",
            content=children,
        )
    return snapshots


def _validated_wrapper_marker(path: Path) -> str | None:
    if path.is_symlink() or not path.is_dir():
        return None
    present = [
        marker_name
        for marker_name in sorted(ADAPTED_MARKERS)
        if (path / marker_name).exists() or (path / marker_name).is_symlink()
    ]
    if not present:
        return None
    if len(present) != 1:
        raise RuntimeError(f"Ambiguous managed skill wrapper markers: {path}")
    marker = path / present[0]
    if marker.is_symlink() or not marker.is_file():
        raise RuntimeError(f"Malformed managed skill wrapper marker: {marker}")
    return present[0]


def _remove_transaction_entry(path: Path, source_root: Path) -> None:
    if path.is_symlink():
        if _is_relative_to(_symlink_target(path), source_root):
            path.unlink()
        return
    if not path.is_dir():
        return
    if _validated_wrapper_marker(path) is None:
        return
    _remove_transaction_children(path, source_root)
    try:
        path.rmdir()
    except OSError:
        pass


def _remove_transaction_children(path: Path, source_root: Path) -> None:
    for child in list(path.iterdir()):
        if child.name == "SKILL.md" or child.name in ADAPTED_MARKERS:
            if child.is_symlink() or child.is_file():
                child.unlink()
            continue
        if child.is_symlink() and _is_relative_to(
            _symlink_target(child), source_root
        ):
            child.unlink()


def _restore_managed_entry(
    path: Path,
    expected: _ManagedEntryState,
    source_root: Path,
) -> None:
    if expected.kind == "link":
        _remove_transaction_entry(path, source_root)
        if path.exists() or path.is_symlink():
            if path.is_symlink() and os.readlink(path) == expected.content:
                return
            raise RuntimeError(f"Cannot restore managed skill link without data loss: {path}")
        path.symlink_to(str(expected.content))
        return

    if path.is_symlink():
        if not _is_relative_to(_symlink_target(path), source_root):
            raise RuntimeError(f"Cannot replace user-owned skill link: {path}")
        path.unlink()
    if path.exists() and not path.is_dir():
        raise RuntimeError(f"Cannot restore managed skill wrapper: {path}")
    path.mkdir(exist_ok=True)
    _remove_transaction_children(path, source_root)
    children = expected.content
    if not isinstance(children, dict):
        raise RuntimeError(f"Invalid managed wrapper snapshot: {path}")
    for name, child_state in children.items():
        destination = path / name
        if child_state.kind == "link":
            destination.symlink_to(str(child_state.content))
            continue
        data = child_state.content
        if not isinstance(data, bytes):
            raise RuntimeError(f"Invalid managed file snapshot: {destination}")
        temp_path = _stage_bytes(destination, data)
        try:
            os.chmod(temp_path, child_state.permissions)
            os.replace(temp_path, destination)
        finally:
            temp_path.unlink(missing_ok=True)
    _fsync_directory(path)


def set_skill_surface_owners(
    skills_dst: Path,
    owners: set[str],
    *,
    expected_state: _OwnerMarkerState | None = None,
) -> None:
    """Record explicit owners for the otherwise ambiguous shared directory."""
    _assert_safe_skill_roots(skills_dst.parent, skills_dst)
    marker = skills_dst.parent / SKILL_SURFACE_OWNERS_MARKER
    previous = expected_state or _read_owner_marker_state(marker)
    temp_path = _stage_bytes(marker, serialize_skill_surface_owners(owners))
    try:
        _assert_owner_marker_state(marker, previous)
        os.replace(temp_path, marker)
        _fsync_directory(skills_dst.parent)
    finally:
        temp_path.unlink(missing_ok=True)


def skill_surface_owners(skills_dst: Path) -> set[str] | None:
    """Return declared owners, ``None`` for a legacy unowned surface."""
    marker = skills_dst.parent / SKILL_SURFACE_OWNERS_MARKER
    try:
        state = _read_owner_marker_state(marker)
    except RuntimeError:
        return set()
    if state.data is None:
        return None
    owners = parse_skill_surface_owners(state.data)
    return owners if owners is not None else set()


class _SkillSurfaceTransaction:
    """Rollback guard for the installer-owned portion of `.agents/skills`."""

    def __init__(self, target_dir: Path, skills_src: Path) -> None:
        self.target_dir = target_dir
        self.skills_src = skills_src
        self.agents_dir = target_dir / ".agents"
        self.skills_dst = self.agents_dir / "skills"
        self.marker = self.agents_dir / SKILL_SURFACE_OWNERS_MARKER
        self.marker_state = _read_owner_marker_state(self.marker)
        self.agents_existed = self.agents_dir.is_dir()
        self.skills_existed = self.skills_dst.is_dir()
        _assert_safe_skill_roots(self.agents_dir, self.skills_dst)
        self.entries = _snapshot_managed_entries(self.skills_dst, skills_src)
        self.initial_names = _directory_entry_names(self.skills_dst)
        self.is_committed = False

    def __enter__(self) -> _SkillSurfaceTransaction:
        self.skills_dst = prepare_codex_skills_dir(self.target_dir)
        return self

    def commit(self, owners: set[str]) -> None:
        set_skill_surface_owners(
            self.skills_dst,
            owners,
            expected_state=self.marker_state,
        )
        self.is_committed = True

    def __exit__(self, error_type, error, traceback) -> bool:
        if error is None and self.is_committed:
            return False
        try:
            self._rollback()
        except (OSError, RuntimeError) as rollback_error:
            if error is None:
                raise
            raise RuntimeError(
                f"Managed skill transaction failed and rollback was incomplete: "
                f"{rollback_error}"
            ) from error
        return False

    def _rollback(self) -> None:
        if self.skills_dst.is_dir() and not self.skills_dst.is_symlink():
            current_names = _directory_entry_names(self.skills_dst)
            for name in sorted(current_names - self.initial_names):
                _remove_transaction_entry(
                    self.skills_dst / name,
                    self.skills_src.resolve(),
                )
            for name, entry_state in self.entries.items():
                _restore_managed_entry(
                    self.skills_dst / name,
                    entry_state,
                    self.skills_src.resolve(),
                )
        _restore_owner_marker(self.marker, self.marker_state)
        if not self.skills_existed and self.skills_dst.is_dir():
            try:
                self.skills_dst.rmdir()
            except OSError:
                pass
        if not self.agents_existed and self.agents_dir.is_dir():
            try:
                self.agents_dir.rmdir()
            except OSError:
                pass


def managed_skill_surface_transaction(
    target_dir: Path,
    skills_src: Path,
) -> _SkillSurfaceTransaction:
    """Return a rollback guard for one complete managed skill installation."""
    return _SkillSurfaceTransaction(target_dir, skills_src)


def unmanaged_codex_skill_names(skills_dst: Path, skills_src: Path) -> set[str]:
    """Return logical names declared by user-owned destination entries."""
    names: set[str] = set()
    for item in sorted(skills_dst.iterdir()):
        if _is_managed_entry(item, skills_src):
            continue
        skill_file = item / "SKILL.md"
        try:
            name = frontmatter_field(skill_file, "name")
        except (OSError, UnicodeError):
            continue
        if name:
            names.add(name)
    return names


def cleanup_codex_skills(
    skills_dst: Path,
    skills_src: Path,
    blocked_names: set[str] | None = None,
) -> None:
    """Remove stale or shadowed toolkit-managed entries without touching user data."""
    _assert_safe_skill_roots(skills_dst.parent, skills_dst)
    skills_src_resolved = skills_src.resolve()
    blocked_names = blocked_names or set()
    for item in skills_dst.iterdir():
        src = skills_src / item.name
        if item.name in blocked_names and _is_managed_entry(item, skills_src):
            if item.is_symlink():
                item.unlink()
            else:
                _remove_managed_wrapper(item, skills_src_resolved)
            continue
        if item.is_symlink():
            target = _symlink_target(item)
            if src.is_dir() and target == src.resolve():
                continue
            if _is_relative_to(target, skills_src_resolved):
                item.unlink()
                continue
        if _is_adapted_wrapper(item) and not src.is_dir():
            _remove_managed_wrapper(item, skills_src_resolved)


def _assert_safe_skill_roots(agents_dir: Path, skills_dst: Path) -> None:
    if agents_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked Codex agents directory: {agents_dir}")
    if skills_dst.is_symlink():
        raise RuntimeError(f"Refusing symlinked Codex skills directory: {skills_dst}")


def _symlink_target(path: Path) -> Path:
    raw_target = Path(os.readlink(path))
    if not raw_target.is_absolute():
        raw_target = path.parent / raw_target
    return raw_target.resolve(strict=False)


def _points_to(path: Path, target: Path) -> bool:
    return path.is_symlink() and _symlink_target(path) == target.resolve()


def _adapted_marker(path: Path) -> str | None:
    if path.is_symlink() or not path.is_dir():
        return None
    for marker_name in sorted(ADAPTED_MARKERS):
        marker = path / marker_name
        if not marker.is_symlink() and marker.is_file():
            return marker_name
    return None


def _is_adapted_wrapper(path: Path) -> bool:
    return _adapted_marker(path) is not None


def _is_managed_entry(path: Path, skills_src: Path) -> bool:
    if _is_adapted_wrapper(path):
        return True
    if not path.is_symlink():
        return False
    return _is_relative_to(_symlink_target(path), skills_src.resolve())


def _sync_native_skill(skill_dir: Path, skills_dst: Path) -> str:
    target = skills_dst / skill_dir.name
    if target.is_symlink():
        return "linked" if _points_to(target, skill_dir) else "skipped"
    if _is_adapted_wrapper(target):
        if not _remove_managed_wrapper(target, skill_dir.parent.resolve()):
            return "skipped"
    elif target.exists():
        return "skipped"
    target.symlink_to(skill_dir)
    return "linked"


def _sync_adapted_skill(
    skill_dir: Path,
    skills_dst: Path,
    *,
    platform: str = "codex",
    marker_name: str = ADAPTED_MARKER,
) -> str:
    target = skills_dst / skill_dir.name
    if target.is_symlink():
        if not _points_to(target, skill_dir):
            return "skipped"
        return _create_adapted_wrapper(
            skill_dir,
            target,
            replace_managed_link=True,
            platform=platform,
            marker_name=marker_name,
        )
    if target.exists() and not _is_adapted_wrapper(target):
        return "skipped"
    if not target.exists():
        return _create_adapted_wrapper(
            skill_dir,
            target,
            platform=platform,
            marker_name=marker_name,
        )

    if _adapted_marker(target) != marker_name:
        return _transition_adapted_wrapper(
            skill_dir,
            target,
            platform=platform,
            marker_name=marker_name,
        )

    return _update_adapted_wrapper(
        skill_dir,
        target,
        platform=platform,
        marker_name=marker_name,
    )


def _transition_adapted_wrapper(
    skill_dir: Path,
    target: Path,
    *,
    platform: str,
    marker_name: str,
) -> str:
    """Replace only managed wrapper files while preserving user additions."""
    previous_marker_name = _validated_wrapper_marker(target)
    if previous_marker_name is None:
        return "skipped"
    skill_output = target / "SKILL.md"
    previous_marker = target / previous_marker_name
    next_marker = target / marker_name
    if skill_output.is_symlink() or not skill_output.is_file():
        return "skipped"
    if next_marker.exists() or next_marker.is_symlink():
        return "skipped"

    skill_state = _regular_file_state(skill_output)
    marker_state = _regular_file_state(previous_marker)
    next_skill = _stage_text(
        skill_output,
        _build_managed_skill_text(skill_dir / "SKILL.md", platform),
    )
    next_marker_file = _stage_text(
        next_marker,
        f"generated by ai-toolkit for {platform}\n",
    )
    try:
        _assert_regular_file_state(skill_output, skill_state)
        _assert_regular_file_state(previous_marker, marker_state)
        if next_marker.exists() or next_marker.is_symlink():
            raise RuntimeError(f"Managed skill marker appeared during sync: {next_marker}")
        os.replace(next_skill, skill_output)
        os.replace(next_marker_file, next_marker)
        _assert_regular_file_state(previous_marker, marker_state)
        previous_marker.unlink()
        _sync_auxiliaries(skill_dir, target)
        _fsync_directory(target)
    except Exception:
        _restore_regular_file(skill_output, skill_state)
        if next_marker.is_file() and not next_marker.is_symlink():
            expected = f"generated by ai-toolkit for {platform}\n".encode("utf-8")
            if next_marker.read_bytes() == expected:
                next_marker.unlink()
        _restore_regular_file(previous_marker, marker_state)
        raise
    finally:
        next_skill.unlink(missing_ok=True)
        next_marker_file.unlink(missing_ok=True)
    return "adapted"


def _create_adapted_wrapper(
    skill_dir: Path,
    target: Path,
    *,
    replace_managed_link: bool = False,
    platform: str = "codex",
    marker_name: str = ADAPTED_MARKER,
) -> str:
    """Build a complete sibling wrapper and expose it with one atomic rename."""
    staging = Path(tempfile.mkdtemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    ))
    removed_link = False
    try:
        _write_text_fsync(
            staging / "SKILL.md",
            _build_managed_skill_text(skill_dir / "SKILL.md", platform),
        )
        _write_text_fsync(
            staging / marker_name,
            f"generated by ai-toolkit for {platform}\n",
        )
        _sync_auxiliaries(skill_dir, staging)
        _fsync_directory(staging)

        if replace_managed_link:
            if not _points_to(target, skill_dir):
                raise RuntimeError(f"Codex skill target changed during sync: {target}")
            target.unlink()
            removed_link = True
        elif target.exists() or target.is_symlink():
            raise RuntimeError(f"Codex skill target appeared during sync: {target}")

        os.replace(staging, target)
        _fsync_directory(target.parent)
        return "adapted"
    except Exception:
        _remove_staged_wrapper(staging)
        if removed_link and not target.exists() and not target.is_symlink():
            target.symlink_to(skill_dir)
        raise


def _update_adapted_wrapper(
    skill_dir: Path,
    target: Path,
    *,
    platform: str = "codex",
    marker_name: str = ADAPTED_MARKER,
) -> str:
    """Atomically refresh SKILL.md while leaving the managed marker stable."""
    skill_output = target / "SKILL.md"
    marker = target / marker_name
    if skill_output.is_symlink() or marker.is_symlink():
        return "skipped"
    temp_path = _stage_text(
        skill_output,
        _build_managed_skill_text(skill_dir / "SKILL.md", platform),
    )
    try:
        os.replace(temp_path, skill_output)
        _fsync_directory(target)
    finally:
        temp_path.unlink(missing_ok=True)
    _sync_auxiliaries(skill_dir, target)
    return "adapted"


def _write_text_fsync(destination: Path, content: str) -> None:
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _regular_file_state(path: Path) -> _RegularFileState:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"Managed file is not a regular non-symlink file: {path}")
    metadata = path.stat()
    return _RegularFileState(
        data=path.read_bytes(),
        signature=(
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_size,
            metadata.st_mtime_ns,
        ),
        permissions=stat.S_IMODE(metadata.st_mode),
    )


def _assert_regular_file_state(path: Path, expected: _RegularFileState) -> None:
    actual = _regular_file_state(path)
    if actual != expected:
        raise RuntimeError(f"Managed file changed during skill sync: {path}")


def _restore_regular_file(path: Path, expected: _RegularFileState) -> None:
    try:
        if _regular_file_state(path).data == expected.data:
            return
    except RuntimeError:
        if path.exists() or path.is_symlink():
            raise
    staged = _stage_bytes(path, expected.data)
    try:
        os.chmod(staged, expected.permissions)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
    except OSError as error:
        if error.errno in _UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS:
            return
        raise
    try:
        try:
            os.fsync(fd)
        except OSError as error:
            if error.errno not in _UNSUPPORTED_DIRECTORY_FSYNC_ERRNOS:
                raise
    finally:
        os.close(fd)


def _remove_staged_wrapper(staging: Path) -> None:
    if staging.is_symlink() or not staging.is_dir():
        return
    for child in staging.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
    try:
        staging.rmdir()
    except OSError:
        pass


def _stage_text(destination: Path, content: str) -> Path:
    return _stage_bytes(destination, content.encode("utf-8"))


def _stage_bytes(destination: Path, content: bytes) -> Path:
    fd, temp_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        handle = os.fdopen(fd, "wb")
        fd = -1
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return temp_path
    except Exception:
        if fd >= 0:
            os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise


def _sync_auxiliaries(skill_dir: Path, target: Path) -> None:
    expected = {child.name for child in skill_dir.iterdir() if child.name != "SKILL.md"}
    for child in sorted(skill_dir.iterdir()):
        if child.name == "SKILL.md":
            continue
        destination = target / child.name
        if destination.is_symlink():
            if _points_to(destination, child):
                continue
            continue
        if destination.exists():
            continue
        destination.symlink_to(child)

    source_root = skill_dir.resolve()
    for destination in target.iterdir():
        if destination.name in expected | {"SKILL.md", *ADAPTED_MARKERS}:
            continue
        if destination.is_symlink() and _is_relative_to(
            _symlink_target(destination), source_root
        ):
            destination.unlink()


def _remove_managed_wrapper(path: Path, skills_src_resolved: Path) -> bool:
    if not _is_adapted_wrapper(path):
        return False
    children = list(path.iterdir())
    marker_name = _adapted_marker(path)
    if marker_name is None:
        return False
    for child in children:
        if child.name in {"SKILL.md", marker_name}:
            if child.is_symlink() or not child.is_file():
                return False
            continue
        if not child.is_symlink():
            return False
        if not _is_relative_to(_symlink_target(child), skills_src_resolved):
            return False
    for child in children:
        child.unlink()
    path.rmdir()
    return True


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _invocation_metadata_lines(frontmatter_text: str) -> list[str]:
    """Return exact canonical invocation lines, rejecting duplicate fields."""
    fields = ("user-invocable", "disable-model-invocation")
    lines: list[str] = []
    seen: set[str] = set()
    for line in frontmatter_text.splitlines():
        field = next((name for name in fields if line.startswith(f"{name}:")), None)
        if field is None:
            continue
        if field in seen:
            raise ValueError(f"Duplicate invocation metadata field: {field}")
        seen.add(field)
        lines.append(line)
    return lines


def _render_frontmatter(entries: list[tuple[str, str]]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in entries)


def _adapt_body(body: str, platform: str) -> str:
    label = _PLATFORM_LABELS.get(platform)
    body = _replace_agent_calls(body, label)
    subagents = f"{label}-native subagents" if label else "available subagents"
    body = body.replace("Agent Teams", f"coordinated {subagents}")
    body = body.replace("`Agent` tool", subagents)
    body = body.replace("the `Agent` tool", subagents)
    body = body.replace("Agent tool", subagents)
    for token, replacement in _semantic_replacements(platform).items():
        body = body.replace(token, replacement)
    if platform == "codex":
        body = _POSITIONAL_ARGUMENT_RE.sub(
            lambda match: f"the user-supplied positional task detail {match.group(1)}",
            body,
        )
    return f"{_translation_note(platform).strip()}\n\n{body.strip()}\n"


def _replace_agent_calls(body: str, label: str | None) -> str:
    """Replace balanced Agent calls without consuming surrounding markdown."""
    rendered: list[str] = []
    cursor = 0
    while match := _AGENT_START_RE.search(body, cursor):
        rendered.append(body[cursor:match.start()])
        end = _balanced_call_end(body, match.end() - 1)
        target = f"a suitable {label}-native subagent" if label else "an available subagent"
        rendered.append(f"Delegate this independent work to {target}.")
        cursor = end
    rendered.append(body[cursor:])
    return "".join(rendered)


def _balanced_call_end(text: str, opening_parenthesis: int) -> int:
    depth = 1
    quote: str | None = None
    is_escaped = False
    for index in range(opening_parenthesis + 1, len(text)):
        character = text[index]
        if quote is not None:
            if is_escaped:
                is_escaped = False
            elif character == "\\":
                is_escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError(f"Unbalanced Agent call at character {opening_parenthesis}")
