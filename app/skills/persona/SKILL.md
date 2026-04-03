---
name: persona
description: "Switch engineering persona at runtime: backend-lead, frontend-lead, devops-eng, junior-dev"
effort: low
user-invocable: true
argument-hint: "[backend-lead | frontend-lead | devops-eng | junior-dev | --list | --clear]"
allowed-tools: Read, Glob
---

# /persona - Runtime Persona Switching

$ARGUMENTS

Switch your working persona without re-installing. Personas adjust communication style, preferred skills, and code review priorities for the current session.

## Usage

```
/persona backend-lead     # Activate backend lead persona
/persona frontend-lead    # Activate frontend lead persona
/persona devops-eng       # Activate DevOps engineer persona
/persona junior-dev       # Activate junior developer persona
/persona --list           # Show available personas
/persona --clear          # Reset to default (no persona)
```

## Available Personas

| Persona | Focus | Preferred Skills |
|---------|-------|-----------------|
| `backend-lead` | System design, scalability, data integrity, API stability | `/workflow backend-feature`, `/tdd` |
| `frontend-lead` | Component architecture, a11y, state management, Core Web Vitals | `/design-an-interface`, `/review` |
| `devops-eng` | IaC, CI/CD, blast radius, rollback safety, observability | `/workflow infrastructure-change`, `/deploy` |
| `junior-dev` | Step-by-step explanations, learning resources, small PRs | `/explain`, `/explore`, `/debug` |

## Steps

1. Parse `$ARGUMENTS`
2. If `--list`: read all `app/personas/*.md` files via Glob, display table with name and first-line summary
3. If `--clear`: respond with "Persona cleared. Using default behavior for the rest of this session."
4. If persona name given:
   a. Read the persona file from `app/personas/{name}.md` (relative to toolkit root)
   b. If file not found, try the installed location: `~/.claude/skills/persona/../../../app/personas/{name}.md`
   c. Display the persona content to Claude
   d. State: "**Persona active: {name}**. I will follow these guidelines for the rest of this session."
5. If no argument: show usage and available personas

## How It Works

Unlike `--persona` at install time (which injects into CLAUDE.md permanently), `/persona` applies for the **current session only**. The persona file content is loaded into the conversation context and Claude follows it until the session ends or `/persona --clear` is called.

## Rules

- This skill is READ-ONLY — it never writes files
- Persona stays active for the current session only
- Only one persona active at a time — switching replaces the previous one
- Valid personas are defined by `.md` files in `app/personas/`
