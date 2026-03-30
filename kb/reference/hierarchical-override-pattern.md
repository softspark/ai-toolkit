---
title: "Hierarchical Override Pattern"
category: reference
service: ai-toolkit
description: "Convention for SKILL.md + reference/*.md relationship with explicit override semantics."
tags: [skills, architecture, patterns, override]
created: 2026-04-01
last_updated: 2026-04-01
---

# Hierarchical Override Pattern

## Overview

Skills in ai-toolkit follow a two-level content hierarchy: a master `SKILL.md`
file that defines global defaults and the main instruction flow, and optional
`reference/*.md` files that extend and specialize without contradicting the
master.

This document defines the conventions, override semantics, and splitting
criteria for this pattern.

## Architecture

```
app/skills/<skill-name>/
  SKILL.md                    # Master: global defaults, main flow
  reference/
    domain-a.md               # Extension: adds detail for domain A
    domain-b.md               # Extension: adds detail for domain B
    visual-companion.md       # Extension: visual/UI-specific guidance
```

## Roles

### SKILL.md (Master)

The `SKILL.md` file is the single source of truth for a skill. It defines:

- **Purpose and scope** of the skill.
- **Global defaults** that apply unless overridden by context.
- **Main instruction flow** -- the step-by-step process the agent follows.
- **Cross-references** to reference files (explicit `see reference/X.md` links).
- **Invocation metadata** (frontmatter: `disable-model-invocation`, etc.).

The master file is always loaded. It is the entry point for the agent.

### reference/*.md (Extensions)

Reference files extend the master by providing:

- **Domain-specific detail** that would bloat the master.
- **Lookup tables** (e.g., language-specific patterns, framework configs).
- **Specialized workflows** that apply in narrow contexts.
- **Examples and templates** too long for inline inclusion.

Reference files are loaded on demand -- only when the agent determines the
context requires them, or when the master explicitly references them.

## Override Semantics

The relationship between master and reference files follows strict rules:

### Rule 1: Reference files ADD, never REPLACE

A reference file must not contradict the master. It adds specificity within the
boundaries the master defines.

```
SKILL.md says:     "Use type hints on all public APIs"
reference/go.md:   "Use Go's built-in type system; exported functions are public APIs"
```

This is valid -- it specializes the general rule for Go without contradicting it.

```
SKILL.md says:     "Always validate input at the API boundary"
reference/perf.md: "Skip validation for internal microservice calls"
```

This is INVALID -- it contradicts the master. If an exception is needed, it must
be documented in the master itself with explicit conditions.

### Rule 2: Master defines the contract, references fill in the details

Think of it as interface vs. implementation:

| Layer | Defines | Example |
|-------|---------|---------|
| Master | "Validate all inputs" | General principle |
| Reference | "In Python, use Pydantic v2 BaseModel with Field validators" | Concrete implementation |

### Rule 3: Conflicts are resolved by the master

If a reference file and the master appear to conflict, the master wins. This
should be treated as a bug in the reference file and corrected.

### Rule 4: References may cross-reference each other

Reference files can link to other reference files, but the dependency graph
should remain shallow (max 2 levels deep). Deep chains make maintenance
difficult.

## When to Split

Split content from `SKILL.md` into `reference/*.md` when:

| Criterion | Threshold |
|-----------|-----------|
| **Total line count** | Master exceeds 300 lines |
| **Distinct sub-domains** | Content covers 3+ distinct domains (languages, frameworks, concerns) |
| **Lookup tables** | Tables with 20+ rows that serve as reference material |
| **Reuse potential** | Content could be useful to multiple skills |
| **Update frequency** | A section changes much more frequently than the rest |

Do NOT split when:

- The master is under 300 lines and covers a single domain.
- The "reference" content is only a few paragraphs.
- Splitting would force the agent to always load multiple files for basic
  operation.

## Examples from Existing Skills

### write-a-prd

```
app/skills/write-a-prd/
  SKILL.md                          # Main PRD creation flow
  reference/visual-companion.md     # Visual/UI-specific PRD guidance
```

- `SKILL.md` defines the interview-driven PRD process, output format, and
  quality criteria.
- `reference/visual-companion.md` extends with guidance for PRDs that involve
  visual interfaces -- design system references, wireframe conventions,
  accessibility requirements.
- The master references it: `"For visual products, see reference/visual-companion.md"`

### clean-code

```
app/skills/clean-code/
  SKILL.md                    # Universal clean code principles
  reference/python.md         # Python-specific patterns
  reference/typescript.md     # TypeScript-specific patterns
  reference/php.md            # PHP-specific patterns
  reference/go.md             # Go-specific patterns
  reference/dart.md           # Dart/Flutter-specific patterns
```

- `SKILL.md` defines language-agnostic principles (naming, SRP, DRY).
- Each `reference/<lang>.md` provides language-specific idioms, linting config,
  and type system patterns.
- The master links to them: `"For Python patterns, see reference/python.md"`

### testing-patterns

```
app/skills/testing-patterns/
  SKILL.md                             # Universal testing principles (AAA, org, targets)
  reference/python-pytest.md           # pytest specifics
  reference/typescript-vitest.md       # Vitest/Jest specifics
  reference/php-phpunit.md             # PHPUnit specifics
  reference/go-testing.md              # Go testing specifics
  reference/flutter-testing.md         # Flutter/Dart testing specifics
```

Same pattern: master defines the universal structure, references specialize per
ecosystem.

## Authoring Guidelines

1. **Master first.** Always write the `SKILL.md` completely before splitting.
   Premature splitting leads to fragmented, hard-to-follow skills.

2. **Explicit cross-references.** Every reference file must be linked from the
   master with a clear sentence explaining when to consult it.

3. **Self-contained references.** A reference file should be useful on its own
   for someone who has already read the master. Do not assume the reader will
   re-read the master alongside it.

4. **Consistent frontmatter.** Reference files do not need frontmatter unless
   they are independently searchable. If they are, use the same YAML format as
   the master.

5. **Naming convention.** Use kebab-case filenames that describe the domain:
   `python.md`, `visual-companion.md`, `database-patterns.md`. Avoid generic
   names like `extra.md` or `notes.md`.

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Reference contradicts master | Agent gets conflicting instructions | Move exception to master with conditions |
| Master too thin | Agent lacks context without loading all references | Keep core flow in master, only split detail |
| Circular references | Infinite loading, confused agent | Keep dependency graph acyclic and shallow |
| Unnamed splits | `misc.md`, `extra.md` -- no signal about content | Use descriptive domain-based names |
| Over-splitting | 10+ reference files for a simple skill | Consolidate until the 300-line / 3-domain threshold justifies splitting |
