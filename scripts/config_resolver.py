#!/usr/bin/env python3
"""Config resolver for ai-toolkit extends system.

Resolves base configs from npm packages, git URLs, or local paths.
Caches resolved configs in ~/.softspark/ai-toolkit/config-cache/.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (
    BASE_CONFIG_FILENAME,
    CONFIG_CACHE_DIR,
    LEGACY_PROJECT_CONFIG,
    PROJECT_CONFIG_FILENAME as _PROJECT_CONFIG,
)

MAX_EXTENDS_DEPTH = 5
CONFIG_FILENAME = BASE_CONFIG_FILENAME
PROJECT_CONFIG_FILENAME = _PROJECT_CONFIG
CACHE_DIR_NAME = "config-cache"


def _cache_root() -> Path:
    """Return the cache root directory."""
    return CONFIG_CACHE_DIR


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BaseConfig:
    """A resolved base configuration."""

    source: str              # original extends string
    root: Path               # directory containing the config
    data: dict[str, Any]     # parsed ai-toolkit.config.json
    version: str = ""        # resolved version (if npm)
    integrity: str = ""      # sha256 hash of config file

    @property
    def name(self) -> str:
        return self.data.get("name", self.source)

    @property
    def extends(self) -> str | None:
        return self.data.get("extends") or None


@dataclass
class ResolutionResult:
    """Result of resolving an extends chain."""

    configs: list[BaseConfig] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ConfigResolverError(Exception):
    """Raised when config resolution fails."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_extends(
    extends_value: str,
    project_root: str | Path,
    *,
    refresh: bool = False,
) -> ResolutionResult:
    """Resolve an extends chain into an ordered list of base configs.

    Args:
        extends_value: The extends string from .softspark-toolkit.json.
        project_root: The project directory (for resolving relative paths).
        refresh: Force re-fetch ignoring cache.

    Returns:
        ResolutionResult with ordered configs (deepest ancestor first).

    Raises:
        ConfigResolverError: On resolution failure.
    """
    result = ResolutionResult()
    _resolve_chain(extends_value, Path(project_root), set(), result, refresh=refresh)
    return result


def load_project_config(project_root: str | Path) -> dict[str, Any] | None:
    """Load .softspark-toolkit.json from the project root.

    Falls back to legacy .ai-toolkit.json if the new file doesn't exist.
    Returns None if neither file exists.
    """
    config_path = Path(project_root) / PROJECT_CONFIG_FILENAME
    if not config_path.is_file():
        # Fallback to legacy filename
        legacy_path = Path(project_root) / LEGACY_PROJECT_CONFIG
        if legacy_path.is_file():
            return _load_json(legacy_path)
        return None
    return _load_json(config_path)


def load_base_config(config_dir: str | Path) -> dict[str, Any]:
    """Load ai-toolkit.config.json from a directory."""
    config_path = Path(config_dir) / CONFIG_FILENAME
    if not config_path.is_file():
        raise ConfigResolverError(
            f"Base config not found: {config_path}\n"
            f"Expected {CONFIG_FILENAME} in the extends target directory."
        )
    return _load_json(config_path)


# ---------------------------------------------------------------------------
# Internal: chain resolution
# ---------------------------------------------------------------------------

def _resolve_chain(
    extends_value: str,
    project_root: Path,
    visited: set[str],
    result: ResolutionResult,
    *,
    refresh: bool = False,
) -> None:
    """Recursively resolve extends chain with cycle + depth detection."""
    # Cycle detection
    canonical = _canonical_source(extends_value)
    if canonical in visited:
        raise ConfigResolverError(
            f"Circular extends detected: '{extends_value}' already in chain "
            f"{' -> '.join(visited)}.\n"
            f"Check your base config's 'extends' field."
        )

    # Depth check
    if len(visited) >= MAX_EXTENDS_DEPTH:
        raise ConfigResolverError(
            f"Extends chain too deep (max {MAX_EXTENDS_DEPTH} levels).\n"
            f"Chain: {' -> '.join(visited)}"
        )

    visited.add(canonical)

    # Resolve this source
    base_config = _resolve_source(extends_value, project_root, result, refresh=refresh)

    # Recurse if this base also extends something
    if base_config.extends:
        _resolve_chain(
            base_config.extends,
            base_config.root,
            visited,
            result,
            refresh=refresh,
        )

    # Append after recursion (deepest ancestor first)
    result.configs.append(base_config)


def _resolve_source(
    source: str,
    project_root: Path,
    result: ResolutionResult,
    *,
    refresh: bool = False,
) -> BaseConfig:
    """Resolve a single extends source."""
    if source.startswith("git+"):
        return _resolve_git(source, result, refresh=refresh)
    if source.startswith(".") or source.startswith("/") or source.startswith("~"):
        return _resolve_local(source, project_root)
    # Default: npm package
    return _resolve_npm(source, result, refresh=refresh)


# ---------------------------------------------------------------------------
# Resolvers: npm
# ---------------------------------------------------------------------------

def _resolve_npm(
    source: str,
    result: ResolutionResult,
    *,
    refresh: bool = False,
) -> BaseConfig:
    """Resolve from npm registry via npm pack."""
    package_name, version_spec = _parse_npm_source(source)
    cache_dir = _npm_cache_dir(package_name)

    # Check cache first (unless refresh)
    if not refresh:
        cached = _find_cached_npm(cache_dir)
        if cached:
            # If we have a cached version and are offline, use it
            try:
                return _load_cached_config(cached, source)
            except ConfigResolverError:
                pass  # cache corrupt, re-fetch

    # Fetch via npm pack
    pack_source = f"{package_name}@{version_spec}" if version_spec else package_name

    with tempfile.TemporaryDirectory(prefix="ai-toolkit-npm-") as tmp:
        tmp_path = Path(tmp)
        try:
            proc = subprocess.run(
                ["npm", "pack", pack_source, "--pack-destination", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except FileNotFoundError:
            return _offline_fallback(cache_dir, source, result, "npm not found in PATH")
        except subprocess.TimeoutExpired:
            return _offline_fallback(cache_dir, source, result, "npm pack timed out (60s)")

        if proc.returncode != 0:
            return _offline_fallback(
                cache_dir, source, result,
                f"npm pack failed: {proc.stderr.strip()}"
            )

        # Find the tarball
        tarballs = list(tmp_path.glob("*.tgz"))
        if not tarballs:
            return _offline_fallback(cache_dir, source, result, "npm pack produced no tarball")

        tarball = tarballs[0]
        version = _extract_version_from_tarball(tarball.name, package_name)

        # Extract to cache
        dest = cache_dir / version
        dest.mkdir(parents=True, exist_ok=True)
        _extract_tarball(tarball, dest)

    return _load_cached_config(dest, source, version=version)


def _parse_npm_source(source: str) -> tuple[str, str]:
    """Parse 'package@version' into (package, version) tuple."""
    # Handle scoped packages: @scope/pkg@version
    if source.startswith("@"):
        # Find the second @ (version separator)
        rest = source[1:]
        if "@" in rest.split("/", 1)[-1]:
            # @scope/pkg@version
            parts = source.rsplit("@", 1)
            return parts[0], parts[1]
        return source, ""

    if "@" in source:
        parts = source.rsplit("@", 1)
        return parts[0], parts[1]

    return source, ""


def _npm_cache_dir(package_name: str) -> Path:
    """Cache directory for an npm package."""
    # @scope/pkg -> @scope/pkg/
    return _cache_root() / package_name


def _find_cached_npm(cache_dir: Path) -> Path | None:
    """Find the latest cached version directory."""
    if not cache_dir.is_dir():
        return None
    versions = sorted(
        [d for d in cache_dir.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    return versions[0] if versions else None


def _extract_tarball(tarball: Path, dest: Path) -> None:
    """Extract npm tarball (which has a package/ prefix) to dest.

    Validates that extracted paths stay within dest to prevent path traversal.
    Rejects symlinks and absolute paths. Uses tarfile filter="data" on 3.12+
    as defense in depth (Python 3.14 will require it).
    """
    dest_resolved = dest.resolve()
    # filter="data" landed in 3.12 and becomes the default in 3.14
    supports_filter = sys.version_info >= (3, 12)
    with tarfile.open(tarball, "r:gz") as tf:
        for member in tf.getmembers():
            # npm tarballs have a "package/" prefix
            if not member.name.startswith("package/"):
                continue
            member.name = member.name[len("package/"):]
            if not member.name:  # skip empty (the "package/" dir itself)
                continue
            # Reject symlinks and absolute paths
            if member.issym() or member.islnk() or member.name.startswith("/"):
                continue
            # Path traversal protection
            target = (dest / member.name).resolve()
            if not str(target).startswith(str(dest_resolved)):
                continue
            if supports_filter:
                tf.extract(member, dest, filter="data")
            else:
                tf.extract(member, dest)


def _extract_version_from_tarball(filename: str, package_name: str) -> str:
    """Extract version from tarball filename."""
    # Pattern: scope-pkg-1.0.0.tgz or pkg-1.0.0.tgz
    name = filename.removesuffix(".tgz")
    # Remove scope prefix if present
    clean_pkg = package_name.replace("@", "").replace("/", "-")
    if name.startswith(clean_pkg + "-"):
        return name[len(clean_pkg) + 1:]
    return name


# ---------------------------------------------------------------------------
# Resolvers: git
# ---------------------------------------------------------------------------

def _resolve_git(
    source: str,
    result: ResolutionResult,
    *,
    refresh: bool = False,
) -> BaseConfig:
    """Resolve from git URL (git+https://...)."""
    url = source.removeprefix("git+")
    if not url.startswith("https://"):
        raise ConfigResolverError(
            f"Only HTTPS git URLs are supported (got: {url.split('://')[0]}://)"
        )
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:16]
    cache_dir = _cache_root() / "git" / cache_key

    if not refresh and cache_dir.is_dir() and (cache_dir / CONFIG_FILENAME).is_file():
        return _load_cached_config(cache_dir, source)

    # Clone (shallow)
    cache_dir.mkdir(parents=True, exist_ok=True)
    try:
        # Clean previous clone if refreshing
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True)

        proc = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(cache_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return _offline_fallback(cache_dir, source, result, "git not found in PATH")
    except subprocess.TimeoutExpired:
        return _offline_fallback(cache_dir, source, result, "git clone timed out (120s)")

    if proc.returncode != 0:
        return _offline_fallback(
            cache_dir, source, result,
            f"git clone failed: {proc.stderr.strip()}"
        )

    return _load_cached_config(cache_dir, source)


# ---------------------------------------------------------------------------
# Resolvers: local path
# ---------------------------------------------------------------------------

def _resolve_local(source: str, project_root: Path) -> BaseConfig:
    """Resolve from a local path (relative or absolute)."""
    if source.startswith("~"):
        resolved = Path(source).expanduser()
    else:
        resolved = (project_root / source).resolve()

    if not resolved.is_dir():
        raise ConfigResolverError(
            f"Local extends path not found: {resolved}\n"
            f"Source: '{source}' resolved from project root: {project_root}"
        )

    return _load_cached_config(resolved, source)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _load_cached_config(
    config_dir: Path,
    source: str,
    version: str = "",
) -> BaseConfig:
    """Load a BaseConfig from a directory."""
    config_path = config_dir / CONFIG_FILENAME
    if not config_path.is_file():
        raise ConfigResolverError(
            f"Base config not found: {config_path}\n"
            f"Expected '{CONFIG_FILENAME}' in extends target.\n"
            f"Source: {source}"
        )

    data = _load_json(config_path)
    integrity = _file_hash(config_path)

    return BaseConfig(
        source=source,
        root=config_dir,
        data=data,
        version=version or data.get("version", ""),
        integrity=integrity,
    )


def _offline_fallback(
    cache_dir: Path,
    source: str,
    result: ResolutionResult,
    reason: str,
) -> BaseConfig:
    """Fall back to cached config when fetch fails."""
    cached = _find_cached_npm(cache_dir) if cache_dir.is_dir() else None

    # For git caches, check directly
    if cached is None and cache_dir.is_dir() and (cache_dir / CONFIG_FILENAME).is_file():
        cached = cache_dir

    if cached:
        result.warnings.append(
            f"Using cached config for '{source}' (offline). Reason: {reason}"
        )
        return _load_cached_config(cached, source)

    raise ConfigResolverError(
        f"Cannot resolve extends '{source}': {reason}\n"
        f"No cached version found.\n"
        f"Run 'ai-toolkit update --local --refresh-base' when online."
    )


def _load_json(path: Path) -> dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigResolverError(f"Invalid JSON in {path}: {e}") from e
    except OSError as e:
        raise ConfigResolverError(f"Cannot read {path}: {e}") from e


def _file_hash(path: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _canonical_source(source: str) -> str:
    """Normalize source string for cycle detection."""
    # Strip version specifiers for comparison
    s = source.strip()
    if s.startswith("git+"):
        return s.lower()
    # npm: strip version
    name, _ = _parse_npm_source(s)
    return name.lower()


# ---------------------------------------------------------------------------
# CLI entry point (for testing)
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI: resolve extends and print result as JSON."""
    if len(sys.argv) < 2:
        print("Usage: config_resolver.py <project-dir> [--refresh]", file=sys.stderr)
        sys.exit(1)

    project_dir = Path(sys.argv[1])
    refresh = "--refresh" in sys.argv

    config = load_project_config(project_dir)
    if config is None:
        print(json.dumps({"error": f"No {PROJECT_CONFIG_FILENAME} found in {project_dir}"}))
        sys.exit(1)

    extends = config.get("extends")
    if not extends:
        print(json.dumps({"configs": [], "warnings": []}))
        sys.exit(0)

    try:
        result = resolve_extends(extends, project_dir, refresh=refresh)
        print(json.dumps({
            "configs": [
                {
                    "source": c.source,
                    "name": c.name,
                    "version": c.version,
                    "root": str(c.root),
                    "integrity": c.integrity,
                }
                for c in result.configs
            ],
            "warnings": result.warnings,
        }, indent=2))
    except ConfigResolverError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
