---
title: "No Hardcoded Counts in Secondary Docs"
category: best-practices
service: ai-toolkit
tags: [counts, documentation, maintenance, skills, agents, hooks, tests]
created: "2026-04-07"
last_updated: "2026-04-07"
description: "Counts (skills, agents, hooks, tests) should only appear in README.md and manifest.json. All other docs must NOT contain hardcoded numbers to avoid drift."
---

# No Hardcoded Counts in Secondary Docs

## Rule

Hardcoded counts (skills, agents, hooks, tests, plugins) are allowed ONLY in:
- **README.md** — badges, "What You Get" table, comparison table
- **manifest.json** — module descriptions
- **package.json** — description field

All other files (CLAUDE.md, ARCHITECTURE.md, KB docs, plugin.json, llms.txt, AGENTS.md, copilot-instructions, rules, GEMINI.md) must NOT contain hardcoded counts like "90 skills" or "44 agents".

## Why

Every time a skill, agent, or hook is added/removed, dozens of files need updating. This causes constant drift and stale counts that erode trust. Consolidating to 2-3 files makes maintenance tractable.

## How to Apply

- In secondary docs, use relative language: "all agents", "the full skill set", "available hooks"
- If a doc MUST reference scale, use: "see README.md for current counts"
- `validate.py` checks counts only in README.md badges — that's sufficient
- When adding skills/agents/hooks, update ONLY: README.md badges + manifest.json descriptions

## Anti-Pattern

```markdown
# BAD — hardcoded count in ARCHITECTURE.md
Shared AI development toolkit — 90 skills, 44 agents

# GOOD — no count
Shared AI development toolkit with multi-platform support
```
