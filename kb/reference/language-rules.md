---
title: "Language Rules System"
category: reference
service: ai-toolkit
tags: [rules, languages, coding-style, testing, patterns, security]
version: "2.3.0"
created: "2026-04-07"
last_updated: "2026-09-24"
description: "Reference for the language-specific rules system: 13 per-language rule sets shipped as knowledge skills, plus common rules installed as Claude Code path-scoped user-level rules, with project copies only for what the global install lacks."
---

# Language Rules System

## Overview

ai-toolkit ships rule content for 13 languages/platforms plus a language-agnostic common set. Source files live under `app/rules/` and are split into two delivery channels:

- **Common rules** (`app/rules/common/*.md`): the global install (`ai-toolkit install` / `update`) writes full content to `~/.claude/rules/ai-toolkit-*.md` with Claude Code `paths` frontmatter; user-level rules load in every project and `paths` scoping works there. `install --local` writes a project copy only of a rule the global install does not provide. The project's `.claude/CLAUDE.md` keeps only a compact `<!-- TOOLKIT:language-rules START -->` index. This follows Claude Code's current guidance to keep `CLAUDE.md` concise and move larger instruction sets into scoped rules.
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

**Total: 13 per-language directories × 5 files + 1 common directory × 6 files (5 in every profile + `git-team` in `strict`) + 3 standalone files** (see README.md for canonical count). Per-language directories ship as `<lang>-rules` knowledge skills; the common directory is installed as Claude Code `.claude/rules/ai-toolkit-*.md` files.

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

The common security rules distinguish safe, actionable failure messages from
private diagnostics. Common testing rules cover API error contracts and prohibit
overlapping runners that reset a shared database. The `api-patterns` skill carries
the focused error-contract guidance; the `review` checklist checks the same
failure boundaries. These are content rules, not new hooks or runtime permissions.

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

Common rules are installed as path-scoped Claude Code user-level rule files by the global install:

```
~/.claude/rules/
├── ai-toolkit-coding-style.md
├── ai-toolkit-git-team.md        # --profile strict only
├── ai-toolkit-git-workflow.md
├── ai-toolkit-performance.md
├── ai-toolkit-security.md
└── ai-toolkit-testing.md
```

They are not copied into projects. Claude Code loads `~/.claude/rules/` in every project and also loads `.claude/rules/` from parent directories, so a project copy loaded every rule twice, and once more for each registered parent directory (a workspace folder installed with `--local` above its projects). `install --local` writes a project copy only of a rule the global install does not provide, decided by the files actually present in `~/.claude/rules/`:

| Global install | Project | Project `.claude/rules/ai-toolkit-*.md` |
|---|---|---|
| present, `standard` | `standard` | none |
| present, `standard` | `strict` | `ai-toolkit-git-team.md` only |
| present, `strict` | any | none |
| absent | any | every rule the project profile ships, as before |

Managed project copies the global install now provides are removed on the next `install --local` or `update`, so existing projects converge. User-authored files in `.claude/rules/` are never touched.

A source rule may also carry `profiles:` (same block-list form). `git-team` declares `profiles: ["strict"]`: branching, pull-request, and review conventions for teams, kept out of `standard` so a solo maintainer who releases straight to `main` is not told to open PRs against themselves. The global install filters by its own profile, a project install by the project's; rerunning either with a different profile adds or removes the managed file. Only the Claude Code installs honour `profiles`; the Claude app export, `compile-slm`, and editor `lang-common` bundles still receive every common rule (see `DECISIONS.md`, 2026-09-04).

Each file's `paths` frontmatter is copied from the source rule in `app/rules/common/<category>.md`. A source rule without a `paths` block is always-on:

```yaml
---
paths:
  - "**/*"
---
```

A source rule with a `paths` block is path-scoped, so Claude Code loads it only when a matching file is touched. As of v4.32.0 `testing` (`**/*.test.*`, `**/*.spec.*`, `**/test_*`, `**/*_test.*`, `**/tests/**`) and `performance` (source-file extensions plus `**/*.sql`) are scoped; `coding-style`, `git-workflow`, and `security` stay always-on because they carry prohibitions that must hold in every session. To change a scope, edit the source frontmatter; `validate.py` rejects inline lists and unquoted globs because the installer reads only the block form:

```yaml
---
language: common
category: testing
version: "1.1.0"
paths:
  - "**/tests/**"
---
```

The project `CLAUDE.md` receives only a compact index between a single named marker (the per-language markers from v1.x are no longer used):

```
<!-- TOOLKIT:language-rules START -->
# Language Rules

Common ai-toolkit rules load as Claude Code rules with `paths`
frontmatter instead of expanding this CLAUDE.md: from
`~/.claude/rules/` when the global install provides them, from this
project's `.claude/rules/` only for a rule it does not. Always-on
rules load in every session; path-scoped rules load only when a
matching file is touched.

Always-on: `~/.claude/rules/ai-toolkit-coding-style.md`, ...

Path-scoped: `~/.claude/rules/ai-toolkit-performance.md`, ...

Language-specific rules live in `<lang>-rules` knowledge skills (e.g.
`python-rules`, `typescript-rules`) and load automatically when their
triggers match.

Detected languages: `python-rules`, `typescript-rules`.
<!-- TOOLKIT:language-rules END -->
```

Re-running `install --local` is idempotent — the existing block is replaced, not duplicated, and only managed `.claude/rules/ai-toolkit-*.md` files are written or removed. User-authored `.claude/rules/*.md` files are preserved. Per-language rules are not injected into `CLAUDE.md` for Claude — they are loaded contextually via their respective `<lang>-rules` knowledge skills.

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
| `rules-common` | Common coding rules (6 files: 5 in every profile, `git-team` in `strict` only), included in `standard` profile |
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
| Delivery to Claude | Path-scoped user-level `~/.claude/rules/ai-toolkit-*.md` files (global install), project copies only for rules the global install lacks, + compact `CLAUDE.md` index | Generated as `<lang>-rules` knowledge skills, loaded contextually | Loaded contextually by description match |
| Visibility | Always-on (`coding-style`, `git-workflow`, `security`) or loaded when a matching file is touched (`testing`, `performance`) | Loaded when triggers match (file extensions, framework names) | Loaded when triggers match |
| Scope | Language-agnostic standards (security, git, testing, perf, style) | Per-language coding-style, frameworks, patterns, security, testing | Domain skills (testing, debugging, RAG, etc.) |
| Install | Global install; `ai-toolkit install --local` only fills gaps | Global install (skills directory is symlinked); skills for languages no registered project uses are turned off via `skillOverrides` (`--language-skills detected`, the default) unless `--language-skills all` was chosen | Global install |
| Other editors | Inlined into editor-specific rule files | Inlined into editor-specific rule files (still full content, not skills) | N/A |

Per-language content delivered as a knowledge skill is the same Markdown that other editors receive inlined. The split exists only for Claude, where the Agent Skills progressive-disclosure mechanism keeps the system prompt small.

## Related Documentation

- [PATH: kb/reference/manifest-install.md] — module-level install granularity
- [PATH: kb/reference/extension-api.md] — injecting rules from external tools
- [PATH: kb/reference/architecture-overview.md] — overall install model
