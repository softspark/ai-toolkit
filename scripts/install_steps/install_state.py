# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Track installed modules and versions in ~/.softspark/ai-toolkit/state.json."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import secrets
import stat
import sys
import tempfile
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import EXTERNAL_HOOKS_DIR, RULES_DIR, STATE_FILE

_STATE_LOCK_TIMEOUT_SECONDS = 2.0
_STATE_LOCK_POLL_SECONDS = 0.025
# Top-level key of the retired DSH profile lifecycle; dropped on the next write.
LEGACY_DSH_STATE_KEY = "dsh"


@dataclass(frozen=True)
class _StateWriterContext:
    """One state transaction bound to the parent inode that owns its lock."""

    path: Path
    parent_descriptor: int | None
    parent_device: int | None
    parent_inode: int | None


def _load_sources(sources_file: Path, key: str) -> list[tuple[str, str, str, str]]:
    """Read a sources.json registry.

    Returns a list of ``(name, origin, fetched_at, kind)`` tuples where
    ``kind`` is ``"url"`` for remote sources, ``"local"`` for path-tracked
    sources, and ``"unknown"`` if neither field is present.
    """
    if not sources_file.is_file():
        return []
    try:
        with open(sources_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    entries = data.get(key, {}) if isinstance(data, dict) else {}
    if not isinstance(entries, dict):
        return []
    out: list[tuple[str, str, str, str]] = []
    for name, meta in sorted(entries.items()):
        if not isinstance(meta, dict):
            continue
        if "url" in meta:
            origin, kind = str(meta["url"]), "url"
        elif "path" in meta:
            origin, kind = str(meta["path"]), "local"
        else:
            origin, kind = "", "unknown"
        out.append((name, origin, str(meta.get("fetched_at", "")), kind))
    return out


def _orphan_rule_files(rules_dir: Path, registered: set[str]) -> list[str]:
    """Return rule names present on disk but missing from sources.json."""
    if not rules_dir.is_dir():
        return []
    return sorted(f.stem for f in rules_dir.glob("*.md") if f.stem not in registered)


def _state_path() -> Path:
    """Return the canonical path to state.json."""
    return STATE_FILE


def _unsafe_state_root() -> Path | None:
    path = _state_path()
    for candidate in (path.parent.parent, path.parent):
        if candidate.is_symlink():
            return candidate
        if candidate.exists() and not candidate.is_dir():
            return candidate
    return None


def _prepare_state_parent() -> None:
    if unsafe_root := _unsafe_state_root():
        raise OSError(f"unsafe ai-toolkit state root: {unsafe_root}")
    _state_path().parent.mkdir(parents=True, exist_ok=True)
    if unsafe_root := _unsafe_state_root():
        raise OSError(f"unsafe ai-toolkit state root: {unsafe_root}")


def _release_state_lock(
    lock_path: Path,
    identity: tuple[int, int],
    *,
    secure: bool,
    parent_descriptor: int | None,
) -> None:
    if not secure:
        try:
            metadata = lock_path.stat(follow_symlinks=False)
        except OSError as error:
            raise OSError("ai-toolkit state lock disappeared before release") from error
        if (
            not stat.S_ISREG(metadata.st_mode)
            or (metadata.st_dev, metadata.st_ino) != identity
        ):
            raise OSError(
                f"ai-toolkit state lock identity changed; preserved at {lock_path}"
            )
        lock_path.unlink()
        return
    if parent_descriptor is None:
        raise OSError("secure ai-toolkit state lock parent is unavailable")
    parent_matches = _state_parent_path_matches(
        lock_path.parent,
        parent_descriptor,
    )
    recovery = lock_path.parent / (
        f".state-lock-release-{os.getpid()}-{secrets.token_hex(12)}"
    )
    try:
        _state_rename_operation(
            lock_path,
            recovery,
            exchange=False,
            source_parent_descriptor=parent_descriptor,
            destination_parent_descriptor=parent_descriptor,
        )
        metadata = os.stat(
            recovery.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as error:
        raise OSError("ai-toolkit state lock disappeared before release") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != identity
    ):
        raise OSError(
            f"ai-toolkit state lock identity changed; preserved at {recovery}"
        )
    os.unlink(recovery.name, dir_fd=parent_descriptor)
    if not parent_matches or not _state_parent_path_matches(
        lock_path.parent,
        parent_descriptor,
    ):
        raise OSError(
            "ai-toolkit state parent identity changed; both roots were preserved"
        )


@contextmanager
def _state_writer_lock() -> Iterator[_StateWriterContext]:
    """Hold the bounded cooperative lock for one complete state transaction."""
    _prepare_state_parent()
    state_path = _state_path()
    lock_path = state_path.parent / ".state.lock"
    deadline = time.monotonic() + _STATE_LOCK_TIMEOUT_SECONDS
    descriptor: int | None = None
    identity: tuple[int, int] | None = None
    parent_descriptor = (
        _open_state_parent(lock_path.parent)
        if _secure_state_mutation_supported()
        else None
    )
    parent_metadata = (
        os.fstat(parent_descriptor) if parent_descriptor is not None else None
    )
    try:
        while descriptor is None:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                if parent_descriptor is None:
                    descriptor = os.open(lock_path, flags, 0o600)
                else:
                    descriptor = os.open(
                        lock_path.name,
                        flags,
                        0o600,
                        dir_fd=parent_descriptor,
                    )
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise OSError("ai-toolkit state lock is not a regular file")
                identity = metadata.st_dev, metadata.st_ino
                os.write(descriptor, b"ai-toolkit state writer\n")
                os.fsync(descriptor)
            except FileExistsError:
                try:
                    if parent_descriptor is None:
                        metadata = lock_path.stat(follow_symlinks=False)
                    else:
                        metadata = os.stat(
                            lock_path.name,
                            dir_fd=parent_descriptor,
                            follow_symlinks=False,
                        )
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(metadata.st_mode):
                    raise OSError(f"unsafe ai-toolkit state lock: {lock_path}")
                if time.monotonic() >= deadline:
                    raise OSError(
                        f"timed out waiting for ai-toolkit state lock: {lock_path}"
                    )
                time.sleep(_STATE_LOCK_POLL_SECONDS)
            except (OSError, KeyboardInterrupt):
                if descriptor is not None:
                    os.close(descriptor)
                    descriptor = None
                    if identity is not None:
                        _release_state_lock(
                            lock_path,
                            identity,
                            secure=False,
                            parent_descriptor=parent_descriptor,
                        )
                raise
        os.close(descriptor)
        descriptor = None
        if identity is None:
            raise OSError("ai-toolkit state lock identity was not captured")
        try:
            context = _StateWriterContext(
                path=state_path,
                parent_descriptor=parent_descriptor,
                parent_device=(
                    parent_metadata.st_dev if parent_metadata is not None else None
                ),
                parent_inode=(
                    parent_metadata.st_ino if parent_metadata is not None else None
                ),
            )
            if parent_descriptor is not None and not _state_parent_path_matches(
                context.path.parent,
                parent_descriptor,
            ):
                raise OSError("ai-toolkit state parent identity changed")
            yield context
        finally:
            _release_state_lock(
                lock_path,
                identity,
                secure=parent_descriptor is not None,
                parent_descriptor=parent_descriptor,
            )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent_descriptor is not None:
            os.close(parent_descriptor)


@dataclass(frozen=True)
class _OpenedStableStateFile:
    content: bytes
    metadata: os.stat_result
    digest: str


def _state_file_signature(metadata: os.stat_result) -> tuple[int, ...]:
    """Return the complete stable-read signature for one state file."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_declared_state_size(
    descriptor: int,
    *,
    declared_size: int,
    path: Path,
) -> bytes:
    """Read exactly the declared state size and reject early EOF or growth."""
    remaining = declared_size
    chunks: list[bytes] = []
    while remaining:
        chunk = os.read(descriptor, min(64 * 1024, remaining))
        if not chunk:
            raise OSError(f"ai-toolkit state changed while reading: {path}")
        chunks.append(chunk)
        remaining -= len(chunk)
    if os.read(descriptor, 1):
        raise OSError(f"ai-toolkit state changed while reading: {path}")
    return b"".join(chunks)


def _state_parent_path_matches(path: Path, descriptor: int) -> bool:
    """Confirm a state parent path still names the pinned directory inode."""
    try:
        current = _open_state_parent(path)
    except OSError:
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


def _assert_state_writer_binding(context: _StateWriterContext) -> None:
    """Fail before I/O if the lexical state parent no longer names the lock inode."""
    descriptor = context.parent_descriptor
    if descriptor is None:
        return
    metadata = os.fstat(descriptor)
    if (
        metadata.st_dev,
        metadata.st_ino,
    ) != (
        context.parent_device,
        context.parent_inode,
    ) or not _state_parent_path_matches(context.path.parent, descriptor):
        raise OSError(
            "ai-toolkit state parent identity changed; both roots were preserved"
        )


def _state_name_exists(context: _StateWriterContext, name: str) -> bool:
    descriptor = context.parent_descriptor
    if descriptor is None:
        path = context.path.parent / name
        return path.exists() or path.is_symlink()
    try:
        os.stat(name, dir_fd=descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


@contextmanager
def _open_stable_state_file(
    path: Path,
    *,
    secure: bool,
    parent_descriptor: int | None = None,
) -> Iterator[_OpenedStableStateFile]:
    """Pin, validate, and read one regular state inode exactly once."""
    opened_parent_descriptor = parent_descriptor
    owns_parent_descriptor = False
    descriptor: int | None = None
    try:
        if secure:
            if opened_parent_descriptor is None:
                opened_parent_descriptor = _open_state_parent(path.parent)
                owns_parent_descriptor = True
            if not _state_parent_path_matches(path.parent, opened_parent_descriptor):
                raise OSError("ai-toolkit state parent identity changed")
            named_before = os.stat(
                path.name,
                dir_fd=opened_parent_descriptor,
                follow_symlinks=False,
            )
            descriptor = os.open(
                path.name,
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=opened_parent_descriptor,
            )
        else:
            named_before = path.stat(follow_symlinks=False)
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        signature = _state_file_signature(opened)
        if (
            not stat.S_ISREG(named_before.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or _state_file_signature(named_before) != signature
        ):
            raise OSError("ai-toolkit state identity changed")
        content = _read_declared_state_size(
            descriptor,
            declared_size=opened.st_size,
            path=path,
        )
        after_read = os.fstat(descriptor)
        if secure:
            if opened_parent_descriptor is None:
                raise OSError("secure ai-toolkit state parent is unavailable")
            named_after = os.stat(
                path.name,
                dir_fd=opened_parent_descriptor,
                follow_symlinks=False,
            )
            parent_matches = _state_parent_path_matches(
                path.parent,
                opened_parent_descriptor,
            )
        else:
            named_after = path.stat(follow_symlinks=False)
            parent_matches = True
        if (
            not stat.S_ISREG(after_read.st_mode)
            or not stat.S_ISREG(named_after.st_mode)
            or _state_file_signature(after_read) != signature
            or _state_file_signature(named_after) != signature
            or not parent_matches
        ):
            raise OSError("ai-toolkit state identity changed")
        yield _OpenedStableStateFile(
            content=content,
            metadata=opened,
            digest=hashlib.sha256(content).hexdigest(),
        )
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if owns_parent_descriptor and opened_parent_descriptor is not None:
            os.close(opened_parent_descriptor)


def _decode_state_document(content: bytes) -> dict:
    try:
        state = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError("malformed ai-toolkit state file") from error
    if not isinstance(state, dict):
        raise ValueError("malformed ai-toolkit state file")
    return state


def _opened_state_revision(
    opened: _OpenedStableStateFile,
) -> tuple[bool, int, int, str]:
    return (
        True,
        opened.metadata.st_dev,
        opened.metadata.st_ino,
        opened.digest,
    )


def load_state() -> dict:
    """Load state from ~/.softspark/ai-toolkit/state.json.

    Returns an empty dict if the file does not exist or is malformed.
    """
    try:
        return _load_state_strict()
    except ValueError:
        return {}


def _load_state_strict(
    *,
    secure: bool = False,
    transaction: _StateWriterContext | None = None,
) -> dict:
    """Load shared state for ownership-sensitive lifecycle operations."""
    path = transaction.path if transaction is not None else _state_path()
    if transaction is not None:
        _assert_state_writer_binding(transaction)
    if unsafe_root := _unsafe_state_root():
        raise ValueError(f"unsafe ai-toolkit state root: {unsafe_root}")
    if transaction is not None and not _state_name_exists(transaction, path.name):
        return {}
    if transaction is None and not path.exists() and not path.is_symlink():
        return {}
    try:
        with _open_stable_state_file(
            path,
            secure=secure
            or (transaction is not None and transaction.parent_descriptor is not None),
            parent_descriptor=(
                transaction.parent_descriptor if transaction is not None else None
            ),
        ) as opened:
            return _decode_state_document(opened.content)
    except (OSError, ValueError) as error:
        raise ValueError("malformed ai-toolkit state file") from error


def _load_state_revision_strict(
    *,
    secure: bool = False,
    transaction: _StateWriterContext | None = None,
) -> tuple[dict, tuple[bool, int, int, str]]:
    """Read one stable state inode and return its compare-and-swap revision."""
    path = transaction.path if transaction is not None else _state_path()
    if transaction is not None:
        _assert_state_writer_binding(transaction)
    if unsafe_root := _unsafe_state_root():
        raise ValueError(f"unsafe ai-toolkit state root: {unsafe_root}")
    if transaction is not None and not _state_name_exists(transaction, path.name):
        return {}, (False, 0, 0, "")
    if transaction is None and not path.exists() and not path.is_symlink():
        return {}, (False, 0, 0, "")
    try:
        with _open_stable_state_file(
            path,
            secure=secure
            or (transaction is not None and transaction.parent_descriptor is not None),
            parent_descriptor=(
                transaction.parent_descriptor if transaction is not None else None
            ),
        ) as opened:
            state = _decode_state_document(opened.content)
            return state, _opened_state_revision(opened)
    except (OSError, ValueError) as error:
        raise ValueError("malformed or unsafe ai-toolkit state file") from error


def _secure_state_mutation_supported() -> bool:
    if not (
        os.name == "posix"
        and hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and {os.stat, os.unlink, os.rename}.issubset(os.supports_dir_fd)
        and sys.platform.startswith(("darwin", "linux"))
    ):
        return False
    try:
        library = ctypes.CDLL(None, use_errno=True)
        getattr(library, "renameatx_np" if sys.platform == "darwin" else "renameat2")
    except (AttributeError, OSError):
        return False
    return True


def _open_state_parent(path: Path) -> int:
    if not _secure_state_mutation_supported():
        raise OSError("secure ai-toolkit state mutation requires Linux, WSL, or macOS")
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISDIR(before.st_mode):
        raise OSError(f"unsafe ai-toolkit state parent: {path}")
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
        os.close(descriptor)
        raise OSError(f"ai-toolkit state parent identity changed: {path}")
    return descriptor


def _state_rename_operation(
    source: Path,
    destination: Path,
    *,
    exchange: bool,
    source_parent_descriptor: int | None = None,
    destination_parent_descriptor: int | None = None,
) -> None:
    source_parent = (
        source_parent_descriptor
        if source_parent_descriptor is not None
        else _open_state_parent(source.parent)
    )
    destination_parent = (
        destination_parent_descriptor
        if destination_parent_descriptor is not None
        else _open_state_parent(destination.parent)
    )
    try:
        library = ctypes.CDLL(None, use_errno=True)
        source_name = os.fsencode(source.name)
        destination_name = os.fsencode(destination.name)
        flag = (
            0x00000002
            if exchange
            else (0x00000004 if sys.platform == "darwin" else 0x00000001)
        )
        if sys.platform == "darwin":
            operation = library.renameatx_np
        else:
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
            flag,
        )
        if result != 0:
            code = ctypes.get_errno()
            if not exchange and code in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(code, os.strerror(code), str(destination))
            if code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
                raise OSError("secure state rename primitive is unavailable")
            raise OSError(code, os.strerror(code), str(source))
    finally:
        if destination_parent_descriptor is None:
            os.close(destination_parent)
        if source_parent_descriptor is None:
            os.close(source_parent)


def _path_revision(
    path: Path,
    *,
    parent_descriptor: int | None = None,
) -> tuple[bool, int, int, str]:
    if parent_descriptor is None:
        if not path.exists() and not path.is_symlink():
            return False, 0, 0, ""
    else:
        try:
            os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        except FileNotFoundError:
            return False, 0, 0, ""
    with _open_stable_state_file(
        path,
        secure=True,
        parent_descriptor=parent_descriptor,
    ) as opened:
        return _opened_state_revision(opened)


def _secure_publish_state(
    temporary: Path,
    path: Path,
    expected_revision: tuple[bool, int, int, str],
    *,
    parent_descriptor: int | None = None,
    transaction: _StateWriterContext | None = None,
) -> bool:
    """Publish state atomically without destroying a raced inode."""
    if transaction is not None:
        _assert_state_writer_binding(transaction)
    if not expected_revision[0]:
        try:
            if transaction is not None:
                _assert_state_writer_binding(transaction)
            _state_rename_operation(
                temporary,
                path,
                exchange=False,
                source_parent_descriptor=parent_descriptor,
                destination_parent_descriptor=parent_descriptor,
            )
        except FileExistsError:
            return False
        if transaction is not None:
            _assert_state_writer_binding(transaction)
        return True
    try:
        current = (
            path.stat(follow_symlinks=False)
            if parent_descriptor is None
            else os.stat(
                path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        )
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(current.st_mode):
        return False
    if transaction is not None:
        _assert_state_writer_binding(transaction)
    _state_rename_operation(
        temporary,
        path,
        exchange=True,
        source_parent_descriptor=parent_descriptor,
        destination_parent_descriptor=parent_descriptor,
    )
    try:
        if (
            _path_revision(
                temporary,
                parent_descriptor=parent_descriptor,
            )
            != expected_revision
        ):
            _state_rename_operation(
                temporary,
                path,
                exchange=True,
                source_parent_descriptor=parent_descriptor,
                destination_parent_descriptor=parent_descriptor,
            )
            return False
        _secure_cleanup_private_file(
            temporary,
            (expected_revision[1], expected_revision[2]),
            parent_descriptor=parent_descriptor,
        )
        if transaction is not None:
            _assert_state_writer_binding(transaction)
        return True
    except (OSError, KeyboardInterrupt):
        temporary_exists = (
            temporary.exists()
            if parent_descriptor is None
            else _descriptor_name_exists(parent_descriptor, temporary.name)
        )
        path_exists = (
            path.exists()
            if parent_descriptor is None
            else _descriptor_name_exists(parent_descriptor, path.name)
        )
        if temporary_exists and path_exists:
            try:
                _state_rename_operation(
                    temporary,
                    path,
                    exchange=True,
                    source_parent_descriptor=parent_descriptor,
                    destination_parent_descriptor=parent_descriptor,
                )
            except OSError:
                pass
        raise


def _descriptor_name_exists(parent_descriptor: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return True


def _secure_cleanup_private_file(
    path: Path,
    identity: tuple[int, int],
    *,
    parent_descriptor: int | None = None,
) -> None:
    if parent_descriptor is None:
        if not path.exists() and not path.is_symlink():
            return
    elif not _descriptor_name_exists(parent_descriptor, path.name):
        return
    recovery = path.parent / (
        f".state-private-cleanup-{os.getpid()}-{secrets.token_hex(12)}"
    )
    _state_rename_operation(
        path,
        recovery,
        exchange=False,
        source_parent_descriptor=parent_descriptor,
        destination_parent_descriptor=parent_descriptor,
    )
    metadata = (
        recovery.stat(follow_symlinks=False)
        if parent_descriptor is None
        else os.stat(
            recovery.name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    )
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != identity
    ):
        raise OSError(f"state temporary identity changed; preserved at {recovery}")
    parent = (
        parent_descriptor
        if parent_descriptor is not None
        else _open_state_parent(recovery.parent)
    )
    try:
        os.unlink(recovery.name, dir_fd=parent)
    finally:
        if parent_descriptor is None:
            os.close(parent)


def _create_state_temporary(
    context: _StateWriterContext,
    *,
    prefix: str,
    suffix: str,
    mode: int = 0o600,
) -> tuple[int, Path, tuple[int, int]]:
    """Create a private state temporary inside the transaction's pinned parent."""
    _assert_state_writer_binding(context)
    if context.parent_descriptor is None:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=prefix,
            suffix=suffix,
            dir=context.path.parent,
        )
        temporary = Path(temporary_name)
    else:
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        for _attempt in range(16):
            name = f"{prefix}{secrets.token_hex(12)}{suffix}"
            try:
                descriptor = os.open(
                    name,
                    flags,
                    mode,
                    dir_fd=context.parent_descriptor,
                )
            except FileExistsError:
                continue
            temporary = context.path.parent / name
            break
        else:
            raise OSError("unable to claim private ai-toolkit state temporary")
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        raise OSError("ai-toolkit state temporary is not a regular file")
    return descriptor, temporary, (metadata.st_dev, metadata.st_ino)


def _portable_cleanup_private_file(
    path: Path,
    identity: tuple[int, int],
) -> None:
    """Clean a private temporary on platforms without secure state primitives."""
    if not path.exists() and not path.is_symlink():
        return
    metadata = path.stat(follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or (metadata.st_dev, metadata.st_ino) != identity
    ):
        raise OSError(f"state temporary identity changed; preserved at {path}")
    path.unlink()


def _write_state_locked(
    state: dict,
    *,
    prefix: str = ".state.",
    transaction: _StateWriterContext,
) -> None:
    path = transaction.path
    _assert_state_writer_binding(transaction)
    _, revision = _load_state_revision_strict(
        secure=transaction.parent_descriptor is not None,
        transaction=transaction,
    )
    payload = json.dumps(state, indent=2) + "\n"
    descriptor, temporary, temporary_identity = _create_state_temporary(
        transaction,
        prefix=prefix,
        suffix=".tmp",
    )
    try:
        if callable(fchmod := getattr(os, "fchmod", None)):
            fchmod(descriptor, 0o600)
        else:
            os.chmod(temporary, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _assert_state_writer_binding(transaction)
        if transaction.parent_descriptor is not None:
            if not _secure_publish_state(
                temporary,
                path,
                revision,
                parent_descriptor=transaction.parent_descriptor,
                transaction=transaction,
            ):
                raise OSError("concurrent ai-toolkit state change")
        else:
            os.replace(temporary, path)
        _assert_state_writer_binding(transaction)
    finally:
        if transaction.parent_descriptor is not None:
            _secure_cleanup_private_file(
                temporary,
                temporary_identity,
                parent_descriptor=transaction.parent_descriptor,
            )
        else:
            _portable_cleanup_private_file(temporary, temporary_identity)


def _mutate_state(mutator: Callable[[dict], None]) -> None:
    with _state_writer_lock() as transaction:
        state = _load_state_strict(
            secure=transaction.parent_descriptor is not None,
            transaction=transaction,
        )
        state.pop(LEGACY_DSH_STATE_KEY, None)
        mutator(state)
        _write_state_locked(state, transaction=transaction)


def save_state(state: dict) -> None:
    """Save state to ~/.softspark/ai-toolkit/state.json.

    Creates the parent directory if it does not exist.
    """

    def merge(current: dict) -> None:
        current.update(state)

    _mutate_state(merge)


def get_mcp_templates() -> list[str]:
    """Return list of globally tracked MCP template names."""
    state = load_state()
    templates = state.get("mcp_templates", [])
    return templates if isinstance(templates, list) else []


def record_mcp_template(name: str) -> None:
    """Add a template name to the tracked set in state.json."""

    def update(state: dict) -> None:
        templates = set(state.get("mcp_templates", []))
        templates.add(name)
        state["mcp_templates"] = sorted(templates)

    _mutate_state(update)


def remove_mcp_template(name: str) -> None:
    """Remove a template name from the tracked set in state.json."""

    def update(state: dict) -> None:
        templates = set(state.get("mcp_templates", []))
        templates.discard(name)
        state["mcp_templates"] = sorted(templates)

    _mutate_state(update)


# Default global install: Claude only — no other editors unless --editors is used
DEFAULT_GLOBAL_EDITORS: list[str] = []

# All editors that support global install (opt-in via --editors).
#
# Scope varies by editor's documented global file surfaces:
#   - cursor: HOOKS only (~/.cursor/hooks.json). Cursor RULES stay project-local
#     — their only global surface is the Settings UI, not a mergeable file.
#   - copilot: user-level instructions (~/.copilot/, read by Copilot CLI).
#   - antigravity: global skill pointer (~/.gemini/config/skills,
#     ~/.gemini/antigravity-cli/skills). Rules stay project-local.
GLOBAL_CAPABLE_EDITORS = [
    "aider",
    "antigravity",
    "augment",
    "cline",
    "codex",
    "copilot",
    "cursor",
    "gemini",
    "opencode",
    "roo",
    "windsurf",
]


def get_global_editors() -> list[str]:
    """Return list of globally installed editor names from state."""
    state = load_state()
    editors = state.get("global_editors", [])
    return editors if isinstance(editors, list) else []


def record_global_editors(editors: list[str]) -> None:
    """Record which editors are installed globally in state.json."""

    def update(state: dict) -> None:
        state["global_editors"] = sorted(set(editors))

    _mutate_state(update)


def _now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_install(
    version: str,
    modules: list[str],
    profile: str,
    auto_detected: list[str] | None = None,
    extends_info: dict | None = None,
) -> None:
    """Record a successful install in state.json.

    If state already exists, preserves ``installed_at`` and updates
    ``last_updated``. Otherwise sets both timestamps.

    ``extends_info`` (optional) records config inheritance metadata:
    source, version, resolved_at, hash, overrides_applied.
    """
    now = _now_iso()

    def update(state: dict) -> None:
        state["installed_version"] = version
        if "installed_at" not in state:
            state["installed_at"] = now
        state["last_updated"] = now
        state["installed_modules"] = sorted(set(modules))
        state["profile"] = profile
        if auto_detected is not None:
            state["auto_detected_languages"] = sorted(auto_detected)
        else:
            state.pop("auto_detected_languages", None)

        if extends_info is not None:
            state["extends"] = {
                "source": extends_info.get("source", ""),
                "configs": extends_info.get("configs", []),
                "resolved_at": now,
                "overrides_applied": extends_info.get("overrides_applied", []),
            }
        else:
            state.pop("extends", None)

    _mutate_state(update)

    # Clear version check cache (version may have changed)
    cache_file = _state_path().parent / "version-check.json"
    if cache_file.is_file():
        cache_file.unlink()


def print_status() -> None:
    """Print a human-readable summary of the install state."""
    state = load_state()
    if not state:
        print(f"No install state found ({STATE_FILE} missing).")
        print("Run 'ai-toolkit install' to set up the toolkit.")
        return

    print("AI Toolkit Install Status")
    print("=========================")
    print(f"  Version:    {state.get('installed_version', 'unknown')}")
    print(f"  Installed:  {state.get('installed_at', 'unknown')}")
    print(f"  Updated:    {state.get('last_updated', 'unknown')}")
    print(f"  Profile:    {state.get('profile', 'unknown')}")

    modules = state.get("installed_modules", [])
    if modules:
        print(f"  Modules:    {', '.join(modules)}")
    else:
        print("  Modules:    (none recorded)")

    detected = state.get("auto_detected_languages", [])
    if detected:
        # Strip "rules-" prefix for readability
        langs = [m.replace("rules-", "") for m in detected]
        print(f"  Detected:   {', '.join(langs)}")

    editors = state.get("global_editors", [])
    if editors:
        print(f"  Editors:    {', '.join(editors)}")

    mcp = state.get("mcp_templates", [])
    if mcp:
        print(f"  MCP:        {', '.join(mcp)}")

    ext_rules = _load_sources(RULES_DIR / "sources.json", "rules")
    ext_hooks = _load_sources(EXTERNAL_HOOKS_DIR / "sources.json", "hooks")
    rule_orphans = _orphan_rule_files(RULES_DIR, {n for n, _, _, _ in ext_rules})
    if ext_rules or ext_hooks or rule_orphans:
        print()
        print("  External sources:")
        for name, origin, fetched_at, kind in ext_rules:
            tag = " [local]" if kind == "local" else ""
            stamp = f" ({fetched_at})" if fetched_at else ""
            print(f"    rule  {name}  <- {origin}{tag}{stamp}")
        for name in rule_orphans:
            print(
                f"    rule  {name}  <- (orphan, no source recorded — re-run add-rule)"
            )
        for name, origin, fetched_at, kind in ext_hooks:
            tag = " [local]" if kind == "local" else ""
            stamp = f" ({fetched_at})" if fetched_at else ""
            print(f"    hook  {name}  <- {origin}{tag}{stamp}")

    extends = state.get("extends")
    if extends:
        print(f"  Extends:    {extends.get('source', 'unknown')}")
        for cfg in extends.get("configs", []):
            version_str = f" v{cfg['version']}" if cfg.get("version") else ""
            print(
                f"              → {cfg.get('name', cfg.get('source', '?'))}{version_str}"
            )
        if extends.get("resolved_at"):
            print(f"  Resolved:   {extends['resolved_at']}")

    # Check for updates
    try:
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from version_check import check

        result = check(force=True)
        if result["update_available"]:
            print()
            print(f"  Update available: {result['installed']} -> {result['latest']}")
            print(
                "  Run: npm install -g @softspark/ai-toolkit@latest && ai-toolkit update"
            )
        else:
            print(f"  Latest:     {result['latest']} (up to date)")
    except Exception:
        pass  # version check is optional
