---
title: "Distribution Model"
category: reference
service: ai-toolkit
tags: [architecture, distribution, symlinks, npm, install]
version: "1.0.0"
created: "2026-03-23"
last_updated: "2026-03-28"
description: "Reference description of how ai-toolkit is delivered and propagated on a developer machine."
---

# Distribution Model

## Summary

`ai-toolkit` uses a split delivery model:

- **npm package** for delivery to the machine,
- **filesystem symlinks and merged files** for propagation into Claude Code directories.

```text
npm install -g @softspark/ai-toolkit   → delivers toolkit files
ai-toolkit install                     → links / merges into ~/.claude/
```

## Why this model exists

The toolkit must be reusable across many projects while remaining easy to update from one place.

This model gives:
- standard installation and versioning,
- instant propagation for symlinked assets,
- predictable update flow for merged / copied assets,
- one source of truth per machine.

## Adopted Strategies

| Layer | Mechanism | Result |
|------|-----------|--------|
| Delivery | npm package | standard install / update UX |
| Agents | per-file symlinks | zero-overhead propagation |
| Skills | per-directory symlinks | zero-overhead propagation |
| Hooks | copied scripts + merged JSON | safe runtime integration |
| Docs / rules | marker injection | user content preserved |

## Trade-offs

### Positive
- easy installation
- clear update path
- global reuse across projects
- low propagation overhead

### Negative
- symlink targets depend on a valid global install location
- merged / copied assets require `ai-toolkit update` after source changes
- all projects on a machine share the same installed toolkit version

## Related Documents

- `kb/reference/global-install-model.md`
- `kb/reference/merge-friendly-install-model.md`
- `kb/reference/architecture-overview.md`
