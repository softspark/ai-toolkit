---
title: "Language Rules System"
category: reference
service: ai-toolkit
tags: [rules, languages, coding-style, testing, patterns, security]
version: "1.0.0"
created: "2026-04-07"
last_updated: "2026-04-07"
description: "Reference for the language-specific rules system: 13 languages, 5 categories per language, auto-detection."
---

# Language Rules System

## Overview

ai-toolkit ships 70 language-specific rule files covering 13 programming languages plus a common set. Rules are plain Markdown files injected into `CLAUDE.md` via `ai-toolkit install --local`. They provide coding-style, testing, patterns, frameworks, and security guidance specific to each language.

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
└── ruby/
```

**Total: 13 languages × 5 files + 5 common = 70 rule files**

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

When `--auto-detect` is passed, `scripts/install_steps/detect_language.py` scans the current directory for known marker files and selects the matching language module:

```bash
ai-toolkit install --local --auto-detect
```

Detection logic (first match wins when multiple markers are present):
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

Common rules are always injected regardless of detected language.

## Installation

```bash
# Auto-detect language from project files
ai-toolkit install --local --auto-detect

# Explicitly select a language
ai-toolkit install --local --lang typescript

# Install without language rules
ai-toolkit install --local
```

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
