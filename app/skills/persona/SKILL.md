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

- **MUST** remain read-only — this skill never writes files, only loads persona content into the session
- **MUST** state the active persona explicitly at switch time so the user knows which lens is in effect
- **NEVER** keep the previous persona active after a switch — replace, do not stack
- **NEVER** mix personas in a single response — each persona has internally consistent priorities that clash if blended
- **CRITICAL**: personas apply for the **current session only**. `/persona --clear` resets; a new session starts from default.
- **MANDATORY**: valid personas are defined by `.md` files in `app/personas/` — do not invent or describe a persona that has no file

## Gotchas

- The persona file lives in `app/personas/<name>.md` relative to the toolkit root. When the toolkit is globally installed, that root is at `~/.claude/skills/persona/../../../app/personas/` — fallback paths matter.
- Switching personas mid-task can produce a jarring tone shift in the user's output. Announce the switch, briefly restate the current task in the new persona, then continue.
- `/persona --clear` only resets the **in-session** persona. If the user ran `ai-toolkit install --persona <name>` at install time, that persona is injected into CLAUDE.md and survives session clears. Clearing requires editing CLAUDE.md directly.
- Personas are **style overlays**, not skill enablers. Activating `devops-eng` does not give access to `/deploy` if it was not already installed; it only biases which skills the agent reaches for first.
- A persona that contradicts project-level CLAUDE.md rules (e.g. `junior-dev` asking for explanations in a project that says "no pleasantries") creates a tone conflict. Project rules win; adjust the persona or the project rules, not both silently.

## When NOT to Use

- For **permanent** persona injection at install time — use `ai-toolkit install --persona <name>` (project or global)
- For multi-agent parallel work with different specialists — use `/orchestrate` or `/teams`
- For a specific language or framework context (not a general engineering stance) — use the language-pattern skills (`/typescript-patterns`, etc.)
- To edit or create a persona file — edit `app/personas/<name>.md` directly; this skill only switches between existing ones
