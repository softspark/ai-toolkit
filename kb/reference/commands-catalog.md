---
title: "AI Toolkit - Commands Catalog (DEPRECATED)"
category: reference
service: ai-toolkit
tags: [commands, deprecated]
version: "1.0.0"
created: "2026-03-23"
last_updated: "2026-03-28"
description: "DEPRECATED: All slash commands are implemented as skills. See skills-catalog.md for the current catalog."
---

# Commands Catalog (DEPRECATED)

All slash commands have been migrated to skills.

See **[Skills Catalog](skills-catalog.md)** for the complete list of skills, including:
- **28 Task Skills** — formerly standalone commands and creator workflows (e.g., `/commit`, `/test`, `/deploy`, `/hook-creator`, `/plugin-creator`)
- **30 Hybrid Skills** — slash commands that also provide agent knowledge (e.g., `/review`, `/debug`, `/plan`, `/tdd`, `/write-a-prd`, `/council`, `/introspect`)
- **32 Knowledge Skills** — domain patterns auto-loaded by agents (e.g., `brand-voice`, `clean-code`, `testing-patterns`)

Slash command syntax (`/command`) continues to work. The underlying implementation moved from `app/commands/` to `app/skills/`.
