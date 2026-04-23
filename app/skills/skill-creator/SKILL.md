---
name: skill-creator
description: "Create new skills from templates with guided workflow"
effort: high
disable-model-invocation: true
argument-hint: "[skill name or description]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Skill Creator

$ARGUMENTS

Create a new skill following the Agent Skills standard.

## Workflow

1. **Capture intent** -- ask: what should the skill do? Who invokes it?
2. **Classify** -- task, hybrid, or knowledge? (see Classification Guide below)
3. **Interview** -- gather: framework, tools, scope, output format, constraints
4. **Write SKILL.md** -- frontmatter + body, under 500 lines
5. **Create supporting files** -- reference/, templates/, scripts/ as needed
6. **Test and iterate** -- invoke, observe, refine

## Frontmatter Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Lowercase, hyphens only, max 64 chars |
| `description` | string | yes | Third person, max 1024 chars, include key terms |
| `effort` | low/medium/high/max | no | Controls model thinking budget |
| `disable-model-invocation` | bool | no | `true` = only user can trigger (task skills) |
| `user-invocable` | bool | no | `false` = knowledge skill, Claude auto-loads |
| `allowed-tools` | csv | no | Restrict tool access for safety |
| `model` | string | no | Override default model |
| `context` | string | no | `fork` to run in isolated subagent |
| `agent` | string | no | Agent type to use when `context: fork` |
| `argument-hint` | string | no | Shown in autocomplete, e.g. `"[target]"` |
| `hooks` | object | no | Lifecycle hooks (PreToolUse, PostToolUse, Stop) |

## Classification Guide

| Type | When to use | Key fields |
|------|-------------|------------|
| **Task** | User-triggered actions with side effects (build, deploy, commit) | `disable-model-invocation: true`, `allowed-tools` |
| **Hybrid** | Both user and Claude invoke (review, analyze) | defaults |
| **Knowledge** | Domain patterns Claude auto-loads (clean-code, api-patterns) | `user-invocable: false` |

## Writing Guidelines

- **Description**: third person ("Generates...", "Provides..."), **min 50 chars**, include searchable key terms **and a trigger hint** (e.g., "Use when..."). Short descriptions cause over-triggering — adjacent skills fight for the same query.
- **Name**: lowercase, hyphens, max 64 chars -- match the directory name
- **Length**: SKILL.md under 500 lines; use `reference/` for overflow
- **Be concise**: Claude is smart -- give structure, not lectures
- **Degrees of freedom**: be specific on format/constraints, flexible on implementation
- **File references**: max 1 level deep (e.g., `reference/details.md`)
- **Use `$ARGUMENTS`**: place it early so user input is visible
- **Tables over prose**: for options, patterns, mappings

## Mandatory Sections (meta-architect audit criteria)

Every SKILL.md must contain all five, or it will lower the toolkit quality score:

1. **Description ≥50 chars** with trigger hint in frontmatter
2. **At least one concrete example** — fenced code block or `## Example` section
3. **Hard rules** using uppercase markers: `MUST`, `NEVER`, `CRITICAL`, `MANDATORY`, or `DO NOT`
4. **"When NOT to Use" section** — list 2-3 adjacent skills and the boundary between them
5. **Under 500 lines** — split into `reference/` if needed

These map directly to the mutation strategies in `meta-architect.md`:
`add_example`, `add_constraint`, `add_edge_case`, `restructure`.

### Rules vs Gotchas — different semantic buckets

Split the "hard rules" criterion into two sections when both apply:

- **`## Rules`** — prescriptive process constraints (always-true MUST / NEVER): *"MUST form a testable hypothesis before changing code"*, *"NEVER force-push main"*. Required in every skill.
- **`## Gotchas`** — environment-specific traps the agent would miss without being told, taken from [Anthropic's best practices](https://agentskills.io/skill-creation/best-practices.md#gotchas-sections). Example from their docs: *"The `users` table uses soft deletes. Queries must include `WHERE deleted_at IS NULL` or results will include deactivated accounts."* Add this section only when real domain traps exist — do not pad with a `(none)` placeholder.

## Directory Structure

```
skill-name/
  SKILL.md              # Main instructions (required, <500 lines)
  reference/            # Detailed docs (loaded on-demand)
  templates/            # Reusable templates for output
  scripts/              # Executable helper scripts
```

Only create subdirectories when the skill needs them. Most skills are a single SKILL.md.

## SKILL.md Template

```markdown
---
name: {name}
description: "{Third-person description, min 50 chars, with trigger hint like 'Use when...'}"
argument-hint: "[hint]"
allowed-tools: Read, Grep, Glob
---

# {Title}

$ARGUMENTS

{One-line purpose statement.}

## Usage

\`\`\`
/{name} [arguments]
\`\`\`

## What This Command Does

1. **Step one**
2. **Step two**
3. **Step three**

## Example

\`\`\`
/{name} example-argument
\`\`\`

{Expected observable behavior.}

## Rules

- **MUST** {non-negotiable rule 1}
- **NEVER** {forbidden action}
- **CRITICAL**: {safety constraint}

## Gotchas

- {environment-specific trap the agent would miss — concrete, not general}
- {non-obvious behavior of a tool, API, or data layout}

## When NOT to Use

- For {adjacent use case} -- use `/{other-skill}` instead
- For {another case} -- use `/{another-skill}`
- If {precondition} is not met
```

Leave out `## Gotchas` entirely when the skill has no domain-specific traps — it is not mandatory, and a stub with nothing concrete is worse than no section.

## Quality Checklist

Before finalizing, verify:

- [ ] Description ≥50 chars, third-person, with trigger hint
- [ ] At least one concrete code-fenced example
- [ ] `## Rules` section with prescriptive MUST / NEVER / CRITICAL / MANDATORY
- [ ] `## Gotchas` section when the domain has real environment-specific traps (otherwise omit)
- [ ] `## When NOT to Use` section naming 2-3 adjacent skills
- [ ] SKILL.md under 500 lines
- [ ] No time-sensitive information (versions, dates)
- [ ] Consistent terminology throughout
- [ ] File references max 1 level deep
- [ ] Workflows have numbered steps
- [ ] Frontmatter fields match classification type
- [ ] `$ARGUMENTS` is present for task/hybrid skills
- [ ] `allowed-tools` is minimal (principle of least privilege)

## Evaluation

After creating the skill, test it:

1. Invoke with a representative prompt
2. Check output matches expected structure
3. Verify dynamic injection (`$ARGUMENTS`) works
4. Test with varied argument patterns
5. Confirm `allowed-tools` are sufficient but not excessive
6. Iterate: tighten instructions where output diverges

## Installation

After creating the skill:

1. Verify the skill directory exists under `app/skills/{name}/`
2. Update `skills-catalog.md` if it exists
3. Update `ARCHITECTURE.md` skill counts if referenced
4. Run `validate.sh` if available
5. Run `evaluate-skills.sh` if available

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Description too vague | Add specific terms: "Python", "REST API", "migration" |
| SKILL.md too long | Move details to `reference/` subdirectory |
| Missing `$ARGUMENTS` | Add after the H1 heading for task/hybrid skills |
| Over-specifying steps | Give structure, let Claude fill details |
| Wrong classification | Task = side effects, Knowledge = patterns, Hybrid = both |
