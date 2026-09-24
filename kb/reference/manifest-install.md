---
title: "Manifest-Driven Install System"
category: reference
service: ai-toolkit
tags: [install, manifest, modules, profiles, auto-detect, state-tracking]
version: "1.17.0"
created: "2026-04-07"
last_updated: "2026-09-24"
description: "Reference for manifest-driven project installation and install state in ~/.softspark/ai-toolkit/state.json."
---

# Manifest-Driven Install System

## Overview

ai-toolkit's install system supports module-level granularity on top of the existing profile-based install. Instead of choosing only between minimal/standard/strict, you can select individual modules (specific language rules, MCP templates, etc.) or enable auto-detection of the project language.

All existing `--profile` behavior is preserved and unchanged. The manifest system is an additive opt-in layer.

## Modules

Modules are defined in `manifest.json` at the repository root. There are 17 modules:

| Module | Description | In Profile |
|--------|-------------|-----------|
| `core` | Core hooks and essential skills | minimal, standard, strict, full |
| `agents` | Specialized agents | standard, strict, full |
| `skills` | All skills (task, hybrid, knowledge) | standard, strict, full |
| `rules-common` | Common coding rules (5 files) | standard, strict, full |
| `rules-typescript` | TypeScript-specific rules (5 files) | auto-detect |
| `rules-python` | Python-specific rules (5 files) | auto-detect |
| `rules-golang` | Go-specific rules (5 files) | auto-detect |
| `rules-rust` | Rust-specific rules (5 files) | auto-detect |
| `rules-java` | Java-specific rules (5 files) | auto-detect |
| `rules-kotlin` | Kotlin-specific rules (5 files) | auto-detect |
| `rules-swift` | Swift-specific rules (5 files) | auto-detect |
| `rules-dart` | Dart/Flutter-specific rules (5 files) | auto-detect |
| `rules-csharp` | C#/.NET-specific rules (5 files) | auto-detect |
| `rules-php` | PHP-specific rules (5 files) | auto-detect |
| `rules-cpp` | C++-specific rules (5 files) | auto-detect |
| `rules-ruby` | Ruby-specific rules (5 files) | auto-detect |
| `mcp-templates` | 28 MCP server config templates | strict, full |

## Profiles

Profiles are predefined module sets. They map directly to `--profile` values:

| Profile | Modules |
|---------|---------|
| `minimal` | `core` |
| `standard` | `core`, `agents`, `skills`, `rules-common` |
| `strict` | `core`, `agents`, `skills`, `rules-common`, `mcp-templates` |
| `full` | All modules (same as strict currently; language rules added via `--auto-detect`) |

## CLI

```bash
# Profile-based install (existing behavior, unchanged)
ai-toolkit install --profile standard

# Module-based install (new)
ai-toolkit install --modules core,agents,rules-typescript

# --local implies --auto-detect (language rules auto-detected)
ai-toolkit install --local

# Show currently installed modules and their state
ai-toolkit status

# Incremental update (only re-applies modules with changed content)
ai-toolkit update
```

### --modules

Accepts a comma-separated list of module names. Can be combined with a profile:

```bash
# Start from standard profile, also add TypeScript rules
ai-toolkit install --profile standard --modules rules-typescript
```

### --auto-detect

Scans the current working directory for marker files and selects the matching language module. Implemented in `scripts/install_steps/detect_language.py`.

Detection markers per module:

| Module | Detected when these files exist |
|--------|--------------------------------|
| `rules-typescript` | `package.json` or `tsconfig.json` |
| `rules-python` | `requirements.txt`, `pyproject.toml`, `setup.py`, or `Pipfile` |
| `rules-golang` | `go.mod` |
| `rules-rust` | `Cargo.toml` |
| `rules-java` | `pom.xml` or `build.gradle` |
| `rules-kotlin` | `build.gradle.kts` |
| `rules-swift` | `Package.swift` |
| `rules-dart` | `pubspec.yaml` |
| `rules-csharp` | `*.csproj` or `*.sln` |
| `rules-php` | `composer.json` |
| `rules-cpp` | `CMakeLists.txt` or `Makefile` |
| `rules-ruby` | `Gemfile` |

### status

Lists all currently installed modules with version and install timestamp:

```bash
ai-toolkit status
# Installed modules (from ~/.softspark/ai-toolkit/state.json):
#   core            v1.3.0   installed 2026-04-07T10:00:00Z
#   agents          v1.3.0   installed 2026-04-07T10:00:00Z
#   skills          v1.3.0   installed 2026-04-07T10:00:00Z
#   rules-common    v1.3.0   installed 2026-04-07T10:00:00Z
#   rules-typescript v1.3.0  installed 2026-04-07T10:00:00Z
```

### update

Re-applies installed modules, skipping files whose content hash has not changed since last install. Implemented in `scripts/install_steps/install_state.py`.

## Retired DSH Profile Lifecycle

`ai-toolkit install --local --editors dsh` and `ai-toolkit dsh install|update|doctor|uninstall` were removed on 2026-09-24. Project `.agents/skills` surfaces written for DSH are migrated by `update` / `install --local` and removed by `ai-toolkit uninstall`. DSH profiles are not touched by the toolkit any more. Remove them with DSH itself as described in [DSH Compatibility (retired)](dsh-compatibility.md).

## State Tracking

Installed module state is persisted to `~/.softspark/ai-toolkit/state.json`:

```json
{
  "installed_version": "1.3.0",
  "installed_modules": ["core", "agents", "skills", "rules-common", "rules-typescript"],
  "installed_at": "2026-04-07T10:00:00Z",
  "last_updated": "2026-04-07T10:00:00Z",
  "file_hashes": {
    "app/hooks/session-start.sh": "abc123..."
  }
}
```

- `installed_modules` — used by `update` to know which modules to re-apply
- `file_hashes` — used to skip unchanged files during `update`
- The file is written after every successful install or update

Every shared state writer uses the canonical path from `AI_TOOLKIT_HOME`, `SOFTSPARK_HOME`, or the default `~/.softspark/ai-toolkit/state.json` and cooperates through the same bounded `.state.lock`. Where the host provides descriptor-relative atomic primitives, the lock context pins the state parent device and inode. Transaction reads, snapshots, compare-and-swap merges, private temporary creation, writes, `fsync`, publication, mode changes, cleanup, and lock release then address entries relative to that same open parent descriptor. The lexical parent binding is checked before publication and release. Replacing the state directory therefore fails without publishing into the replacement or losing either root. Generic install, MCP, and editor state writers retain the portable state contract on every supported Python platform. They use this pinned atomic publisher when available and otherwise publish a private temporary with the platform's atomic replacement primitive while holding the shared lock.

## Implementation Files

| File | Purpose |
|------|---------|
| `manifest.json` | Module and profile definitions |
| `scripts/install_steps/detect_language.py` | Auto-detect project language from marker files |
| `scripts/install_steps/install_state.py` | Read/write `~/.softspark/ai-toolkit/state.json` |

## Backward Compatibility

Existing `--profile` usage works identically. The manifest system does not change what gets installed when you use `--profile minimal/standard/strict`. It only adds:

1. `--modules` for granular selection
2. `--auto-detect` for language rules
3. `state.json` tracking for incremental updates
4. `status` command to inspect installed state

No existing install scripts or CI configurations need changes.

## Related Documentation

- [PATH: kb/reference/language-rules.md] — language rules structure and auto-detection detail
- [PATH: kb/reference/mcp-templates.md] — MCP server templates (the `mcp-templates` module)
- [PATH: kb/reference/architecture-overview.md] — overall install model
- [PATH: kb/reference/dsh-compatibility.md] - retired DSH integration and manual profile cleanup
