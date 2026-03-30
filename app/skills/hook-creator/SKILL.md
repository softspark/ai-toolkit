---
name: hook-creator
description: "Creates new Claude Code hooks with guided workflow, strict conventions, and validation"
effort: high
disable-model-invocation: true
argument-hint: "[hook event or description]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Hook Creator

$ARGUMENTS

Create a new Claude Code hook following ai-toolkit conventions.

## Supported Hook Events

| Event | Fires When | Matcher | Typical Use |
|-------|-----------|---------|-------------|
| `SessionStart` | Session begins or resumes after compact | `startup\|compact` | Context injection, rules reminder |
| `Notification` | Claude sends a notification | any | OS alerts, Slack pings |
| `PreToolUse` | Before a tool executes | tool name (e.g. `Bash`) | Safety guards, validation |
| `PostToolUse` | After a tool executes | tool name | Feedback loops, logging |
| `Stop` | Claude finishes responding | any | Quality checks, session save |
| `PreCompact` | Before context compaction | any | Context preservation |
| `SubagentStop` | Subagent completes | any | Result validation |
| `UserPromptSubmit` | User submits a prompt | any | Prompt governance |
| `TaskCompleted` | Agent Teams task done | any | Lint, type check |
| `TeammateIdle` | Agent Teams member idle | any | Completeness reminder |

## Workflow

1. **Capture intent** -- ask: what should the hook do? Which lifecycle event?
2. **Select event** -- pick from the Supported Hook Events table above
3. **Define matcher** -- tool name for PreToolUse/PostToolUse, empty for global
4. **Write script** -- create `app/hooks/{event-name-kebab}.sh`
5. **Register in hooks.json** -- add entry to `app/hooks.json`
6. **Validate** -- run `scripts/validate.py`

## Hook Script Conventions

- Location: `app/hooks/{event-name-kebab}.sh`
- Shebang: `#!/bin/bash`
- Header comment: script name, purpose, event, matcher
- Respect `TOOLKIT_HOOK_PROFILE` env var (`minimal` = skip non-essential hooks)
- Always `exit 0` on success (non-zero blocks the operation for Pre* hooks)
- Output goes to Claude's context as plain text
- No external dependencies -- bash builtins and coreutils only
- Keep output concise -- hooks fire frequently

## hooks.json Entry Format

```json
{
    "_source": "ai-toolkit",
    "matcher": "",
    "hooks": [
        {
            "type": "command",
            "command": "\"$HOME/.ai-toolkit/hooks/{script-name}.sh\""
        }
    ]
}
```

Required fields:
- `_source`: always `"ai-toolkit"` (used by merge/strip logic)
- `matcher`: tool name or regex for Pre/PostToolUse, empty string for global events
- `hooks[].type`: always `"command"`
- `hooks[].command`: path to script using `$HOME/.ai-toolkit/hooks/` prefix

## Script Template

```bash
#!/bin/bash
# {script-name}.sh — {One-line purpose}.
#
# Fires on: {EventName}
# Matcher: {matcher or "all"}
# Skipped when TOOLKIT_HOOK_PROFILE=minimal.

PROFILE="${TOOLKIT_HOOK_PROFILE:-standard}"
[ "$PROFILE" = "minimal" ] && exit 0

# --- Hook logic here ---

exit 0
```

## Rules

- One script per hook entry (no inline multi-line commands)
- Script filename must use kebab-case matching the event purpose
- Pre* hooks can block operations -- keep them fast and deterministic
- Never write secrets or credentials to stdout (output goes to LLM context)
- Test the script standalone before registering: `bash app/hooks/{name}.sh`

## Validation Checklist

After creating the hook:

- [ ] Script exists in `app/hooks/` and is executable (`chmod +x`)
- [ ] Entry added to `app/hooks.json` with `_source: "ai-toolkit"`
- [ ] Event name matches a supported lifecycle event
- [ ] `scripts/validate.py` passes
- [ ] Script runs without errors: `bash app/hooks/{name}.sh`
- [ ] Hook count in README.md and docs updated if needed
