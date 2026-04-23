---
name: command-creator
description: "Creates new Claude Code slash commands with frontmatter, workflow guidance, and validation"
effort: high
disable-model-invocation: true
argument-hint: "[command name or description]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Command Creator

$ARGUMENTS

Create a new Claude Code slash command following ai-toolkit conventions.

## Workflow

1. **Capture intent** -- what should the command do and who invokes it?
2. **Pick scope** -- project command, user command, or plugin command?
3. **Define frontmatter** -- description, argument hint, allowed tools, model if needed
4. **Write command body** -- instructions for Claude, not explanation for the user
5. **Add validation context** -- expected output, constraints, follow-up checks
6. **Test and iterate** -- invoke the command with representative arguments

## Command Locations

- Project: `.claude/commands/<name>.md`
- User: `~/.claude/commands/<name>.md`
- Plugin: `plugin-name/commands/<name>.md`

In `ai-toolkit`, command-development guidance belongs in skill form and any reusable command templates should live under `app/skills/<skill-name>/templates/` or KB docs.

## Frontmatter Template

```yaml
---
description: "One-line help text shown in /help"
argument-hint: "[target]"
allowed-tools: Read, Grep, Bash
model: sonnet
---
```

## Command Authoring Rules

- Write commands as **instructions for Claude**, not marketing copy for the user
- Keep the first paragraph action-oriented and deterministic
- Use `$ARGUMENTS` early when the command takes user input
- Prefer numbered phases for multi-step workflows
- List required checks explicitly (`lint`, `tests`, `docs`, etc.)
- Avoid hidden assumptions about project structure unless the command is project-specific
- **Description ≥50 chars** with a trigger hint (`Use when…`) — short descriptions cause adjacent commands to fight for the same query
- Include **hard rules** (MUST / NEVER / CRITICAL) so the agent cannot improvise around safety boundaries
- Include **"When NOT to use"** naming 2-3 adjacent commands, to prevent over-triggering

## Minimal Template

```markdown
---
description: "{Third-person description, min 50 chars, with trigger hint like 'Use when...'}"
argument-hint: "[arguments]"
allowed-tools: Read, Grep, Bash
---

# {Command Title}

$ARGUMENTS

Perform the requested task using this workflow:

1. Gather context from the repository.
2. Ask clarifying questions if critical information is missing.
3. Execute the task using the smallest safe set of changes.
4. Validate the result.
5. Summarize outcome and follow-up actions.

## Example

\`\`\`
/{command} example-argument
\`\`\`

## Rules

- **MUST** {non-negotiable rule}
- **NEVER** {forbidden action}

## Gotchas

- {environment-specific trap — only if the command has one; omit the section otherwise}

## When NOT to Use

- For {adjacent use case} -- use `/{other-command}` instead
- If {precondition} is not met
```

Follow [Anthropic's Gotchas guidance](https://agentskills.io/skill-creation/best-practices.md#gotchas-sections): *"concrete corrections to mistakes the agent will make without being told otherwise"* — not general advice. Omit the section when no domain traps exist.

## Validation Checklist

- [ ] Command file uses markdown and valid YAML frontmatter
- [ ] Description ≥50 chars, third-person, with trigger hint
- [ ] At least one concrete code-fenced example
- [ ] `## Rules` with MUST / NEVER / CRITICAL (prescriptive)
- [ ] `## Gotchas` when the command has real environment-specific traps (optional)
- [ ] `## When NOT to Use` section naming 2-3 adjacent commands
- [ ] Body is instruction-oriented, not user-facing prose
- [ ] `$ARGUMENTS` is present when arguments are expected
- [ ] Validation steps are explicit
- [ ] Command has been tested with at least one realistic invocation

