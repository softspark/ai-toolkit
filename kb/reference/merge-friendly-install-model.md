---
title: "Merge-Friendly Install Model"
category: reference
service: ai-toolkit
tags: [install, merge, hooks, injection, symlinks]
version: "1.0.0"
created: "2026-03-27"
last_updated: "2026-03-28"
description: "Reference description of how ai-toolkit preserves user content while installing toolkit components."
---

# Merge-Friendly Install Model

## Summary

`ai-toolkit` preserves user content while injecting toolkit behavior.

Instead of replacing entire directories or files, the installer uses merge-friendly strategies tailored to each component type.

## Component Strategies

| Component | Strategy | User content behavior |
|-----------|----------|-----------------------|
| `agents/*.md` | per-file symlinks | preserved; user file wins on name conflict |
| `skills/*/` | per-directory symlinks | preserved; user directory wins on name conflict |
| `settings.json` hooks | JSON merge with `_source: ai-toolkit` | preserved; toolkit entries removable |
| `constitution.md` | marker injection | preserved outside markers |
| `ARCHITECTURE.md` | marker injection | preserved outside markers |
| `CLAUDE.md` | marker injection | preserved outside markers |

## Why this model exists

This avoids two common failure modes:
1. users losing custom agents / skills due to whole-directory symlinks,
2. users losing custom hooks or docs due to full-file replacement.

## Operational Consequences

### Positive
- reversible installs and uninstalls,
- backward-compatible upgrades,
- safe coexistence of toolkit and user customizations,
- idempotent update flow.

### Trade-offs
- merged / copied artifacts require `ai-toolkit update` to refresh,
- hook merge logic depends on valid JSON and the `_source` tagging convention,
- install behavior is more complex than a simple copy or symlink-only model.

## Local Project Setup

Project-local setup uses the same preservation approach for files that should remain repository-specific, especially `CLAUDE.md` and `.claude/settings.local.json`.

## Related Documents

- `kb/reference/distribution-model.md`
- `kb/reference/global-install-model.md`
- `kb/reference/hooks-catalog.md`
