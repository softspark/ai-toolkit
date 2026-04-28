---
title: "Language Rules System"
category: reference
service: ai-toolkit
tags: [rules, languages, coding-style, testing, patterns, security]
version: "2.0.0"
created: "2026-04-07"
last_updated: "2026-04-28"
description: "Reference for the language-specific rules system: 13 per-language rule sets shipped as knowledge skills, plus a common set inlined into CLAUDE.md."
---

# Language Rules System

## Overview

ai-toolkit ships rule content for 13 languages/platforms plus a language-agnostic common set. Source files live under `app/rules/` and are split into two delivery channels by `ai-toolkit install --local`:

- **Common rules** (`app/rules/common/*.md`): full content is inlined into the project's `.claude/CLAUDE.md` under a single `<!-- TOOLKIT:language-rules START -->` marker. They cover coding-style, git-workflow, performance, security, and testing — concerns that apply regardless of language, so they stay always visible.
- **Per-language rules** (`app/rules/<lang>/*.md`): emitted at build time as `<lang>-rules` knowledge skills under `app/skills/`. Each skill is `user-invocable: false`, so Claude loads it via the Agent Skills progressive-disclosure mechanism only when its description triggers match (file extensions, framework names, or matching keywords in the prompt).

The skills are generated from the rule files via `python3 scripts/generate_language_rules_skills.py`, which is idempotent and rerun-safe. Other editors (Cursor, Windsurf, Cline, Roo, Augment, Codex, Copilot, Antigravity, Gemini, opencode) still receive the full per-language rule content via their own generators in `scripts/dir_rules_shared.py::build_language_rules()` — Claude is the only target where the per-language content is now skill-delivered rather than inlined.

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

**Total: 13 per-language directories × 5 files + 1 common directory × 5 files + 3 standalone files** (see README.md for canonical count). Per-language directories ship as `<lang>-rules` knowledge skills; the common directory is inlined into CLAUDE.md.

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

Common rules are injected into the project `CLAUDE.md` between a single named marker (the per-language markers from v1.x are no longer used):

```
<!-- TOOLKIT:language-rules START -->
# Language Rules

Common (language-agnostic) rules apply to every change in this project.
Language-specific rules live in `<lang>-rules` knowledge skills (e.g.
`python-rules`, `typescript-rules`) and load automatically when their
triggers match.

Detected languages: `python-rules`, `typescript-rules`.

---

... full content of app/rules/common/*.md inlined here ...
<!-- TOOLKIT:language-rules END -->
```

Re-running `install --local` is idempotent — the existing block is replaced, not duplicated. Per-language rules are not injected into `CLAUDE.md` for Claude — they are loaded contextually via their respective `<lang>-rules` knowledge skills.

### Generating language-rules skills

The `<lang>-rules` skills under `app/skills/` are produced by:

```bash
python3 scripts/generate_language_rules_skills.py            # write all
python3 scripts/generate_language_rules_skills.py --check    # dry-run, exit 1 on diff
python3 scripts/generate_language_rules_skills.py --langs python,rust  # subset
```

The generator reads `app/rules/<lang>/*.md`, strips YAML frontmatter, concatenates the categories, and writes `app/skills/<lang>-rules/SKILL.md` with frontmatter:

- `name: <lang>-rules`
- `description: ...` — language label, rule categories, and concrete trigger keywords (file extensions, framework names) so the skill activates reliably when Claude is working on that language.
- `user-invocable: false` — knowledge skill, no slash command.
- `allowed-tools: Read` — the skill body is reference content, not an action.

Rerunning the generator is idempotent. Editing rule files under `app/rules/<lang>/` and rerunning the generator is the canonical way to update a language skill.

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

| | Common rules | Per-language rules | Other skills |
|---|---|---|---|
| Source | `app/rules/common/` | `app/rules/<lang>/` | `app/skills/<name>/SKILL.md` |
| Delivery to Claude | Inlined into project `CLAUDE.md` (`--local`) | Generated as `<lang>-rules` knowledge skills, loaded contextually | Loaded contextually by description match |
| Visibility | Always in context | Loaded when triggers match (file extensions, framework names) | Loaded when triggers match |
| Scope | Language-agnostic standards (security, git, testing, perf, style) | Per-language coding-style, frameworks, patterns, security, testing | Domain skills (testing, debugging, RAG, etc.) |
| Install | `ai-toolkit install --local` | Global install (skills directory is symlinked) | Global install |
| Other editors | Inlined into editor-specific rule files | Inlined into editor-specific rule files (still full content, not skills) | N/A |

Per-language content delivered as a knowledge skill is the same Markdown that other editors receive inlined. The split exists only for Claude, where the Agent Skills progressive-disclosure mechanism keeps the system prompt small.

## Related Documentation

- [PATH: kb/reference/manifest-install.md] — module-level install granularity
- [PATH: kb/reference/extension-api.md] — injecting rules from external tools
- [PATH: kb/reference/architecture-overview.md] — overall install model
