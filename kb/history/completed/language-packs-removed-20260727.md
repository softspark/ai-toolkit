---
title: "AI Toolkit - Language Plugin Packs (removed)"
category: planning
service: ai-toolkit
tags: [plugins, languages, rust, java, csharp, kotlin, swift, ruby, removed]
doc_type: postmortem
status: completed
version: "1.1.0"
created: "2026-03-29"
last_updated: "2026-07-27"
description: "REMOVED 2026-07-27 in v4.20.0. The six language packs wrapped skills that already ship in core, so installing one put zero files on disk. The skills themselves (rust-patterns, java-patterns, csharp-patterns, kotlin-patterns, swift-patterns, ruby-patterns) were never in the packs and are unaffected."
---

# Language Plugin Packs — REMOVED

> **Removed 2026-07-27 in v4.20.0. Nothing was lost.**
>
> The six packs described below each declared exactly one skill —
> `rust-patterns`, `java-patterns`, `csharp-patterns`, `kotlin-patterns`,
> `swift-patterns`, `ruby-patterns` — and every one of those skills lives in
> `app/skills/`, is part of the core install, and **still does**. The packs
> owned no files of their own beyond a `README.md`.
>
> Because `ai-toolkit install` links every core skill, installing a language
> pack put **zero** files on disk. Measured on both runtimes and all three
> profiles: `(0 file items)` every time.
>
> **If you used one of these packs, you lose nothing.** The skill it named is
> already installed and triggers on the same file types it always did — open a
> `.rs` file and `rust-patterns` still loads.
>
> Full measurement and the rule that now prevents a repeat:
> [`no-op-plugin-packs-removed-20260727.md`](no-op-plugin-packs-removed-20260727.md).
>
> The document below is preserved as written on 2026-03-29.

---

## Overview

Language packs are domain-scoped plugin packs that provide knowledge skills for specific programming languages. Each pack contains a single knowledge skill with idiomatic patterns, error handling, testing conventions, common frameworks, and performance tips.

## Available Packs

| Pack | Skill | Language | Key Topics |
|------|-------|----------|------------|
| `rust-pack` | `rust-patterns` | Rust | Ownership, borrowing, Cargo, tokio, serde |
| `java-pack` | `java-patterns` | Java | Records, sealed classes, Spring Boot, JUnit 5 |
| `csharp-pack` | `csharp-patterns` | C# / .NET | Nullable refs, async/await, ASP.NET Core, EF Core |
| `kotlin-pack` | `kotlin-patterns` | Kotlin | Coroutines, DSLs, sealed classes, Ktor, MockK |
| `swift-pack` | `swift-patterns` | Swift / iOS | Protocol-oriented, SwiftUI, async/await, SPM |
| `ruby-pack` | `ruby-patterns` | Ruby | Blocks, Rails conventions, RSpec, ActiveRecord |

## Skill Content Sections

Each language skill follows a consistent structure:

1. **Project Structure** — standard directory layout and build tool configuration
2. **Idioms / Code Style** — language-specific patterns and conventions
3. **Error Handling** — error types, patterns, and best practices
4. **Testing Patterns** — test frameworks, assertion libraries, mocking
5. **Common Libraries / Frameworks** — ecosystem essentials
6. **Performance Tips** — optimization techniques and profiling
7. **Build / Package Management** — dependency management and CI

## How Knowledge Skills Work

These skills have `user-invocable: false` in their frontmatter, meaning they are NOT slash commands. Instead, Claude loads them contextually when the conversation topic matches the skill's description trigger.

For example, when a user asks "How do I handle errors in Rust?", Claude automatically loads `rust-patterns` to provide idiomatic Rust error handling guidance.

## Requesting New Language Packs

File an issue with the `language-pack` label. Include:
- Language name
- Key topics to cover
- Popular frameworks/libraries to include
