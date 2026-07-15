"""Pinned-directory filesystem mutations for trusted configuration roots.

All mutating syscalls operate relative to directory descriptors opened with
``O_NOFOLLOW``. Parent descriptors stay open for the whole transaction, so an
ancestor rename or symlink swap cannot redirect writes or rollback outside the
declared trust boundary.
"""

from __future__ import annotations

import os
import secrets
import stat
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar


SECURE_DIR_FD = (
    hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and all(
        function in os.supports_dir_fd
        for function in (
            os.open,
            os.unlink,
            os.rmdir,
            os.mkdir,
            os.rename,
            os.stat,
            os.readlink,
            os.symlink,
        )
    )
)

_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
_WRITE_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)


@dataclass(frozen=True)
class SecureDestination:
    path: Path
    trusted_root: Path
    label: str


@dataclass(frozen=True)
class _Snapshot:
    existed: bool
    content: bytes | None
    mode: int
    device: int | None
    inode: int | None


@dataclass
class _PinnedDestination:
    destination: SecureDestination
    parent_fd: int
    target_name: str
    missing_parent_parts: tuple[str, ...]
    snapshot: _Snapshot
    materialized: bool


def lexical_absolute(path: str | os.PathLike[str]) -> Path:
    """Return an absolute normalized path without resolving symlinks."""
    return Path(os.path.abspath(os.path.expanduser(os.fspath(path))))


def nearest_existing_root(path: Path) -> Path:
    """Return the closest existing real directory at or above ``path``."""
    candidate = lexical_absolute(path)
    while not candidate.exists() and not candidate.is_symlink():
        parent = candidate.parent
        if parent == candidate:
            break
        candidate = parent
    if candidate.is_symlink():
        raise RuntimeError(f"Refusing symlinked destination ancestor: {candidate}")
    if not candidate.is_dir():
        raise RuntimeError(f"Destination ancestor is not a directory: {candidate}")
    return candidate


def _open_absolute_directory(path: Path) -> int:
    """Resolve and open every absolute-path component from a stable root fd."""
    absolute = lexical_absolute(path)
    pending = deque(absolute.parts[1:])
    descriptors = [os.open(os.sep, _DIRECTORY_FLAGS)]
    symlink_expansions = 0
    try:
        while pending:
            part = pending.popleft()
            if part in ("", "."):
                continue
            if part == "..":
                if len(descriptors) == 1:
                    raise RuntimeError(f"Trusted root escapes filesystem root: {path}")
                os.close(descriptors.pop())
                continue
            try:
                next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptors[-1])
            except OSError as open_error:
                if not pending:
                    raise open_error
                try:
                    link_target = os.readlink(part, dir_fd=descriptors[-1])
                except OSError:
                    raise open_error
                symlink_expansions += 1
                if symlink_expansions > 40:
                    raise RuntimeError(f"Too many symlinks in trusted root: {path}")
                target_parts = list(Path(link_target).parts)
                if os.path.isabs(link_target):
                    while len(descriptors) > 1:
                        os.close(descriptors.pop())
                    target_parts = target_parts[1:]
                pending.extendleft(reversed(target_parts))
                continue
            descriptors.append(next_fd)
    except BaseException:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass
        raise
    directory_fd = descriptors.pop()
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass
    return directory_fd


def _parts(destination: SecureDestination) -> tuple[Path, Path, tuple[str, ...]]:
    path = lexical_absolute(destination.path)
    root = lexical_absolute(destination.trusted_root)
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RuntimeError(
            f"{destination.label} escapes trusted root {root}: {path}"
        ) from error
    if relative == Path(".") or not relative.parts or ".." in relative.parts:
        raise RuntimeError(f"Refusing mutation of trusted root itself: {path}")
    return path, root, relative.parts


def _read_regular_file(parent_fd: int, name: str, label: str) -> _Snapshot:
    try:
        metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return _Snapshot(False, None, 0o600, None, None)
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError(f"Refusing non-regular {label} destination: {name}")

    file_fd = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
    primary_error: BaseException | None = None
    try:
        opened = os.fstat(file_fd)
        if not stat.S_ISREG(opened.st_mode):
            raise RuntimeError(f"Refusing non-regular {label} destination: {name}")
        with os.fdopen(file_fd, "rb") as handle:
            file_fd = -1
            content = handle.read()
    except BaseException as error:
        primary_error = error
        raise
    finally:
        if file_fd >= 0:
            try:
                os.close(file_fd)
            except OSError:
                if primary_error is None:
                    raise
    return _Snapshot(
        True,
        content,
        stat.S_IMODE(opened.st_mode),
        opened.st_dev,
        opened.st_ino,
    )


class SecureTransaction:
    """Hold pinned parent descriptors for apply and byte-exact rollback."""

    def __init__(self, destinations: list[SecureDestination]) -> None:
        if not SECURE_DIR_FD:
            raise RuntimeError("Secure mutations require POSIX dir_fd and O_NOFOLLOW")
        self._pinned: dict[Path, _PinnedDestination] = {}
        self._root_fds: dict[Path, int] = {}
        self._created_directories: list[tuple[int, str]] = []
        self._touched: set[Path] = set()
        try:
            for destination in destinations:
                path = lexical_absolute(destination.path)
                if path in self._pinned:
                    existing_root = self._pinned[path].destination.trusted_root
                    if lexical_absolute(destination.trusted_root) != existing_root:
                        raise RuntimeError(
                            f"Conflicting trusted roots for destination: {path}"
                        )
                    continue
                self._pinned[path] = self._prepare(destination)
        except BaseException:
            self.close()
            raise

    def _prepare(self, destination: SecureDestination) -> _PinnedDestination:
        path, root, parts = _parts(destination)
        root_fd = self._root_fds.get(root)
        if root_fd is None:
            try:
                root_fd = _open_absolute_directory(root)
            except OSError as error:
                raise RuntimeError(
                    f"Refusing unsafe trusted root for {destination.label}: "
                    f"{root}: {error}"
                ) from error
            self._root_fds[root] = root_fd
        directory_fd = os.dup(root_fd)
        missing: list[str] = []
        try:
            for part in parts[:-1]:
                if missing:
                    missing.append(part)
                    continue
                try:
                    next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=directory_fd)
                except FileNotFoundError:
                    missing.append(part)
                    continue
                os.close(directory_fd)
                directory_fd = next_fd
            snapshot = (
                _Snapshot(False, None, 0o600, None, None)
                if missing
                else _read_regular_file(directory_fd, parts[-1], destination.label)
            )
        except BaseException as error:
            try:
                os.close(directory_fd)
            except OSError:
                pass
            if not isinstance(error, OSError):
                raise
            raise RuntimeError(
                f"Refusing unsafe ancestor for {destination.label}: {path.parent}: {error}"
            ) from error
        return _PinnedDestination(
            SecureDestination(path, root, destination.label),
            directory_fd,
            parts[-1],
            tuple(missing),
            snapshot,
            not missing,
        )

    def materialize_parents(self) -> None:
        """Create missing ancestors only after every destination is preflighted."""
        for pinned in self._pinned.values():
            if not pinned.missing_parent_parts:
                continue
            directory_fd = pinned.parent_fd
            for part in pinned.missing_parent_parts:
                created = False
                try:
                    os.mkdir(part, mode=0o755, dir_fd=directory_fd)
                    created = True
                except FileExistsError:
                    pass
                if created:
                    self._created_directories.append((os.dup(directory_fd), part))
                    os.fsync(directory_fd)
                try:
                    next_fd = os.open(part, _DIRECTORY_FLAGS, dir_fd=directory_fd)
                except OSError as error:
                    raise RuntimeError(
                        f"Refusing unsafe created ancestor for "
                        f"{pinned.destination.label}: {error}"
                    ) from error
                os.close(directory_fd)
                directory_fd = next_fd
                pinned.parent_fd = directory_fd
            pinned.parent_fd = directory_fd
            pinned.missing_parent_parts = ()
            pinned.materialized = True
            if self._exists(pinned):
                raise RuntimeError(
                    f"{pinned.destination.label} appeared during secure preparation"
                )

    @staticmethod
    def _exists(pinned: _PinnedDestination) -> bool:
        try:
            os.stat(
                pinned.target_name,
                dir_fd=pinned.parent_fd,
                follow_symlinks=False,
            )
            return True
        except FileNotFoundError:
            return False

    def _get(self, destination: SecureDestination) -> _PinnedDestination:
        path = lexical_absolute(destination.path)
        try:
            return self._pinned[path]
        except KeyError as error:
            raise RuntimeError(f"Destination was not pinned: {path}") from error

    def initial_content(self, destination: SecureDestination) -> bytes | None:
        """Return the bytes captured through the pinned parent descriptor."""
        return self._get(destination).snapshot.content

    def atomic_write(
        self,
        destination: SecureDestination,
        content: bytes,
        mode: int | None = None,
    ) -> None:
        self._atomic_write(destination, content, mode, enforce_snapshot=True)

    def _atomic_write(
        self,
        destination: SecureDestination,
        content: bytes,
        mode: int | None,
        *,
        enforce_snapshot: bool,
    ) -> None:
        pinned = self._get(destination)
        if not pinned.materialized:
            raise RuntimeError(
                f"Destination parent was not materialized: {pinned.destination.path}"
            )
        if pinned.snapshot.existed:
            file_mode = pinned.snapshot.mode
            set_exact_mode = True
        elif mode is None:
            file_mode = 0o600
            set_exact_mode = False
        else:
            file_mode = mode
            set_exact_mode = True
        temporary_name = f".{pinned.target_name}.{secrets.token_hex(8)}.tmp"
        temporary_fd = -1
        primary_error: BaseException | None = None
        try:
            temporary_fd = os.open(
                temporary_name,
                _WRITE_FLAGS,
                file_mode,
                dir_fd=pinned.parent_fd,
            )
            with os.fdopen(temporary_fd, "wb") as handle:
                temporary_fd = -1
                handle.write(content)
                handle.flush()
                if set_exact_mode:
                    os.fchmod(handle.fileno(), file_mode)
                os.fsync(handle.fileno())
            current = None
            try:
                current = os.stat(
                    pinned.target_name,
                    dir_fd=pinned.parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                pass
            if current is not None and not stat.S_ISREG(current.st_mode):
                raise RuntimeError(
                    f"Refusing replaced {pinned.destination.label} destination"
                )
            if enforce_snapshot:
                if not pinned.snapshot.existed and current is not None:
                    raise RuntimeError(
                        f"Unexpected {pinned.destination.label} destination appeared"
                    )
                if pinned.snapshot.existed and (
                    current is None
                    or current.st_dev != pinned.snapshot.device
                    or current.st_ino != pinned.snapshot.inode
                ):
                    raise RuntimeError(
                        f"Refusing changed {pinned.destination.label} destination"
                    )
            self._touched.add(pinned.destination.path)
            os.replace(
                temporary_name,
                pinned.target_name,
                src_dir_fd=pinned.parent_fd,
                dst_dir_fd=pinned.parent_fd,
            )
            os.fsync(pinned.parent_fd)
        except BaseException as error:
            primary_error = error
            raise
        finally:
            cleanup_error: OSError | None = None
            if temporary_fd >= 0:
                try:
                    os.close(temporary_fd)
                except OSError as error:
                    cleanup_error = error
            try:
                os.unlink(temporary_name, dir_fd=pinned.parent_fd)
            except FileNotFoundError:
                pass
            except OSError as error:
                cleanup_error = cleanup_error or error
            if primary_error is None and cleanup_error is not None:
                raise cleanup_error

    def unlink(self, destination: SecureDestination) -> None:
        self._unlink(destination, enforce_snapshot=True)

    def _unlink(
        self,
        destination: SecureDestination,
        *,
        enforce_snapshot: bool,
    ) -> None:
        pinned = self._get(destination)
        try:
            metadata = os.stat(
                pinned.target_name,
                dir_fd=pinned.parent_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError(
                f"Refusing to unlink non-regular {pinned.destination.label}"
            )
        if enforce_snapshot and (
            not pinned.snapshot.existed
            or metadata.st_dev != pinned.snapshot.device
            or metadata.st_ino != pinned.snapshot.inode
        ):
            raise RuntimeError(
                f"Refusing changed {pinned.destination.label} destination"
            )
        self._touched.add(pinned.destination.path)
        os.unlink(pinned.target_name, dir_fd=pinned.parent_fd)
        os.fsync(pinned.parent_fd)

    def rollback(self) -> None:
        errors: list[Exception] = []
        for pinned in reversed(list(self._pinned.values())):
            if not pinned.materialized or pinned.destination.path not in self._touched:
                continue
            try:
                if pinned.snapshot.existed:
                    assert pinned.snapshot.content is not None
                    self._atomic_write(
                        pinned.destination,
                        pinned.snapshot.content,
                        pinned.snapshot.mode,
                        enforce_snapshot=False,
                    )
                else:
                    self._unlink(pinned.destination, enforce_snapshot=False)
            except Exception as error:  # pragma: no cover - catastrophic I/O
                errors.append(error)
        for parent_fd, name in reversed(self._created_directories):
            try:
                os.rmdir(name, dir_fd=parent_fd)
                os.fsync(parent_fd)
            except Exception as error:  # pragma: no cover - catastrophic I/O
                errors.append(error)
        if errors:
            raise RuntimeError(f"Secure rollback was incomplete: {errors}")

    def close(self) -> None:
        for pinned in self._pinned.values():
            if pinned.parent_fd >= 0:
                try:
                    os.close(pinned.parent_fd)
                except OSError:
                    pass
                pinned.parent_fd = -1
        for root_fd in self._root_fds.values():
            try:
                os.close(root_fd)
            except OSError:
                pass
        self._root_fds.clear()
        for parent_fd, _ in self._created_directories:
            try:
                os.close(parent_fd)
            except OSError:
                pass
        self._created_directories.clear()


T = TypeVar("T")


def run_secure_transaction(
    destinations: list[SecureDestination],
    mutation: Callable[[SecureTransaction], T],
) -> T:
    """Preflight all paths, apply via pinned fds, and rollback on failure."""
    transaction = SecureTransaction(destinations)
    try:
        transaction.materialize_parents()
        return mutation(transaction)
    except BaseException as error:
        try:
            transaction.rollback()
        except Exception as rollback_error:
            raise RuntimeError(
                f"Secure mutation failed and rollback was incomplete: {rollback_error}"
            ) from error
        raise
    finally:
        transaction.close()
