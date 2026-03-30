---
title: "Anti-Pattern Registry Format"
category: reference
service: ai-toolkit
description: "Structured JSON format for anti-patterns with severity, auto-fixability, and conflict rules. Used by domain skills with reasoning engines."
tags: [anti-patterns, skills, reasoning-engine, format]
created: 2026-04-01
last_updated: 2026-04-01
---

# Anti-Pattern Registry Format

## Overview

The anti-pattern registry is a structured JSON format used by domain skills that
employ reasoning engines. It provides a machine-readable catalog of known
anti-patterns with severity levels, auto-fix capabilities, and conflict rules.

## When to Use

Use structured JSON registries (this format) when:

- The skill catalogs **more than 50 items** across **more than 3 compatibility
  dimensions** (e.g., domain, severity, language, framework).
- Items have relationships (conflicts, prerequisites, alternatives) that must be
  queryable at runtime.
- The reasoning engine (`search.py`) needs to filter, score, and exclude
  conflicting entries programmatically.

Use Markdown tables when:

- Fewer than 50 items with 3 or fewer dimensions.
- No inter-item relationships.
- Human readability is the only consumer.

## JSON Schema

Each entry in the registry follows this schema:

```json
{
  "id": "string (required)",
  "name": "string (required)",
  "domain": "string (required)",
  "description": "string (required)",
  "pattern": "string (optional)",
  "severity": "string (required)",
  "auto_fixable": "boolean (required)",
  "conflicts_with": ["string (optional)"],
  "remediation": "string (required)",
  "tags": ["string (optional)"]
}
```

### Field Definitions

#### `id` (required)

Unique identifier in kebab-case. Must be globally unique across all registry
files within the same assets directory.

```
"id": "n-plus-one-query"
```

#### `name` (required)

Human-readable display name. Used in reports and dashboards.

```
"name": "N+1 Query Problem"
```

#### `domain` (required)

The skill domain this anti-pattern belongs to. Used for filtering when a
reasoning engine serves multiple domains.

Valid domains include: `security`, `database`, `api`, `architecture`,
`performance`, `testing`, `general`. Skills may define additional domains as
needed.

```
"domain": "database"
```

#### `description` (required)

Clear explanation of what this anti-pattern is and why it is problematic. Should
be actionable -- a developer reading this should understand the risk.

```
"description": "Executing one query per item in a loop instead of a single batch query. Causes O(n) database round-trips where O(1) is possible."
```

#### `pattern` (optional)

A regex pattern for automated detection in source code. When present, tooling
can scan codebases for occurrences. Omit if the anti-pattern is architectural
or cannot be detected via regex.

```
"pattern": "for\\s+.*\\sin\\s+.*:\\s*\\n\\s+.*\\.objects\\.get"
```

#### `severity` (required)

Impact level. Must be one of:

| Value | Meaning |
|-------|---------|
| `critical` | Causes security vulnerabilities, data loss, or production outages. Must fix before merge. |
| `important` | Degrades performance, maintainability, or reliability significantly. Should fix in current sprint. |
| `suggestion` | Improvement opportunity. Fix when convenient or during refactoring. |

```
"severity": "important"
```

#### `auto_fixable` (required)

Boolean indicating whether tooling can automatically remediate this
anti-pattern. When `true`, the reasoning engine or a companion script can
generate a fix.

```
"auto_fixable": true
```

#### `conflicts_with` (optional)

List of anti-pattern IDs that conflict with this entry. The reasoning engine
uses this for mutual exclusion -- if one pattern is selected/detected, the
conflicting ones are filtered out of results.

This prevents contradictory advice (e.g., "use eager loading" and "use lazy
loading" simultaneously).

```
"conflicts_with": ["eager-load-everything"]
```

#### `remediation` (required)

Concrete instructions for fixing the anti-pattern. Should include a code
example or reference to a known-good pattern when possible.

```
"remediation": "Replace loop queries with select_related() or prefetch_related() for Django, or use JOIN/eager loading in your ORM."
```

#### `tags` (optional)

Freeform tags for cross-cutting search. Useful for filtering by technology,
language, or concern that does not map to a single domain.

```
"tags": ["orm", "django", "sqlalchemy", "performance"]
```

## Complete Example

```json
[
  {
    "id": "n-plus-one-query",
    "name": "N+1 Query Problem",
    "domain": "database",
    "description": "Executing one query per item in a loop instead of a single batch query. Causes O(n) database round-trips where O(1) is possible.",
    "pattern": "for\\s+.*\\sin\\s+.*:\\s*\\n\\s+.*\\.objects\\.get",
    "severity": "important",
    "auto_fixable": false,
    "conflicts_with": [],
    "remediation": "Replace loop queries with select_related() or prefetch_related() for Django, or use JOIN/eager loading in your ORM.",
    "tags": ["orm", "django", "sqlalchemy", "performance"]
  },
  {
    "id": "hardcoded-secrets",
    "name": "Hardcoded Secrets",
    "domain": "security",
    "description": "API keys, passwords, or tokens embedded directly in source code. Exposed in version control history even after removal.",
    "pattern": "(api_key|secret|password|token)\\s*=\\s*[\"'][^\"']+[\"']",
    "severity": "critical",
    "auto_fixable": true,
    "conflicts_with": [],
    "remediation": "Move secrets to environment variables or a secrets manager (AWS SSM, Vault, dotenv for local). Reference via os.environ or settings module.",
    "tags": ["secrets", "env", "vault", "ci"]
  }
]
```

## File Organization

Registry files live in the `assets/` directory alongside the reasoning engine:

```
templates/reasoning-engine/
  search.py           # Reasoning engine
  assets/
    example.json      # Template/example entries
    security.json     # Security anti-patterns
    database.json     # Database anti-patterns
    api.json          # API anti-patterns
```

Each file is a JSON array. The reasoning engine loads and merges all `*.json`
files from `assets/` at startup. Keep files organized by domain to avoid merge
conflicts and improve discoverability.

## Integration with Reasoning Engine

The `search.py` reasoning engine uses registry entries as follows:

1. **Load**: All JSON files in `assets/` are loaded and merged into a flat list.
2. **Match**: User query is tokenized and scored against all fields.
3. **Filter**: `conflicts_with` entries are excluded based on already-selected
   items via `filter_anti_patterns()`.
4. **Return**: Top results are returned as JSON to stdout.

Skills that use this pattern should document the `--domain` flag to scope
searches to their specific domain.
