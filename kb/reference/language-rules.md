---
title: "Language Rules System"
category: reference
service: ai-toolkit
tags: [rules, languages, coding-style, testing, patterns, security]
version: "1.0.0"
created: "2026-04-07"
last_updated: "2026-04-07"
description: "Reference for the language-specific rules system: 14 languages, 5 categories per language, auto-detection."
---

# Language Rules System

## Overview

ai-toolkit ships language-specific rule files covering 14 languages/platforms plus a common set (see README.md for current count). Rules are plain Markdown files injected into `CLAUDE.md` via `ai-toolkit install --local`. They provide coding-style, testing, patterns, frameworks, and security guidance specific to each language.

Rules are distinct from skills: rules are injected as static text into `CLAUDE.md` and are always visible to Claude, whereas skills are loaded contextually by agents.

## File Structure

```
app/rules/
├── common/
│   ├── coding-style.md     # KISS, DRY, YAGNI, immutability
│   ├── testing.md          # Universal testing standards
│   ├── git-workflow.md     # Commit conventions
│   ├── performance.md      # Performance guidelines
│   └── security.md         # OWASP, input validation
├── typescript/
│   ├── coding-style.md     # Strict mode, no-any, naming
│   ├── testing.md          # Vitest/Jest patterns
│   ├── patterns.md         # Discriminated unions, utility types
│   ├── frameworks.md       # React hooks, Next.js, lifecycle
│   └── security.md         # XSS prevention, sanitization
├── python/
│   ├── coding-style.md     # PEP 8, type hints, dataclasses
│   ├── testing.md          # pytest, fixtures, parametrize
│   ├── patterns.md         # Python idioms, context managers
│   ├── frameworks.md       # FastAPI/Django lifecycle, SQLAlchemy
│   └── security.md         # SQL injection, SSTI prevention
├── golang/           # same 5-file structure
├── rust/
├── java/
├── kotlin/
├── swift/
├── dart/
├── csharp/
├── php/
├── cpp/
├── ruby/
└── medplum/
```

**Total: 14 directories × 5 files each + 3 standalone = 73 rule files** (see README.md for canonical count)

## Supported Languages

| Language | Directory | Auto-detect Files |
|----------|-----------|------------------|
| Common | `rules/common/` | always included |
| TypeScript | `rules/typescript/` | `package.json`, `tsconfig.json` |
| Python | `rules/python/` | `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` |
| Go | `rules/golang/` | `go.mod` |
| Rust | `rules/rust/` | `Cargo.toml` |
| Java | `rules/java/` | `pom.xml`, `build.gradle`, `build.gradle.kts` |
| Kotlin | `rules/kotlin/` | `build.gradle.kts` |
| Swift | `rules/swift/` | `Package.swift`, `*.xcodeproj` |
| Dart | `rules/dart/` | `pubspec.yaml` |
| C# | `rules/csharp/` | `*.csproj`, `*.sln` |
| PHP | `rules/php/` | `composer.json` |
| C++ | `rules/cpp/` | `CMakeLists.txt`, `Makefile`, `*.cpp` |
| Ruby | `rules/ruby/` | `Gemfile`, `*.gemspec` |
| Medplum | `rules/medplum/` | `medplum.config.mts`, `medplum.config.ts` |

## Rule Categories

| Category | Filename | Content |
|----------|----------|---------|
| `coding-style` | `coding-style.md` | Naming, formatting, idiomatic constructs, linter config |
| `testing` | `testing.md` | Test framework usage, fixture patterns, coverage targets |
| `patterns` | `patterns.md` | Language-specific design patterns and idioms |
| `frameworks` | `frameworks.md` | Recommended framework conventions and lifecycle hooks |
| `security` | `security.md` | Common language-specific vulnerabilities and mitigations |

The `common/` directory uses the same structure except `frameworks.md` is replaced by `git-workflow.md` and `performance.md`.

## Auto-Detection

`--local` automatically enables language auto-detection. `scripts/install_steps/detect_language.py` uses two-phase detection and merges results from both:

```bash
ai-toolkit install --local     # auto-detects language (--auto-detect is implied)
```

### Phase 1: Marker files (config-level signals)

Scans for configuration files defined in each module's `auto_detect` list in `manifest.json`:

1. `package.json` or `tsconfig.json` → TypeScript
2. `go.mod` → Go
3. `Cargo.toml` → Rust
4. `pubspec.yaml` → Dart
5. `composer.json` → PHP
6. `Gemfile` → Ruby
7. `requirements.txt`, `pyproject.toml`, `setup.py`, or `Pipfile` → Python
8. `pom.xml` or `build.gradle` → Java
9. `build.gradle.kts` → Kotlin
10. `Package.swift` → Swift
11. `*.csproj` or `*.sln` → C#
12. `CMakeLists.txt` or `Makefile` → C++
13. `medplum.config.mts` or `medplum.config.ts` → Medplum

### Phase 2: Source file extensions (actual code presence)

Scans top-level files and one directory level deep for source file extensions (`.py`, `.ts`, `.go`, `.rs`, `.java`, `.kt`, `.swift`, `.dart`, `.cs`, `.php`, `.cpp`, `.rb`, etc.). Skips dependency/build directories (`node_modules`, `venv`, `dist`, `build`, etc.) for speed.

This catches cases where marker files are misleading — e.g., a Python project with a `package.json` only for its npm CLI wrapper will correctly detect both Python (via `.py` files) and TypeScript (via `package.json`).

Both phases contribute; results are merged and deduplicated. Common rules are always injected regardless of detected language.

## Installation

```bash
# Auto-detect language from project files (default with --local)
ai-toolkit install --local

# Explicitly select a language (implies --local, disables auto-detect)
ai-toolkit install --local --lang typescript

# Multiple languages
ai-toolkit install --local --lang go,python

# Skip auto-detect, install specific modules only
ai-toolkit install --local --modules core,agents
```

The `--lang` flag accepts comma-separated language names and converts them to `rules-<lang>` modules. Common aliases are supported: `go` → `golang`, `c++` → `cpp`, `c#`/`cs` → `csharp`. Using `--lang` implies `--local` and disables auto-detection.

Language rules are injected into the project `CLAUDE.md` between named markers:

```
<!-- TOOLKIT:rules-typescript START -->
... TypeScript rules content ...
<!-- TOOLKIT:rules-typescript END -->
```

Re-running `install --local` is idempotent — existing blocks are replaced, not duplicated.

## Manifest Module Names

Language rules are tracked as modules in `manifest.json`:

| Module | Description |
|--------|-------------|
| `rules-common` | Common coding rules (5 files), included in `standard` profile |
| `rules-typescript` | TypeScript-specific rules |
| `rules-python` | Python-specific rules |
| `rules-golang` | Go-specific rules |
| `rules-rust` | Rust-specific rules |
| `rules-java` | Java-specific rules |
| `rules-kotlin` | Kotlin-specific rules |
| `rules-swift` | Swift-specific rules |
| `rules-dart` | Dart/Flutter-specific rules |
| `rules-csharp` | C#/.NET-specific rules |
| `rules-php` | PHP-specific rules |
| `rules-cpp` | C++-specific rules |
| `rules-ruby` | Ruby-specific rules |
| `rules-medplum` | Medplum/FHIR healthcare platform rules |

## Rules vs Skills

| | Rules | Skills |
|---|-------|--------|
| Location | `app/rules/` | `app/skills/` |
| Delivery | Injected into `CLAUDE.md` text | Loaded from `~/.claude/skills/` |
| Visibility | Always visible in context | Loaded contextually by agents |
| Scope | Per-language static guidance | Domain-specific agent behavior |
| Install | `--local` only | Global install |

## Related Documentation

- [PATH: kb/reference/manifest-install.md] — module-level install granularity
- [PATH: kb/reference/extension-api.md] — injecting rules from external tools
- [PATH: kb/reference/architecture-overview.md] — overall install model
