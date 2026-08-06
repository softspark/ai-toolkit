---
title: "AI Toolkit - Skill Templates"
category: reference
service: ai-toolkit
tags: [templates, scaffolding, create, skills]
version: "1.1.0"
created: "2026-03-29"
last_updated: "2026-08-06"
description: "5 skill templates for scaffolding new skills: linter, reviewer, generator, workflow, knowledge. Includes the ${CLAUDE_SKILL_DIR} rule for shipping executable scripts."
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
3. If the skill ships an executable, invoke it **only** through
   `${CLAUDE_SKILL_DIR}` — see [Shipping a script](#shipping-a-script)
4. Run `ai-toolkit validate` to verify

## Shipping a script

Put executables in `app/skills/{name}/scripts/` and document them as:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/{name}.py [args]
```

That is the only path that resolves once a skill is installed and symlinked into
`~/.claude/skills/`. Three other spellings look correct in the repo and fail for
every user:

| Spelling | Resolves against | Result after install |
|----------|------------------|----------------------|
| `scripts/foo.py` | the user's working directory | not found |
| `app/skills/{name}/scripts/foo.py` | a repo the user does not have | not found |
| `$(dirname "$0")/scripts/foo.py` | the shell's directory | not found |

Nine skills shipped with one of these before `validate.py` began failing the
build on it. The check also enforces that the interpreter matches the file — a
`.py` run through `bash` is an error, and bare `python` a warning, because it is
missing or Python 2 on many systems.

The frontmatter `scripts:` list stays relative. It declares which files the skill
owns; it does not run them.

**Give the script `--help`.** A script that treats `--help` as a positional
argument answers with a traceback, and a stdin filter with no input must return
an error rather than blocking forever — the post-release SOP probes every shipped
script exactly this way.
