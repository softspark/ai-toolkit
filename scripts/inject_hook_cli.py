#!/usr/bin/env python3
"""Inject external hooks into Claude settings and native Codex hooks.

Allows external tools (MCP servers, plugins, etc.) to register their own
hooks alongside ai-toolkit's hooks.  Each injected file is tagged with a
``_source`` derived from the filename stem so that re-running is idempotent
and removal is safe in Claude settings. Command handlers for native Codex
events are translated without ``_source`` and carry exact command ownership
markers under the active ``CODEX_HOME``.

Usage:
    inject_hook_cli.py <hooks-file-or-url> [hook-name] [target-dir]
    inject_hook_cli.py --remove <hook-source-name> [target-dir]

Arguments:
    hooks-file-or-url  Path to a JSON file or HTTPS URL with
                       ``{"hooks": {"EventName": [...]}}``
    hook-name          Override the source name (default: filename stem or
                       URL last segment)
    target-dir         Directory containing ``.claude/settings.json``
                       (default: $HOME)

Flags:
    --remove      Remove all hook entries tagged with the given source name
                  (also unregisters URL source if present)

The source name is derived from the filename stem (e.g.,
``rag-mcp-hooks.json`` becomes ``"rag-mcp-hooks"``).  All entries are tagged
with ``"_source": "<source-name>"`` for idempotent updates.  Re-running
replaces old entries with the same source name.

Entries tagged with ``_source: "ai-toolkit"`` are **never** modified -- those
are managed exclusively by the toolkit itself.

Exit codes:
    0  success
    1  usage / argument error
    2  JSON parse error
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from secure_fs import (
    SECURE_DIR_FD,
    SecureDestination,
    SecureTransaction,
    lexical_absolute,
    nearest_existing_root,
    run_secure_transaction,
)

# Protected source tag -- this CLI must never touch ai-toolkit's own entries.
PROTECTED_SOURCE = "ai-toolkit"

# Codex CLI's native HookEventName enum defines these 10 events. External
# command hooks can target all of them even though ai-toolkit's base bundle does
# not currently ship a PostCompact handler.
CODEX_EVENTS = {
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "Stop",
}

CODEX_OWNER_PREFIX = "ai-toolkit-external"
CODEX_NATIVE_GROUP_KEYS = frozenset({"matcher", "hooks"})
CODEX_NATIVE_HANDLER_KEYS = frozenset(
    {
        "type",
        "command",
        "commandWindows",
        "timeout",
        "statusMessage",
        "async",
    }
)
CODEX_OWNER_PATTERN = re.compile(
    r"(?:^|\s)AI_TOOLKIT_HOOK_OWNER=(?P<owner>[a-z0-9][a-z0-9-]*)(?=\s|$)"
)
SOURCE_NAME_PATTERN = re.compile(r"[a-zA-Z0-9_-]+")
_SECURE_DIR_FD = SECURE_DIR_FD
_UNSAFE_MUTATION_PLATFORM_ERROR = (
    "Safe hook mutations require POSIX dir_fd and O_NOFOLLOW support, "
    "which this Python runtime does not provide. No files were changed. "
    "On Windows, run ai-toolkit inject-hook or remove-hook from WSL."
)


def _require_secure_mutation_support() -> None:
    if not _SECURE_DIR_FD:
        raise RuntimeError(_UNSAFE_MUTATION_PLATFORM_ERROR)


_Destination = SecureDestination


def _absolute_path(path: str | os.PathLike[str]) -> Path:
    """Return an absolute lexical path without resolving symlinks."""
    return lexical_absolute(path)


def _trusted_target_root(target_dir: str) -> Path:
    """Validate the caller-selected root before inspecting child configs."""
    root = _absolute_path(target_dir)
    if root.is_symlink():
        raise RuntimeError(f"Refusing symlinked target directory: {root}")
    if not root.is_dir():
        raise RuntimeError(f"Target directory must already exist: {root}")
    return root


def _nearest_existing_root(path: Path) -> Path:
    """Find a real existing ancestor that can anchor symlink checks."""
    return nearest_existing_root(path)


def _assert_safe_destination(destination: _Destination) -> None:
    """Reject symlinks or non-directory ancestors below a trusted root."""
    root = _absolute_path(destination.trusted_root)
    path = _absolute_path(destination.path)
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise RuntimeError(
            f"{destination.label} escapes trusted root {root}: {path}"
        ) from error

    candidates = [root]
    current = root
    for part in relative.parts:
        current /= part
        candidates.append(current)

    for candidate in candidates:
        if candidate.is_symlink():
            raise RuntimeError(
                f"Refusing symlinked {destination.label} path: {candidate}"
            )
        if not candidate.exists():
            continue
        if candidate == path:
            if not candidate.is_file():
                raise RuntimeError(
                    f"{destination.label} destination is not a file: {candidate}"
                )
        elif not candidate.is_dir():
            raise RuntimeError(
                f"{destination.label} ancestor is not a directory: {candidate}"
            )


def _json_bytes(data: dict, indent: int = 4) -> bytes:
    return (json.dumps(data, indent=indent, ensure_ascii=False) + "\n").encode()


class _MalformedDestinationJson(ValueError):
    def __init__(self, path: Path, error: Exception | str) -> None:
        super().__init__(f"malformed JSON in {path}: {error}")


def _load_destination_json(content: bytes | None, path: Path) -> dict:
    """Parse configuration bytes captured by the active transaction."""
    if content is None:
        return {}
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _MalformedDestinationJson(path, error) from error
    if not isinstance(data, dict):
        raise _MalformedDestinationJson(path, "top-level value must be an object")
    return data


def _run_transaction(
    destinations: list[_Destination],
    mutation: Callable[[SecureTransaction], None],
) -> None:
    """Apply through pinned parent fds with byte-for-byte rollback."""
    _require_secure_mutation_support()
    run_secure_transaction(destinations, mutation)


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def _is_url(source: str) -> bool:
    """Check if source looks like an HTTP(S) URL."""
    return source.startswith("https://") or source.startswith("http://")


def _name_from_url(url: str) -> str:
    """Derive a hook source name from a URL's last path segment."""
    parsed = urllib.parse.urlparse(url)
    filename = parsed.path.rstrip("/").split("/")[-1]
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return re.sub(r"[^a-zA-Z0-9_-]", "", stem)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _entry_source(entry: dict) -> str | None:
    """Return the ``_source`` tag of a hook entry, checking nested hooks too.

    Args:
        entry: A single hook entry dict.

    Returns:
        The source string, or ``None`` if untagged.
    """
    if "_source" in entry:
        return entry["_source"]
    for hook in entry.get("hooks", []):
        if isinstance(hook, dict) and "_source" in hook:
            return hook["_source"]
    return None


def _entry_signature(entry: dict) -> tuple:
    """Return behavior-defining hook fields without source tags."""
    handlers = []
    for hook in entry.get("hooks", []):
        if not isinstance(hook, dict):
            handlers.append(hook)
            continue
        handlers.append(
            tuple(
                sorted((key, value) for key, value in hook.items() if key != "_source")
            )
        )
    return (entry.get("matcher", ""), tuple(handlers))


def strip_source(
    hooks: dict, source: str, replacement_hooks: dict | None = None
) -> dict:
    """Remove all entries whose ``_source`` matches *source*.

    Args:
        hooks: Existing hooks dict (event-name -> list of entries).
        source: Source tag to strip.
        replacement_hooks: Optional hook entries being re-injected. When
            provided, untagged legacy entries with the same event/matcher/
            handler payload are stripped as belonging to the same source.

    Returns:
        New hooks dict with matching entries removed.  Empty event lists
        are omitted.
    """
    legacy_signatures: dict[str, set[tuple]] = {}
    if replacement_hooks:
        for event, entries in replacement_hooks.items():
            legacy_signatures[event] = {
                _entry_signature(entry) for entry in entries if isinstance(entry, dict)
            }

    result: dict = {}
    for event, entries in hooks.items():
        signatures = legacy_signatures.get(event, set())
        filtered = [
            e
            for e in entries
            if _entry_source(e) != source
            and not (
                isinstance(e, dict)
                and _entry_source(e) is None
                and _entry_signature(e) in signatures
            )
        ]
        if filtered:
            result[event] = filtered
    return result


def tag_entries(hooks: dict, source: str) -> dict:
    """Tag every entry in *hooks* with ``"_source": source``.

    Operates on top-level entries only (not nested ``hooks`` arrays) to
    match the convention used in ``app/hooks.json``.

    Args:
        hooks: Hook entries to tag (event-name -> list of entries).
        source: Source tag to apply.

    Returns:
        New hooks dict with all entries tagged.
    """
    result: dict = {}
    for event, entries in hooks.items():
        tagged = []
        for entry in entries:
            entry_copy = dict(entry)
            entry_copy["_source"] = source
            tagged.append(entry_copy)
        result[event] = tagged
    return result


def merge_hooks(new_hooks: dict, existing_hooks: dict, source: str) -> dict:
    """Strip old entries for *source*, then append *new_hooks*.

    Args:
        new_hooks: Tagged hook entries to inject.
        existing_hooks: Current hooks from the settings file.
        source: Source tag being injected.

    Returns:
        Merged hooks dict.
    """
    merged = strip_source(existing_hooks, source, new_hooks)
    for event, entries in new_hooks.items():
        if event not in merged:
            merged[event] = []
        merged[event].extend(entries)
    return merged


# ---------------------------------------------------------------------------
# Codex propagation
# ---------------------------------------------------------------------------


def _codex_hooks_path(target_dir: str) -> Path:
    """Return the active user-level Codex hooks path.

    ``CODEX_HOME`` replaces the default ``~/.codex`` root. The configured path
    must follow Codex's documented contract: absolute, existing, and a real
    directory. The public Codex writer performs the final per-path symlink
    checks before replacing any bytes.
    """
    configured = os.environ.get("CODEX_HOME", "").strip()
    if not configured:
        return _absolute_path(target_dir) / ".codex" / "hooks.json"

    codex_home = Path(configured).expanduser()
    if not codex_home.is_absolute():
        raise RuntimeError("CODEX_HOME must be an absolute path")
    if not codex_home.exists():
        raise RuntimeError(f"Configured CODEX_HOME does not exist: {codex_home}")
    if not codex_home.is_dir():
        raise RuntimeError(f"Configured CODEX_HOME is not a directory: {codex_home}")
    if codex_home.is_symlink():
        raise RuntimeError(f"Refusing symlinked CODEX_HOME: {codex_home}")
    return _absolute_path(codex_home) / "hooks.json"


def _codex_destination(target_root: Path) -> _Destination:
    """Resolve and preflight the active Codex hooks destination."""
    hooks_path = _codex_hooks_path(str(target_root))
    configured = os.environ.get("CODEX_HOME", "").strip()
    trusted_root = hooks_path.parent if configured else target_root
    destination = _Destination(hooks_path, trusted_root, "Codex hooks")
    _assert_safe_destination(destination)
    return destination


def _codex_owner(source: str) -> str:
    """Build a collision-resistant, shell-safe owner marker for a source."""
    slug = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-") or "source"
    slug = slug[:48].rstrip("-") or "source"
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]
    return f"{CODEX_OWNER_PREFIX}-{slug}-{digest}"


def _has_codex_owner(command: str, owner: str) -> bool:
    match = CODEX_OWNER_PATTERN.search(command)
    return match is not None and match.group("owner") == owner


def _owned_codex_command(command: str, owner: str) -> str:
    """Attach native ownership without allowing an injected owner conflict."""
    match = CODEX_OWNER_PATTERN.search(command)
    if match is not None:
        raise ValueError(
            "External Codex hook commands must not set AI_TOOLKIT_HOOK_OWNER"
        )
    return f"AI_TOOLKIT_HOOK_OWNER={owner} {command}"


def _translate_codex_hooks(hooks: dict, source: str) -> tuple[dict, list[str]]:
    """Translate the unambiguous command-only subset to native Codex groups."""
    if not isinstance(hooks, dict):
        raise ValueError("hooks must be an object")

    owner = _codex_owner(source)
    translated: dict[str, list[dict]] = {}
    skipped: list[str] = []
    for event, groups in hooks.items():
        if event not in CODEX_EVENTS:
            skipped.append(f"event {event!r} is not supported by Codex")
            continue
        if not isinstance(groups, list):
            raise ValueError(f"Hook event {event} must contain a list")

        translated_groups: list[dict] = []
        for index, group in enumerate(groups):
            if not isinstance(group, dict):
                raise ValueError(f"Hook event {event} group {index} must be an object")
            unknown_group_keys = set(group) - CODEX_NATIVE_GROUP_KEYS - {"_source"}
            if unknown_group_keys:
                skipped.append(
                    f"{event} group {index} uses unsupported fields "
                    f"{sorted(unknown_group_keys)}"
                )
                continue

            handlers = group.get("hooks")
            if not isinstance(handlers, list) or not handlers:
                raise ValueError(f"Hook event {event} group {index} needs handlers")
            native_handlers: list[dict] = []
            for handler_index, handler in enumerate(handlers):
                if not isinstance(handler, dict):
                    raise ValueError(
                        f"Hook event {event} handler {handler_index} must be an object"
                    )
                unknown_handler_keys = (
                    set(handler) - CODEX_NATIVE_HANDLER_KEYS - {"_source"}
                )
                if unknown_handler_keys:
                    skipped.append(
                        f"{event} handler {handler_index} uses unsupported fields "
                        f"{sorted(unknown_handler_keys)}"
                    )
                    continue
                if handler.get("type") != "command":
                    skipped.append(
                        f"{event} handler {handler_index} is not a command handler"
                    )
                    continue
                command = handler.get("command")
                if not isinstance(command, str) or not command.strip():
                    raise ValueError(
                        f"Hook event {event} handler {handler_index} needs a command"
                    )
                native_handler = {
                    key: value
                    for key, value in handler.items()
                    if key in CODEX_NATIVE_HANDLER_KEYS
                }
                native_handler["command"] = _owned_codex_command(command, owner)
                native_handlers.append(native_handler)

            if not native_handlers:
                continue
            native_group: dict = {"hooks": native_handlers}
            matcher = group.get("matcher")
            if matcher not in (None, ""):
                if event in {"UserPromptSubmit", "Stop"}:
                    skipped.append(f"{event} does not support a matcher in Codex")
                    continue
                native_group["matcher"] = matcher
            translated_groups.append(native_group)

        if translated_groups:
            translated[event] = translated_groups
    return translated, skipped


def _migrate_legacy_codex_sources(data: dict) -> dict:
    """Convert the invalid ``_source`` ownership emitted by older releases."""
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        return data

    for event, groups in data.get("hooks", {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict) or "_source" not in group:
                continue
            source = group.get("_source")
            if not isinstance(source, str) or not source:
                continue
            if source == PROTECTED_SOURCE:
                owner = PROTECTED_SOURCE
            elif re.fullmatch(r"ai-toolkit-plugin-[a-z0-9][a-z0-9-]*", source):
                owner = source
            else:
                owner = _codex_owner(source)
            handlers = group.get("hooks", [])
            if not isinstance(handlers, list):
                continue
            for handler in handlers:
                if not isinstance(handler, dict) or handler.get("type") != "command":
                    continue
                command = handler.get("command")
                if not isinstance(command, str) or not command.strip():
                    continue
                match = CODEX_OWNER_PATTERN.search(command)
                if match is not None and match.group("owner") != owner:
                    raise ValueError(
                        f"Legacy Codex {event} owner conflicts with its command marker"
                    )
                if match is None:
                    handler["command"] = f"AI_TOOLKIT_HOOK_OWNER={owner} {command}"
            matcher = group.get("matcher")
            if matcher == "":
                group.pop("matcher", None)
            elif event in {"UserPromptSubmit", "Stop"} and matcher is not None:
                raise ValueError(
                    f"Legacy Codex {event} hook has an unsupported matcher"
                )
            del group["_source"]
    return data


def _has_legacy_source(data: object) -> bool:
    if isinstance(data, dict):
        return "_source" in data or any(
            _has_legacy_source(value) for value in data.values()
        )
    if isinstance(data, list):
        return any(_has_legacy_source(value) for value in data)
    return False


def _load_codex_hooks_bytes(content: bytes | None, path: Path) -> dict:
    """Parse a pinned snapshot and migrate only the known legacy shape."""
    from generate_codex_hooks import (
        parse_hooks_json_bytes,
        validate_hooks_document,
    )

    try:
        return parse_hooks_json_bytes(content, path)
    except ValueError as validation_error:
        if content is None:
            raise
        try:
            data = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise validation_error
        if not _has_legacy_source(data):
            raise validation_error
        migrated = _migrate_legacy_codex_sources(data)
        validate_hooks_document(migrated)
        return migrated


def _strip_codex_owner(data: dict, owner: str) -> bool:
    """Remove only handlers carrying the exact external-source owner marker."""
    changed = False
    hooks = data.get("hooks", {})
    for event in list(hooks):
        retained_groups: list[dict] = []
        for group in hooks[event]:
            handlers = group.get("hooks", [])
            retained = [
                handler
                for handler in handlers
                if not _has_codex_owner(handler.get("command", ""), owner)
            ]
            if len(retained) != len(handlers):
                changed = True
            if retained:
                retained_group = dict(group)
                retained_group["hooks"] = retained
                retained_groups.append(retained_group)
        if retained_groups:
            hooks[event] = retained_groups
        else:
            del hooks[event]
    return changed


@dataclass(frozen=True)
class _CodexUpdate:
    destination: _Destination
    data: dict
    message: str


def _prepare_codex_injection(
    codex_hooks: dict,
    source: str,
    target_root: Path,
    content: bytes | None,
) -> _CodexUpdate | None:
    """Merge native Codex hooks from a transaction-pinned snapshot."""
    destination = _codex_destination(target_root)
    if not codex_hooks and content is None:
        return

    data = _load_codex_hooks_bytes(content, destination.path)
    changed = _strip_codex_owner(data, _codex_owner(source))
    for event, groups in codex_hooks.items():
        data.setdefault("hooks", {}).setdefault(event, []).extend(groups)
        changed = True
    if not changed:
        return

    from generate_codex_hooks import validate_hooks_document

    validate_hooks_document(data)
    events = ", ".join(sorted(codex_hooks.keys()))
    action = f"events: {events}" if events else "removed stale source handlers"
    return _CodexUpdate(
        destination,
        data,
        f"Propagated to Codex: {destination.path} ({action})",
    )


def _prepare_codex_removal(
    source_name: str,
    target_root: Path,
    content: bytes | None,
) -> _CodexUpdate | None:
    """Prepare an exact removal from a transaction-pinned snapshot."""
    destination = _codex_destination(target_root)
    if content is None:
        return None
    data = _load_codex_hooks_bytes(content, destination.path)
    if not _strip_codex_owner(data, _codex_owner(source_name)):
        return None
    from generate_codex_hooks import validate_hooks_document

    validate_hooks_document(data)
    return _CodexUpdate(
        destination,
        data,
        f"Removed '{source_name}' from Codex: {destination.path}",
    )


def _write_codex_update(
    update: _CodexUpdate,
    transaction: SecureTransaction | None = None,
) -> None:
    _require_secure_mutation_support()
    from generate_codex_hooks import write_hooks_json

    _assert_safe_destination(update.destination)
    write_hooks_json(
        update.destination.path,
        update.data,
        transaction=transaction,
        trusted_root=update.destination.trusted_root,
    )


# ---------------------------------------------------------------------------
# CLI actions
# ---------------------------------------------------------------------------


def _validate_source_name(source: str) -> str:
    """Reject reserved or path-like source names before building destinations."""
    if source == PROTECTED_SOURCE:
        raise ValueError(f"source name '{PROTECTED_SOURCE}' is reserved")
    if SOURCE_NAME_PATTERN.fullmatch(source) is None:
        raise ValueError(
            "hook source names may contain only letters, numbers, '_' and '-'"
        )
    return source


@dataclass(frozen=True)
class _RegistryUpdate:
    destination: _Destination
    data: dict


def _registry_destinations(source: str) -> tuple[_Destination, _Destination]:
    """Return safe source-registry and URL-cache destinations."""
    from paths import EXTERNAL_HOOKS_DIR, TOOLKIT_DATA_DIR

    toolkit_root = _absolute_path(TOOLKIT_DATA_DIR)
    trusted_root = _nearest_existing_root(toolkit_root)
    registry = _Destination(
        _absolute_path(EXTERNAL_HOOKS_DIR / "sources.json"),
        trusted_root,
        "hook source registry",
    )
    cache = _Destination(
        _absolute_path(EXTERNAL_HOOKS_DIR / f"{source}.json"),
        trusted_root,
        "hook URL cache",
    )
    _assert_safe_destination(registry)
    _assert_safe_destination(cache)
    return registry, cache


def _load_sources_bytes(content: bytes | None) -> dict[str, dict]:
    """Mirror hook_sources.load_sources using transaction-pinned bytes."""
    if content is None:
        return {}
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        return {}
    return dict(data.get("hooks", {}))


def _prepare_registry_update(
    source: str,
    content: bytes,
    registry_content: bytes | None,
    *,
    source_path: Path | None = None,
    url: str | None = None,
) -> tuple[_RegistryUpdate | None, _Destination]:
    """Build source metadata without mutating the registry or cache."""
    registry, cache = _registry_destinations(source)
    sources = _load_sources_bytes(registry_content)
    existing = sources.get(source) or {}
    if url is None and "url" in existing:
        return None, cache

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = hashlib.sha256(content).hexdigest()
    if url is not None:
        previous_digest = existing.get("sha256")
        if previous_digest and previous_digest != digest:
            print(
                f"  CHECKSUM CHANGED: hook '{source}' sha256 "
                f"{previous_digest[:12]}... -> {digest[:12]}..."
            )
            if os.environ.get("AI_TOOLKIT_STRICT_PIN") == "1":
                raise SystemExit(
                    f"Refusing to update '{source}' under AI_TOOLKIT_STRICT_PIN=1."
                )
        entry = {"url": url, "fetched_at": timestamp, "sha256": digest}
    else:
        assert source_path is not None
        entry = {
            "path": str(source_path.resolve()),
            "fetched_at": timestamp,
            "sha256": digest,
        }
    sources[source] = entry
    return _RegistryUpdate(
        registry,
        {"schema_version": 1, "hooks": sources},
    ), cache


def _prepare_registry_removal(
    source: str,
    registry_content: bytes | None,
) -> tuple[_RegistryUpdate | None, _Destination, bool]:
    """Prepare registry removal and report whether the entry owns a URL cache."""
    registry, cache = _registry_destinations(source)
    sources = _load_sources_bytes(registry_content)
    existing = sources.get(source)
    if existing is None:
        return None, cache, False
    was_url = isinstance(existing, dict) and "url" in existing
    del sources[source]
    return (
        _RegistryUpdate(
            registry,
            {"schema_version": 1, "hooks": sources},
        ),
        cache,
        was_url,
    )


def _fetch_url(url: str) -> bytes:
    """Fetch and validate a remote hooks document without changing local state."""
    from url_fetch import fetch_url

    try:
        data = fetch_url(url)
    except Exception as exc:
        print(f"Error fetching URL: {exc}", file=sys.stderr)
        sys.exit(1)

    # Validate JSON before caching
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        print(f"Error: URL returned invalid JSON: {exc}", file=sys.stderr)
        sys.exit(2)

    if "hooks" not in parsed:
        print("Warning: no 'hooks' key found in URL response", file=sys.stderr)
    return data


def inject(hooks_file: str, target_dir: str, source_override: str = "") -> None:
    """Inject hooks from *hooks_file* (or URL) into the target settings.json.

    Args:
        hooks_file: Path to the external hooks JSON file, or an HTTPS URL.
        target_dir: Directory containing ``.claude/settings.json``.
        source_override: Explicit source name (overrides filename-derived name).
    """
    _require_secure_mutation_support()
    is_url = _is_url(hooks_file)
    source_url: str | None = hooks_file if is_url else None
    source_path: Path | None = None

    if is_url:
        if hooks_file.startswith("http://"):
            print(
                "Error: only HTTPS URLs are supported. Use https:// for security.",
                file=sys.stderr,
            )
            sys.exit(1)

        source = source_override or _name_from_url(hooks_file)
        source = re.sub(r"[^a-zA-Z0-9_-]", "", source)
        if not source:
            print(
                "Error: could not derive hook name from URL. Provide one explicitly.",
                file=sys.stderr,
            )
            sys.exit(1)

        try:
            _validate_source_name(source)
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)
        hooks_content = _fetch_url(hooks_file)
    else:
        # Derive source name from filename stem
        source = source_override or Path(hooks_file).stem
        try:
            _validate_source_name(source)
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(1)
        source_path = _absolute_path(hooks_file)
        try:
            hooks_content = source_path.read_bytes()
        except OSError as error:
            print(f"Error reading hooks file: {error}", file=sys.stderr)
            sys.exit(1)

    # Load the hooks file
    try:
        hooks_data = json.loads(hooks_content)
    except json.JSONDecodeError as exc:
        print(f"Error: malformed JSON in {hooks_file}: {exc}", file=sys.stderr)
        sys.exit(2)

    new_hooks = hooks_data.get("hooks", {})
    if not new_hooks:
        print(f"Warning: no 'hooks' key found in {hooks_file}", file=sys.stderr)
        return

    # Tag entries with source
    tagged = tag_entries(new_hooks, source)

    # Prepare every destination before changing any file. The root is trusted;
    # all descendants are checked component-by-component for symlinks.
    target_root = _trusted_target_root(target_dir)
    settings_path = target_root / ".claude" / "settings.json"
    settings_destination = _Destination(
        settings_path,
        target_root,
        "Claude settings",
    )
    _assert_safe_destination(settings_destination)

    codex_hooks, skipped = _translate_codex_hooks(new_hooks, source)
    for reason in skipped:
        print(f"Skipped Codex hook: {reason}", file=sys.stderr)
    codex_destination = _codex_destination(target_root)
    include_codex = bool(codex_hooks) or codex_destination.path.exists()
    registry_destination, cache_destination = _registry_destinations(source)

    destinations = [settings_destination, registry_destination]
    if is_url:
        destinations.append(cache_destination)
    if include_codex:
        destinations.append(codex_destination)

    result: dict[str, _CodexUpdate | None] = {"codex": None}

    def apply_injection(transaction: SecureTransaction) -> None:
        settings = _load_destination_json(
            transaction.initial_content(settings_destination),
            settings_path,
        )
        existing_hooks = settings.get("hooks", {})
        settings["hooks"] = merge_hooks(tagged, existing_hooks, source)
        registry_update, _ = _prepare_registry_update(
            source,
            hooks_content,
            transaction.initial_content(registry_destination),
            source_path=source_path,
            url=source_url,
        )
        codex_update = (
            _prepare_codex_injection(
                codex_hooks,
                source,
                target_root,
                transaction.initial_content(codex_destination),
            )
            if include_codex
            else None
        )
        result["codex"] = codex_update

        if is_url:
            transaction.atomic_write(cache_destination, hooks_content)
        if registry_update is not None:
            transaction.atomic_write(
                registry_update.destination,
                _json_bytes(registry_update.data, indent=2),
            )
        transaction.atomic_write(settings_destination, _json_bytes(settings))
        if codex_update is not None:
            _write_codex_update(codex_update, transaction)

    try:
        _run_transaction(destinations, apply_injection)
    except _MalformedDestinationJson as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)
    if is_url:
        print(f"Fetched hooks from URL (source: '{source}')")
    print(f"Injected hooks from '{source}' into {settings_path}")
    codex_update = result["codex"]
    if isinstance(codex_update, _CodexUpdate):
        print(codex_update.message)


def remove(source_name: str, target_dir: str) -> None:
    """Remove all hook entries tagged with *source_name*.

    Also unregisters the URL source if it was URL-sourced.

    Args:
        source_name: The ``_source`` tag to remove.
        target_dir: Directory containing ``.claude/settings.json``.
    """
    _require_secure_mutation_support()
    try:
        _validate_source_name(source_name)
    except ValueError as error:
        suffix = (
            " Use 'ai-toolkit uninstall' instead."
            if source_name == PROTECTED_SOURCE
            else ""
        )
        print(f"Error: {error}.{suffix}", file=sys.stderr)
        sys.exit(1)

    target_root = _trusted_target_root(target_dir)
    settings_path = target_root / ".claude" / "settings.json"
    settings_destination = _Destination(
        settings_path,
        target_root,
        "Claude settings",
    )
    _assert_safe_destination(settings_destination)
    codex_destination = _codex_destination(target_root)
    registry_destination, cache_destination = _registry_destinations(source_name)
    include_settings = settings_path.is_file()
    include_codex = codex_destination.path.is_file()
    include_registry = registry_destination.path.is_file()
    destinations: list[_Destination] = []
    if include_settings:
        destinations.append(settings_destination)
    if include_codex:
        destinations.append(codex_destination)
    if include_registry:
        destinations.append(registry_destination)
        destinations.append(cache_destination)

    result: dict[str, object] = {
        "settings": None,
        "codex": None,
        "registry": None,
    }

    def apply_removal(transaction: SecureTransaction) -> None:
        settings_update: dict | None = None
        if include_settings:
            settings_content = transaction.initial_content(settings_destination)
            if settings_content is not None:
                settings = _load_destination_json(settings_content, settings_path)
                existing_hooks = settings.get("hooks", {})
                cleaned = strip_source(existing_hooks, source_name)
                if cleaned:
                    settings["hooks"] = cleaned
                else:
                    settings.pop("hooks", None)
                settings_update = settings
        codex_update = (
            _prepare_codex_removal(
                source_name,
                target_root,
                transaction.initial_content(codex_destination),
            )
            if include_codex
            else None
        )
        registry_update, _, remove_cache = (
            _prepare_registry_removal(
                source_name,
                transaction.initial_content(registry_destination),
            )
            if include_registry
            else (None, cache_destination, False)
        )
        result["settings"] = settings_update
        result["codex"] = codex_update
        result["registry"] = registry_update

        if settings_update is not None:
            transaction.atomic_write(
                settings_destination,
                _json_bytes(settings_update),
            )
        if codex_update is not None:
            _write_codex_update(codex_update, transaction)
        if registry_update is not None:
            transaction.atomic_write(
                registry_update.destination,
                _json_bytes(registry_update.data, indent=2),
            )
        if remove_cache:
            transaction.unlink(cache_destination)

    try:
        _run_transaction(destinations, apply_removal)
    except _MalformedDestinationJson as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)
    settings_update = result["settings"]
    if settings_update is not None:
        print(f"Removed hooks with source '{source_name}' from {settings_path}")
    else:
        print(f"No settings.json found at {settings_path}")
    codex_update = result["codex"]
    if isinstance(codex_update, _CodexUpdate):
        print(codex_update.message)
    if isinstance(result["registry"], _RegistryUpdate):
        print(f"Unregistered hook source '{source_name}'")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str]) -> dict:
    """Parse CLI arguments.

    Returns:
        Dict with keys: remove_mode, remove_name, source_file, hook_name,
        target_dir.
    """
    result: dict = {
        "remove_mode": False,
        "remove_name": "",
        "source_file": "",
        "hook_name": "",
        "target_dir": str(Path.home()),
    }

    i = 0
    positional = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--remove":
            result["remove_mode"] = True
            i += 1
            if i >= len(argv):
                print("--remove requires a hook source name", file=sys.stderr)
                sys.exit(1)
            result["remove_name"] = argv[i]
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            if positional == 0:
                if not result["remove_mode"]:
                    result["source_file"] = arg
                else:
                    result["target_dir"] = arg
            elif positional == 1:
                # Preserve the historical two-positional form
                # ``<source> <target-dir>`` while honoring the documented
                # ``<source> <hook-name> [target-dir]`` form. Valid hook names
                # cannot begin with path sigils.
                looks_like_path = (
                    arg.startswith(("/", "~", "."))
                    or os.sep in arg
                    or (os.altsep is not None and os.altsep in arg)
                    or (
                        not _is_url(result["source_file"])
                        and Path(arg).expanduser().is_dir()
                    )
                )
                if looks_like_path:
                    result["target_dir"] = arg
                else:
                    result["hook_name"] = arg
            elif positional == 2:
                result["target_dir"] = arg
            positional += 1
        i += 1

    return result


def main() -> None:
    """Inject or remove external hooks in Claude and Codex configs."""
    args = _parse_args(sys.argv[1:])

    # -- remove mode ---------------------------------------------------------
    if args["remove_mode"]:
        remove(args["remove_name"], args["target_dir"])
        return

    # -- inject mode ---------------------------------------------------------
    source_file = args["source_file"]
    if not source_file:
        print(
            "Usage: inject_hook_cli.py <hooks-file-or-url> [hook-name] [target-dir]",
            file=sys.stderr,
        )
        print(
            "       inject_hook_cli.py --remove <hook-source-name> [target-dir]",
            file=sys.stderr,
        )
        sys.exit(1)

    if not _is_url(source_file):
        source_path = Path(source_file)
        if not source_path.is_file():
            print(f"Hooks file not found: {source_path}", file=sys.stderr)
            sys.exit(1)

    inject(source_file, args["target_dir"], source_override=args["hook_name"])


if __name__ == "__main__":
    main()
