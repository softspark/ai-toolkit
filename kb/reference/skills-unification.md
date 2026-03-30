---
title: "Skills Unification Model"
category: reference
service: ai-toolkit
tags: [skills, commands, architecture, classification]
version: "1.0.0"
created: "2026-03-25"
last_updated: "2026-03-28"
description: "Reference explanation of why ai-toolkit standardizes on the Agent Skills format for slash-command behavior."
---

# Skills Unification Model

## Summary

`ai-toolkit` standardizes on the Agent Skills directory format for all reusable slash-command behavior.

The toolkit no longer treats commands and skills as separate implementation models. Instead, it uses one consistent format:

- task skills,
- hybrid skills,
- knowledge skills.

## Why this model is used

The Agent Skills format supports capabilities that plain command markdown files do not:
- richer frontmatter,
- progressive disclosure,
- bundled scripts,
- templates and reference files,
- cross-tool compatibility.

## Classification

| Type | Frontmatter signal | Purpose |
|------|--------------------|---------|
| Task skill | `disable-model-invocation: true` | explicit user-triggered actions |
| Hybrid skill | default invocation | user-invocable + agent-usable workflows |
| Knowledge skill | `user-invocable: false` | auto-loaded patterns and conventions |

## Consequences

### Positive
- one mental model for reusable behavior,
- easier validation,
- simpler install logic,
- better alignment with Claude Code ecosystem conventions.

### Trade-offs
- more directories than a flat commands model,
- stronger need for naming and frontmatter conventions,
- documentation and generators must stay synchronized with counts.

## Related Documents

- `kb/reference/skills-catalog.md`
- `kb/reference/architecture-overview.md`
