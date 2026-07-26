"""Retirement cleanup for the v4.16.x native tool-output filter.

v4.16.0 and v4.16.1 installed a PostToolUse filter that wrote files outside the
npm package: a hook script, a global policy, per-project policy files, and
private recovery trees that can hold captured command output. v4.17.0 removed
the feature, so those files are orphaned on every machine that ran the old
releases. ``install``/``update`` and ``uninstall`` both reclaim them here.

The implementation is deliberately self-contained. The package that wrote these
files (``scripts/tool_output_filter/``) no longer exists in the repository, so
the ownership rules it enforced are re-stated as literal constants instead of
being imported. Nothing is removed without matching one of those rules, and no
path is ever opened through a symlink.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path

# ---------------------------------------------------------------------------
# Ownership constants copied from the removed v4.16.x runtime
# ---------------------------------------------------------------------------

HOOK_SCRIPT_NAME = "filter-tool-output.sh"
HOOK_SCRIPT_MARKER = b"# Claude PostToolUse adapter for the native tool-output filter."

GLOBAL_POLICY_NAME = "output-filter-policy.json"

PROJECT_POLICY_NAME = "ai-toolkit-output-filter.json"
PROJECT_OWNER_NAME = ".ai-toolkit-output-filter.owner"
PROJECT_OWNER_MARKER = b"ai-toolkit-output-filter-policy-v1\n"

RUNTIME_SCRIPTS: tuple[tuple[str, bytes], ...] = (
    (
        "output_filter_hook.py",
        b'"""Lean process entry point for the Claude output-filter hook."""',
    ),
    (
        "output_filter_cli.py",
        b'"""Manual and hook entry points for native tool-output filtering."""',
    ),
)

RUNTIME_PACKAGE_NAME = "tool_output_filter"
RUNTIME_PACKAGE_MARKER = b'"""Dependency-free post-execution tool-output filtering."""'
_PACKAGE_MODULES: tuple[str, ...] = (
    "__init__.py",
    "contracts.py",
    "engine.py",
    "hook_runtime.py",
    "input.py",
    "invariants.py",
    "policy.py",
    "recovery.py",
    "telemetry.py",
)
_PACKAGE_SUBPACKAGES: dict[str, tuple[str, ...]] = {
    "profiles": ("__init__.py", "repeat_lines.py", "tap_success.py"),
}

_RECOVERY_DIRECTORY_NAME = "output-filter"
_RECOVERY_TOKEN_LENGTH = 32
_RECOVERY_CIRCUIT_STATE_NAME = ".circuit-state.json"
_RECOVERY_TELEMETRY_NAME = ".telemetry.jsonl"
_RECOVERY_PENDING_PREFIX = ".pending-"
_RECOVERY_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


# ---------------------------------------------------------------------------
# Recovery trees (sessions/<repo-key>/output-filter/<session>/)
# ---------------------------------------------------------------------------

def _is_recovery_token(name: str) -> bool:
    return (
        len(name) == _RECOVERY_TOKEN_LENGTH
        and all(character in "0123456789abcdef" for character in name)
    )


def _is_recovery_artifact_name(name: str) -> bool:
    """Match only the artifact names the removed filter could have written."""
    if name in {_RECOVERY_CIRCUIT_STATE_NAME, _RECOVERY_TELEMETRY_NAME}:
        return True
    if name.endswith(".json") and _is_recovery_token(name[:-len(".json")]):
        return True
    return name.startswith(_RECOVERY_PENDING_PREFIX) and _is_recovery_token(
        name[len(_RECOVERY_PENDING_PREFIX):]
    )


def _assert_private_recovery_directory(directory_fd: int, label: str) -> None:
    metadata = os.fstat(directory_fd)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(f"{label} is not a directory")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RuntimeError(f"{label} is not private")
    if metadata.st_uid != os.getuid():
        raise RuntimeError(f"{label} is not owned by this user")


def _open_recovery_directory(parent_fd: int, name: str, label: str) -> int:
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError(f"{label} is not a directory")
    return os.open(name, _RECOVERY_DIRECTORY_FLAGS, dir_fd=parent_fd)


def _scan_recovery_session(session_fd: int) -> tuple[str, ...]:
    """Return validated artifact names, refusing anything not owner-private."""
    _assert_private_recovery_directory(session_fd, "owned recovery session")
    artifacts = tuple(
        name for name in os.listdir(session_fd) if _is_recovery_artifact_name(name)
    )
    for artifact_name in artifacts:
        metadata = os.stat(artifact_name, dir_fd=session_fd, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("owned recovery artifact is not regular")
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RuntimeError("owned recovery artifact is not private")
    return artifacts


def _walk_recovery_tree(sessions_root: Path, *, delete: bool) -> int:
    """Validate every repo tree, optionally unlinking the owned artifacts.

    Counting validates the whole tree before ``delete`` ever runs, so an unsafe
    symlink anywhere aborts the cleanup before the first unlink.
    """
    try:
        root_fd = os.open(sessions_root, _RECOVERY_DIRECTORY_FLAGS)
    except FileNotFoundError:
        return 0
    except OSError as error:
        raise RuntimeError(f"recovery base is unavailable: {error}") from error
    total = 0
    try:
        for repo_name in sorted(os.listdir(root_fd)):
            try:
                metadata = os.stat(repo_name, dir_fd=root_fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISDIR(metadata.st_mode):
                continue
            repo_fd = os.open(repo_name, _RECOVERY_DIRECTORY_FLAGS, dir_fd=root_fd)
            try:
                total += _walk_recovery_repo(repo_fd, delete=delete)
            finally:
                os.close(repo_fd)
    finally:
        os.close(root_fd)
    return total


def _walk_recovery_repo(repo_fd: int, *, delete: bool) -> int:
    try:
        output_fd = _open_recovery_directory(
            repo_fd,
            _RECOVERY_DIRECTORY_NAME,
            "owned output-filter directory",
        )
    except FileNotFoundError:
        return 0
    total = 0
    try:
        _assert_private_recovery_directory(
            output_fd,
            "owned output-filter directory",
        )
        for session_name in sorted(os.listdir(output_fd)):
            if not _is_recovery_token(session_name):
                continue
            session_fd = _open_recovery_directory(
                output_fd,
                session_name,
                "owned recovery session",
            )
            try:
                artifacts = _scan_recovery_session(session_fd)
                total += len(artifacts)
                if not delete:
                    continue
                for artifact_name in artifacts:
                    os.unlink(artifact_name, dir_fd=session_fd)
                if artifacts:
                    os.fsync(session_fd)
            finally:
                os.close(session_fd)
            if delete:
                # Foreign content keeps the directory: rmdir fails, we move on.
                try:
                    os.rmdir(session_name, dir_fd=output_fd)
                except OSError:
                    pass
    finally:
        os.close(output_fd)
    if delete:
        try:
            os.rmdir(_RECOVERY_DIRECTORY_NAME, dir_fd=repo_fd)
        except OSError:
            pass
    return total


def count_owned_recovery_artifacts(sessions_root: Path) -> int:
    """Count validated leftover filter artifacts without mutating the tree."""
    return _walk_recovery_tree(sessions_root, delete=False)


def clean_owned_recovery_tree(sessions_root: Path) -> int:
    """Delete validated leftover filter artifacts below all repo sessions."""
    return _walk_recovery_tree(sessions_root, delete=True)


# ---------------------------------------------------------------------------
# Per-project policy pair (<project>/.claude/)
# ---------------------------------------------------------------------------

def managed_project_policy(claude_dir: Path) -> list[Path]:
    """Return the managed per-project policy pair, or [] when unmanaged.

    The owner marker is the ownership test: without it the policy file was
    hand-written by the user and stays put.
    """
    if claude_dir.is_symlink():
        return []
    policy = claude_dir / PROJECT_POLICY_NAME
    owner = claude_dir / PROJECT_OWNER_NAME
    if owner.is_symlink() or not owner.is_file():
        return []
    try:
        if owner.read_bytes() != PROJECT_OWNER_MARKER:
            return []
    except OSError:
        return []
    managed = [owner]
    if not policy.is_symlink() and policy.is_file():
        managed.insert(0, policy)
    return managed


# ---------------------------------------------------------------------------
# Global artifacts (~/.softspark/ai-toolkit/)
# ---------------------------------------------------------------------------

def _owned_regular_file(path: Path, marker: bytes | None) -> bool:
    """True only for a real file that still carries its shipped marker."""
    if path.is_symlink() or not path.is_file():
        return False
    if marker is None:
        return True
    try:
        return marker in path.read_bytes()
    except OSError:
        return False


def _owned_global_policy(path: Path) -> bool:
    """True for the seeded global policy, including a user-edited mode."""
    if path.is_symlink() or not path.is_file():
        return False
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(document, dict) and "mode" in document


def _owned_package_root(package_root: Path) -> bool:
    if package_root.is_symlink() or not package_root.is_dir():
        return False
    return _owned_regular_file(package_root / "__init__.py", RUNTIME_PACKAGE_MARKER)


def _remove_package_members(directory: Path, modules: tuple[str, ...]) -> None:
    """Unlink known modules plus their bytecode, leaving anything else alone."""
    stems = {name[: -len(".py")] for name in modules}
    for name in modules:
        member = directory / name
        if not member.is_symlink() and member.is_file():
            member.unlink()
    cache = directory / "__pycache__"
    if not cache.is_symlink() and cache.is_dir():
        for compiled in sorted(cache.iterdir()):
            if compiled.is_symlink() or not compiled.is_file():
                continue
            if not compiled.name.endswith(".pyc") or ".cpython-" not in compiled.name:
                continue
            if compiled.name.split(".", 1)[0] in stems:
                compiled.unlink()
        _rmdir_if_empty(cache)


def _rmdir_if_empty(directory: Path) -> None:
    try:
        directory.rmdir()
    except OSError:
        # Foreign content still lives here: leave the whole directory in place.
        pass


def _global_artifact_paths(toolkit_data_dir: Path) -> list[tuple[Path, str]]:
    """Return every verified global leftover as (path, human label)."""
    hooks_dir = toolkit_data_dir / "hooks"
    scripts_dir = toolkit_data_dir / "scripts"
    found: list[tuple[Path, str]] = []

    if not hooks_dir.is_symlink() and hooks_dir.is_dir():
        hook_script = hooks_dir / HOOK_SCRIPT_NAME
        if _owned_regular_file(hook_script, HOOK_SCRIPT_MARKER):
            found.append((hook_script, f"hooks/{HOOK_SCRIPT_NAME}"))
        global_policy = hooks_dir / GLOBAL_POLICY_NAME
        if _owned_global_policy(global_policy):
            found.append((global_policy, f"hooks/{GLOBAL_POLICY_NAME}"))

    if not scripts_dir.is_symlink() and scripts_dir.is_dir():
        for name, marker in RUNTIME_SCRIPTS:
            runtime_script = scripts_dir / name
            if _owned_regular_file(runtime_script, marker):
                found.append((runtime_script, f"scripts/{name}"))
        package_root = scripts_dir / RUNTIME_PACKAGE_NAME
        if _owned_package_root(package_root):
            found.append((package_root, f"scripts/{RUNTIME_PACKAGE_NAME}/"))

    return found


def _recovery_label(artifacts: int) -> str:
    noun = "file" if artifacts == 1 else "files"
    return f"sessions/*/{_RECOVERY_DIRECTORY_NAME}/ ({artifacts} {noun})"


def find_global_artifacts(toolkit_data_dir: Path) -> list[str]:
    """List labels for leftovers a cleanup run would remove. Never mutates."""
    labels = [label for _, label in _global_artifact_paths(toolkit_data_dir)]
    try:
        artifacts = count_owned_recovery_artifacts(toolkit_data_dir / "sessions")
    except (OSError, RuntimeError):
        artifacts = 0
    if artifacts:
        labels.append(_recovery_label(artifacts))
    return labels


def cleanup_global_artifacts(toolkit_data_dir: Path) -> tuple[list[str], list[str]]:
    """Remove verified leftovers under the toolkit data directory.

    Returns ``(removed_labels, warnings)``. Both are empty on a clean machine,
    which keeps the caller silent when there is nothing to retire.
    """
    removed: list[str] = []
    warnings: list[str] = []

    for path, label in _global_artifact_paths(toolkit_data_dir):
        try:
            if path.is_dir():
                _remove_package_members(path, _PACKAGE_MODULES)
                for sub_name, sub_modules in _PACKAGE_SUBPACKAGES.items():
                    sub_directory = path / sub_name
                    if sub_directory.is_symlink() or not sub_directory.is_dir():
                        continue
                    _remove_package_members(sub_directory, sub_modules)
                    _rmdir_if_empty(sub_directory)
                _rmdir_if_empty(path)
                if path.exists():
                    warnings.append(
                        f"removed {label} modules but kept the directory "
                        "(unrecognized files inside)"
                    )
                    continue
            else:
                path.unlink()
        except OSError as error:
            warnings.append(f"kept {label} ({error})")
            continue
        removed.append(label)

    sessions_root = toolkit_data_dir / "sessions"
    try:
        artifacts = clean_owned_recovery_tree(sessions_root)
    except (OSError, RuntimeError) as error:
        warnings.append(
            f"kept sessions/*/{_RECOVERY_DIRECTORY_NAME}/ recovery data ({error})"
        )
    else:
        if artifacts:
            removed.append(_recovery_label(artifacts))

    return removed, warnings
