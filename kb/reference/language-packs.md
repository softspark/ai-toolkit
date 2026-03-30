---
title: "AI Toolkit - Language Plugin Packs"
category: reference
service: ai-toolkit
tags: [plugins, languages, rust, java, csharp, kotlin, swift, ruby]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-03-29"
description: "6 language-specific plugin packs providing knowledge skills for Rust, Java, C#, Kotlin, Swift, and Ruby."
---

# Language Plugin Packs

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
