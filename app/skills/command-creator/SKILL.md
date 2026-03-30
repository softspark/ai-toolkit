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

## Minimal Template

```markdown
---
description: "{one-line description}"
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
```

## Validation Checklist

- [ ] Command file uses markdown and valid YAML frontmatter
- [ ] Help text is concise and searchable
- [ ] Body is instruction-oriented, not user-facing prose
- [ ] `$ARGUMENTS` is present when arguments are expected
- [ ] Validation steps are explicit
- [ ] Command has been tested with at least one realistic invocation

