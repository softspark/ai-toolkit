---
name: hook-creator
description: "Create a new Claude Code lifecycle hook (PreToolUse, PostToolUse, Stop, SessionStart, etc.) with a bash script and hooks.json registration. Use when the user wants automated behavior tied to a specific event — not for one-off commands."
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
            "command": "\"$HOME/.softspark/ai-toolkit/hooks/{script-name}.sh\""
        }
    ]
}
```

Required fields:
- `_source`: always `"ai-toolkit"` (used by merge/strip logic)
- `matcher`: tool name or regex for Pre/PostToolUse, empty string for global events
- `hooks[].type`: always `"command"`
- `hooks[].command`: path to script using `$HOME/.softspark/ai-toolkit/hooks/` prefix

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

- **MUST** use one script per hook entry — no inline multi-line commands inside `hooks.json`
- **MUST** keep `Pre*` hooks fast and deterministic — they gate every matching tool call, slow hooks throttle the whole agent
- **NEVER** write secrets, tokens, or credentials to stdout — hook output is injected into LLM context and can be extracted
- **NEVER** exit non-zero from a `Post*` or `Stop` hook unless you intend to block further processing; exit 0 is the safe default
- **CRITICAL**: respect the `TOOLKIT_HOOK_PROFILE` env var. Profile `minimal` must be a no-op for non-essential hooks.
- **MANDATORY**: test the script standalone (`bash app/hooks/{name}.sh`) before adding it to `hooks.json`

## Gotchas

- `PreToolUse` hooks that exit non-zero **block** the tool call. A slow or flaky hook (network call, lock contention) becomes a DoS against Claude's own workflow. Keep Pre hooks to pure-bash checks of local state.
- Hook output (stdout) is injected verbatim into the model's context. A hook that runs `git log --all` prints hundreds of lines the model then has to wade through — be surgical, print only what matters.
- The path in `hooks.json` is resolved relative to the user's machine, not the ai-toolkit repo. Use `$HOME/.softspark/ai-toolkit/hooks/<name>.sh` as the canonical location (installer symlinks there).
- `SessionStart` with matcher `startup|compact` fires on both fresh starts AND after context compaction. Hooks that assume "new session" will mis-fire after compaction — check for explicit context markers if the distinction matters.
- Bash hooks on Windows (without WSL) will not run. If the hook must work cross-platform, wrap it in a Node or Python script and call from the bash stub — or flag the hook as `posix-only` in the description.

## Validation Checklist

After creating the hook:

- [ ] Script exists in `app/hooks/` and is executable (`chmod +x`)
- [ ] Entry added to `app/hooks.json` with `_source: "ai-toolkit"`
- [ ] Event name matches a supported lifecycle event
- [ ] `scripts/validate.py` passes
- [ ] Script runs without errors: `bash app/hooks/{name}.sh`
- [ ] Hook count in README.md and docs updated if needed

## When NOT to Use

- For a **skill** (slash command) — use `/skill-creator`
- For an **agent** definition — use `/agent-creator`
- For a git pre-commit hook (not a Claude Code hook) — use `/git-mastery` or `scripts/install_git_hooks.py`
- For one-off automation that is not tied to a Claude Code event — use a plain shell script outside the toolkit
- To modify an existing toolkit hook — edit the file directly; this skill is create-only
