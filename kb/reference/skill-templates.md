---
title: "AI Toolkit - Skill Templates"
category: reference
service: ai-toolkit
tags: [templates, scaffolding, create, skills]
version: "1.0.0"
created: "2026-03-29"
last_updated: "2026-04-01"
description: "5 skill templates for scaffolding new skills: linter, reviewer, generator, workflow, knowledge."
---

# Skill Templates

## Overview

`ai-toolkit create skill` scaffolds new skills from predefined templates. Each template produces a valid SKILL.md that passes `validate.py`.

## Usage

```bash
ai-toolkit create skill my-skill --template=linter
ai-toolkit create skill my-checker --template=reviewer --description="Review security headers"
```

## Available Templates

| Template | Skill Type | Key Frontmatter | Use When |
|----------|-----------|-----------------|----------|
| `linter` | Task | `disable-model-invocation: true`, `allowed-tools: Bash, Read` | Automated checks, validators |
| `reviewer` | Hybrid | `context: fork`, `agent: code-reviewer` | Code review with agent delegation |
| `generator` | Task | `allowed-tools: Read, Write, Bash, Glob` | File generation, scaffolding |
| `workflow` | Hybrid | `context: fork`, `agent: orchestrator`, `model: opus` | Multi-phase orchestration |
| `knowledge` | Knowledge | `user-invocable: false` | Auto-loaded domain patterns |

## Template Variables

| Variable | Replaced With | Example |
|----------|--------------|---------|
| `{{NAME}}` | Skill name argument | `my-linter` |
| `{{DESCRIPTION}}` | `--description` value or default | `Provides my-linter functionality` |

## Template Location

Templates are stored in `app/templates/skill/{type}/SKILL.md.template`.

## After Scaffolding

1. Edit the generated `app/skills/{name}/SKILL.md`
2. Add `reference/` or `templates/` subdirectories if needed
3. Run `ai-toolkit validate` to verify
