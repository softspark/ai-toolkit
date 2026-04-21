---
title: "Enterprise Config Inheritance Guide"
category: reference
service: ai-toolkit
tags:
  - enterprise
  - config-inheritance
  - extends
  - governance
  - multi-repo
doc_type: reference
created: "2026-04-11"
last_updated: "2026-04-11"
description: "Comprehensive guide for setting up and using ai-toolkit configuration inheritance. Covers base config creation, project setup, enforcement rules, CI integration, and troubleshooting."
---

# Enterprise Config Inheritance Guide

## Overview

Configuration inheritance enables organizations to define a shared base config published as an npm package, Git URL, or local path. Individual projects extend this base via an `extends` field in `.softspark-toolkit.json`. Changes to the base propagate automatically on `ai-toolkit update --local`.

**Pattern:** Mirrors ESLint's `extends`, TypeScript's `extends`, and Prettier's shared configs.

---

## Quick Start

### 1. Create a base config (team lead)

```bash
ai-toolkit config create-base @mycompany/ai-toolkit-config
cd mycompany-ai-toolkit-config

# Edit ai-toolkit.config.json — add your org's rules, agents, enforcement
# Add rule files to rules/
# Add custom agent definitions to agents/

npm publish
```

### 2. Set up a project (developer)

```bash
cd my-project
ai-toolkit config init --extends @mycompany/ai-toolkit-config
ai-toolkit install --local
```

Or manually create `.softspark-toolkit.json`:

```json
{
  "extends": "@mycompany/ai-toolkit-config",
  "profile": "standard",
  "agents": {
    "enabled": ["frontend-specialist"]
  }
}
```

### 3. Verify

```bash
ai-toolkit config validate    # Schema + extends + enforcement
ai-toolkit config diff        # Show differences from base
ai-toolkit config check       # CI enforcement check
```

---

## Configuration Reference

### Project config (`.softspark-toolkit.json`)

| Field | Type | Description |
|-------|------|-------------|
| `extends` | string | Base config source (npm, git URL, local path) |
| `profile` | enum | `minimal`, `standard`, `strict`, `full`, `offline-slm` |
| `agents` | object | `enabled`, `disabled`, `custom` arrays |
| `rules` | object | `inject`, `remove` arrays |
| `constitution` | object | `amendments` array (article 6+ only) |
| `enforce` | object | Non-overridable constraints (base configs only) |
| `overrides` | object | Explicit overrides with justification |

### Base config (`ai-toolkit.config.json`)

Same fields as project config, plus:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Package identity (required) |
| `version` | string | Semver version (required) |

### Extends sources

| Source | Syntax | Example |
|--------|--------|---------|
| npm package | `"@scope/pkg"` | `"@mycompany/ai-toolkit-config"` |
| npm + version | `"@scope/pkg@version"` | `"@mycompany/ai-toolkit-config@^2.0.0"` |
| Git URL | `"git+https://..."` | `"git+https://github.com/myco/config.git"` |
| Local path | `"./path"` or `"../path"` | `"../shared-config"` |

---

## Merge Semantics

When a project extends a base, configs are merged with these rules:

| Type | Rule |
|------|------|
| **Dicts** | Recursive deep merge |
| **Lists** | Union (base + project, deduplicated) |
| **Scalars** | Project wins |
| **Agents** | Union enabled, project can disable (unless required) |
| **Rules** | Union inject, project can remove |
| **Constitution** | Base articles immutable, project adds only (6+) |
| **Enforce** | Base wins (cannot weaken, only strengthen) |
| **Profile** | Project can change |

### Merge order (multi-level)

```
grandparent → parent → project
```

Deepest ancestor is resolved first. Max chain depth: 5 levels.

---

## Enforcement

Base configs can define non-overridable constraints via the `enforce` block:

```json
{
  "enforce": {
    "minHookProfile": "standard",
    "requiredPlugins": ["security-pack"],
    "forbidOverride": ["constitution", "guard-destructive"],
    "requiredAgents": ["security-auditor"]
  }
}
```

| Constraint | Effect |
|------------|--------|
| `minHookProfile` | Projects cannot use a weaker hook profile |
| `requiredPlugins` | Must be installed in all projects |
| `forbidOverride` | These components cannot be overridden |
| `requiredAgents` | Must be enabled in all projects |

### Overrides

Projects can override base settings, but must declare intent:

```json
{
  "overrides": {
    "quality-check": {
      "override": true,
      "justification": "Company uses custom lint pipeline via Jenkins",
      "replacement": "skip"
    }
  }
}
```

Requirements:
- `override: true` must be explicit
- `justification` must be at least 20 characters
- Component must not be in `enforce.forbidOverride`

---

## Constitution Immutability

- **Articles I-VI** (toolkit core) are absolutely immutable
- **Base config articles** are immutable — projects cannot modify them
- Projects can **only ADD** new articles (article 7+)

```json
{
  "constitution": {
    "amendments": [
      {"article": 8, "title": "API Standards", "text": "All APIs must be RESTful."}
    ]
  }
}
```

---

## CLI Commands

### `ai-toolkit config validate [path]`

Validates `.softspark-toolkit.json` schema, resolves extends, checks enforcement.

```bash
ai-toolkit config validate
# ✓ schema valid
# ✓ extends resolved: 1 base config(s)
# ✓ no forbidden overrides
# ✓ constitution articles intact
```

### `ai-toolkit config diff [path]`

Shows differences between project config and base.

```bash
ai-toolkit config diff
# Base: @mycompany/ai-toolkit-config@2.1.0
# Profile:     strict (base) → standard (project) ⚠ OVERRIDE
# Agents:
#   + frontend-specialist     (project adds)
#   = security-auditor        (base requires, cannot disable)
```

### `ai-toolkit config init [flags]`

Create `.softspark-toolkit.json` interactively or with flags.

```bash
ai-toolkit config init                                    # interactive
ai-toolkit config init --extends @mycompany/config        # with extends
ai-toolkit config init --no-extends --profile standard    # without extends
ai-toolkit config init --force                            # overwrite existing
```

### `ai-toolkit config create-base <name> [output-dir]`

Scaffold a base config npm package.

```bash
ai-toolkit config create-base @mycompany/ai-toolkit-config
# Creates: mycompany-ai-toolkit-config/
#   package.json, ai-toolkit.config.json, rules/, agents/, README.md
```

### `ai-toolkit config check [path] [--json]`

CI enforcement check. Exit codes: 0 (pass), 1 (fail), 2 (no config).

```bash
ai-toolkit config check --json
# {"status": "pass", "code": 0, "checks": [...]}
```

GitHub Actions example:

```yaml
- name: AI Toolkit Governance Check
  run: |
    npx @softspark/ai-toolkit config check --json
    npx @softspark/ai-toolkit config validate --strict
```

---

## Lock File

`.softspark-toolkit.lock.json` pins exact resolved versions for reproducible installs.

- `install --local` → creates/updates lock file
- `update --local` → re-resolves and updates lock file
- `update --local --refresh-base` → force re-fetch ignoring cache
- Commit `.softspark-toolkit.lock.json` to git for team synchronization

```json
{
  "lockfileVersion": 1,
  "resolved": {
    "@mycompany/ai-toolkit-config": {
      "version": "2.1.0",
      "integrity": "sha256:abc123...",
      "cached": "~/.softspark/ai-toolkit/config-cache/@mycompany/ai-toolkit-config/2.1.0/"
    }
  }
}
```

---

## Offline Support

When npm/git is unavailable:

1. Checks cache (`~/.softspark/ai-toolkit/config-cache/`)
2. If cached version found → uses with warning
3. If not cached → error with instructions

```bash
# Force refresh when back online:
ai-toolkit update --local --refresh-base
```

---

## Troubleshooting

### "Cannot resolve extends"

- Check network connectivity
- Verify npm package name is correct
- For private packages, ensure `.npmrc` has auth configured
- Try `--refresh-base` to clear cache

### "Cannot disable agent — required by base config"

The base config's `enforce.requiredAgents` prevents disabling this agent.
Contact your team lead to request an exemption.

### "Cannot modify Constitution Article X"

Base constitution articles are immutable. You can only ADD new articles with higher numbers.

### "Override requires justification"

All overrides need `"override": true` and a `"justification"` field (min 20 chars).

### "Circular extends detected"

Your extends chain has a loop. Check that base configs don't reference each other cyclically. Max depth is 5 levels.

### Lock file stale

Run `ai-toolkit update --local` to re-resolve and update the lock file.
