# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Explicit lifecycle for SoftSpark packages in one DSH profile."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import signal
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
except ImportError:  # pragma: no cover - native Windows is rejected before mutation
    fcntl = None  # type: ignore[assignment]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from install_steps.install_state import (
    DshStateSnapshot,
    capture_dsh_profile_snapshot,
    dsh_profile_matches_snapshot,
    get_dsh_profile,
    record_dsh_profile,
    remove_dsh_profile,
    restore_dsh_profile_snapshot,
    secure_dsh_state_mutation_supported,
)

SUPPORTED_DSH_VERSION = "0.1.1-rc.2"
MINIMUM_PNPM_VERSION = (11, 7, 0)
MAXIMUM_PNPM_VERSION_EXCLUSIVE = (12, 0, 0)
SUPPORTED_PNPM_RANGE = ">=11.7.0,<12.0.0"
DEFAULT_PROFILE = "web"
PRESET_NAME = "softspark-orchestrator"
PACKAGES = {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}
MANAGED_PACKAGE_NAMES = tuple(PACKAGES)
PROBE_TIMEOUT_SECONDS = 5
PACKAGE_MUTATION_TIMEOUT_SECONDS = 300
PROCESS_TERMINATION_GRACE_SECONDS = 1.0
PROCESS_GROUP_POLL_SECONDS = 0.01
MAX_TEARDOWN_INTERRUPT_RETRIES = 8
LIFECYCLE_LOCK_TIMEOUT_SECONDS = 1.0
LIFECYCLE_LOCK_POLL_SECONDS = 0.05
PROFILE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
EXACT_VERSION_PATTERN = re.compile(
    r"^[0-9]+\.[0-9]+\.[0-9]+"
    r"(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?"
    r"(?:\+[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?$"
)
PNPM_VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
)
RECOVERY_SUFFIXES = ("new", "backup", "uninstall", "package", "cleanup")
RECOVERY_TOKEN_BYTES = 12
RECOVERY_CLAIM_ATTEMPTS = 8
PROCESS_TREE_RECOVERY_PREFIX = ".ai-toolkit-lifecycle-tree-recovery-"
TREE_IDENTITY_DOMAIN = b"ai-toolkit-tree-identity-v1\0"
TREE_MAX_ENTRIES = 100_000
TREE_MAX_DEPTH = 128


class DshLifecycleError(RuntimeError):
    """A fail-closed DSH lifecycle error safe to show to the user."""


class _ProcessTreeTerminationError(DshLifecycleError):
    """The mutation process group could not be confirmed stopped."""

    def __init__(self, message: str, *, process_group: int, profile: str) -> None:
        super().__init__(message)
        self.process_group = process_group
        self.profile = profile


def _secure_mutation_supported() -> bool:
    required_dir_fd = {
        os.mkdir,
        os.open,
        os.readlink,
        os.rename,
        os.rmdir,
        os.stat,
        os.symlink,
        os.unlink,
    }
    if not (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "fchmod")
        and hasattr(os, "fsync")
        and required_dir_fd.issubset(os.supports_dir_fd)
        and os.stat in os.supports_follow_symlinks
        and sys.platform.startswith(("darwin", "linux"))
    ):
        return False
    try:
        library = ctypes.CDLL(None, use_errno=True)
        getattr(library, "renameatx_np" if sys.platform == "darwin" else "renameat2")
    except (AttributeError, OSError):
        return False
    return True


def _open_pinned_directory(path: Path) -> int:
    """Walk to one directory inode without following any ancestor symlink."""
    if not _secure_mutation_supported():
        raise DshLifecycleError(
            "secure DSH filesystem mutation is unsupported on this platform; "
            "use Linux, WSL, or macOS"
        )
    absolute = path if path.is_absolute() else Path.cwd() / path
    if ".." in absolute.parts:
        raise DshLifecycleError(f"unsafe secure mutation parent: {path}")
    descriptor = os.open(
        absolute.anchor,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    try:
        for component in absolute.parts[1:]:
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise DshLifecycleError(
                    f"secure mutation parent is not a directory: {path}"
                )
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            opened = os.fstat(child)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                os.close(child)
                raise DshLifecycleError(
                    f"secure mutation parent identity changed: {path}"
                )
            os.close(descriptor)
            descriptor = child
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        os.close(descriptor)
        raise
    return descriptor


def _secure_rename_noreplace(source: Path, destination: Path) -> None:
    """Atomically rename between pinned parents and never replace a destination."""
    _assert_active_dsh_home_binding()
    source_parent = _open_active_dsh_directory(source.parent)
    destination_parent = _open_active_dsh_directory(destination.parent)
    try:
        library = ctypes.CDLL(None, use_errno=True)
        source_name = os.fsencode(source.name)
        destination_name = os.fsencode(destination.name)
        if sys.platform == "darwin":
            operation = library.renameatx_np
            operation.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            operation.restype = ctypes.c_int
            result = operation(
                source_parent,
                source_name,
                destination_parent,
                destination_name,
                0x00000004,
            )
        elif sys.platform.startswith("linux"):
            operation = library.renameat2
            operation.argtypes = [
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            ]
            operation.restype = ctypes.c_int
            result = operation(
                source_parent,
                source_name,
                destination_parent,
                destination_name,
                0x00000001,
            )
        else:
            raise DshLifecycleError(
                "secure DSH filesystem mutation is unsupported on this platform"
            )
        if result != 0:
            code = ctypes.get_errno()
            if code in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(code, os.strerror(code), str(destination))
            if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
                raise DshLifecycleError(
                    "secure no-replace rename is unavailable; refusing mutation"
                )
            raise OSError(code, os.strerror(code), str(source))
        _assert_active_dsh_home_binding()
    finally:
        os.close(destination_parent)
        os.close(source_parent)


@dataclass(frozen=True)
class _PinnedDshHome:
    path: Path
    parent_descriptor: int
    root_descriptor: int
    parent_device: int
    parent_inode: int
    root_device: int
    root_inode: int


@dataclass(frozen=True)
class _LifecycleLock:
    path: Path
    descriptor: int
    device: int
    inode: int
    home: _PinnedDshHome


@dataclass(frozen=True)
class _ExecutablePrerequisite:
    name: str
    command_path: Path
    resolved_path: Path
    command_signature: tuple[int, ...]
    command_link_target: str | None
    resolved_signature: tuple[int, ...]


@dataclass(frozen=True)
class _PrerequisiteRecord:
    execution_path: str
    dsh: _ExecutablePrerequisite
    pnpm: _ExecutablePrerequisite


_ACTIVE_DSH_HOME: _PinnedDshHome | None = None
_ACTIVE_PREREQUISITES: _PrerequisiteRecord | None = None


def _pin_dsh_home(path: Path) -> _PinnedDshHome:
    """Pin the exact lexical DSH parent and root inodes for one lifecycle."""
    parent_descriptor = _open_pinned_directory(path.parent)
    root_descriptor: int | None = None
    try:
        parent_metadata = os.fstat(parent_descriptor)
        named = os.stat(
            path.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISDIR(named.st_mode):
            raise DshLifecycleError(f"DSH home is not a directory: {path}")
        root_descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_descriptor,
        )
        opened = os.fstat(root_descriptor)
        if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
            named.st_dev,
            named.st_ino,
        ):
            raise DshLifecycleError(f"DSH home identity changed: {path}")
        return _PinnedDshHome(
            path=path,
            parent_descriptor=parent_descriptor,
            root_descriptor=root_descriptor,
            parent_device=parent_metadata.st_dev,
            parent_inode=parent_metadata.st_ino,
            root_device=opened.st_dev,
            root_inode=opened.st_ino,
        )
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        if root_descriptor is not None:
            os.close(root_descriptor)
        os.close(parent_descriptor)
        raise


def _dsh_home_binding_matches(home: _PinnedDshHome) -> bool:
    try:
        parent = os.fstat(home.parent_descriptor)
        root = os.fstat(home.root_descriptor)
        if (
            not stat.S_ISDIR(parent.st_mode)
            or not stat.S_ISDIR(root.st_mode)
            or (parent.st_dev, parent.st_ino) != (home.parent_device, home.parent_inode)
            or (root.st_dev, root.st_ino) != (home.root_device, home.root_inode)
        ):
            return False
        current_parent = _open_pinned_directory(home.path.parent)
        try:
            current_parent_metadata = os.fstat(current_parent)
            if (current_parent_metadata.st_dev, current_parent_metadata.st_ino) != (
                home.parent_device,
                home.parent_inode,
            ):
                return False
        finally:
            os.close(current_parent)
        named = os.stat(
            home.path.name,
            dir_fd=home.parent_descriptor,
            follow_symlinks=False,
        )
        return stat.S_ISDIR(named.st_mode) and (
            named.st_dev,
            named.st_ino,
        ) == (home.root_device, home.root_inode)
    except (DshLifecycleError, OSError):
        return False


def _assert_dsh_home_binding(home: _PinnedDshHome) -> None:
    if not _dsh_home_binding_matches(home):
        raise DshLifecycleError(
            "DSH home identity changed; both roots were preserved; run "
            "'ai-toolkit dsh doctor' after restoring the intended DSH_HOME"
        )


def _assert_active_dsh_home_binding() -> None:
    if _ACTIVE_DSH_HOME is not None:
        _assert_dsh_home_binding(_ACTIVE_DSH_HOME)


def _close_pinned_dsh_home(home: _PinnedDshHome) -> None:
    os.close(home.root_descriptor)
    os.close(home.parent_descriptor)


def _directory_lifecycle_lock_supported() -> bool:
    return (
        os.name == "posix"
        and fcntl is not None
        and hasattr(fcntl, "flock")
        and hasattr(fcntl, "LOCK_EX")
        and hasattr(fcntl, "LOCK_NB")
        and hasattr(fcntl, "LOCK_UN")
    )


def _acquire_dsh_home_directory_lock(home: _PinnedDshHome) -> None:
    if not _directory_lifecycle_lock_supported():
        raise DshLifecycleError(
            "DSH home directory lifecycle locking is unsupported; "
            "use Linux, WSL, or macOS"
        )
    try:
        fcntl.flock(home.root_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise DshLifecycleError(
            "DSH home directory lifecycle lock is busy"
        ) from error
    except OSError as error:
        raise DshLifecycleError(
            "unable to acquire DSH home directory lifecycle lock"
        ) from error


def _release_dsh_home_directory_lock(home: _PinnedDshHome) -> None:
    if fcntl is None:
        return
    try:
        fcntl.flock(home.root_descriptor, fcntl.LOCK_UN)
    except OSError as error:
        raise DshLifecycleError(
            "unable to release DSH home directory lifecycle lock"
        ) from error


def _cleanup_failed_lifecycle_lock(
    path: Path,
    home: _PinnedDshHome,
    identity: tuple[int, int],
) -> Path | None:
    """Remove only the exact lock inode created by failed initialization."""
    recovery = path.parent / (
        f".ai-toolkit-lifecycle-lock-init-{os.getpid()}-"
        f"{secrets.token_hex(RECOVERY_TOKEN_BYTES)}"
    )
    try:
        named = os.stat(
            path.name,
            dir_fd=home.root_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(named.st_mode) or (
            named.st_dev,
            named.st_ino,
        ) != identity:
            return path
        _secure_rename_noreplace_at(
            home.root_descriptor,
            path.name,
            recovery.name,
        )
        moved = os.stat(
            recovery.name,
            dir_fd=home.root_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(moved.st_mode) or (
            moved.st_dev,
            moved.st_ino,
        ) != identity:
            return recovery
        os.unlink(recovery.name, dir_fd=home.root_descriptor)
        return None
    except BaseException:
        try:
            os.stat(
                recovery.name,
                dir_fd=home.root_descriptor,
                follow_symlinks=False,
            )
        except (FileNotFoundError, OSError):
            return path
        return recovery


def _lifecycle_lock_recovery_artifacts(dsh_home: Path) -> tuple[Path, ...]:
    """Return doctor-visible lock files left by interrupted initialization."""
    candidates = {dsh_home / ".ai-toolkit-lifecycle.lock"}
    try:
        candidates.update(dsh_home.glob(".ai-toolkit-lifecycle-lock-init-*"))
        candidates.update(dsh_home.glob(".ai-toolkit-lifecycle-lock-release-*"))
        candidates.update(dsh_home.glob(f"{PROCESS_TREE_RECOVERY_PREFIX}*"))
    except OSError:
        pass
    return tuple(
        sorted(
            (
                path
                for path in candidates
                if path.exists() or path.is_symlink()
            ),
            key=str,
        )
    )


def _process_tree_recovery_artifacts_at(
    home: _PinnedDshHome,
) -> tuple[Path, ...]:
    _assert_dsh_home_binding(home)
    try:
        names = os.listdir(home.root_descriptor)
    except OSError as error:
        raise DshLifecycleError(
            "unable to inspect DSH process-tree recovery gates"
        ) from error
    return tuple(
        sorted(
            (
                home.path / name
                for name in names
                if name.startswith(PROCESS_TREE_RECOVERY_PREFIX)
            ),
            key=str,
        )
    )


def _assert_no_process_tree_recovery_gate(home: _PinnedDshHome) -> None:
    artifacts = _process_tree_recovery_artifacts_at(home)
    if artifacts:
        raise DshLifecycleError(
            "DSH lifecycle recovery gate blocks mutation; run "
            f"'ai-toolkit dsh doctor' and inspect: {artifacts[0]}"
        )


def _read_lifecycle_lock_fields(descriptor: int) -> dict[str, str]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    payload = os.read(descriptor, 4096).decode("ascii", errors="replace")
    fields: dict[str, str] = {}
    for line in payload.splitlines():
        name, separator, value = line.partition("=")
        if separator and name:
            fields[name] = value
    return fields


def _read_lifecycle_lock_fields_at(
    home: _PinnedDshHome,
    path: Path,
    identity: tuple[int, int],
) -> dict[str, str]:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path.name, flags, dir_fd=home.root_descriptor)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or (
            metadata.st_dev,
            metadata.st_ino,
        ) != identity:
            raise DshLifecycleError(
                f"DSH lifecycle lock identity changed while reading: {path}"
            )
        return _read_lifecycle_lock_fields(descriptor)
    finally:
        os.close(descriptor)


def _read_lifecycle_recovery_gate(path: Path) -> dict[str, str] | None:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return None
        fields = _read_lifecycle_lock_fields(descriptor)
        return fields if fields.get("state") == "recovery" else None
    except OSError:
        return None
    finally:
        os.close(descriptor)


def _acquire_lifecycle_lock(dsh_home: Path) -> _LifecycleLock:
    """Claim one DSH home without following or deleting an existing lock."""
    path = dsh_home / ".ai-toolkit-lifecycle.lock"
    home = _pin_dsh_home(dsh_home)
    try:
        _acquire_dsh_home_directory_lock(home)
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        _close_pinned_dsh_home(home)
        raise
    deadline = time.monotonic() + LIFECYCLE_LOCK_TIMEOUT_SECONDS
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    while True:
        try:
            _assert_dsh_home_binding(home)
            _assert_no_process_tree_recovery_gate(home)
            descriptor = os.open(
                path.name,
                flags,
                0o600,
                dir_fd=home.root_descriptor,
            )
        except FileExistsError:
            try:
                metadata = os.stat(
                    path.name,
                    dir_fd=home.root_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            except OSError as error:
                _close_pinned_dsh_home(home)
                raise DshLifecycleError(
                    f"DSH lifecycle lock is unreadable: {path}"
                ) from error
            if not _dsh_home_binding_matches(home):
                _close_pinned_dsh_home(home)
                raise DshLifecycleError(
                    "DSH home identity changed; both roots were preserved"
                )
            if not stat.S_ISREG(metadata.st_mode):
                _close_pinned_dsh_home(home)
                raise DshLifecycleError(
                    f"DSH lifecycle lock is not a regular file: {path}"
                )
            fields = _read_lifecycle_lock_fields_at(
                home,
                path,
                (metadata.st_dev, metadata.st_ino),
            )
            if fields.get("state") == "recovery":
                _close_pinned_dsh_home(home)
                raise DshLifecycleError(
                    "DSH lifecycle recovery gate blocks mutation; run "
                    f"'ai-toolkit dsh doctor' and inspect: {path}"
                )
            if time.monotonic() >= deadline:
                _close_pinned_dsh_home(home)
                raise DshLifecycleError(
                    f"DSH lifecycle lock timed out after "
                    f"{LIFECYCLE_LOCK_TIMEOUT_SECONDS:.1f}s: {path}"
                )
            time.sleep(LIFECYCLE_LOCK_POLL_SECONDS)
        except OSError as error:
            _close_pinned_dsh_home(home)
            raise DshLifecycleError(
                f"unable to acquire DSH lifecycle lock: {path}"
            ) from error
        except DshLifecycleError:
            _close_pinned_dsh_home(home)
            raise
        else:
            identity: tuple[int, int] | None = None
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise DshLifecycleError(
                        f"DSH lifecycle lock is not a regular file: {path}"
                    )
                identity = metadata.st_dev, metadata.st_ino
                _assert_no_process_tree_recovery_gate(home)
                os.write(descriptor, f"pid={os.getpid()}\n".encode("ascii"))
                os.fsync(descriptor)
                return _LifecycleLock(
                    path,
                    descriptor,
                    metadata.st_dev,
                    metadata.st_ino,
                    home,
                )
            except BaseException as error:
                artifact = (
                    path
                    if identity is None
                    else _cleanup_failed_lifecycle_lock(path, home, identity)
                )
                close_error: BaseException | None = None
                try:
                    os.close(descriptor)
                except BaseException as caught:
                    close_error = caught
                try:
                    _close_pinned_dsh_home(home)
                except BaseException as caught:
                    close_error = close_error or caught
                if artifact is not None or close_error is not None:
                    recovery = artifact or path
                    raise DshLifecycleError(
                        "unable to initialize DSH lifecycle lock; "
                        f"Recovery artifact: {str(recovery)!r}"
                    ) from error
                if isinstance(error, KeyboardInterrupt):
                    raise
                if isinstance(error, DshLifecycleError):
                    raise
                raise DshLifecycleError(
                    f"unable to acquire DSH lifecycle lock: {path}"
                ) from error


def _secure_rename_noreplace_at(
    parent_descriptor: int,
    source_name: str,
    destination_name: str,
) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    operation = library.renameatx_np if sys.platform == "darwin" else library.renameat2
    operation.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    operation.restype = ctypes.c_int
    flag = 0x00000004 if sys.platform == "darwin" else 0x00000001
    result = operation(
        parent_descriptor,
        os.fsencode(source_name),
        parent_descriptor,
        os.fsencode(destination_name),
        flag,
    )
    if result == 0:
        return
    code = ctypes.get_errno()
    if code in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(code, os.strerror(code), destination_name)
    if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
        raise DshLifecycleError(
            "secure no-replace rename is unavailable; refusing mutation"
        )
    raise OSError(code, os.strerror(code), source_name)


def _release_lifecycle_lock(lock: _LifecycleLock) -> None:
    """Release only the exact regular inode claimed by this process."""
    recovery = lock.path.parent / (
        f".ai-toolkit-lifecycle-lock-release-{os.getpid()}-"
        f"{secrets.token_hex(RECOVERY_TOKEN_BYTES)}"
    )
    binding_matches = _dsh_home_binding_matches(lock.home)
    try:
        _secure_rename_noreplace_at(
            lock.home.root_descriptor,
            lock.path.name,
            recovery.name,
        )
        metadata = os.stat(
            recovery.name,
            dir_fd=lock.home.root_descriptor,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(metadata.st_mode) or (
            metadata.st_dev,
            metadata.st_ino,
        ) != (lock.device, lock.inode):
            raise DshLifecycleError(
                f"DSH lifecycle lock identity changed; preserved: {recovery}"
            )
        os.unlink(recovery.name, dir_fd=lock.home.root_descriptor)
        if not binding_matches or not _dsh_home_binding_matches(lock.home):
            raise DshLifecycleError(
                "DSH home identity changed; both roots were preserved; run "
                "'ai-toolkit dsh doctor' after restoring the intended DSH_HOME"
            )
    except DshLifecycleError:
        raise
    except OSError as error:
        raise DshLifecycleError(
            f"unable to release DSH lifecycle lock; inspect: {lock.path}"
        ) from error
    finally:
        os.close(lock.descriptor)
        try:
            _release_dsh_home_directory_lock(lock.home)
        finally:
            _close_pinned_dsh_home(lock.home)


def _find_process_tree_termination(
    error: BaseException,
) -> _ProcessTreeTerminationError | None:
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, _ProcessTreeTerminationError):
            return current
        current = current.__cause__ or current.__context__
    return None


def _preserve_lifecycle_recovery_gate(
    lock: _LifecycleLock,
    termination: _ProcessTreeTerminationError,
) -> None:
    """Close the lock while preserving its inode as a durable recovery gate."""
    payload = (
        "state=recovery\n"
        "reason=unconfirmed-process-tree\n"
        f"owner_pid={os.getpid()}\n"
        f"process_group={termination.process_group}\n"
        f"profile={termination.profile}\n"
    ).encode("ascii")
    write_error: BaseException | None = None
    try:
        canonical_matches = _lifecycle_lock_binding_matches(lock)
        _create_process_tree_recovery_gate(lock.home, payload)
        if canonical_matches and _lifecycle_lock_binding_matches(lock):
            os.ftruncate(lock.descriptor, 0)
            os.lseek(lock.descriptor, 0, os.SEEK_SET)
            _write_all(lock.descriptor, payload)
            os.fsync(lock.descriptor)
    except BaseException as error:
        write_error = error
    finally:
        close_error: BaseException | None = None
        try:
            os.close(lock.descriptor)
        except BaseException as error:
            close_error = error
        try:
            _release_dsh_home_directory_lock(lock.home)
        except BaseException as error:
            close_error = close_error or error
        try:
            _close_pinned_dsh_home(lock.home)
        except BaseException as error:
            close_error = close_error or error
    if write_error is not None or close_error is not None:
        raise DshLifecycleError(
            "DSH process-tree recovery gate was preserved but its metadata "
            f"could not be finalized; inspect: {lock.path}"
        ) from (write_error or close_error)


def _lifecycle_lock_binding_matches(lock: _LifecycleLock) -> bool:
    try:
        descriptor = os.fstat(lock.descriptor)
        canonical = os.stat(
            lock.path.name,
            dir_fd=lock.home.root_descriptor,
            follow_symlinks=False,
        )
    except OSError:
        return False
    expected = lock.device, lock.inode
    return (
        _dsh_home_binding_matches(lock.home)
        and stat.S_ISREG(descriptor.st_mode)
        and stat.S_ISREG(canonical.st_mode)
        and (descriptor.st_dev, descriptor.st_ino) == expected
        and (canonical.st_dev, canonical.st_ino) == expected
    )


def _create_process_tree_recovery_gate(
    home: _PinnedDshHome,
    payload: bytes,
) -> Path:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    for _ in range(RECOVERY_CLAIM_ATTEMPTS):
        name = (
            f"{PROCESS_TREE_RECOVERY_PREFIX}{os.getpid()}-"
            f"{secrets.token_hex(RECOVERY_TOKEN_BYTES)}"
        )
        path = home.path / name
        try:
            descriptor = os.open(name, flags, 0o600, dir_fd=home.root_descriptor)
        except FileExistsError:
            continue
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise DshLifecycleError(
                    f"DSH process-tree recovery gate is not regular: {path}"
                )
            _write_all(descriptor, payload)
            os.fsync(descriptor)
            os.fsync(home.root_descriptor)
            return path
        finally:
            os.close(descriptor)
    raise DshLifecycleError("unable to claim DSH process-tree recovery gate")


@contextmanager
def _locked_lifecycle(dsh_home: Path, prerequisites: _PrerequisiteRecord):
    global _ACTIVE_DSH_HOME, _ACTIVE_PREREQUISITES
    lock = _acquire_lifecycle_lock(dsh_home)
    previous_home = _ACTIVE_DSH_HOME
    previous_prerequisites = _ACTIVE_PREREQUISITES
    _ACTIVE_DSH_HOME = lock.home
    _ACTIVE_PREREQUISITES = prerequisites
    try:
        _assert_dsh_home_binding(lock.home)
        _assert_prerequisites_unchanged(prerequisites)
        yield lock.home
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        termination = _find_process_tree_termination(error)
        if termination is not None:
            _preserve_lifecycle_recovery_gate(lock, termination)
            raise
        try:
            _release_lifecycle_lock(lock)
        except (DshLifecycleError, OSError, KeyboardInterrupt) as release_error:
            raise DshLifecycleError(
                f"{error}\nRecovery required; DSH lifecycle lock cleanup failed: "
                f"{release_error}"
            ) from error
        raise
    else:
        _release_lifecycle_lock(lock)
    finally:
        _ACTIVE_PREREQUISITES = previous_prerequisites
        _ACTIVE_DSH_HOME = previous_home


def _regular_file_signature(metadata: os.stat_result) -> tuple[int, ...]:
    """Return the complete stable-read signature for one regular file."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_declared_regular_size(
    descriptor: int,
    *,
    declared_size: int,
    path: Path,
) -> bytes:
    """Read exactly one declared file size and reject early EOF or growth."""
    remaining = declared_size
    chunks: list[bytes] = []
    while remaining:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            raise DshLifecycleError(f"managed file changed while reading: {path}")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise DshLifecycleError(f"managed file changed while reading: {path}")
    return b"".join(chunks)


def _stable_regular_file_bytes(path: Path) -> tuple[bytes, os.stat_result]:
    """Read bytes and metadata from one pathname-bound regular-file inode."""
    parent: int | None = None
    descriptor: int | None = None
    try:
        parent = _open_active_dsh_directory(path.parent)
        named_before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISREG(named_before.st_mode):
            raise DshLifecycleError(f"managed file is not regular: {path}")
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW,
            dir_fd=parent,
        )
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or _regular_file_signature(
            opened
        ) != _regular_file_signature(named_before):
            raise DshLifecycleError(f"managed file identity changed: {path}")
        content = _read_declared_regular_size(
            descriptor,
            declared_size=opened.st_size,
            path=path,
        )
        after_read = os.fstat(descriptor)
        named_after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        signature = _regular_file_signature(opened)
        if (
            not stat.S_ISREG(after_read.st_mode)
            or not stat.S_ISREG(named_after.st_mode)
            or _regular_file_signature(after_read) != signature
            or _regular_file_signature(named_after) != signature
            or not _pinned_directory_path_matches(path.parent, parent)
        ):
            raise DshLifecycleError(f"managed file identity changed: {path}")
        return content, opened
    except DshLifecycleError:
        raise
    except OSError as error:
        raise DshLifecycleError(f"managed file is unreadable: {path}") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


def _read_regular_bytes(path: Path) -> bytes:
    """Read one stable regular-file inode without following a symlink."""
    content, _metadata = _stable_regular_file_bytes(path)
    return content


@dataclass(frozen=True)
class _OwnedEntry:
    path: Path
    device: int
    inode: int
    kind: str
    digest: str | None = None
    link_target: str | None = None
    parent_device: int | None = None
    parent_inode: int | None = None


@dataclass(frozen=True)
class _RecoveryLocation:
    root: _OwnedEntry
    payload: Path


@dataclass(frozen=True)
class _RelocatedPreset:
    location: _RecoveryLocation
    payload: _OwnedEntry


@dataclass(frozen=True)
class _PathPrestate:
    path: Path
    kind: str
    mode: int
    content: bytes | None = None
    link_target: str | None = None


@dataclass
class _ProfileTransaction:
    profile_root: Path
    base_existed: dict[Path, bool]
    manifest: _PathPrestate | None
    package_trees: dict[Path, dict[Path, _PathPrestate] | None]
    created_base: dict[Path, _OwnedEntry]
    latest_manifest: _OwnedEntry | None = None
    latest_package_identity: _PackageMutationIdentity | None = None
    rollback_blocked: bool = False


@dataclass(frozen=True)
class _PackageMutationIdentity:
    manifest: _PathPrestate | None
    package_trees: dict[Path, dict[Path, _PathPrestate] | None]


@dataclass(frozen=True)
class _RecoveryCommandTarget:
    profile: str
    managed_packages: dict[str, str]
    unmanaged_dependencies: dict[str, dict[str, object]]
    package_trees: dict[Path, dict[Path, _PathPrestate] | None]


def _path_prestate(path: Path) -> _PathPrestate:
    metadata = path.stat(follow_symlinks=False)
    mode = stat.S_IFMT(metadata.st_mode)
    permissions = metadata.st_mode & 0o777
    if stat.S_ISLNK(mode):
        return _PathPrestate(
            path, "symlink", permissions, link_target=os.readlink(path)
        )
    if stat.S_ISDIR(mode):
        return _PathPrestate(path, "directory", permissions)
    if stat.S_ISREG(mode):
        content, stable_metadata = _stable_regular_file_bytes(path)
        return _PathPrestate(
            path,
            "file",
            stat.S_IMODE(stable_metadata.st_mode),
            content=content,
        )
    raise DshLifecycleError(f"unsupported entry in managed package prestate: {path}")


def _snapshot_tree(root: Path) -> dict[Path, _PathPrestate] | None:
    if not root.exists() and not root.is_symlink():
        return None
    root_snapshot = _path_prestate(root)
    if root_snapshot.kind != "directory":
        raise DshLifecycleError(f"managed package root is not a directory: {root}")
    snapshots = {root: root_snapshot}
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            children = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as error:
            raise DshLifecycleError(
                f"unable to snapshot managed package root: {root}"
            ) from error
        for child in children:
            snapshot = _path_prestate(child)
            snapshots[child] = snapshot
            if snapshot.kind == "directory":
                pending.append(child)
    return snapshots


def _capture_package_mutation_identity(
    profile_root: Path,
) -> _PackageMutationIdentity:
    manifest_path = profile_root / "package.json"
    manifest = (
        _path_prestate(manifest_path)
        if manifest_path.exists() or manifest_path.is_symlink()
        else None
    )
    package_trees = {
        profile_root / "node_modules" / Path(package): _snapshot_tree(
            profile_root / "node_modules" / Path(package)
        )
        for package in PACKAGES
    }
    return _PackageMutationIdentity(manifest, package_trees)


def _capture_profile_transaction(dsh_home: Path, profile: str) -> _ProfileTransaction:
    profile_root = dsh_home / "profiles" / profile
    node_modules = profile_root / "node_modules"
    namespace = node_modules / "@softspark"
    base_paths = (profile_root, node_modules, namespace)
    base_existed = {
        path: path.exists() and path.is_dir() and not path.is_symlink()
        for path in base_paths
    }
    manifest_path = profile_root / "package.json"
    manifest = (
        _path_prestate(manifest_path)
        if manifest_path.exists() or manifest_path.is_symlink()
        else None
    )
    if manifest is not None and manifest.kind != "file":
        raise DshLifecycleError(f"unsafe DSH profile package manifest: {manifest_path}")
    package_trees = {
        profile_root / "node_modules" / Path(package): _snapshot_tree(
            profile_root / "node_modules" / Path(package)
        )
        for package in PACKAGES
    }
    transaction = _ProfileTransaction(
        profile_root,
        base_existed,
        manifest,
        package_trees,
        {},
    )
    transaction.latest_package_identity = _capture_package_mutation_identity(
        profile_root
    )
    _observe_profile_transaction(transaction)
    return transaction


def _observe_profile_transaction(transaction: _ProfileTransaction) -> None:
    for path, existed in transaction.base_existed.items():
        if existed or path in transaction.created_base:
            continue
        if path.exists() and path.is_dir() and not path.is_symlink():
            device, inode = _entry_identity(path)
            transaction.created_base[path] = _OwnedEntry(
                path, device, inode, "directory"
            )
    manifest_path = transaction.profile_root / "package.json"
    if manifest_path.exists() or manifest_path.is_symlink():
        try:
            transaction.latest_manifest = _capture_entry(manifest_path)
        except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
            transaction.latest_manifest = None
    else:
        transaction.latest_manifest = None


def _run_profile_command(
    argv: list[str],
    *,
    dsh_home: Path,
    transaction: _ProfileTransaction,
    recovery_target: _RecoveryCommandTarget | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        before = _capture_package_mutation_identity(transaction.profile_root)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        transaction.rollback_blocked = True
        raise DshLifecycleError(
            "package identity unreadable before external mutation; refusing"
        ) from error
    if transaction.latest_package_identity != before:
        transaction.rollback_blocked = True
        raise DshLifecycleError(
            "package identity changed before external mutation; refusing"
        )
    try:
        result = _run(argv, dsh_home=dsh_home)
    except _ProcessTreeTerminationError:
        transaction.rollback_blocked = True
        raise
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        try:
            after = _capture_package_mutation_identity(transaction.profile_root)
        except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
            after = None
            transaction.rollback_blocked = True
        transaction.latest_package_identity = after
        _observe_profile_transaction(transaction)
        if after != before:
            transaction.rollback_blocked = True
            description = (
                "DSH command was interrupted"
                if isinstance(error, KeyboardInterrupt)
                else str(error)
            )
            raise DshLifecycleError(
                f"{description}; package identity changed during failed external mutation"
            ) from error
        raise
    try:
        after = _capture_package_mutation_identity(transaction.profile_root)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        transaction.rollback_blocked = True
        raise DshLifecycleError(
            "package identity unreadable after external mutation; recovery required"
        ) from error
    _observe_profile_transaction(transaction)
    if recovery_target is not None:
        try:
            found_managed = _profile_package_versions(dsh_home, recovery_target.profile)
            found_unmanaged = _profile_unmanaged_dependencies(
                dsh_home, recovery_target.profile
            )
        except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
            transaction.rollback_blocked = True
            raise DshLifecycleError(
                "package recovery target unreadable after external mutation"
            ) from error
        if (
            found_managed != recovery_target.managed_packages
            or found_unmanaged != recovery_target.unmanaged_dependencies
            or after.package_trees != recovery_target.package_trees
        ):
            transaction.rollback_blocked = True
            raise DshLifecycleError(
                "package recovery target drifted during successful external mutation"
            )
    transaction.latest_package_identity = after
    return result


def _pinned_directory_path_matches(path: Path, descriptor: int) -> bool:
    """Confirm the pathname still resolves to the already pinned directory."""
    try:
        current = _open_pinned_directory(path)
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        return False
    try:
        expected_metadata = os.fstat(descriptor)
        current_metadata = os.fstat(current)
        return (expected_metadata.st_dev, expected_metadata.st_ino) == (
            current_metadata.st_dev,
            current_metadata.st_ino,
        )
    finally:
        os.close(current)


def _open_active_dsh_directory(path: Path) -> int:
    """Open a directory through the active pinned DSH root when available."""
    home = _ACTIVE_DSH_HOME
    if home is None:
        return _open_pinned_directory(path)
    _assert_dsh_home_binding(home)
    try:
        relative = path.relative_to(home.path)
    except ValueError as error:
        raise DshLifecycleError(
            f"secure mutation path is outside the active DSH home: {path}"
        ) from error
    if ".." in relative.parts:
        raise DshLifecycleError(f"unsafe secure mutation parent: {path}")
    descriptor = os.dup(home.root_descriptor)
    try:
        for component in relative.parts:
            before = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise DshLifecycleError(
                    f"secure mutation parent is not a directory: {path}"
                )
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            opened = os.fstat(child)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                os.close(child)
                raise DshLifecycleError(
                    f"secure mutation parent identity changed: {path}"
                )
            os.close(descriptor)
            descriptor = child
        _assert_dsh_home_binding(home)
        return descriptor
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        os.close(descriptor)
        raise


def _write_all(descriptor: int, content: bytes) -> None:
    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short write while restoring managed package snapshot")
        remaining = remaining[written:]


def _discard_pinned_temporary(
    parent: int,
    name: str,
    descriptor: int,
) -> bool:
    """Remove only the still-named temporary inode through its pinned parent."""
    try:
        opened = os.fstat(descriptor)
        named = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(named.st_mode)
            or (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            return False
        os.unlink(name, dir_fd=parent)
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return True
        return False
    except FileNotFoundError:
        return True
    except OSError:
        return False


def _create_pinned_temporary(
    parent: int, *, prefix: str, suffix: str
) -> tuple[int, str]:
    """Create one exclusive regular temporary file below a pinned directory."""
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    for _attempt in range(RECOVERY_CLAIM_ATTEMPTS):
        name = f"{prefix}{secrets.token_hex(RECOVERY_TOKEN_BYTES)}{suffix}"
        descriptor: int | None = None
        try:
            _assert_active_dsh_home_binding()
            descriptor = os.open(name, flags, 0o600, dir_fd=parent)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise DshLifecycleError(
                    "manifest rollback temporary is not a regular file"
                )
            _assert_active_dsh_home_binding()
            return descriptor, name
        except FileExistsError:
            if descriptor is not None:
                os.close(descriptor)
            continue
        except (DshLifecycleError, OSError, KeyboardInterrupt):
            if descriptor is not None:
                _discard_pinned_temporary(parent, name, descriptor)
                os.close(descriptor)
            raise
    raise DshLifecycleError("unable to claim manifest rollback temporary")


def _descriptor_digest(descriptor: int) -> tuple[int, str]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    while chunk := os.read(descriptor, 1024 * 1024):
        size += len(chunk)
        digest.update(chunk)
    return size, digest.hexdigest()


def _content_metadata_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _created_file_matches(
    *,
    parent: int,
    descriptor: int,
    name: str,
    snapshot: _PathPrestate,
    created: os.stat_result,
) -> bool:
    content = snapshot.content or b""
    opened = os.fstat(descriptor)
    size, digest = _descriptor_digest(descriptor)
    after_read = os.fstat(descriptor)
    named = os.stat(name, dir_fd=parent, follow_symlinks=False)
    identity = (created.st_dev, created.st_ino)
    return (
        stat.S_ISREG(opened.st_mode)
        and (opened.st_dev, opened.st_ino) == identity
        and (after_read.st_dev, after_read.st_ino) == identity
        and (named.st_dev, named.st_ino) == identity
        and _content_metadata_signature(opened)
        == _content_metadata_signature(after_read)
        == _content_metadata_signature(named)
        and stat.S_IMODE(opened.st_mode) == snapshot.mode
        and stat.S_IMODE(named.st_mode) == snapshot.mode
        and size == len(content)
        and digest == hashlib.sha256(content).hexdigest()
    )


def _create_snapshot_file(snapshot: _PathPrestate, parent: int) -> bool:
    _assert_active_dsh_home_binding()
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(snapshot.path.name, flags, snapshot.mode, dir_fd=parent)
    try:
        created = os.fstat(descriptor)
        if not stat.S_ISREG(created.st_mode):
            return False
        _write_all(descriptor, snapshot.content or b"")
        os.fsync(descriptor)
        os.fchmod(descriptor, snapshot.mode)
        created_matches = _created_file_matches(
            parent=parent,
            descriptor=descriptor,
            name=snapshot.path.name,
            snapshot=snapshot,
            created=created,
        )
        _assert_active_dsh_home_binding()
        return created_matches
    finally:
        os.close(descriptor)


def _create_snapshot_directory(snapshot: _PathPrestate, parent: int) -> bool:
    _assert_active_dsh_home_binding()
    os.mkdir(snapshot.path.name, snapshot.mode, dir_fd=parent)
    descriptor = os.open(
        snapshot.path.name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        dir_fd=parent,
    )
    try:
        created = os.fstat(descriptor)
        if not stat.S_ISDIR(created.st_mode):
            return False
        os.fchmod(descriptor, snapshot.mode)
        opened = os.fstat(descriptor)
        named = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
        identity = (created.st_dev, created.st_ino)
        created_matches = (
            (opened.st_dev, opened.st_ino) == identity
            and (named.st_dev, named.st_ino) == identity
            and stat.S_ISDIR(opened.st_mode)
            and stat.S_ISDIR(named.st_mode)
            and stat.S_IMODE(opened.st_mode) == snapshot.mode
            and stat.S_IMODE(named.st_mode) == snapshot.mode
        )
        _assert_active_dsh_home_binding()
        return created_matches
    finally:
        os.close(descriptor)


def _create_snapshot_symlink(snapshot: _PathPrestate, parent: int) -> bool:
    _assert_active_dsh_home_binding()
    target = snapshot.link_target or ""
    os.symlink(target, snapshot.path.name, dir_fd=parent)
    before = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
    observed_target = os.readlink(snapshot.path.name, dir_fd=parent)
    after = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
    created_matches = (
        stat.S_ISLNK(before.st_mode)
        and stat.S_ISLNK(after.st_mode)
        and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        and stat.S_IMODE(before.st_mode) == snapshot.mode
        and stat.S_IMODE(after.st_mode) == snapshot.mode
        and observed_target == target
    )
    _assert_active_dsh_home_binding()
    return created_matches


def _create_snapshot_entry(snapshot: _PathPrestate) -> bool:
    parent: int | None = None
    try:
        parent = _open_active_dsh_directory(snapshot.path.parent)
        if snapshot.kind == "file":
            created = _create_snapshot_file(snapshot, parent)
        elif snapshot.kind == "directory":
            created = _create_snapshot_directory(snapshot, parent)
        elif snapshot.kind == "symlink":
            created = _create_snapshot_symlink(snapshot, parent)
        else:
            return False
        return created and _pinned_directory_path_matches(snapshot.path.parent, parent)
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        return False
    finally:
        if parent is not None:
            os.close(parent)


def _secure_restore_file_snapshot(
    snapshot: _PathPrestate,
    parent: int,
    before: os.stat_result,
) -> bool:
    _assert_active_dsh_home_binding()
    descriptor = os.open(
        snapshot.path.name,
        os.O_RDONLY | os.O_NOFOLLOW,
        dir_fd=parent,
    )
    try:
        opened = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (
                opened.st_dev,
                opened.st_ino,
            )
            != identity
        ):
            return False
        content = snapshot.content or b""
        size, digest = _descriptor_digest(descriptor)
        verified = os.fstat(descriptor)
        if size != len(content) or digest != hashlib.sha256(content).hexdigest():
            return False
        if _content_metadata_signature(opened) != _content_metadata_signature(verified):
            return False
        if stat.S_IMODE(opened.st_mode) != snapshot.mode:
            if not _pinned_directory_path_matches(snapshot.path.parent, parent):
                return False
            _assert_active_dsh_home_binding()
            os.fchmod(descriptor, snapshot.mode)
            _assert_active_dsh_home_binding()
            if not _pinned_directory_path_matches(snapshot.path.parent, parent):
                return False
        before_final_read = os.fstat(descriptor)
        final_size, final_digest = _descriptor_digest(descriptor)
        final = os.fstat(descriptor)
        named = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
        restored = (
            (final.st_dev, final.st_ino) == identity
            and (named.st_dev, named.st_ino) == identity
            and _content_metadata_signature(before_final_read)
            == _content_metadata_signature(final)
            == _content_metadata_signature(named)
            and stat.S_ISREG(final.st_mode)
            and stat.S_ISREG(named.st_mode)
            and stat.S_IMODE(final.st_mode) == snapshot.mode
            and stat.S_IMODE(named.st_mode) == snapshot.mode
            and final_size == len(content)
            and final_digest == hashlib.sha256(content).hexdigest()
        )
        _assert_active_dsh_home_binding()
        return restored
    finally:
        os.close(descriptor)


def _secure_restore_directory_snapshot(
    snapshot: _PathPrestate,
    parent: int,
    before: os.stat_result,
) -> bool:
    _assert_active_dsh_home_binding()
    descriptor = os.open(
        snapshot.path.name,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
        dir_fd=parent,
    )
    try:
        opened = os.fstat(descriptor)
        identity = (before.st_dev, before.st_ino)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or (
                opened.st_dev,
                opened.st_ino,
            )
            != identity
        ):
            return False
        if stat.S_IMODE(opened.st_mode) != snapshot.mode:
            if not _pinned_directory_path_matches(snapshot.path.parent, parent):
                return False
            _assert_active_dsh_home_binding()
            os.fchmod(descriptor, snapshot.mode)
            _assert_active_dsh_home_binding()
            if not _pinned_directory_path_matches(snapshot.path.parent, parent):
                return False
        final = os.fstat(descriptor)
        named = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
        restored = (
            (final.st_dev, final.st_ino) == identity
            and (named.st_dev, named.st_ino) == identity
            and stat.S_ISDIR(final.st_mode)
            and stat.S_ISDIR(named.st_mode)
            and stat.S_IMODE(final.st_mode) == snapshot.mode
            and stat.S_IMODE(named.st_mode) == snapshot.mode
        )
        _assert_active_dsh_home_binding()
        return restored
    finally:
        os.close(descriptor)


def _secure_restore_symlink_snapshot(
    snapshot: _PathPrestate,
    parent: int,
    before: os.stat_result,
) -> bool:
    target = os.readlink(snapshot.path.name, dir_fd=parent)
    after = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
    return (
        stat.S_ISLNK(before.st_mode)
        and stat.S_ISLNK(after.st_mode)
        and (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        and stat.S_IMODE(before.st_mode) == snapshot.mode
        and stat.S_IMODE(after.st_mode) == snapshot.mode
        and target == (snapshot.link_target or "")
    )


def _secure_restore_snapshot_entry(
    snapshot: _PathPrestate,
    *,
    expected_entry: _OwnedEntry | None = None,
) -> bool:
    parent: int | None = None
    try:
        _assert_active_dsh_home_binding()
        parent = _open_active_dsh_directory(snapshot.path.parent)
        if not _pinned_directory_path_matches(snapshot.path.parent, parent):
            return False
        before = os.stat(snapshot.path.name, dir_fd=parent, follow_symlinks=False)
        if expected_entry is not None and (
            before.st_dev,
            before.st_ino,
        ) != (expected_entry.device, expected_entry.inode):
            return False
        if snapshot.kind == "file":
            restored = _secure_restore_file_snapshot(snapshot, parent, before)
        elif snapshot.kind == "directory":
            restored = _secure_restore_directory_snapshot(snapshot, parent, before)
        elif snapshot.kind == "symlink":
            restored = _secure_restore_symlink_snapshot(snapshot, parent, before)
        else:
            return False
        _assert_active_dsh_home_binding()
        return restored and _pinned_directory_path_matches(snapshot.path.parent, parent)
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        return False
    finally:
        if parent is not None:
            os.close(parent)


def _restore_tree_prestate(
    root: Path,
    snapshots: dict[Path, _PathPrestate] | None,
) -> list[Path]:
    if snapshots is None:
        return [root] if root.exists() or root.is_symlink() else []
    residuals: list[Path] = []
    ordered = sorted(
        snapshots.values(),
        key=lambda item: (len(item.path.parts), str(item.path)),
    )
    for snapshot in ordered:
        if not snapshot.path.exists() and not snapshot.path.is_symlink():
            if not _create_snapshot_entry(snapshot):
                residuals.append(snapshot.path)
            continue
        if not _secure_restore_snapshot_entry(snapshot):
            residuals.append(snapshot.path)
    try:
        current_paths = set((_snapshot_tree(root) or {}).keys())
    except DshLifecycleError:
        current_paths = {root}
    residuals.extend(current_paths.difference(snapshots))
    return sorted(set(residuals), key=str)


def _manifest_has_only_empty_managed_dependencies(path: Path) -> bool:
    try:
        document = json.loads(_read_regular_bytes(path).decode("utf-8"))
    except (DshLifecycleError, UnicodeError, json.JSONDecodeError):
        return False
    return document == {"dependencies": {}}


def _restore_manifest_prestate(transaction: _ProfileTransaction) -> list[Path]:
    path = transaction.profile_root / "package.json"
    expected = transaction.manifest
    current_identity = transaction.latest_manifest
    if expected is None:
        if not path.exists() and not path.is_symlink():
            return []
        if (
            current_identity is None
            or current_identity.kind != "file"
            or not _manifest_has_only_empty_managed_dependencies(path)
        ):
            return [path]
        try:
            _assert_entry_unchanged(current_identity, "profile package manifest")
            residual = _secure_cleanup_owned_entry(current_identity)
            return [residual] if residual is not None else []
        except (DshLifecycleError, OSError, KeyboardInterrupt):
            return [path]
    if not path.exists() or path.is_symlink() or not path.is_file():
        return [path]
    try:
        if _read_regular_bytes(path) == expected.content:
            if current_identity is None:
                return [path]
            return (
                []
                if _secure_restore_snapshot_entry(
                    expected,
                    expected_entry=current_identity,
                )
                else [path]
            )
        if current_identity is None:
            return [path]
        _assert_entry_unchanged(current_identity, "profile package manifest")
        parent: int | None = None
        descriptor: int | None = None
        temporary_name: str | None = None
        temporary_published = False
        backup: _RelocatedPreset | None = None
        residuals: list[Path] = []
        try:
            parent = _open_active_dsh_directory(path.parent)
            _assert_entry_unchanged(current_identity, "profile package manifest")
            descriptor, temporary_name = _create_pinned_temporary(
                parent,
                prefix=".package.dsh-rollback-",
                suffix=".tmp",
            )
            created = os.fstat(descriptor)
            _write_all(descriptor, expected.content or b"")
            os.fsync(descriptor)
            _assert_active_dsh_home_binding()
            os.fchmod(descriptor, expected.mode)
            os.fsync(descriptor)
            _assert_active_dsh_home_binding()
            if not _created_file_matches(
                parent=parent,
                descriptor=descriptor,
                name=temporary_name,
                snapshot=expected,
                created=created,
            ):
                raise DshLifecycleError("manifest rollback temporary identity changed")
            _assert_entry_unchanged(current_identity, "profile package manifest")
            backup = _relocate_owned_preset(current_identity, "package")
            _assert_active_dsh_home_binding()
            _secure_rename_noreplace_at(parent, temporary_name, path.name)
            temporary_published = True
            _assert_active_dsh_home_binding()
            if not _created_file_matches(
                parent=parent,
                descriptor=descriptor,
                name=path.name,
                snapshot=expected,
                created=created,
            ):
                raise DshLifecycleError(
                    "restored profile package manifest identity changed"
                )
            if backup_residual := _secure_cleanup_owned_entry(backup.payload):
                residuals.extend((backup_residual, backup.location.root.path))
            else:
                _cleanup_recovery_location(backup.location)
            return sorted(set(residuals), key=str)
        except (DshLifecycleError, OSError, KeyboardInterrupt):
            if backup is not None:
                if not path.exists() and not path.is_symlink():
                    try:
                        _assert_entry_unchanged(
                            backup.payload,
                            "relocated profile package manifest",
                        )
                        _secure_rename_noreplace(backup.payload.path, path)
                        _relocated_entry(
                            current_identity,
                            path,
                            "restored original profile package manifest",
                        )
                        _cleanup_recovery_location(backup.location)
                    except (DshLifecycleError, OSError, KeyboardInterrupt):
                        residuals.append(backup.location.root.path)
                else:
                    residuals.append(backup.location.root.path)
            if (
                parent is not None
                and descriptor is not None
                and temporary_name is not None
                and not temporary_published
                and not _discard_pinned_temporary(
                    parent,
                    temporary_name,
                    descriptor,
                )
            ):
                residuals.append(path.parent / temporary_name)
            return sorted(set(residuals or [path]), key=str)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if parent is not None:
                os.close(parent)
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        return [path]


def _restore_profile_prestate(transaction: _ProfileTransaction) -> list[Path]:
    residuals: list[Path] = []
    for root, snapshots in transaction.package_trees.items():
        residuals.extend(_restore_tree_prestate(root, snapshots))
    residuals.extend(_restore_manifest_prestate(transaction))
    for path in reversed(tuple(transaction.base_existed)):
        if transaction.base_existed[path]:
            continue
        if not path.exists() and not path.is_symlink():
            continue
        expected = transaction.created_base.get(path)
        try:
            if (
                expected is None
                or path.is_symlink()
                or not path.is_dir()
                or _entry_identity(path) != (expected.device, expected.inode)
            ):
                residuals.append(path)
                continue
            if cleanup_residual := _secure_cleanup_owned_entry(expected):
                residuals.append(cleanup_residual)
        except (OSError, KeyboardInterrupt):
            residuals.append(path)
    return sorted(set(residuals), key=str)


def _create_package_recovery_marker(destination: Path) -> Path:
    try:
        parent = _open_active_dsh_directory(destination.parent)
    except FileNotFoundError:
        _claim_directory(destination.parent, [])
    else:
        os.close(parent)
    location = _claim_recovery_location(destination, "package")
    marker = location.root.path
    notice = marker / "RECOVERY.txt"
    root = _open_active_dsh_directory(marker)
    descriptor: int | None = None
    try:
        _assert_owned_directory_binding(location.root, root)
        descriptor = os.open(
            notice.name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=root,
        )
        metadata = os.fstat(descriptor)
        _write_all(
            descriptor,
            b"Package filesystem rollback requires manual recovery.\n",
        )
        os.fsync(descriptor)
        named = os.stat(
            notice.name,
            dir_fd=root,
            follow_symlinks=False,
        )
        if not stat.S_ISREG(named.st_mode) or (
            named.st_dev,
            named.st_ino,
        ) != (metadata.st_dev, metadata.st_ino):
            raise DshLifecycleError(
                f"package recovery marker identity changed: {notice}"
            )
        _assert_owned_directory_binding(location.root, root)
        _assert_active_dsh_home_binding()
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(root)
    return marker


def _record_profile_recovery(
    destination: Path,
    residuals: list[Path],
    failed: list[str],
) -> None:
    failed.extend(
        f"inspect preserved recovery path {str(path)!r}" for path in residuals
    )
    if not residuals:
        return
    try:
        marker = _create_package_recovery_marker(destination)
        failed.append(f"inspect preserved recovery path {str(marker)!r}")
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        marker = destination.parent / f".{destination.name}.ai-toolkit-package"
        failed.append(f"create recovery marker at {str(marker)!r}")


def _capture_state(
    profile: str,
    expected_profile: dict | None,
) -> DshStateSnapshot:
    try:
        return capture_dsh_profile_snapshot(
            profile,
            expected_profile=expected_profile,
            binding_validator=_assert_active_dsh_home_binding,
        )
    except (OSError, ValueError, KeyboardInterrupt) as error:
        raise DshLifecycleError(str(error)) from error


def _restore_state(
    snapshot: DshStateSnapshot, expected_profile: dict | None
) -> Path | None:
    try:
        if dsh_profile_matches_snapshot(snapshot):
            return None
    except (OSError, ValueError, KeyboardInterrupt):
        return snapshot.path
    return restore_dsh_profile_snapshot(
        snapshot,
        expected_profile=expected_profile,
        binding_validator=_assert_active_dsh_home_binding,
    )


def _entry_identity(path: Path) -> tuple[int, int]:
    parent = _open_active_dsh_directory(path.parent)
    try:
        metadata = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        return metadata.st_dev, metadata.st_ino
    finally:
        os.close(parent)


def _capture_entry(path: Path) -> _OwnedEntry:
    """Capture one path without following links for mutation-boundary checks."""
    parent: int | None = None
    try:
        parent = _open_active_dsh_directory(path.parent)
        parent_metadata = os.fstat(parent)
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    except OSError as error:
        if parent is not None:
            os.close(parent)
        raise DshLifecycleError(
            f"managed path is missing or unreadable: {path}"
        ) from error
    try:
        mode = stat.S_IFMT(before.st_mode)
        common = {
            "parent_device": parent_metadata.st_dev,
            "parent_inode": parent_metadata.st_ino,
        }
        if stat.S_ISLNK(mode):
            link_target = os.readlink(path.name, dir_fd=parent)
            after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
                raise DshLifecycleError(f"managed path identity changed: {path}")
            return _OwnedEntry(
                path,
                before.st_dev,
                before.st_ino,
                "symlink",
                link_target=link_target,
                **common,
            )
        if stat.S_ISREG(mode):
            digest = _file_digest(path)
            after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
                raise DshLifecycleError(f"managed path identity changed: {path}")
            return _OwnedEntry(
                path,
                before.st_dev,
                before.st_ino,
                "file",
                digest,
                **common,
            )
        if stat.S_ISDIR(mode):
            digest = _tree_hash(path)
            after = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            if (after.st_dev, after.st_ino) != (before.st_dev, before.st_ino):
                raise DshLifecycleError(f"managed path identity changed: {path}")
            return _OwnedEntry(
                path,
                before.st_dev,
                before.st_ino,
                "directory",
                digest,
                **common,
            )
        return _OwnedEntry(
            path,
            before.st_dev,
            before.st_ino,
            "unsupported",
            **common,
        )
    finally:
        os.close(parent)


def _assert_entry_unchanged(expected: _OwnedEntry, label: str) -> None:
    """Refuse a mutation when the preflight path identity or content changed."""
    try:
        current = _capture_entry(expected.path)
    except DshLifecycleError as error:
        raise DshLifecycleError(
            f"{label} identity changed; refusing mutation"
        ) from error
    identity_changed = (
        current.device,
        current.inode,
        current.kind,
        current.digest,
        current.link_target,
    ) != (
        expected.device,
        expected.inode,
        expected.kind,
        expected.digest,
        expected.link_target,
    )
    parent_changed = expected.parent_device is not None and (
        current.parent_device,
        current.parent_inode,
    ) != (expected.parent_device, expected.parent_inode)
    if identity_changed or parent_changed:
        raise DshLifecycleError(f"{label} identity changed; refusing mutation")


def _relocated_entry(
    expected: _OwnedEntry,
    destination: Path,
    label: str,
) -> _OwnedEntry:
    parent = _open_active_dsh_directory(destination.parent)
    try:
        parent_metadata = os.fstat(parent)
    finally:
        os.close(parent)
    relocated = _OwnedEntry(
        destination,
        expected.device,
        expected.inode,
        expected.kind,
        expected.digest,
        expected.link_target,
        parent_metadata.st_dev,
        parent_metadata.st_ino,
    )
    _assert_entry_unchanged(relocated, label)
    return relocated


def _claim_directory(
    path: Path,
    owned: list[_OwnedEntry],
    *,
    mode: int = 0o700,
) -> None:
    parent: int | None = None
    child: int | None = None
    try:
        parent = _open_active_dsh_directory(path.parent)
        parent_metadata = os.fstat(parent)
        os.mkdir(path.name, mode=mode, dir_fd=parent)
    except FileExistsError as error:
        if parent is not None:
            os.close(parent)
        raise DshLifecycleError(
            f"preset collision, refusing to overwrite: {path}"
        ) from error
    except BaseException:
        if parent is not None:
            os.close(parent)
        raise
    try:
        named = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        child = os.open(
            path.name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent,
        )
        opened = os.fstat(child)
        if not stat.S_ISDIR(named.st_mode) or (
            opened.st_dev,
            opened.st_ino,
        ) != (named.st_dev, named.st_ino):
            raise DshLifecycleError(
                f"managed preset directory identity changed: {path}"
            )
        owned.append(
            _OwnedEntry(
                path,
                opened.st_dev,
                opened.st_ino,
                "directory",
                parent_device=parent_metadata.st_dev,
                parent_inode=parent_metadata.st_ino,
            )
        )
        _assert_active_dsh_home_binding()
    finally:
        if child is not None:
            os.close(child)
        if parent is not None:
            os.close(parent)


def _claim_recovery_location(destination: Path, suffix: str) -> _RecoveryLocation:
    """Atomically claim one private, transaction-unique recovery container."""
    for _attempt in range(RECOVERY_CLAIM_ATTEMPTS):
        token = secrets.token_hex(RECOVERY_TOKEN_BYTES)
        root_path = destination.parent / (
            f".{destination.name}.ai-toolkit-{suffix}.{token}"
        )
        parent: int | None = None
        child: int | None = None
        try:
            parent = _open_active_dsh_directory(root_path.parent)
            parent_metadata = os.fstat(parent)
            os.mkdir(root_path.name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            if parent is not None:
                os.close(parent)
            continue
        except OSError as error:
            if parent is not None:
                os.close(parent)
            raise DshLifecycleError(
                f"unable to claim managed preset recovery path: {root_path}"
            ) from error
        try:
            named = os.stat(
                root_path.name,
                dir_fd=parent,
                follow_symlinks=False,
            )
            child = os.open(
                root_path.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent,
            )
            opened = os.fstat(child)
            if not stat.S_ISDIR(named.st_mode) or (
                opened.st_dev,
                opened.st_ino,
            ) != (named.st_dev, named.st_ino):
                raise DshLifecycleError(
                    f"managed preset recovery claim is not a directory: {root_path}"
                )
            root = _OwnedEntry(
                root_path,
                opened.st_dev,
                opened.st_ino,
                "directory",
                _canonical_tree_digest(
                    [
                        {
                            "type": "directory",
                            "path": ".",
                            "mode": stat.S_IMODE(opened.st_mode),
                        }
                    ]
                ),
                parent_device=parent_metadata.st_dev,
                parent_inode=parent_metadata.st_ino,
            )
            _assert_active_dsh_home_binding()
            return _RecoveryLocation(root, root_path / "managed-preset")
        finally:
            if child is not None:
                os.close(child)
            if parent is not None:
                os.close(parent)
    raise DshLifecycleError("unable to claim a unique managed preset recovery path")


def _cleanup_recovery_location(location: _RecoveryLocation) -> None:
    """Remove an empty recovery container only while its exact inode is owned."""
    _assert_active_dsh_home_binding()
    root = _open_active_dsh_directory(location.root.path)
    parent = _open_active_dsh_directory(location.root.path.parent)
    try:
        root_metadata = os.fstat(root)
        if (root_metadata.st_dev, root_metadata.st_ino) != (
            location.root.device,
            location.root.inode,
        ):
            raise DshLifecycleError(
                "managed preset recovery container identity changed; preserved"
            )
        try:
            os.stat(
                location.payload.name,
                dir_fd=root,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            pass
        else:
            raise DshLifecycleError(
                f"managed preset recovery payload survives: {location.payload}"
            )
        metadata = os.stat(
            location.root.path.name,
            dir_fd=parent,
            follow_symlinks=False,
        )
        if (metadata.st_dev, metadata.st_ino) != (
            location.root.device,
            location.root.inode,
        ):
            raise DshLifecycleError(
                "managed preset recovery container identity changed; preserved"
            )
        os.rmdir(location.root.path.name, dir_fd=parent)
        _assert_active_dsh_home_binding()
    finally:
        os.close(root)
        os.close(parent)


def _relocate_owned_preset(
    expected: _OwnedEntry,
    suffix: str,
    recovery_owned: list[_RelocatedPreset] | None = None,
) -> _RelocatedPreset:
    """Move an owned preset into a private recovery container without clobbering."""
    location = _claim_recovery_location(expected.path, suffix)
    try:
        _assert_entry_unchanged(expected, "managed preset")
        _assert_entry_unchanged(
            location.root,
            "managed preset recovery container",
        )
        _secure_rename_noreplace(expected.path, location.payload)
        payload = _relocated_entry(
            expected,
            location.payload,
            "relocated managed preset recovery payload",
        )
        relocated = _RelocatedPreset(location, payload)
        if recovery_owned is not None:
            recovery_owned.append(relocated)
        return relocated
    except (DshLifecycleError, OSError, KeyboardInterrupt) as error:
        residuals: list[Path] = []
        if location.payload.exists() or location.payload.is_symlink():
            if recovery_owned is not None:
                try:
                    payload = _relocated_entry(
                        expected,
                        location.payload,
                        "relocated managed preset recovery payload",
                    )
                    recovery_owned.append(_RelocatedPreset(location, payload))
                except (DshLifecycleError, OSError, KeyboardInterrupt):
                    pass
            residuals.append(location.root.path)
        else:
            try:
                _cleanup_recovery_location(location)
            except (DshLifecycleError, OSError, KeyboardInterrupt):
                residuals.append(location.root.path)
        if residuals:
            paths = ", ".join(repr(str(path)) for path in residuals)
            detail = (
                "managed preset relocation was interrupted"
                if isinstance(error, KeyboardInterrupt)
                else str(error) or type(error).__name__
            )
            raise DshLifecycleError(
                f"{detail}; preserved recovery path: {paths}"
            ) from error
        raise


def _file_digest(path: Path) -> str:
    return hashlib.sha256(_read_regular_bytes(path)).hexdigest()


def _open_relative_destination_directory(
    root_descriptor: int,
    relative: Path,
    display_path: Path,
) -> int:
    """Walk a mutation destination from an already pinned tree root."""
    descriptor = os.dup(root_descriptor)
    try:
        for component in relative.parts:
            named = os.stat(
                component,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISDIR(named.st_mode):
                raise DshLifecycleError(
                    f"managed preset destination is not a directory: {display_path}"
                )
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            opened = os.fstat(child)
            if (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino):
                os.close(child)
                raise DshLifecycleError(
                    f"managed preset destination identity changed: {display_path}"
                )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _assert_owned_directory_binding(entry: _OwnedEntry, descriptor: int) -> None:
    opened = os.fstat(descriptor)
    if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
        entry.device,
        entry.inode,
    ):
        raise DshLifecycleError(
            f"managed preset destination identity changed: {entry.path}"
        )
    current = _open_active_dsh_directory(entry.path)
    try:
        named = os.fstat(current)
        if (named.st_dev, named.st_ino) != (entry.device, entry.inode):
            raise DshLifecycleError(
                f"managed preset destination identity changed: {entry.path}"
            )
    finally:
        os.close(current)


def _copy_tree_exclusive(
    source: Path,
    destination: Path,
    owned: list[_OwnedEntry],
) -> None:
    root_entry = next(
        (entry for entry in reversed(owned) if entry.path == destination),
        None,
    )
    if root_entry is None or root_entry.kind != "directory":
        raise DshLifecycleError(
            f"managed preset destination ownership is missing: {destination}"
        )
    root_descriptor = _open_active_dsh_directory(destination)
    try:
        _assert_owned_directory_binding(root_entry, root_descriptor)
        for source_path in sorted(
            source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()
        ):
            relative = source_path.relative_to(source)
            target = destination / relative
            if source_path.is_symlink():
                raise DshLifecycleError(
                    f"managed preset contains a symlink: {relative}"
                )
            parent = _open_relative_destination_directory(
                root_descriptor,
                relative.parent,
                target.parent,
            )
            try:
                parent_metadata = os.fstat(parent)
                if source_path.is_dir():
                    source_mode = stat.S_IMODE(
                        source_path.stat(follow_symlinks=False).st_mode
                    )
                    try:
                        os.mkdir(
                            target.name,
                            mode=source_mode,
                            dir_fd=parent,
                        )
                    except FileExistsError as error:
                        raise DshLifecycleError(
                            f"preset collision, refusing to overwrite: {target}"
                        ) from error
                    named = os.stat(
                        target.name,
                        dir_fd=parent,
                        follow_symlinks=False,
                    )
                    child = os.open(
                        target.name,
                        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                        dir_fd=parent,
                    )
                    try:
                        opened = os.fstat(child)
                        if not stat.S_ISDIR(named.st_mode) or (
                            opened.st_dev,
                            opened.st_ino,
                        ) != (named.st_dev, named.st_ino):
                            raise DshLifecycleError(
                                f"managed preset destination identity changed: {target}"
                            )
                        owned.append(
                            _OwnedEntry(
                                target,
                                opened.st_dev,
                                opened.st_ino,
                                "directory",
                                parent_device=parent_metadata.st_dev,
                                parent_inode=parent_metadata.st_ino,
                            )
                        )
                    finally:
                        os.close(child)
                    _assert_owned_directory_binding(root_entry, root_descriptor)
                    continue
                if not source_path.is_file():
                    raise DshLifecycleError(
                        f"managed preset contains an unsupported entry: {relative}"
                    )
                source_content, source_metadata = _stable_regular_file_bytes(source_path)
                expected_digest = hashlib.sha256(source_content).hexdigest()
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
                try:
                    descriptor = os.open(
                        target.name,
                        flags,
                        stat.S_IMODE(source_metadata.st_mode),
                        dir_fd=parent,
                    )
                except FileExistsError as error:
                    raise DshLifecycleError(
                        f"preset collision, refusing to overwrite: {target}"
                    ) from error
                metadata = os.fstat(descriptor)
                owned.append(
                    _OwnedEntry(
                        target,
                        metadata.st_dev,
                        metadata.st_ino,
                        "file",
                        expected_digest,
                        parent_device=parent_metadata.st_dev,
                        parent_inode=parent_metadata.st_ino,
                    )
                )
                try:
                    _write_all(descriptor, source_content)
                    os.fsync(descriptor)
                    final = os.fstat(descriptor)
                    named = os.stat(
                        target.name,
                        dir_fd=parent,
                        follow_symlinks=False,
                    )
                    if (
                        not stat.S_ISREG(final.st_mode)
                        or not stat.S_ISREG(named.st_mode)
                        or (final.st_dev, final.st_ino)
                        != (metadata.st_dev, metadata.st_ino)
                        or (named.st_dev, named.st_ino)
                        != (metadata.st_dev, metadata.st_ino)
                    ):
                        raise DshLifecycleError(
                            f"managed preset destination identity changed: {target}"
                        )
                finally:
                    os.close(descriptor)
                _assert_owned_directory_binding(root_entry, root_descriptor)
            finally:
                os.close(parent)
        _assert_owned_directory_binding(root_entry, root_descriptor)
        _assert_active_dsh_home_binding()
    finally:
        os.close(root_descriptor)


def _secure_cleanup_owned_entry(entry: _OwnedEntry) -> Path | None:
    """Move one candidate no-clobber, validate the moved inode, then remove it."""
    _assert_active_dsh_home_binding()
    location = _claim_recovery_location(entry.path, "cleanup")

    def preserve_collision() -> Path:
        try:
            _secure_rename_noreplace(location.payload, entry.path)
            _cleanup_recovery_location(location)
            return entry.path
        except (DshLifecycleError, OSError, KeyboardInterrupt):
            pass
        return location.root.path

    try:
        _secure_rename_noreplace(entry.path, location.payload)
        parent = _open_active_dsh_directory(location.payload.parent)
        try:
            metadata = os.stat(
                location.payload.name,
                dir_fd=parent,
                follow_symlinks=False,
            )
            if (metadata.st_dev, metadata.st_ino) != (entry.device, entry.inode):
                return preserve_collision()
            if entry.kind == "file":
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or _file_digest(location.payload) != entry.digest
                ):
                    return preserve_collision()
            elif entry.kind == "symlink":
                if (
                    not stat.S_ISLNK(metadata.st_mode)
                    or os.readlink(location.payload.name, dir_fd=parent)
                    != entry.link_target
                ):
                    return preserve_collision()
            elif entry.kind == "directory":
                if not stat.S_ISDIR(metadata.st_mode):
                    return preserve_collision()
            else:
                return preserve_collision()
            current = os.stat(
                location.payload.name,
                dir_fd=parent,
                follow_symlinks=False,
            )
            if (current.st_dev, current.st_ino) != (entry.device, entry.inode):
                return preserve_collision()
            if entry.kind == "directory":
                os.rmdir(location.payload.name, dir_fd=parent)
            else:
                os.unlink(location.payload.name, dir_fd=parent)
            _assert_active_dsh_home_binding()
        finally:
            os.close(parent)
        _cleanup_recovery_location(location)
        return None
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        try:
            payload_parent = _open_active_dsh_directory(location.payload.parent)
            try:
                os.stat(
                    location.payload.name,
                    dir_fd=payload_parent,
                    follow_symlinks=False,
                )
                payload_exists = True
            except FileNotFoundError:
                payload_exists = False
            finally:
                os.close(payload_parent)
        except (DshLifecycleError, OSError, KeyboardInterrupt):
            payload_exists = True
        if payload_exists:
            return preserve_collision()
        try:
            _cleanup_recovery_location(location)
        except (DshLifecycleError, OSError, KeyboardInterrupt):
            return location.root.path
        return entry.path


def _cleanup_owned_entries(owned: list[_OwnedEntry]) -> list[Path]:
    remaining: list[Path] = []
    for entry in reversed(owned):
        if residual := _secure_cleanup_owned_entry(entry):
            remaining.append(residual)
    return sorted(set(remaining), key=str)


def _cleanup_staging_entries(
    staging: Path,
    owned: list[_OwnedEntry],
    failed: list[str] | None = None,
) -> list[Path]:
    failures = failed if failed is not None else []
    try:
        residuals = set(_cleanup_owned_entries(owned))
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        failures.append(_recovery_error("owned staging cleanup failed", error))
        residuals = {entry.path for entry in owned}
    if not staging.exists() and not staging.is_symlink():
        return sorted(residuals, key=str)
    try:
        snapshots = _snapshot_tree(staging)
        residuals.update((snapshots or {}).keys())
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        failures.append(_recovery_error("snapshot cleanup failed", error))
        residuals.add(staging)
    return sorted(residuals, key=str)


def _raise_staging_failure(
    error: DshLifecycleError | OSError | KeyboardInterrupt,
    residuals: list[Path],
    cleanup_failures: list[str] | None = None,
) -> None:
    if isinstance(error, KeyboardInterrupt):
        message = "managed preset staging was interrupted"
    elif isinstance(error, DshLifecycleError):
        message = str(error)
    else:
        message = "managed preset staging failed"
    recovery = list(cleanup_failures or [])
    recovery.extend(
        f"inspect preserved recovery path {str(path)!r}" for path in residuals
    )
    if recovery:
        paths = "\n".join(f"  {action}" for action in recovery)
        raise DshLifecycleError(
            f"{message}\nRecovery required; complete these deterministic steps:\n{paths}"
        ) from error
    if isinstance(error, KeyboardInterrupt):
        raise DshLifecycleError(message) from error
    if isinstance(error, DshLifecycleError):
        raise error
    raise DshLifecycleError(message) from error


def _inventory_tree(path: Path) -> list[_OwnedEntry]:
    """Capture a no-follow, deterministic inventory for one managed tree."""
    root = _capture_entry(path)
    if root.kind != "directory":
        raise DshLifecycleError(f"managed cleanup root is not a directory: {path}")
    inventory = [root]
    try:
        candidates = sorted(
            path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()
        )
    except OSError as error:
        raise DshLifecycleError(f"managed tree inventory failed: {path}") from error
    inventory.extend(_capture_entry(candidate) for candidate in candidates)
    return inventory


def _assert_inventory_unchanged(inventory: list[_OwnedEntry]) -> None:
    for expected in inventory:
        _assert_entry_unchanged(expected, "managed cleanup entry")


def _restore_preset_from_source(
    source: Path,
    destination: Path,
) -> list[Path]:
    expected_hash = _tree_hash(source)
    if destination.exists() or destination.is_symlink():
        if destination.is_symlink() or not destination.is_dir():
            return [destination]
        return [] if _tree_hash(destination) == expected_hash else [destination]
    owned: list[_OwnedEntry] = []
    try:
        source_mode = stat.S_IMODE(source.stat(follow_symlinks=False).st_mode)
        _claim_directory(destination, owned, mode=source_mode)
        _copy_tree_exclusive(source, destination, owned)
        if _tree_hash(destination) != expected_hash:
            raise DshLifecycleError("restored preset failed hash verification")
    except (DshLifecycleError, OSError, KeyboardInterrupt):
        remaining = _cleanup_owned_entries(owned)
        return remaining or [destination]
    return []


def _remove_exact_managed_tree(
    path: Path,
    expected_hash: str,
    *,
    expected_root: _OwnedEntry | None = None,
) -> None:
    if path.is_symlink() or not path.is_dir():
        raise DshLifecycleError(
            f"managed preset cleanup collision; preserved: {str(path)!r}"
        )
    inventory = _inventory_tree(path)
    if expected_root is not None and inventory[0] != expected_root:
        raise DshLifecycleError(
            f"managed preset cleanup identity changed; preserved: {str(path)!r}"
        )
    if inventory[0].digest != expected_hash:
        raise DshLifecycleError(
            f"managed preset cleanup collision; preserved: {str(path)!r}"
        )
    _assert_inventory_unchanged(inventory)
    remaining = _cleanup_owned_entries(inventory)
    if remaining:
        paths = ", ".join(repr(str(candidate)) for candidate in remaining)
        raise DshLifecycleError(f"managed preset cleanup collision; preserved: {paths}")


def _validate_profile(profile: str) -> str:
    if profile in {".", ".."} or not PROFILE_PATTERN.fullmatch(profile):
        raise DshLifecycleError(
            "invalid DSH profile id; use 1-64 lowercase letters, digits, '.', '_' or '-'"
        )
    return profile


def _dsh_home() -> Path:
    configured = os.environ.get("DSH_HOME")
    home = Path(configured) if configured else Path.home() / ".dsh"
    if not home.is_absolute():
        raise DshLifecycleError("DSH_HOME must be an absolute path")
    if home.is_symlink():
        raise DshLifecycleError("DSH_HOME must not be a symlink")
    for candidate in home.parents:
        if candidate.is_symlink() and candidate.lstat().st_uid != 0:
            raise DshLifecycleError(
                f"DSH_HOME has unsafe symlink ancestry: {candidate}"
            )
    return home.resolve(strict=False)


def _assert_no_symlink_ancestry(path: Path, label: str) -> None:
    current = path
    while not current.exists() and not current.is_symlink():
        if current.parent == current:
            break
        current = current.parent
    for candidate in (current, *current.parents):
        if candidate.is_symlink():
            raise DshLifecycleError(f"{label} has unsafe symlink ancestry: {candidate}")


def _assert_profile_roots(dsh_home: Path, profile: str) -> None:
    for path in (
        dsh_home / "profiles",
        dsh_home / "profiles" / profile,
        dsh_home / "profiles" / profile / "node_modules",
        dsh_home / "profiles" / profile / "node_modules" / "@softspark",
        dsh_home / ".agent-presets",
    ):
        if path.is_symlink():
            raise DshLifecycleError(f"unsafe symlink in managed DSH path: {path}")
        if path.exists() and not path.is_dir():
            raise DshLifecycleError(f"managed DSH path is not a directory: {path}")


def _minimal_environment(dsh_home: Path) -> dict[str, str]:
    environment = {
        "HOME": str(Path.home()),
        "DSH_HOME": str(dsh_home),
        "PATH": os.environ.get("PATH", os.defpath),
    }
    for name in ("LANG", "LC_ALL", "TMPDIR"):
        if value := os.environ.get(name):
            environment[name] = value
    return environment


def _mutation_process_groups_supported() -> bool:
    return (
        os.name == "posix"
        and hasattr(os, "killpg")
        and hasattr(os, "setsid")
        and hasattr(signal, "pthread_sigmask")
        and hasattr(signal, "SIG_BLOCK")
        and hasattr(signal, "SIG_SETMASK")
    )


def _mutation_environment(
    dsh_home: Path,
    prerequisites: _PrerequisiteRecord,
) -> dict[str, str]:
    environment = _minimal_environment(dsh_home)
    verified_directory = str(prerequisites.pnpm.command_path.parent)
    environment["PATH"] = (
        verified_directory + os.pathsep + prerequisites.execution_path
    )
    selected = shutil.which("pnpm", path=environment["PATH"])
    if selected is None or _absolute_command_path(selected) != prerequisites.pnpm.command_path:
        raise DshLifecycleError("pnpm prerequisite PATH binding changed")
    return environment


def _process_group_exists(process_group: int) -> bool:
    try:
        os.killpg(process_group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_process_group_exit(process_group: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while _process_group_exists(process_group):
        if time.monotonic() >= deadline:
            return False
        time.sleep(PROCESS_GROUP_POLL_SECONDS)
    return True


def _signal_process_group(process_group: int, signal_number: int) -> None:
    try:
        os.killpg(process_group, signal_number)
    except ProcessLookupError:
        pass


@contextmanager
def _defer_sigint_during_process_teardown():
    previous_handler: object | None = None
    try:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (OSError, ValueError):
        previous_handler = None
    try:
        yield
    finally:
        if previous_handler is not None:
            signal.signal(signal.SIGINT, previous_handler)


def _retry_teardown_interrupts(
    operation: Callable[[], bool],
    *,
    process_group: int,
    profile: str,
) -> bool:
    for _ in range(MAX_TEARDOWN_INTERRUPT_RETRIES):
        try:
            return operation()
        except KeyboardInterrupt:
            continue
    raise _ProcessTreeTerminationError(
        "DSH process tree teardown was repeatedly interrupted; "
        "package recovery is blocked",
        process_group=process_group,
        profile=profile,
    )


def _signal_bound_process_group(
    process: subprocess.Popen[str],
    signal_number: int,
    *,
    profile: str,
) -> bool:
    """Signal only while the unreaped child still binds its PID and PGID."""
    process_group = process.pid

    def signal_if_bound() -> bool:
        if process.poll() is not None:
            return False
        _signal_process_group(process_group, signal_number)
        return True

    return bool(
        _retry_teardown_interrupts(
            signal_if_bound,
            process_group=process_group,
            profile=profile,
        )
    )


def _communicate_during_teardown(
    process: subprocess.Popen[str],
    timeout: float,
    *,
    profile: str,
) -> bool:
    """Wait through repeated interrupts; return whether the child was reaped."""
    deadline = time.monotonic() + timeout

    def communicate_once() -> bool:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.communicate(timeout=remaining)
        except subprocess.TimeoutExpired:
            return False
        return True

    return bool(
        _retry_teardown_interrupts(
            communicate_once,
            process_group=process.pid,
            profile=profile,
        )
    )


def _wait_for_process_group_exit_during_teardown(
    process_group: int,
    timeout: float,
    *,
    profile: str,
) -> bool:
    return bool(
        _retry_teardown_interrupts(
            lambda: _wait_for_process_group_exit(process_group, timeout),
            process_group=process_group,
            profile=profile,
        )
    )


def _terminate_mutation_process_tree(
    process: subprocess.Popen[str],
    *,
    profile: str,
) -> None:
    process_group = process.pid
    with _defer_sigint_during_process_teardown():
        _signal_bound_process_group(process, signal.SIGTERM, profile=profile)
        child_reaped = _communicate_during_teardown(
            process,
            PROCESS_TERMINATION_GRACE_SECONDS,
            profile=profile,
        )
        if not child_reaped:
            _signal_bound_process_group(process, signal.SIGKILL, profile=profile)
            child_reaped = _communicate_during_teardown(
                process,
                PROCESS_TERMINATION_GRACE_SECONDS,
                profile=profile,
            )
        group_stopped = _wait_for_process_group_exit_during_teardown(
            process_group,
            PROCESS_TERMINATION_GRACE_SECONDS,
            profile=profile,
        )
    if not child_reaped or not group_stopped:
        raise _ProcessTreeTerminationError(
            "DSH process tree termination could not be confirmed; "
            "package recovery is blocked",
            process_group=process_group,
            profile=profile,
        )


def _run(argv: list[str], *, dsh_home: Path) -> subprocess.CompletedProcess[str]:
    _assert_active_dsh_home_binding()
    prerequisites = _active_prerequisites()
    if Path(argv[0]) != prerequisites.dsh.resolved_path:
        raise DshLifecycleError("DSH prerequisite executable binding changed")
    if not _mutation_process_groups_supported():
        raise DshLifecycleError(
            "DSH mutation process-group termination is unsupported; "
            "use Linux, WSL, or macOS"
        )
    try:
        profile = argv[argv.index("--profile") + 1]
    except (ValueError, IndexError) as error:
        raise DshLifecycleError("DSH mutation profile argument is missing") from error
    _validate_profile(profile)
    previous_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT})
    try:
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                text=True,
                shell=False,
                env=_mutation_environment(dsh_home, prerequisites),
            )
        except OSError as error:
            _assert_active_dsh_home_binding()
            raise DshLifecycleError("unable to execute DSH command") from error
        try:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_signal_mask)
            stdout, stderr = process.communicate(
                timeout=PACKAGE_MUTATION_TIMEOUT_SECONDS
            )
            if _process_group_exists(process.pid):
                raise DshLifecycleError(
                    "DSH command left a descendant process running"
                )
            _assert_active_dsh_home_binding()
            _active_prerequisites()
            if process.returncode in {-2, 130}:
                raise DshLifecycleError("DSH command was interrupted")
            if process.returncode != 0:
                raise DshLifecycleError(
                    f"DSH command failed with exit status {process.returncode}"
                )
            return subprocess.CompletedProcess(
                argv,
                process.returncode,
                stdout,
                stderr,
            )
        except BaseException as error:
            _terminate_mutation_process_tree(process, profile=profile)
            _assert_active_dsh_home_binding()
            _active_prerequisites()
            if isinstance(error, subprocess.TimeoutExpired):
                raise DshLifecycleError(
                    f"DSH command timed out after {PACKAGE_MUTATION_TIMEOUT_SECONDS}s"
                ) from error
            if isinstance(error, KeyboardInterrupt):
                raise DshLifecycleError("DSH command was interrupted") from error
            raise
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_signal_mask)


def _absolute_command_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (Path.cwd() / path).absolute()


def _capture_executable_prerequisite(
    name: str,
    *,
    execution_path: str,
    missing_error: str,
) -> _ExecutablePrerequisite:
    executable = shutil.which(name, path=execution_path)
    if executable is None:
        raise DshLifecycleError(missing_error)
    command_path = _absolute_command_path(executable)
    try:
        command_metadata = command_path.lstat()
        command_link_target = (
            os.readlink(command_path) if stat.S_ISLNK(command_metadata.st_mode) else None
        )
        resolved_path = command_path.resolve(strict=True)
        resolved_metadata = resolved_path.stat(follow_symlinks=False)
    except OSError as error:
        raise DshLifecycleError(f"{name} executable path cannot be resolved") from error
    if (
        not resolved_path.is_absolute()
        or not stat.S_ISREG(resolved_metadata.st_mode)
        or not os.access(command_path, os.X_OK)
    ):
        raise DshLifecycleError(
            f"{name} executable path is not an absolute executable regular file"
        )
    return _ExecutablePrerequisite(
        name=name,
        command_path=command_path,
        resolved_path=resolved_path,
        command_signature=_regular_file_signature(command_metadata),
        command_link_target=command_link_target,
        resolved_signature=_regular_file_signature(resolved_metadata),
    )


def _assert_executable_prerequisite(
    expected: _ExecutablePrerequisite,
    *,
    execution_path: str,
) -> None:
    try:
        current = _capture_executable_prerequisite(
            expected.name,
            execution_path=execution_path,
            missing_error=f"{expected.name} prerequisite executable disappeared",
        )
    except DshLifecycleError as error:
        raise DshLifecycleError(
            f"{expected.name} prerequisite identity changed: {error}"
        ) from error
    if current != expected:
        raise DshLifecycleError(
            f"{expected.name} prerequisite identity or PATH resolution changed"
        )


def _run_version_probe(
    argv: list[str],
    *,
    dsh_home: Path,
    label: str,
    remediation: str,
) -> subprocess.CompletedProcess[str]:
    _assert_active_dsh_home_binding()
    try:
        result = subprocess.run(
            argv,
            check=True,
            capture_output=True,
            text=True,
            shell=False,
            timeout=PROBE_TIMEOUT_SECONDS,
            env=_minimal_environment(dsh_home),
        )
        _assert_active_dsh_home_binding()
        return result
    except subprocess.TimeoutExpired as error:
        _assert_active_dsh_home_binding()
        raise DshLifecycleError(
            f"{label} prerequisite probe timed out after {PROBE_TIMEOUT_SECONDS}s; "
            f"{remediation}"
        ) from error
    except subprocess.CalledProcessError as error:
        _assert_active_dsh_home_binding()
        if error.returncode in {-2, 130}:
            detail = "was interrupted"
        else:
            detail = f"failed with exit status {error.returncode}"
        raise DshLifecycleError(
            f"{label} prerequisite probe {detail}; {remediation}"
        ) from error
    except KeyboardInterrupt as error:
        _assert_active_dsh_home_binding()
        raise DshLifecycleError(
            f"{label} prerequisite probe was interrupted; {remediation}"
        ) from error
    except OSError as error:
        _assert_active_dsh_home_binding()
        raise DshLifecycleError(
            f"unable to execute {label} prerequisite probe; {remediation}"
        ) from error


def _probe_supported_dsh(
    dsh_home: Path,
    executable: _ExecutablePrerequisite,
) -> None:
    result = _run_version_probe(
        [str(executable.resolved_path), "--version"],
        dsh_home=dsh_home,
        label="DSH runtime",
        remediation=f"install DSH {SUPPORTED_DSH_VERSION} and ensure it is on PATH",
    )
    match = re.search(
        r"(?<![0-9])([0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?)", result.stdout
    )
    version = match.group(1) if match else ""
    if version != SUPPORTED_DSH_VERSION:
        found = version or "unparseable"
        raise DshLifecycleError(
            f"unsupported DSH version {found}; required {SUPPORTED_DSH_VERSION}"
        )


def _discover_supported_dsh(
    dsh_home: Path,
    execution_path: str,
) -> _ExecutablePrerequisite:
    executable = _capture_executable_prerequisite(
        "dsh",
        execution_path=execution_path,
        missing_error="DSH executable not found on PATH",
    )
    _probe_supported_dsh(dsh_home, executable)
    _assert_executable_prerequisite(executable, execution_path=execution_path)
    return executable


def _find_supported_dsh(dsh_home: Path) -> str:
    execution_path = _minimal_environment(dsh_home)["PATH"]
    executable = _discover_supported_dsh(dsh_home, execution_path)
    return str(executable.resolved_path)


def _probe_supported_pnpm(
    dsh_home: Path,
    executable: _ExecutablePrerequisite,
) -> str:
    remediation = f"install pnpm {SUPPORTED_PNPM_RANGE} and ensure it is on PATH"
    result = _run_version_probe(
        [str(executable.resolved_path), "--version"],
        dsh_home=dsh_home,
        label="pnpm",
        remediation=remediation,
    )
    version = result.stdout.strip()
    match = PNPM_VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise DshLifecycleError(
            f"pnpm prerequisite version is unparseable; {remediation}"
        )
    parsed = tuple(int(part) for part in match.groups())
    if not MINIMUM_PNPM_VERSION <= parsed < MAXIMUM_PNPM_VERSION_EXCLUSIVE:
        raise DshLifecycleError(
            f"pnpm prerequisite version {version} is unsupported; "
            f"required {SUPPORTED_PNPM_RANGE}"
        )
    return version


def _discover_supported_pnpm(
    dsh_home: Path,
    execution_path: str,
) -> tuple[_ExecutablePrerequisite, str]:
    remediation = f"install pnpm {SUPPORTED_PNPM_RANGE} and ensure it is on PATH"
    executable = _capture_executable_prerequisite(
        "pnpm",
        execution_path=execution_path,
        missing_error=f"pnpm executable not found on PATH; {remediation}",
    )
    version = _probe_supported_pnpm(dsh_home, executable)
    _assert_executable_prerequisite(executable, execution_path=execution_path)
    return executable, version


def _find_supported_pnpm(dsh_home: Path) -> tuple[str, str]:
    execution_path = _minimal_environment(dsh_home)["PATH"]
    executable, version = _discover_supported_pnpm(dsh_home, execution_path)
    return str(executable.resolved_path), version


def _assert_prerequisites_unchanged(prerequisites: _PrerequisiteRecord) -> None:
    _assert_executable_prerequisite(
        prerequisites.dsh,
        execution_path=prerequisites.execution_path,
    )
    _assert_executable_prerequisite(
        prerequisites.pnpm,
        execution_path=prerequisites.execution_path,
    )


def _preflight_prerequisites(dsh_home: Path) -> _PrerequisiteRecord:
    execution_path = _minimal_environment(dsh_home)["PATH"]
    dsh = _discover_supported_dsh(dsh_home, execution_path)
    pnpm, _ = _discover_supported_pnpm(dsh_home, execution_path)
    return _PrerequisiteRecord(execution_path, dsh, pnpm)


def _active_prerequisites() -> _PrerequisiteRecord:
    if _ACTIVE_PREREQUISITES is None:
        raise DshLifecycleError("DSH mutation prerequisites are not pinned")
    _assert_prerequisites_unchanged(_ACTIVE_PREREQUISITES)
    return _ACTIVE_PREREQUISITES


def _current_dsh_executable(dsh_home: Path) -> str:
    if _ACTIVE_PREREQUISITES is None:
        return _find_supported_dsh(dsh_home)
    return str(_active_prerequisites().dsh.resolved_path)


def _frame_bytes(value: bytes) -> bytes:
    """Return one unambiguous unsigned-length-prefixed byte string."""
    return len(value).to_bytes(8, "big") + value


def _canonical_tree_digest(entries: list[dict[str, object]]) -> str:
    """Hash domain-separated canonical tree records in their stored order."""
    digest = hashlib.sha256(TREE_IDENTITY_DOMAIN)
    for entry in entries:
        kind = str(entry["type"]).encode("ascii")
        relative = str(entry["path"]).encode("utf-8", errors="strict")
        mode = int(entry["mode"])
        digest.update(_frame_bytes(kind))
        digest.update(_frame_bytes(relative))
        digest.update(mode.to_bytes(4, "big"))
        if entry["type"] == "file":
            digest.update(int(entry["size"]).to_bytes(8, "big"))
            digest.update(bytes.fromhex(str(entry["sha256"])))
        elif entry["type"] == "symlink":
            target = str(entry["target"]).encode("utf-8", errors="strict")
            digest.update(_frame_bytes(target))
    return digest.hexdigest()


def _regular_file_identity(path: Path) -> tuple[int, int, int, str]:
    """Return mode, size and digest for one stable no-follow regular inode."""
    content, metadata = _stable_regular_file_bytes(path)
    return (
        stat.S_IMODE(metadata.st_mode),
        len(content),
        metadata.st_ino,
        hashlib.sha256(content).hexdigest(),
    )


def _tree_inventory(root: Path) -> dict[str, object]:
    """Return a bounded, stable, no-follow canonical tree inventory."""
    for candidate in (root, *root.parents):
        if candidate.is_symlink():
            raise DshLifecycleError(
                f"managed tree has unsafe symlink ancestry: {candidate}"
            )
    if not root.is_dir() or root.is_symlink():
        raise DshLifecycleError(f"managed tree root is not a regular directory: {root}")
    root_stat = root.stat(follow_symlinks=False)
    entries: list[dict[str, object]] = [
        {"type": "directory", "path": ".", "mode": stat.S_IMODE(root_stat.st_mode)}
    ]
    pending: list[tuple[Path, int]] = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        if depth >= TREE_MAX_DEPTH:
            raise DshLifecycleError(f"managed tree exceeds depth limit: {root}")
        try:
            children = sorted(
                directory.iterdir(),
                key=lambda item: item.relative_to(root)
                .as_posix()
                .encode("utf-8", errors="strict"),
                reverse=True,
            )
        except (OSError, UnicodeError) as error:
            raise DshLifecycleError(f"managed tree inventory failed: {root}") from error
        for path in children:
            if len(entries) >= TREE_MAX_ENTRIES:
                raise DshLifecycleError(f"managed tree exceeds entry limit: {root}")
            relative = path.relative_to(root).as_posix()
            metadata = path.stat(follow_symlinks=False)
            mode = stat.S_IMODE(metadata.st_mode)
            if stat.S_ISLNK(metadata.st_mode):
                try:
                    target = os.readlink(path)
                except OSError as error:
                    raise DshLifecycleError(
                        f"managed symlink is unreadable: {relative}"
                    ) from error
                entries.append(
                    {
                        "type": "symlink",
                        "path": relative,
                        "mode": mode,
                        "target": target,
                    }
                )
            elif stat.S_ISDIR(metadata.st_mode):
                entries.append({"type": "directory", "path": relative, "mode": mode})
                pending.append((path, depth + 1))
            elif stat.S_ISREG(metadata.st_mode):
                file_mode, size, _inode, file_digest = _regular_file_identity(path)
                entries.append(
                    {
                        "type": "file",
                        "path": relative,
                        "mode": file_mode,
                        "size": size,
                        "sha256": file_digest,
                    }
                )
            else:
                raise DshLifecycleError(
                    f"managed tree contains an unsupported entry: {relative}"
                )
    entries.sort(key=lambda item: str(item["path"]).encode("utf-8", errors="strict"))
    after = root.stat(follow_symlinks=False)
    if (after.st_dev, after.st_ino) != (root_stat.st_dev, root_stat.st_ino):
        raise DshLifecycleError(f"managed tree identity changed: {root}")
    try:
        tree_digest = _canonical_tree_digest(entries)
    except UnicodeError as error:
        raise DshLifecycleError(
            f"managed tree contains a non-UTF-8 path or symlink target: {root}"
        ) from error
    return {"digest": tree_digest, "entries": entries}


def _tree_hash(root: Path) -> str:
    return str(_tree_inventory(root)["digest"])


def _package_source(dsh_home: Path, profile: str) -> Path:
    return (
        dsh_home
        / "profiles"
        / profile
        / "node_modules"
        / "@softspark"
        / "dsh-orchestrator"
        / "agent-presets"
        / PRESET_NAME
    )


def _recovery_paths(destination: Path) -> tuple[Path, ...]:
    """Return legacy fixed recovery names retained for collision discovery."""
    return tuple(
        destination.parent / f".{destination.name}.ai-toolkit-{suffix}"
        for suffix in RECOVERY_SUFFIXES
    )


def _recovery_artifacts(destination: Path) -> tuple[Path, ...]:
    """Discover legacy and transaction-unique recovery paths without following them."""
    artifacts = set(_recovery_paths(destination))
    parent = destination.parent
    if parent.exists() and parent.is_dir() and not parent.is_symlink():
        try:
            for candidate in parent.iterdir():
                if any(
                    candidate.name.startswith(
                        f".{destination.name}.ai-toolkit-{suffix}."
                    )
                    for suffix in RECOVERY_SUFFIXES
                ):
                    artifacts.add(candidate)
        except OSError as error:
            raise DshLifecycleError(
                f"unable to inspect managed preset recovery paths: {parent}"
            ) from error
    return tuple(sorted(artifacts, key=str))


def _assert_no_recovery_paths(destination: Path) -> None:
    for temporary in _recovery_artifacts(destination):
        if temporary.exists() or temporary.is_symlink():
            raise DshLifecycleError(f"managed preset recovery collision: {temporary}")


def _record_detected_recovery_artifacts(
    destination: Path,
    failed: list[str],
) -> None:
    try:
        artifacts = _recovery_artifacts(destination)
    except (DshLifecycleError, OSError, KeyboardInterrupt) as error:
        failed.append(f"inspect recovery namespace after discovery failure: {error}")
        return
    for artifact in artifacts:
        if artifact.exists() or artifact.is_symlink():
            action = f"inspect preserved recovery path {str(artifact)!r}"
            if action not in failed:
                failed.append(action)


def _profile_package_versions(dsh_home: Path, profile: str) -> dict[str, str]:
    profile_root = dsh_home / "profiles" / profile
    manifest = profile_root / "package.json"
    versions: dict[str, str] = {}
    if manifest.exists() or manifest.is_symlink():
        if manifest.is_symlink() or not manifest.is_file():
            raise DshLifecycleError(f"unsafe DSH profile package manifest: {manifest}")
        try:
            document = json.loads(_read_regular_bytes(manifest).decode("utf-8"))
        except (DshLifecycleError, UnicodeError, json.JSONDecodeError) as error:
            raise DshLifecycleError(
                f"invalid DSH profile package manifest: {manifest}"
            ) from error
        if not isinstance(document, dict):
            raise DshLifecycleError(f"invalid DSH profile package manifest: {manifest}")
        for key in ("dependencies", "devDependencies", "optionalDependencies"):
            dependencies = document.get(key, {})
            if not isinstance(dependencies, dict):
                raise DshLifecycleError(
                    f"invalid DSH profile package manifest: {manifest}"
                )
            for package, version in dependencies.items():
                if package not in PACKAGES:
                    continue
                if not isinstance(version, str) or not EXACT_VERSION_PATTERN.fullmatch(
                    version
                ):
                    raise DshLifecycleError(
                        f"invalid managed package version for {package!r} in {manifest}"
                    )
                previous = versions.get(package)
                if previous is not None and previous != version:
                    raise DshLifecycleError(
                        f"conflicting managed package versions for {package!r} in {manifest}"
                    )
                versions[package] = version
    for package in PACKAGES:
        package_root = profile_root / "node_modules" / Path(package)
        if not package_root.exists() and not package_root.is_symlink():
            if package in versions:
                versions[package] = "missing"
            continue
        if package_root.is_symlink() or not package_root.is_dir():
            versions[package] = "unsafe"
            continue
        package_manifest = package_root / "package.json"
        if package_manifest.is_symlink() or not package_manifest.is_file():
            versions[package] = "unknown"
            continue
        try:
            package_document = json.loads(
                _read_regular_bytes(package_manifest).decode("utf-8")
            )
        except (DshLifecycleError, UnicodeError, json.JSONDecodeError):
            versions[package] = "invalid"
            continue
        if (
            not isinstance(package_document, dict)
            or package_document.get("name") != package
            or not isinstance(package_document.get("version"), str)
        ):
            versions[package] = "invalid"
            continue
        installed_version = package_document["version"]
        declared_version = versions.get(package)
        if declared_version is not None and declared_version != installed_version:
            versions[package] = f"manifest:{declared_version}"
        else:
            versions[package] = installed_version
    return versions


def _profile_unmanaged_dependencies(
    dsh_home: Path, profile: str
) -> dict[str, dict[str, object]]:
    """Capture dependency entries outside the packages owned by this lifecycle."""
    manifest = dsh_home / "profiles" / profile / "package.json"
    if not manifest.exists() and not manifest.is_symlink():
        return {}
    if manifest.is_symlink() or not manifest.is_file():
        raise DshLifecycleError(f"unsafe DSH profile package manifest: {manifest}")
    try:
        document = json.loads(_read_regular_bytes(manifest).decode("utf-8"))
    except (DshLifecycleError, UnicodeError, json.JSONDecodeError) as error:
        raise DshLifecycleError(
            f"invalid DSH profile package manifest: {manifest}"
        ) from error
    if not isinstance(document, dict):
        raise DshLifecycleError(f"invalid DSH profile package manifest: {manifest}")
    inventory: dict[str, dict[str, object]] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        dependencies = document.get(key, {})
        if not isinstance(dependencies, dict):
            raise DshLifecycleError(f"invalid DSH profile package manifest: {manifest}")
        unmanaged = {
            package: value
            for package, value in dependencies.items()
            if package not in PACKAGES
        }
        if unmanaged:
            inventory[key] = unmanaged
    return inventory


def _preoperation_unmanaged_dependencies(
    transaction: _ProfileTransaction,
) -> dict[str, dict[str, object]]:
    """Read the unrelated dependency target from the immutable prestate."""
    manifest = transaction.manifest
    if manifest is None:
        return {}
    if manifest.kind != "file" or manifest.content is None:
        raise DshLifecycleError("invalid pre-operation DSH profile manifest")
    try:
        document = json.loads(manifest.content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise DshLifecycleError("invalid pre-operation DSH profile manifest") from error
    if not isinstance(document, dict):
        raise DshLifecycleError("invalid pre-operation DSH profile manifest")
    inventory: dict[str, dict[str, object]] = {}
    for key in ("dependencies", "devDependencies", "optionalDependencies"):
        dependencies = document.get(key, {})
        if not isinstance(dependencies, dict):
            raise DshLifecycleError("invalid pre-operation DSH profile manifest")
        unmanaged = {
            package: value
            for package, value in dependencies.items()
            if package not in PACKAGES
        }
        if unmanaged:
            inventory[key] = unmanaged
    return inventory


def _package_tree_inventories(
    dsh_home: Path,
    profile: str,
    package_names: Iterable[str] = PACKAGES,
) -> dict[str, dict[str, object]]:
    """Capture exact canonical identities for every lifecycle-owned package tree."""
    profile_root = dsh_home / "profiles" / profile
    return {
        package: _tree_inventory(profile_root / "node_modules" / Path(package))
        for package in sorted(package_names)
    }


def _assert_owned_package_trees(
    record: dict,
    *,
    dsh_home: Path,
    profile: str,
) -> None:
    expected = record.get("package_trees")
    if not isinstance(expected, dict) or set(expected) != set(PACKAGES):
        raise DshLifecycleError(
            "invalid DSH package inventory state; "
            "run 'ai-toolkit dsh doctor' and reinstall"
        )
    try:
        current = _package_tree_inventories(dsh_home, profile)
    except (DshLifecycleError, OSError, UnicodeError) as error:
        raise DshLifecycleError(
            "managed DSH package tree drift detected; refusing mutation"
        ) from error
    if current != expected:
        raise DshLifecycleError(
            "managed DSH package tree drift detected; refusing mutation"
        )


def _assert_package_postcondition(
    dsh_home: Path,
    profile: str,
    *,
    expected_managed: dict[str, str],
    expected_unmanaged: dict[str, dict[str, object]],
) -> None:
    """Reject a successful child exit unless its complete managed effect is exact."""
    found_managed = _profile_package_versions(dsh_home, profile)
    found_unmanaged = _profile_unmanaged_dependencies(dsh_home, profile)
    if found_managed != expected_managed or found_unmanaged != expected_unmanaged:
        raise DshLifecycleError(
            "DSH package postcondition failed; refusing to commit lifecycle state"
        )


def _assert_package_inventory_boundary(
    dsh_home: Path,
    profile: str,
    *,
    expected_managed: dict[str, str],
    expected_unmanaged: dict[str, dict[str, object]],
    expected_transaction: _ProfileTransaction,
) -> None:
    """Revalidate the complete package inventory immediately before mutation."""
    try:
        found_managed = _profile_package_versions(dsh_home, profile)
        found_unmanaged = _profile_unmanaged_dependencies(dsh_home, profile)
        manifest_path = expected_transaction.profile_root / "package.json"
        found_manifest = (
            _path_prestate(manifest_path)
            if manifest_path.exists() or manifest_path.is_symlink()
            else None
        )
        found_trees = {
            root: _snapshot_tree(root) for root in expected_transaction.package_trees
        }
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        raise DshLifecycleError(
            "DSH package inventory changed before external mutation; refusing"
        ) from error
    if (
        found_managed != expected_managed
        or found_unmanaged != expected_unmanaged
        or found_manifest != expected_transaction.manifest
        or found_trees != expected_transaction.package_trees
    ):
        raise DshLifecycleError(
            "DSH package inventory changed before external mutation; refusing"
        )


def _restore_packages(
    *,
    executable: str,
    dsh_home: Path,
    profile: str,
    before: dict[str, str],
    force_reinstall: bool = False,
    transaction: _ProfileTransaction | None = None,
) -> list[str]:
    """Best-effort restore of managed package versions; return failed recovery argv."""
    failed: list[str] = []
    recovery_unmanaged: dict[str, dict[str, object]] | None = None
    recovery_trees: dict[Path, dict[Path, _PathPrestate] | None] | None = None

    def append_blocked_recovery() -> None:
        actions = (
            f"run 'ai-toolkit dsh doctor --profile {profile}'",
            f"inspect preserved recovery path {str(transaction.profile_root)!r}",
        )
        failed.extend(action for action in actions if action not in failed)

    def rollback_is_blocked() -> bool:
        if transaction is None:
            return False
        if transaction.rollback_blocked:
            return True
        try:
            current_identity = _capture_package_mutation_identity(
                transaction.profile_root
            )
        except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
            transaction.rollback_blocked = True
            return True
        if current_identity != transaction.latest_package_identity:
            transaction.rollback_blocked = True
            return True
        if recovery_unmanaged is not None:
            try:
                current_unmanaged = _profile_unmanaged_dependencies(dsh_home, profile)
            except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
                transaction.rollback_blocked = True
                return True
            if current_unmanaged != recovery_unmanaged:
                transaction.rollback_blocked = True
                return True
        return False

    if transaction is not None:
        try:
            recovery_unmanaged = _preoperation_unmanaged_dependencies(transaction)
            if transaction.latest_package_identity is None:
                raise DshLifecycleError("missing package recovery identity")
            recovery_trees = dict(transaction.latest_package_identity.package_trees)
        except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
            transaction.rollback_blocked = True

    if rollback_is_blocked():
        append_blocked_recovery()
        return failed
    try:
        current = _profile_package_versions(dsh_home, profile)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        current = {}
    expected_managed = dict(current)
    for package, _expected_version in reversed(list(PACKAGES.items())):
        if rollback_is_blocked():
            append_blocked_recovery()
            break
        previous = before.get(package)
        found = current.get(package)
        if previous is None and found is not None:
            command = [executable, "plugin", "--profile", profile, "remove", package]
        elif previous is not None and (found != previous or force_reinstall):
            command = [
                executable,
                "plugin",
                "--profile",
                profile,
                "add",
                f"{package}@{previous}",
                "--save-exact",
            ]
        else:
            continue
        recovery_target: _RecoveryCommandTarget | None = None
        if transaction is not None:
            if recovery_trees is None or recovery_unmanaged is None:
                transaction.rollback_blocked = True
                append_blocked_recovery()
                break
            target_root = transaction.profile_root / "node_modules" / Path(package)
            expected_tree = transaction.package_trees.get(target_root)
            recovery_trees[target_root] = expected_tree
            if previous is None:
                expected_managed.pop(package, None)
            else:
                expected_managed[package] = previous
            recovery_target = _RecoveryCommandTarget(
                profile=profile,
                managed_packages=dict(expected_managed),
                unmanaged_dependencies=dict(recovery_unmanaged),
                package_trees=dict(recovery_trees),
            )
        try:
            if transaction is None:
                _run(command, dsh_home=dsh_home)
            else:
                _run_profile_command(
                    command,
                    dsh_home=dsh_home,
                    transaction=transaction,
                    recovery_target=recovery_target,
                )
        except _ProcessTreeTerminationError:
            raise
        except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
            failed.append(repr(command))
            if recovery_target is not None and not transaction.rollback_blocked:
                if previous is None:
                    expected_managed[package] = found
                else:
                    if found is None:
                        expected_managed.pop(package, None)
                    else:
                        expected_managed[package] = found
                recovery_trees = dict(transaction.latest_package_identity.package_trees)
            if rollback_is_blocked():
                append_blocked_recovery()
                break
        else:
            if rollback_is_blocked():
                append_blocked_recovery()
                break
    if transaction is not None and transaction.rollback_blocked:
        return failed
    try:
        restored = _profile_package_versions(dsh_home, profile)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        restored = {}
    if restored != before:
        for package in reversed(PACKAGES):
            previous = before.get(package)
            if previous is None:
                command = [
                    executable,
                    "plugin",
                    "--profile",
                    profile,
                    "remove",
                    package,
                ]
            else:
                command = [
                    executable,
                    "plugin",
                    "--profile",
                    profile,
                    "add",
                    f"{package}@{previous}",
                    "--save-exact",
                ]
            rendered = repr(command)
            if restored.get(package) != previous and rendered not in failed:
                failed.append(rendered)
    return failed


def _recovery_error(context: str, error: BaseException) -> str:
    if isinstance(error, KeyboardInterrupt):
        detail = "interrupted"
    else:
        detail = str(error) or type(error).__name__
    return f"{context}: {detail}"


def _safe_cleanup_owned(entries: list[_OwnedEntry], failed: list[str]) -> list[Path]:
    """Best-effort cleanup that always converts failures into recovery paths."""
    if not entries:
        return []
    try:
        return _cleanup_owned_entries(entries)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        failed.append(_recovery_error("owned cleanup failed", error))
        residuals = sorted({entry.path for entry in entries}, key=str)
        failed.extend(
            f"inspect preserved recovery path {str(path)!r}" for path in residuals
        )
        return residuals


def _safe_restore_profile_prestate(
    transaction: _ProfileTransaction,
    destination: Path,
    failed: list[str],
) -> None:
    if transaction.rollback_blocked:
        _record_profile_recovery(destination, [transaction.profile_root], failed)
        return
    try:
        residuals = _restore_profile_prestate(transaction)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        residuals = [transaction.profile_root]
    try:
        _record_profile_recovery(destination, residuals, failed)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        failed.append(
            f"inspect preserved recovery path {str(transaction.profile_root)!r}"
        )


def _safe_restore_state(
    snapshot: DshStateSnapshot,
    expected_profile: dict | None,
    failed: list[str],
) -> None:
    try:
        state_recovery = _restore_state(snapshot, expected_profile)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
        state_recovery = snapshot.path
    if state_recovery is not None:
        failed.append(f"restore ai-toolkit state at {str(state_recovery)!r}")


def _state_timestamp() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _expected_state_record(
    *,
    dsh_home: Path,
    profile: str,
    preset_path: Path,
    preset_hash: str,
    package_trees: dict[str, dict[str, object]],
    previous: dict | None,
    updated_at: str,
) -> dict:
    installed_at = previous.get("installed_at", updated_at) if previous else updated_at
    return {
        "dsh_home": str(dsh_home),
        "profile": profile,
        "packages": dict(sorted(PACKAGES.items())),
        "package_trees": {
            package: package_trees[package] for package in sorted(package_trees)
        },
        "preset_path": str(preset_path),
        "preset_hash": preset_hash,
        "owned": True,
        "installed_at": installed_at,
        "last_updated": updated_at,
    }


def _raise_with_recovery(error: DshLifecycleError, failed_commands: list[str]) -> None:
    if not failed_commands:
        raise error
    commands = "\n".join(f"  {command}" for command in failed_commands)
    raise DshLifecycleError(
        f"{error}\nRecovery required; complete these deterministic steps:\n{commands}"
    ) from error


def _raise_package_recovery_tree_error(
    primary_error: DshLifecycleError,
    recovery_error: _ProcessTreeTerminationError,
) -> None:
    """Preserve safe primary context while propagating an unconfirmed tree."""
    raise _ProcessTreeTerminationError(
        f"{primary_error}\nDSH package recovery stopped: {recovery_error}",
        process_group=recovery_error.process_group,
        profile=recovery_error.profile,
    ) from primary_error


def _block_rollback_for_live_process_tree(
    error: DshLifecycleError,
    *,
    profile: str,
    transaction: _ProfileTransaction,
) -> None:
    if not isinstance(error, _ProcessTreeTerminationError):
        return
    transaction.rollback_blocked = True
    _raise_with_recovery(
        error,
        [
            f"run 'ai-toolkit dsh doctor --profile {profile}'",
            f"inspect preserved recovery path {str(transaction.profile_root)!r}",
        ],
    )


def _validate_owned_record(
    record: dict,
    *,
    dsh_home: Path,
    profile: str,
    preset_destination: Path,
) -> None:
    expected = {
        "dsh_home": str(dsh_home),
        "profile": profile,
        "preset_path": str(preset_destination),
        "owned": True,
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise DshLifecycleError(f"DSH ownership state mismatch for '{key}'")
    packages = record.get("packages")
    if not isinstance(packages, dict) or set(packages) != set(MANAGED_PACKAGE_NAMES):
        raise DshLifecycleError("invalid DSH ownership state for 'packages'")
    for package, version in packages.items():
        if not isinstance(package, str) or not isinstance(version, str):
            raise DshLifecycleError("invalid DSH ownership state for 'packages'")
        if not EXACT_VERSION_PATTERN.fullmatch(version):
            raise DshLifecycleError(
                f"invalid DSH ownership state version for {package!r}"
            )
    package_trees = record.get("package_trees")
    if not isinstance(package_trees, dict) or set(package_trees) != set(packages):
        raise DshLifecycleError(
            "invalid DSH ownership state for 'package_trees'; "
            "run 'ai-toolkit dsh doctor' and reinstall"
        )
    preset_hash = record.get("preset_hash")
    if not isinstance(preset_hash, str) or not re.fullmatch(
        r"[0-9a-f]{64}", preset_hash
    ):
        raise DshLifecycleError("invalid DSH ownership state for 'preset_hash'")
    for key in ("installed_at", "last_updated"):
        if not isinstance(record.get(key), str) or not record[key]:
            raise DshLifecycleError(f"invalid DSH ownership state for '{key}'")


def _install(
    *,
    profile: str,
    dry_run: bool,
    pinned_home: _PinnedDshHome | None = None,
) -> str | None:
    dsh_home = pinned_home.path if pinned_home is not None else _dsh_home()
    if pinned_home is not None:
        _assert_dsh_home_binding(pinned_home)
    _assert_no_symlink_ancestry(dsh_home, "DSH home")
    _assert_profile_roots(dsh_home, profile)
    preset_destination = dsh_home / ".agent-presets" / PRESET_NAME
    owned = get_dsh_profile(profile)
    present_packages = _profile_package_versions(dsh_home, profile)
    unmanaged_dependencies = _profile_unmanaged_dependencies(dsh_home, profile)
    if owned is not None:
        _validate_owned_record(
            owned,
            dsh_home=dsh_home,
            profile=profile,
            preset_destination=preset_destination,
        )
        if present_packages != owned["packages"]:
            raise DshLifecycleError(
                "managed DSH package drift detected; run 'ai-toolkit dsh doctor'"
            )
        _assert_owned_package_trees(owned, dsh_home=dsh_home, profile=profile)
        if not preset_destination.is_dir() or preset_destination.is_symlink():
            raise DshLifecycleError("managed DSH preset is missing or unsafe")
        current_hash = _tree_hash(preset_destination)
        if current_hash != owned["preset_hash"]:
            raise DshLifecycleError(
                "managed DSH preset drift detected; refusing to overwrite"
            )
        source_hash = _tree_hash(_package_source(dsh_home, profile))
        if source_hash != current_hash:
            raise DshLifecycleError("installed DSH package preset source has drifted")
        _current_dsh_executable(dsh_home)
        return f"DSH profile integration already installed and unchanged: {profile}"
    if preset_destination.exists() or preset_destination.is_symlink():
        raise DshLifecycleError(
            f"preset collision, refusing to overwrite: {preset_destination}"
        )
    _assert_no_recovery_paths(preset_destination)
    collisions = sorted(set(PACKAGES).intersection(present_packages))
    if collisions and owned is None:
        raise DshLifecycleError(
            "plugin collision, refusing to overwrite: " + ", ".join(collisions)
        )
    executable = _current_dsh_executable(dsh_home)
    commands = [
        [
            executable,
            "plugin",
            "--profile",
            profile,
            "add",
            f"{package}@{version}",
            "--save-exact",
        ]
        for package, version in PACKAGES.items()
    ]
    if dry_run:
        for command in commands:
            print("PLAN argv:", repr(command))
        print(
            f"PLAN preset: {_package_source(dsh_home, profile)} -> {preset_destination}"
        )
        return None
    staging = preset_destination.parent / f".{preset_destination.name}.ai-toolkit-new"
    if staging.exists() or staging.is_symlink():
        raise DshLifecycleError(f"managed preset recovery collision: {staging}")
    staging_owned: list[_OwnedEntry] = []
    destination_owned: list[_OwnedEntry] = []
    preset_parent_owned: list[_OwnedEntry] = []
    profile_transaction = _capture_profile_transaction(dsh_home, profile)
    state_snapshot = _capture_state(profile, owned)
    state_owned = owned
    _assert_package_inventory_boundary(
        dsh_home,
        profile,
        expected_managed=present_packages,
        expected_unmanaged=unmanaged_dependencies,
        expected_transaction=profile_transaction,
    )
    try:
        expected_managed = dict(present_packages)
        observed_trees: dict[str, dict[str, object]] = {}
        for (package, version), command in zip(PACKAGES.items(), commands, strict=True):
            _run_profile_command(
                command, dsh_home=dsh_home, transaction=profile_transaction
            )
            expected_managed[package] = version
            _assert_package_postcondition(
                dsh_home,
                profile,
                expected_managed=expected_managed,
                expected_unmanaged=unmanaged_dependencies,
            )
            current_trees = _package_tree_inventories(
                dsh_home,
                profile,
                expected_managed,
            )
            if any(
                current_trees.get(name) != identity
                for name, identity in observed_trees.items()
            ):
                profile_transaction.rollback_blocked = True
                raise DshLifecycleError(
                    "package identity changed during successful external mutation"
                )
            observed_trees[package] = current_trees[package]
        _assert_package_postcondition(
            dsh_home,
            profile,
            expected_managed=PACKAGES,
            expected_unmanaged=unmanaged_dependencies,
        )
        package_trees = _package_tree_inventories(dsh_home, profile)
        source = _package_source(dsh_home, profile)
        preset_hash = _tree_hash(source)
        if not preset_destination.parent.exists():
            _claim_directory(preset_destination.parent, preset_parent_owned)
        source_mode = stat.S_IMODE(source.stat(follow_symlinks=False).st_mode)
        _claim_directory(staging, staging_owned, mode=source_mode)
        _copy_tree_exclusive(source, staging, staging_owned)
        if _tree_hash(staging) != preset_hash:
            raise DshLifecycleError("managed preset staging failed hash verification")
        _claim_directory(
            preset_destination,
            destination_owned,
            mode=source_mode,
        )
        _copy_tree_exclusive(staging, preset_destination, destination_owned)
        copied_hash = _tree_hash(preset_destination)
        if copied_hash != preset_hash:
            raise DshLifecycleError("managed preset copy failed hash verification")
        if remaining := _cleanup_owned_entries(staging_owned):
            paths = ", ".join(repr(str(path)) for path in remaining)
            raise DshLifecycleError(
                f"managed preset staging cleanup failed; preserved: {paths}"
            )
        staging_owned.clear()
        state_updated_at = _state_timestamp()
        state_owned = _expected_state_record(
            dsh_home=dsh_home,
            profile=profile,
            preset_path=preset_destination,
            preset_hash=copied_hash,
            package_trees=package_trees,
            previous=owned,
            updated_at=state_updated_at,
        )
        record_dsh_profile(
            dsh_home=dsh_home,
            profile=profile,
            packages=PACKAGES,
            package_trees=package_trees,
            preset_path=preset_destination,
            preset_hash=copied_hash,
            expected_profile=owned,
            updated_at=state_updated_at,
            binding_validator=_assert_active_dsh_home_binding,
            state_snapshot=state_snapshot,
        )
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            lifecycle_error = DshLifecycleError("DSH install was interrupted")
        else:
            lifecycle_error = (
                error
                if isinstance(error, DshLifecycleError)
                else DshLifecycleError(f"DSH install failed: {error}")
            )
        _block_rollback_for_live_process_tree(
            lifecycle_error,
            profile=profile,
            transaction=profile_transaction,
        )
        failed: list[str] = []
        cleanup_residuals = _safe_cleanup_owned(destination_owned, failed)
        cleanup_residuals.extend(_safe_cleanup_owned(staging_owned, failed))
        cleanup_residuals.extend(_safe_cleanup_owned(preset_parent_owned, failed))
        try:
            package_recovery = _restore_packages(
                executable=executable,
                dsh_home=dsh_home,
                profile=profile,
                before=present_packages,
                transaction=profile_transaction,
            )
        except _ProcessTreeTerminationError as recovery_error:
            _raise_package_recovery_tree_error(lifecycle_error, recovery_error)
        failed.extend(package_recovery)
        _safe_restore_profile_prestate(profile_transaction, preset_destination, failed)
        if cleanup_residuals:
            _record_profile_recovery(preset_destination, cleanup_residuals, failed)
        _safe_restore_state(state_snapshot, state_owned, failed)
        _raise_with_recovery(lifecycle_error, failed)
    return f"Installed DSH profile integration: {profile}"


def _replace_owned_preset(
    source: Path,
    destination: Path,
    *,
    expected_destination: _OwnedEntry,
    destination_owned: list[_OwnedEntry],
    retain_backup: bool = False,
    recovery_owned: list[_RelocatedPreset] | None = None,
) -> tuple[str, _RelocatedPreset | None]:
    expected_hash = _tree_hash(source)
    staging = destination.parent / f".{destination.name}.ai-toolkit-new"
    if staging.exists() or staging.is_symlink():
        raise DshLifecycleError(f"managed preset recovery collision: {staging}")
    staging_owned: list[_OwnedEntry] = []
    backup: _RelocatedPreset | None = None
    try:
        source_mode = stat.S_IMODE(source.stat(follow_symlinks=False).st_mode)
        _claim_directory(staging, staging_owned, mode=source_mode)
        _copy_tree_exclusive(source, staging, staging_owned)
        if _tree_hash(staging) != expected_hash:
            raise DshLifecycleError("managed preset staging failed hash verification")
    except (DshLifecycleError, OSError, KeyboardInterrupt) as error:
        cleanup_failures: list[str] = []
        _raise_staging_failure(
            error,
            _cleanup_staging_entries(staging, staging_owned, cleanup_failures),
            cleanup_failures,
        )
    try:
        _assert_entry_unchanged(expected_destination, "managed preset")
        backup = _relocate_owned_preset(
            expected_destination,
            "backup",
            recovery_owned,
        )
        _secure_rename_noreplace(staging, destination)
        destination_owned.extend(
            _OwnedEntry(
                destination / entry.path.relative_to(staging),
                entry.device,
                entry.inode,
                entry.kind,
                entry.digest,
                entry.link_target,
                entry.parent_device,
                entry.parent_inode,
            )
            for entry in staging_owned
        )
        staging_owned.clear()
        if _tree_hash(destination) != expected_hash:
            raise DshLifecycleError(
                "managed preset replacement identity changed; preserved"
            )
    except (DshLifecycleError, OSError, KeyboardInterrupt) as error:
        recovery_residuals: list[Path] = []
        cleanup_failures = []
        if backup is not None and not destination.exists():
            try:
                _assert_entry_unchanged(
                    backup.payload,
                    "relocated managed preset recovery payload",
                )
                _secure_rename_noreplace(backup.payload.path, destination)
                _cleanup_recovery_location(backup.location)
            except (DshLifecycleError, OSError, KeyboardInterrupt):
                recovery_residuals.append(backup.location.root.path)
        recovery_residuals.extend(
            _cleanup_staging_entries(staging, staging_owned, cleanup_failures)
        )
        _raise_staging_failure(
            error,
            sorted(set(recovery_residuals), key=str),
            cleanup_failures,
        )
    if retain_backup:
        return expected_hash, backup
    if backup is None:
        raise DshLifecycleError(
            "relocated managed preset backup identity was not captured"
        )
    _assert_entry_unchanged(
        backup.payload,
        "relocated managed preset recovery payload",
    )
    _remove_exact_managed_tree(
        backup.payload.path,
        expected_destination.digest or _tree_hash(backup.payload.path),
        expected_root=backup.payload,
    )
    _cleanup_recovery_location(backup.location)
    return expected_hash, None


def _update(
    *,
    profile: str,
    dry_run: bool,
    pinned_home: _PinnedDshHome | None = None,
) -> str | None:
    dsh_home = pinned_home.path if pinned_home is not None else _dsh_home()
    if pinned_home is not None:
        _assert_dsh_home_binding(pinned_home)
    _assert_no_symlink_ancestry(dsh_home, "DSH home")
    _assert_profile_roots(dsh_home, profile)
    destination = dsh_home / ".agent-presets" / PRESET_NAME
    record = get_dsh_profile(profile)
    if record is None:
        raise DshLifecycleError(
            f"DSH profile '{profile}' is not owned; run 'ai-toolkit dsh install --profile {profile}'"
        )
    _validate_owned_record(
        record,
        dsh_home=dsh_home,
        profile=profile,
        preset_destination=destination,
    )
    recorded_packages = {
        package: record["packages"][package] for package in MANAGED_PACKAGE_NAMES
    }
    present_packages = _profile_package_versions(dsh_home, profile)
    unmanaged_dependencies = _profile_unmanaged_dependencies(dsh_home, profile)
    if present_packages != recorded_packages:
        raise DshLifecycleError("managed DSH package drift detected; refusing update")
    _assert_owned_package_trees(record, dsh_home=dsh_home, profile=profile)
    destination_identity = _capture_entry(destination)
    if (
        destination_identity.kind != "directory"
        or destination_identity.digest != record["preset_hash"]
    ):
        raise DshLifecycleError("managed DSH preset drift detected; refusing update")
    if _tree_hash(_package_source(dsh_home, profile)) != record["preset_hash"]:
        raise DshLifecycleError("installed DSH package preset source has drifted")
    _assert_no_recovery_paths(destination)
    executable = _current_dsh_executable(dsh_home)
    commands = [
        [
            executable,
            "plugin",
            "--profile",
            profile,
            "add",
            f"{package}@{version}",
            "--save-exact",
        ]
        for package, version in PACKAGES.items()
    ]
    if dry_run:
        for command in commands:
            print("PLAN argv:", repr(command))
        print(f"PLAN preset: {_package_source(dsh_home, profile)} -> {destination}")
        return None
    backup: _RelocatedPreset | None = None
    recovery_owned: list[_RelocatedPreset] = []
    preset_hash: str | None = None
    replacement_owned: list[_OwnedEntry] = []
    profile_transaction = _capture_profile_transaction(dsh_home, profile)
    state_snapshot = _capture_state(profile, record)
    state_owned = record
    _assert_package_inventory_boundary(
        dsh_home,
        profile,
        expected_managed=present_packages,
        expected_unmanaged=unmanaged_dependencies,
        expected_transaction=profile_transaction,
    )
    try:
        expected_managed = dict(recorded_packages)
        expected_trees = dict(record["package_trees"])
        for (package, version), command in zip(
            PACKAGES.items(), commands, strict=True
        ):
            _run_profile_command(
                command, dsh_home=dsh_home, transaction=profile_transaction
            )
            expected_managed[package] = version
            _assert_package_postcondition(
                dsh_home,
                profile,
                expected_managed=expected_managed,
                expected_unmanaged=unmanaged_dependencies,
            )
            current_trees = _package_tree_inventories(dsh_home, profile)
            if any(
                current_trees.get(name) != identity
                for name, identity in expected_trees.items()
                if name != package
            ):
                profile_transaction.rollback_blocked = True
                raise DshLifecycleError(
                    "package identity changed during successful external mutation"
                )
            expected_trees[package] = current_trees[package]
        _assert_package_postcondition(
            dsh_home,
            profile,
            expected_managed=PACKAGES,
            expected_unmanaged=unmanaged_dependencies,
        )
        package_trees = _package_tree_inventories(dsh_home, profile)
        preset_hash, backup = _replace_owned_preset(
            _package_source(dsh_home, profile),
            destination,
            expected_destination=destination_identity,
            destination_owned=replacement_owned,
            retain_backup=True,
            recovery_owned=recovery_owned,
        )
        state_updated_at = _state_timestamp()
        state_owned = _expected_state_record(
            dsh_home=dsh_home,
            profile=profile,
            preset_path=destination,
            preset_hash=preset_hash,
            package_trees=package_trees,
            previous=record,
            updated_at=state_updated_at,
        )
        record_dsh_profile(
            dsh_home=dsh_home,
            profile=profile,
            packages=PACKAGES,
            package_trees=package_trees,
            preset_path=destination,
            preset_hash=preset_hash,
            expected_profile=record,
            updated_at=state_updated_at,
            binding_validator=_assert_active_dsh_home_binding,
            state_snapshot=state_snapshot,
        )
        if backup is not None:
            _assert_entry_unchanged(
                backup.payload,
                "relocated managed preset recovery payload",
            )
            _remove_exact_managed_tree(
                backup.payload.path,
                record["preset_hash"],
                expected_root=backup.payload,
            )
            _cleanup_recovery_location(backup.location)
            backup = None
            recovery_owned.clear()
        _assert_no_recovery_paths(destination)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            lifecycle_error = DshLifecycleError("DSH update was interrupted")
        else:
            lifecycle_error = (
                error
                if isinstance(error, DshLifecycleError)
                else DshLifecycleError(f"DSH update failed: {error}")
            )
        _block_rollback_for_live_process_tree(
            lifecycle_error,
            profile=profile,
            transaction=profile_transaction,
        )
        preset_recovery: list[str] = []
        recovery_backup = backup or (recovery_owned[-1] if recovery_owned else None)
        try:
            failed = _restore_packages(
                executable=executable,
                dsh_home=dsh_home,
                profile=profile,
                before=present_packages,
                force_reinstall=True,
                transaction=profile_transaction,
            )
        except _ProcessTreeTerminationError as recovery_error:
            _raise_package_recovery_tree_error(lifecycle_error, recovery_error)
        _safe_restore_profile_prestate(profile_transaction, destination, failed)
        try:
            source_restored = (
                _tree_hash(_package_source(dsh_home, profile)) == record["preset_hash"]
            )
        except (
            DshLifecycleError,
            OSError,
            ValueError,
            KeyboardInterrupt,
        ) as recovery_error:
            source_restored = False
            failed.append(
                _recovery_error(
                    "verify restored package preset failed",
                    recovery_error,
                )
            )
        backup_collision = False
        backup_is_complete = False
        if recovery_backup is not None:
            try:
                _assert_entry_unchanged(
                    recovery_backup.payload,
                    "relocated managed preset recovery payload",
                )
                backup_is_complete = (
                    recovery_backup.payload.kind == "directory"
                    and recovery_backup.payload.digest == record["preset_hash"]
                )
            except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
                backup_collision = (
                    recovery_backup.location.root.path.exists()
                    or recovery_backup.location.root.path.is_symlink()
                )
                if (
                    backup_collision
                    and not recovery_backup.location.payload.exists()
                    and not recovery_backup.location.payload.is_symlink()
                ):
                    try:
                        _cleanup_recovery_location(recovery_backup.location)
                        backup_collision = False
                    except (DshLifecycleError, OSError, KeyboardInterrupt):
                        pass
            if backup_is_complete:
                if replacement_owned:
                    remaining = _safe_cleanup_owned(replacement_owned, failed)
                    preset_recovery.extend(
                        f"inspect preserved recovery path {str(path)!r}"
                        for path in remaining
                    )
                if not destination.exists() and not destination.is_symlink():
                    try:
                        _assert_entry_unchanged(
                            recovery_backup.payload,
                            "relocated managed preset recovery payload",
                        )
                        _secure_rename_noreplace(
                            recovery_backup.payload.path,
                            destination,
                        )
                        _cleanup_recovery_location(recovery_backup.location)
                    except (DshLifecycleError, OSError, KeyboardInterrupt):
                        preset_recovery.append(
                            "restore managed preset from "
                            f"{str(recovery_backup.location.root.path)!r} "
                            f"to {str(destination)!r}"
                        )
                else:
                    preset_recovery.append(
                        "inspect preserved recovery path "
                        f"{str(recovery_backup.location.root.path)!r}"
                    )
            elif backup_collision:
                preset_recovery.append(
                    "inspect preserved recovery path "
                    f"{str(recovery_backup.location.root.path)!r}"
                )
        if not backup_is_complete and not backup_collision and source_restored:
            if replacement_owned:
                remaining = _safe_cleanup_owned(replacement_owned, failed)
                preset_recovery.extend(
                    f"inspect preserved recovery path {str(path)!r}"
                    for path in remaining
                )
            try:
                restored_paths = _restore_preset_from_source(
                    _package_source(dsh_home, profile), destination
                )
            except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
                restored_paths = [destination]
            for path in restored_paths:
                preset_recovery.append(f"inspect preserved recovery path {str(path)!r}")
        failed.extend(preset_recovery)
        _record_detected_recovery_artifacts(destination, failed)
        if not source_restored:
            recovery = repr(
                [
                    executable,
                    "plugin",
                    "--profile",
                    profile,
                    "add",
                    "@softspark/dsh-orchestrator@"
                    + recorded_packages["@softspark/dsh-orchestrator"],
                    "--save-exact",
                ]
            )
            if recovery not in failed:
                failed.append(recovery)
        _safe_restore_state(state_snapshot, state_owned, failed)
        _raise_with_recovery(lifecycle_error, failed)
    return f"Updated DSH profile integration: {profile}"


def _doctor(*, profile: str) -> int:
    dsh_home = _dsh_home()
    _assert_no_symlink_ancestry(dsh_home, "DSH home")
    _assert_profile_roots(dsh_home, profile)
    healthy = True
    destination = dsh_home / ".agent-presets" / PRESET_NAME
    for artifact in _lifecycle_lock_recovery_artifacts(dsh_home):
        gate = _read_lifecycle_recovery_gate(artifact)
        if gate is not None and gate.get("reason") == "unconfirmed-process-tree":
            process_group = gate.get("process_group", "unknown")
            gate_profile = gate.get("profile", "")
            inspection_path = (
                dsh_home / "profiles" / gate_profile
                if PROFILE_PATTERN.fullmatch(gate_profile)
                else dsh_home / "profiles"
            )
            print(
                "Recovery gate: unconfirmed DSH process tree "
                f"(process group {process_group})"
            )
            print(
                "Recovery guidance: verify that process group "
                f"{process_group} has exited and inspect "
                f"{str(inspection_path)!r}"
            )
            print(
                "Recovery guidance: remove only after manual verification: "
                f"{str(artifact)!r}"
            )
        else:
            print(f"Lifecycle lock recovery artifact: {str(artifact)!r}")
        healthy = False
    for recovery_path in _recovery_artifacts(destination):
        if recovery_path.exists() or recovery_path.is_symlink():
            print(f"Recovery artifact: {str(recovery_path)!r}")
            healthy = False
    try:
        _, pnpm_version = _find_supported_pnpm(dsh_home)
        print(f"Package manager: supported (pnpm {pnpm_version})")
    except DshLifecycleError as error:
        print(f"Package manager: unsupported or missing ({error})")
        healthy = False
    try:
        _find_supported_dsh(dsh_home)
        print(f"Runtime: supported ({SUPPORTED_DSH_VERSION})")
    except DshLifecycleError as error:
        print(f"Runtime: unsupported or missing ({error})")
        healthy = False
    try:
        present_packages = _profile_package_versions(dsh_home, profile)
    except DshLifecycleError as error:
        print(f"Packages: unreadable ({error})")
        present_packages = {}
        healthy = False
    for package, expected in PACKAGES.items():
        found = present_packages.get(package, "missing")
        print(f"{package}: {found} (expected {expected})")
        if found != expected:
            healthy = False
    try:
        record = get_dsh_profile(profile)
    except ValueError as error:
        print(f"State: invalid ({error})")
        record = None
        healthy = False
    if record is None:
        print("Preset: unowned")
        print("State: missing")
        healthy = False
    else:
        try:
            _validate_owned_record(
                record,
                dsh_home=dsh_home,
                profile=profile,
                preset_destination=destination,
            )
            if not destination.is_dir() or destination.is_symlink():
                print("Preset: owned, missing or unsafe")
                healthy = False
            elif _tree_hash(destination) != record["preset_hash"]:
                print("Preset: owned, hash drift")
                healthy = False
            else:
                print("Preset: owned, hash matches")
            source = _package_source(dsh_home, profile)
            try:
                source_matches = _tree_hash(source) == record["preset_hash"]
            except DshLifecycleError:
                source_matches = False
            if source_matches:
                print("Preset source: hash matches")
            else:
                print("Preset source: hash drift")
                healthy = False
            try:
                _assert_owned_package_trees(
                    record,
                    dsh_home=dsh_home,
                    profile=profile,
                )
                print("Package trees: ownership matches")
            except DshLifecycleError:
                print("Package trees: ownership drift")
                healthy = False
            if healthy:
                print("State: consistent")
            else:
                print("State: inconsistent")
        except DshLifecycleError as error:
            print(f"Preset: ownership invalid ({error})")
            print("State: inconsistent")
            healthy = False
    print(f"Recovery needed: {'no' if healthy else 'yes'}")
    return 0 if healthy else 1


def _uninstall(
    *,
    profile: str,
    dry_run: bool,
    assume_yes: bool,
    pinned_home: _PinnedDshHome | None = None,
) -> str | None:
    dsh_home = pinned_home.path if pinned_home is not None else _dsh_home()
    if pinned_home is not None:
        _assert_dsh_home_binding(pinned_home)
    _assert_no_symlink_ancestry(dsh_home, "DSH home")
    _assert_profile_roots(dsh_home, profile)
    destination = dsh_home / ".agent-presets" / PRESET_NAME
    backup: _RelocatedPreset | None = None
    recovery_owned: list[_RelocatedPreset] = []
    record = get_dsh_profile(profile)
    if record is None:
        raise DshLifecycleError(f"DSH profile '{profile}' is not owned by ai-toolkit")
    _validate_owned_record(
        record,
        dsh_home=dsh_home,
        profile=profile,
        preset_destination=destination,
    )
    recorded_packages = {
        package: record["packages"][package] for package in MANAGED_PACKAGE_NAMES
    }
    packages = _profile_package_versions(dsh_home, profile)
    unmanaged_dependencies = _profile_unmanaged_dependencies(dsh_home, profile)
    if packages != recorded_packages:
        raise DshLifecycleError(
            "managed DSH package drift detected; refusing uninstall"
        )
    _assert_owned_package_trees(record, dsh_home=dsh_home, profile=profile)
    destination_identity = _capture_entry(destination)
    if (
        destination_identity.kind != "directory"
        or destination_identity.digest != record["preset_hash"]
    ):
        raise DshLifecycleError("managed DSH preset drift detected; refusing uninstall")
    _assert_no_recovery_paths(destination)
    executable = _current_dsh_executable(dsh_home)
    commands = [
        [executable, "plugin", "--profile", profile, "remove", package]
        for package in reversed(recorded_packages)
    ]
    if dry_run:
        for command in commands:
            print("PLAN argv:", repr(command))
        print(f"PLAN remove preset: {destination}")
        print(f"PLAN remove state: dsh.profiles.{profile}")
        return None
    if not assume_yes:
        try:
            answer = input(
                f"Remove ai-toolkit DSH integration from profile '{profile}'? [y/N] "
            )
        except EOFError as error:
            raise DshLifecycleError(
                "uninstall confirmation required; pass --yes"
            ) from error
        if answer.strip().lower() not in {"y", "yes"}:
            raise DshLifecycleError("uninstall cancelled")
    state_snapshot = _capture_state(profile, record)
    state_owned: dict | None = record
    profile_transaction = _capture_profile_transaction(dsh_home, profile)
    _assert_package_inventory_boundary(
        dsh_home,
        profile,
        expected_managed=packages,
        expected_unmanaged=unmanaged_dependencies,
        expected_transaction=profile_transaction,
    )
    package_mutation_started = False
    try:
        _assert_entry_unchanged(destination_identity, "managed preset")
        backup = _relocate_owned_preset(
            destination_identity,
            "uninstall",
            recovery_owned,
        )
        _assert_package_inventory_boundary(
            dsh_home,
            profile,
            expected_managed=packages,
            expected_unmanaged=unmanaged_dependencies,
            expected_transaction=profile_transaction,
        )
        expected_managed = dict(packages)
        expected_trees = dict(record["package_trees"])
        for package, command in zip(
            reversed(recorded_packages), commands, strict=True
        ):
            package_mutation_started = True
            _run_profile_command(
                command, dsh_home=dsh_home, transaction=profile_transaction
            )
            expected_managed.pop(package, None)
            expected_trees.pop(package, None)
            _assert_package_postcondition(
                dsh_home,
                profile,
                expected_managed=expected_managed,
                expected_unmanaged=unmanaged_dependencies,
            )
            if (
                _package_tree_inventories(
                    dsh_home,
                    profile,
                    expected_managed,
                )
                != expected_trees
            ):
                profile_transaction.rollback_blocked = True
                raise DshLifecycleError(
                    "package identity changed during successful external mutation"
                )
        _assert_package_postcondition(
            dsh_home,
            profile,
            expected_managed={},
            expected_unmanaged=unmanaged_dependencies,
        )
        state_owned = None
        remove_dsh_profile(
            profile,
            expected_profile=record,
            binding_validator=_assert_active_dsh_home_binding,
            state_snapshot=state_snapshot,
        )
        if backup is None:
            raise DshLifecycleError(
                "relocated managed preset uninstall backup identity was not captured"
            )
        _assert_entry_unchanged(
            backup.payload,
            "relocated managed preset recovery payload",
        )
        _remove_exact_managed_tree(
            backup.payload.path,
            record["preset_hash"],
            expected_root=backup.payload,
        )
        _cleanup_recovery_location(backup.location)
        backup = None
        recovery_owned.clear()
        _assert_no_recovery_paths(destination)
    except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            lifecycle_error = DshLifecycleError("DSH uninstall was interrupted")
        else:
            lifecycle_error = (
                error
                if isinstance(error, DshLifecycleError)
                else DshLifecycleError(f"DSH uninstall failed: {error}")
            )
        _block_rollback_for_live_process_tree(
            lifecycle_error,
            profile=profile,
            transaction=profile_transaction,
        )
        preset_recovery: list[str] = []
        failed: list[str] = []
        if package_mutation_started:
            try:
                package_recovery = _restore_packages(
                    executable=executable,
                    dsh_home=dsh_home,
                    profile=profile,
                    before=packages,
                    transaction=profile_transaction,
                )
            except _ProcessTreeTerminationError as recovery_error:
                _raise_package_recovery_tree_error(lifecycle_error, recovery_error)
            failed.extend(package_recovery)
            _safe_restore_profile_prestate(profile_transaction, destination, failed)
        try:
            source_restored = (
                _tree_hash(_package_source(dsh_home, profile)) == record["preset_hash"]
            )
        except (
            DshLifecycleError,
            OSError,
            ValueError,
            KeyboardInterrupt,
        ) as recovery_error:
            source_restored = False
            failed.append(
                _recovery_error(
                    "verify restored package preset failed",
                    recovery_error,
                )
            )
        backup_complete = False
        backup_collision = False
        recovery_backup = backup or (recovery_owned[-1] if recovery_owned else None)
        if recovery_backup is not None:
            try:
                _assert_entry_unchanged(
                    recovery_backup.payload,
                    "relocated managed preset recovery payload",
                )
                backup_complete = (
                    recovery_backup.payload.kind == "directory"
                    and recovery_backup.payload.digest == record["preset_hash"]
                )
            except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
                backup_complete = False
                backup_collision = (
                    recovery_backup.location.root.path.exists()
                    or recovery_backup.location.root.path.is_symlink()
                )
                if (
                    backup_collision
                    and not recovery_backup.location.payload.exists()
                    and not recovery_backup.location.payload.is_symlink()
                ):
                    try:
                        _cleanup_recovery_location(recovery_backup.location)
                        backup_collision = False
                    except (DshLifecycleError, OSError, KeyboardInterrupt):
                        pass
            if (
                backup_complete
                and not destination.exists()
                and not destination.is_symlink()
            ):
                try:
                    _assert_entry_unchanged(
                        recovery_backup.payload,
                        "relocated managed preset recovery payload",
                    )
                    _secure_rename_noreplace(
                        recovery_backup.payload.path,
                        destination,
                    )
                    _cleanup_recovery_location(recovery_backup.location)
                except (DshLifecycleError, OSError, KeyboardInterrupt):
                    preset_recovery.append(
                        "restore managed preset from "
                        f"{str(recovery_backup.location.root.path)!r} "
                        f"to {str(destination)!r}"
                    )
            else:
                preset_recovery.append(
                    "inspect preserved recovery path "
                    f"{str(recovery_backup.location.root.path)!r}"
                )
        if not backup_complete and not backup_collision and source_restored:
            try:
                restored_paths = _restore_preset_from_source(
                    _package_source(dsh_home, profile), destination
                )
            except (DshLifecycleError, OSError, ValueError, KeyboardInterrupt):
                restored_paths = [destination]
            for path in restored_paths:
                preset_recovery.append(f"inspect preserved recovery path {str(path)!r}")
        failed.extend(preset_recovery)
        _record_detected_recovery_artifacts(destination, failed)
        _safe_restore_state(state_snapshot, state_owned, failed)
        _raise_with_recovery(lifecycle_error, failed)
    return f"Uninstalled DSH profile integration: {profile}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    install = subparsers.add_parser("install")
    install.add_argument("--profile", default=DEFAULT_PROFILE)
    install.add_argument("--dry-run", action="store_true")
    update = subparsers.add_parser("update")
    update.add_argument("--profile", default=DEFAULT_PROFILE)
    update.add_argument("--dry-run", action="store_true")
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--profile", default=DEFAULT_PROFILE)
    uninstall = subparsers.add_parser("uninstall")
    uninstall.add_argument("--profile", default=DEFAULT_PROFILE)
    uninstall.add_argument("--dry-run", action="store_true")
    uninstall.add_argument("--yes", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        profile = _validate_profile(args.profile)
        if args.command == "doctor":
            return _doctor(profile=profile)
        dsh_home = _dsh_home()
        _assert_no_symlink_ancestry(dsh_home, "DSH home")
        prerequisites = _preflight_prerequisites(dsh_home)
        if args.dry_run:
            if args.command == "install":
                result = _install(profile=profile, dry_run=True)
            elif args.command == "update":
                result = _update(profile=profile, dry_run=True)
            else:
                result = _uninstall(
                    profile=profile,
                    dry_run=True,
                    assume_yes=args.yes,
                )
            if result is not None:
                print(result)
            return 0
        if not _secure_mutation_supported():
            raise DshLifecycleError(
                "secure DSH filesystem mutation is unsupported on this platform; "
                "use Linux, WSL, or macOS"
            )
        if not secure_dsh_state_mutation_supported():
            raise DshLifecycleError(
                "secure ai-toolkit state mutation is unsupported on this platform; "
                "use Linux, WSL, or macOS"
            )
        if not _directory_lifecycle_lock_supported():
            raise DshLifecycleError(
                "DSH home directory lifecycle locking is unsupported; "
                "use Linux, WSL, or macOS"
            )
        if not _mutation_process_groups_supported():
            raise DshLifecycleError(
                "DSH mutation process-group termination is unsupported; "
                "use Linux, WSL, or macOS"
            )
        with _locked_lifecycle(dsh_home, prerequisites) as pinned_home:
            if args.command == "install":
                result = _install(
                    profile=profile,
                    dry_run=False,
                    pinned_home=pinned_home,
                )
            elif args.command == "update":
                result = _update(
                    profile=profile,
                    dry_run=False,
                    pinned_home=pinned_home,
                )
            else:
                result = _uninstall(
                    profile=profile,
                    dry_run=False,
                    assume_yes=args.yes,
                    pinned_home=pinned_home,
                )
        if result is not None:
            print(result)
    except KeyboardInterrupt:
        print("Error: DSH lifecycle was interrupted", file=sys.stderr)
        return 1
    except (DshLifecycleError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
