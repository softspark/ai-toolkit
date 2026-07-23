"""Recovery-store boundary for lossless safe-mode replacements."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from collections.abc import Callable

from .contracts import FilterTelemetry
from .invariants import DEFAULT_FAILURE_LIMIT
from .telemetry import TelemetrySink

_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_WRITE_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_APPEND_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_APPEND
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_HANDLE_LENGTH = 32
_CIRCUIT_STATE_NAME = ".circuit-state.json"
_TELEMETRY_NAME = ".telemetry.jsonl"
_MAX_TELEMETRY_BYTES = 1024 * 1024
DEFAULT_MAX_SESSION_BYTES = 32 * 1024 * 1024
DEFAULT_TTL_MINUTES = 60


def _secure_hex(byte_count: int) -> str:
    return os.urandom(byte_count).hex()


class RecoveryUnavailableError(RuntimeError):
    """Secure recovery cannot operate on this platform or path."""


class RecoveryStore:
    """Storage contract implemented by the runtime integration."""

    def save(self, response: object) -> str:
        """Persist the exact native response object and return an opaque handle."""
        raise NotImplementedError

    def load(self, handle: str) -> object | None:
        """Load the exact response object for verification or recovery."""
        raise NotImplementedError

    def delete(self, handle: str) -> None:
        """Delete an unused or expired recovery artifact."""
        raise NotImplementedError


def _supports_secure_recovery() -> bool:
    # os.rename is the documented supports_dir_fd member for renameat-backed
    # calls; os.replace shares that implementation.
    required = (
        os.open,
        os.mkdir,
        os.stat,
        os.unlink,
        os.link,
        os.rename,
        os.rmdir,
    )
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and hasattr(os, "fchmod")
        and hasattr(os, "getuid")
        and os.listdir in os.supports_fd
        and all(function in os.supports_dir_fd for function in required)
    )


def _verify_private_directory(directory_fd: int, label: str) -> None:
    metadata = os.fstat(directory_fd)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RecoveryUnavailableError(f"{label} is not a directory")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise RecoveryUnavailableError(f"{label} is not private")
    if metadata.st_uid != os.getuid():
        raise RecoveryUnavailableError(f"{label} is not owned by this user")


def _open_base_directory(path: str | os.PathLike[str]) -> int:
    try:
        directory_fd = os.open(path, _DIRECTORY_FLAGS)
    except OSError as error:
        raise RecoveryUnavailableError(
            f"recovery base is unavailable: {error}"
        ) from error
    metadata = os.fstat(directory_fd)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(directory_fd)
        raise RecoveryUnavailableError("recovery base is not a directory")
    return directory_fd


def _open_private_child(parent_fd: int, name: str) -> int:
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent_fd)
    except FileExistsError:
        pass
    try:
        child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except OSError as error:
        raise RecoveryUnavailableError(
            f"recovery directory is unsafe: {error}"
        ) from error
    try:
        _verify_private_directory(child_fd, "recovery directory")
    except BaseException:
        os.close(child_fd)
        raise
    return child_fd


def _validate_handle(handle: str) -> str:
    if len(handle) != _HANDLE_LENGTH:
        raise ValueError("invalid recovery handle")
    if any(character not in "0123456789abcdef" for character in handle):
        raise ValueError("invalid recovery handle")
    return f"{handle}.json"


def _owned_artifact_name(name: str) -> bool:
    if not name.endswith(".json"):
        return False
    handle = name[:-5]
    try:
        _validate_handle(handle)
    except ValueError:
        return False
    return True


def _owned_pending_artifact_name(name: str) -> bool:
    prefix = ".pending-"
    token = name[len(prefix):] if name.startswith(prefix) else ""
    return (
        len(token) == _HANDLE_LENGTH
        and all(character in "0123456789abcdef" for character in token)
    )


def _owned_recovery_storage_name(name: str) -> bool:
    return _owned_artifact_name(name) or _owned_pending_artifact_name(name)


def _owned_runtime_artifact_name(name: str) -> bool:
    return (
        _owned_recovery_storage_name(name)
        or name in {_CIRCUIT_STATE_NAME, _TELEMETRY_NAME}
    )


def _session_key(session_identifier: str) -> str:
    return hashlib.sha256(
        session_identifier.encode("utf-8")
    ).hexdigest()[:_HANDLE_LENGTH]


class EphemeralRecoveryStore(RecoveryStore, TelemetrySink):
    """Private, bounded session recovery backed by pinned directory fds."""

    def __init__(
        self,
        base_directory: str | os.PathLike[str],
        *,
        session_identifier: str,
        max_session_bytes: int = DEFAULT_MAX_SESSION_BYTES,
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
        clock: Callable[[], float] = time.time,
        random_handle: Callable[[], str] | None = None,
    ) -> None:
        if not _supports_secure_recovery():
            raise RecoveryUnavailableError(
                "secure recovery requires dir_fd and O_NOFOLLOW"
            )
        self._random_handle = random_handle or (
            lambda: _secure_hex(_HANDLE_LENGTH // 2)
        )
        self._max_session_bytes = max_session_bytes
        self._ttl_seconds = ttl_minutes * 60
        self._clock = clock
        base_fd = _open_base_directory(base_directory)
        output_fd = -1
        try:
            output_fd = _open_private_child(base_fd, "output-filter")
            session_key = _session_key(session_identifier)
            self._directory_fd = _open_private_child(output_fd, session_key)
        finally:
            if output_fd >= 0:
                os.close(output_fd)
            os.close(base_fd)

    def _stored_bytes(self) -> int:
        total = 0
        for name in os.listdir(self._directory_fd):
            if not _owned_recovery_storage_name(name):
                continue
            try:
                metadata = os.stat(
                    name,
                    dir_fd=self._directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                # A concurrent session process removed the artifact between
                # listdir and stat; that is not a safety failure.
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise RecoveryUnavailableError(
                    "recovery artifact is not regular"
                )
            total += metadata.st_size
        return total

    def _write_atomic(self, filename: str, content: bytes) -> None:
        temporary_name = f".pending-{_secure_hex(16)}"
        file_fd = os.open(
            temporary_name,
            _WRITE_FLAGS,
            0o600,
            dir_fd=self._directory_fd,
        )
        try:
            with os.fdopen(file_fd, "wb") as file_handle:
                file_fd = -1
                os.fchmod(file_handle.fileno(), 0o600)
                file_handle.write(content)
                file_handle.flush()
                os.fsync(file_handle.fileno())
            os.link(
                temporary_name,
                filename,
                src_dir_fd=self._directory_fd,
                dst_dir_fd=self._directory_fd,
                follow_symlinks=False,
            )
            try:
                os.fsync(self._directory_fd)
            except OSError:
                # The artifact is already published; retract it so a failed
                # save never leaves an orphan counting against the quota.
                try:
                    os.unlink(filename, dir_fd=self._directory_fd)
                except FileNotFoundError:
                    pass
                raise
        finally:
            if file_fd >= 0:
                os.close(file_fd)
            try:
                os.unlink(temporary_name, dir_fd=self._directory_fd)
            except FileNotFoundError:
                pass

    def _replace_atomic(self, filename: str, content: bytes) -> None:
        temporary_name = f".pending-{_secure_hex(16)}"
        file_fd = os.open(
            temporary_name,
            _WRITE_FLAGS,
            0o600,
            dir_fd=self._directory_fd,
        )
        try:
            with os.fdopen(file_fd, "wb") as file_handle:
                file_fd = -1
                os.fchmod(file_handle.fileno(), 0o600)
                file_handle.write(content)
                file_handle.flush()
                os.fsync(file_handle.fileno())
            os.replace(
                temporary_name,
                filename,
                src_dir_fd=self._directory_fd,
                dst_dir_fd=self._directory_fd,
            )
            os.fsync(self._directory_fd)
        finally:
            if file_fd >= 0:
                os.close(file_fd)
            try:
                os.unlink(temporary_name, dir_fd=self._directory_fd)
            except FileNotFoundError:
                pass

    def save(self, response: object) -> str:
        content = json.dumps(
            response,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.clean_expired()
        if self._stored_bytes() + len(content) > self._max_session_bytes:
            raise RecoveryUnavailableError("recovery session quota exceeded")
        for _ in range(5):
            handle = self._random_handle()
            filename = _validate_handle(handle)
            try:
                self._write_atomic(filename, content)
            except FileExistsError:
                continue
            return handle
        raise RecoveryUnavailableError("could not allocate recovery handle")

    def clean_expired(self) -> int:
        cutoff = self._clock() - self._ttl_seconds
        removed = 0
        for name in os.listdir(self._directory_fd):
            if not _owned_recovery_storage_name(name):
                continue
            try:
                metadata = os.stat(
                    name,
                    dir_fd=self._directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise RecoveryUnavailableError(
                    "recovery artifact is not regular"
                )
            if metadata.st_mtime > cutoff:
                continue
            try:
                os.unlink(name, dir_fd=self._directory_fd)
            except FileNotFoundError:
                continue
            removed += 1
        if removed:
            os.fsync(self._directory_fd)
        return removed

    def clean_all(self) -> int:
        return self.clean_recovery()

    def clean_recovery(self) -> int:
        names = []
        for name in os.listdir(self._directory_fd):
            if not _owned_runtime_artifact_name(name):
                continue
            try:
                metadata = os.stat(
                    name,
                    dir_fd=self._directory_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(metadata.st_mode):
                raise RecoveryUnavailableError(
                    "recovery artifact is not regular"
                )
            names.append(name)
        removed = 0
        for name in names:
            try:
                os.unlink(name, dir_fd=self._directory_fd)
            except FileNotFoundError:
                continue
            removed += 1
        if removed:
            os.fsync(self._directory_fd)
        return removed

    def save_failure_count(self, count: int) -> None:
        if isinstance(count, bool) or not 0 <= count <= DEFAULT_FAILURE_LIMIT:
            raise ValueError(
                "failure count must be between zero and "
                f"{DEFAULT_FAILURE_LIMIT}"
            )
        current_count, current_warning = self._load_failure_state()
        warning_emitted = (
            current_warning if count == DEFAULT_FAILURE_LIMIT else False
        )
        if (count, warning_emitted) == (current_count, current_warning):
            return
        content = json.dumps(
            {
                "consecutiveFailures": count,
                "warningEmitted": warning_emitted,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self._replace_atomic(_CIRCUIT_STATE_NAME, content)

    def _load_circuit_state(self) -> dict[str, object]:
        try:
            metadata = os.stat(
                _CIRCUIT_STATE_NAME,
                dir_fd=self._directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return {"consecutiveFailures": 0, "warningEmitted": False}
        if not stat.S_ISREG(metadata.st_mode):
            raise RecoveryUnavailableError("circuit state is not regular")
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RecoveryUnavailableError("circuit state is not private")
        file_fd = os.open(
            _CIRCUIT_STATE_NAME,
            _READ_FLAGS,
            dir_fd=self._directory_fd,
        )
        with os.fdopen(file_fd, "rb") as file_handle:
            data = json.load(file_handle)
        if not isinstance(data, dict):
            raise RecoveryUnavailableError("circuit state is invalid")
        return data

    def _load_failure_state(self) -> tuple[int, bool]:
        data = self._load_circuit_state()
        count = data.get("consecutiveFailures")
        if isinstance(count, bool) or not isinstance(count, int):
            raise RecoveryUnavailableError("circuit state is invalid")
        if not 0 <= count <= DEFAULT_FAILURE_LIMIT:
            raise RecoveryUnavailableError("circuit state is invalid")
        value = data.get("warningEmitted", False)
        if not isinstance(value, bool):
            raise RecoveryUnavailableError("circuit state is invalid")
        return count, value

    def load_failure_count(self) -> int:
        return self._load_failure_state()[0]

    def load_warning_emitted(self) -> bool:
        return self._load_failure_state()[1]

    def mark_warning_emitted(self) -> None:
        count, warning_emitted = self._load_failure_state()
        if warning_emitted:
            return
        content = json.dumps(
            {
                "consecutiveFailures": count,
                "warningEmitted": True,
            },
            separators=(",", ":"),
        ).encode("utf-8")
        self._replace_atomic(_CIRCUIT_STATE_NAME, content)

    def record(self, event: FilterTelemetry) -> None:
        payload = {
            "profileId": event.profile_id,
            "profileVersion": event.profile_version,
            "inputBytes": event.input_bytes,
            "outputBytes": event.output_bytes,
            "inputLines": event.input_lines,
            "outputLines": event.output_lines,
            "durationMs": round(event.duration_ms, 3),
            "outcome": event.outcome,
            "fallbackReason": event.fallback_reason,
        }
        line = (
            json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
            + "\n"
        ).encode("ascii")
        try:
            metadata = os.stat(
                _TELEMETRY_NAME,
                dir_fd=self._directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            metadata = None
        if metadata is not None:
            if not stat.S_ISREG(metadata.st_mode):
                raise RecoveryUnavailableError("telemetry is not regular")
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise RecoveryUnavailableError("telemetry is not private")
            if metadata.st_size + len(line) > _MAX_TELEMETRY_BYTES:
                return
        file_fd = os.open(
            _TELEMETRY_NAME,
            _APPEND_FLAGS,
            0o600,
            dir_fd=self._directory_fd,
        )
        try:
            os.fchmod(file_fd, 0o600)
            if os.write(file_fd, line) != len(line):
                raise OSError("partial telemetry write")
        finally:
            os.close(file_fd)

    def load(self, handle: str) -> object | None:
        filename = _validate_handle(handle)
        try:
            metadata = os.stat(
                filename,
                dir_fd=self._directory_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(metadata.st_mode):
            raise RecoveryUnavailableError("recovery artifact is not regular")
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RecoveryUnavailableError("recovery artifact is not private")
        file_fd = os.open(filename, _READ_FLAGS, dir_fd=self._directory_fd)
        with os.fdopen(file_fd, "rb") as file_handle:
            content = file_handle.read()
        return json.loads(content.decode("utf-8"))

    def delete(self, handle: str) -> None:
        filename = _validate_handle(handle)
        try:
            os.unlink(filename, dir_fd=self._directory_fd)
            os.fsync(self._directory_fd)
        except FileNotFoundError:
            pass

    def close(self) -> None:
        if self._directory_fd >= 0:
            os.close(self._directory_fd)
            self._directory_fd = -1

    def __enter__(self) -> "EphemeralRecoveryStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def clean_session(
    base_directory: str | os.PathLike[str],
    session_identifier: str,
) -> int:
    """Delete owned runtime artifacts for one session, preserving all else."""

    with EphemeralRecoveryStore(
        base_directory,
        session_identifier=session_identifier,
    ) as recovery:
        removed = recovery.clean_recovery()

    base_fd = _open_base_directory(base_directory)
    output_fd = -1
    try:
        output_fd = os.open(
            "output-filter",
            _DIRECTORY_FLAGS,
            dir_fd=base_fd,
        )
        try:
            os.rmdir(_session_key(session_identifier), dir_fd=output_fd)
        except OSError:
            pass
        try:
            os.rmdir("output-filter", dir_fd=base_fd)
        except OSError:
            pass
    finally:
        if output_fd >= 0:
            os.close(output_fd)
        os.close(base_fd)
    return removed


class _TreeSession:
    __slots__ = ("artifact_names", "output_fd", "session_fd", "session_name")

    def __init__(
        self,
        output_fd: int,
        session_fd: int,
        session_name: str,
        artifact_names: tuple[str, ...],
    ) -> None:
        self.output_fd = output_fd
        self.session_fd = session_fd
        self.session_name = session_name
        self.artifact_names = artifact_names


class _TreeOutput:
    __slots__ = ("output_fd", "repo_fd", "sessions")

    def __init__(
        self,
        repo_fd: int,
        output_fd: int,
        sessions: list[_TreeSession],
    ) -> None:
        self.repo_fd = repo_fd
        self.output_fd = output_fd
        self.sessions = sessions


def _is_session_hash(name: str) -> bool:
    return (
        len(name) == _HANDLE_LENGTH
        and all(character in "0123456789abcdef" for character in name)
    )


def _open_directory_at(parent_fd: int, name: str, label: str) -> int:
    metadata = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode):
        raise RecoveryUnavailableError(f"{label} is not a directory")
    return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)


def _scan_tree_session(output_fd: int, session_name: str) -> _TreeSession:
    session_fd = _open_directory_at(
        output_fd,
        session_name,
        "owned recovery session",
    )
    try:
        _verify_private_directory(session_fd, "owned recovery session")
        artifacts = tuple(
            name
            for name in os.listdir(session_fd)
            if _owned_runtime_artifact_name(name)
        )
        for artifact_name in artifacts:
            metadata = os.stat(
                artifact_name,
                dir_fd=session_fd,
                follow_symlinks=False,
            )
            if not stat.S_ISREG(metadata.st_mode):
                raise RecoveryUnavailableError(
                    "owned recovery artifact is not regular"
                )
            if stat.S_IMODE(metadata.st_mode) != 0o600:
                raise RecoveryUnavailableError(
                    "owned recovery artifact is not private"
                )
        return _TreeSession(output_fd, session_fd, session_name, artifacts)
    except BaseException:
        os.close(session_fd)
        raise


def _scan_tree_output(repo_fd: int) -> _TreeOutput | None:
    try:
        output_fd = _open_directory_at(
            repo_fd,
            "output-filter",
            "owned output-filter directory",
        )
    except FileNotFoundError:
        return None
    sessions: list[_TreeSession] = []
    try:
        _verify_private_directory(output_fd, "owned output-filter directory")
        for name in os.listdir(output_fd):
            if _is_session_hash(name):
                sessions.append(_scan_tree_session(output_fd, name))
        return _TreeOutput(repo_fd, output_fd, sessions)
    except BaseException:
        for session in sessions:
            os.close(session.session_fd)
        os.close(output_fd)
        raise


def _delete_tree_output(output: _TreeOutput) -> int:
    removed = 0
    for session in output.sessions:
        for artifact_name in session.artifact_names:
            os.unlink(artifact_name, dir_fd=session.session_fd)
            removed += 1
        if session.artifact_names:
            os.fsync(session.session_fd)
        try:
            os.rmdir(session.session_name, dir_fd=output.output_fd)
        except OSError:
            pass
    try:
        os.rmdir("output-filter", dir_fd=output.repo_fd)
    except OSError:
        pass
    return removed


def clean_owned_repo_recovery(
    base_directory: str | os.PathLike[str],
) -> int:
    """Delete validated runtime artifacts for the current repo."""

    repo_fd = _open_base_directory(base_directory)
    output: _TreeOutput | None = None
    try:
        output = _scan_tree_output(repo_fd)
        return _delete_tree_output(output) if output is not None else 0
    finally:
        if output is not None:
            for session in output.sessions:
                os.close(session.session_fd)
            os.close(output.output_fd)
        os.close(repo_fd)


def _for_each_repo_output(
    root_fd: int,
    action: Callable[[_TreeOutput], int],
) -> int:
    """Scan and process one repo tree at a time to bound open descriptors."""
    total = 0
    for repo_name in os.listdir(root_fd):
        try:
            metadata = os.stat(
                repo_name,
                dir_fd=root_fd,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            continue
        if not stat.S_ISDIR(metadata.st_mode):
            continue
        repo_fd = os.open(repo_name, _DIRECTORY_FLAGS, dir_fd=root_fd)
        try:
            output = _scan_tree_output(repo_fd)
            if output is None:
                continue
            try:
                total += action(output)
            finally:
                for session in output.sessions:
                    os.close(session.session_fd)
                os.close(output.output_fd)
        finally:
            os.close(repo_fd)
    return total


def count_owned_recovery_artifacts(
    sessions_root: str | os.PathLike[str],
) -> int:
    """Securely count owned runtime artifacts without mutating the tree."""

    root_fd = _open_base_directory(sessions_root)
    try:
        return _for_each_repo_output(
            root_fd,
            lambda output: sum(
                len(session.artifact_names)
                for session in output.sessions
            ),
        )
    finally:
        os.close(root_fd)


def clean_owned_recovery_tree(
    sessions_root: str | os.PathLike[str],
) -> int:
    """Delete validated runtime artifacts below all repo sessions."""

    root_fd = _open_base_directory(sessions_root)
    try:
        return _for_each_repo_output(root_fd, _delete_tree_output)
    finally:
        os.close(root_fd)


def _load_response_at(session_fd: int, filename: str) -> object | None:
    try:
        metadata = os.stat(
            filename,
            dir_fd=session_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    if not stat.S_ISREG(metadata.st_mode):
        raise RecoveryUnavailableError("recovery artifact is not regular")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RecoveryUnavailableError("recovery artifact is not private")
    file_fd = os.open(filename, _READ_FLAGS, dir_fd=session_fd)
    with os.fdopen(file_fd, "rb") as file_handle:
        return json.load(file_handle)


def recover_by_handle(
    base_directory: str | os.PathLike[str],
    handle: str,
) -> object | None:
    """Find one exact response by opaque handle below the current repo."""

    filename = _validate_handle(handle)
    base_fd = _open_base_directory(base_directory)
    output_fd = -1
    session_fds: list[int] = []
    matches: list[object] = []
    try:
        try:
            output_fd = _open_directory_at(
                base_fd,
                "output-filter",
                "owned output-filter directory",
            )
        except FileNotFoundError:
            return None
        _verify_private_directory(output_fd, "owned output-filter directory")
        for session_name in os.listdir(output_fd):
            if not _is_session_hash(session_name):
                continue
            session_fd = _open_directory_at(
                output_fd,
                session_name,
                "owned recovery session",
            )
            session_fds.append(session_fd)
            _verify_private_directory(session_fd, "owned recovery session")
            response = _load_response_at(session_fd, filename)
            if response is not None:
                matches.append(response)
        if len(matches) > 1:
            raise RecoveryUnavailableError(
                "recovery handle is ambiguous across sessions"
            )
        return matches[0] if matches else None
    finally:
        for session_fd in session_fds:
            os.close(session_fd)
        if output_fd >= 0:
            os.close(output_fd)
        os.close(base_fd)
