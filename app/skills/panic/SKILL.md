---
name: panic
description: "Emergency kill switch that halts all agent activity via a lockfile gate. Use when agents are looping, misbehaving, or the user wants to stop everything NOW — not for normal workflow interruptions."
effort: low
disable-model-invocation: true
agent: system-governor
context: fork
allowed-tools: Bash
---

# Panic Command (The Kill Switch)

Stops the system dead in its tracks.

## Usage

```bash
/panic [reason]
# Example: /panic "Agents are looping infinitely"
```

## Protocol
1. **Create Lockfile**: `touch .claude/HALT`
2. **Notify User**: "System Halted. Delete .claude/HALT to resume."

## Resume
To resume operations:
```bash
rm .claude/HALT
```

## Rules

- **MUST** create the lockfile at `.claude/HALT` — agents check this path to gate execution
- **NEVER** bypass the lockfile silently once it exists
- **CRITICAL**: emit a clear, single-line notification so the user knows the system is halted
- **MANDATORY**: include the provided reason (if any) in the notification

## Gotchas

- The lockfile is **project-local** (`./.claude/HALT`). Agents running in a different working directory, or globally-invoked tools, will not see it and will keep running. `/panic` is not a system-wide kill switch.
- The lockfile check relies on the `PreToolUse` hook from `ai-toolkit`; if the user disabled hooks in `settings.json` or ejected without keeping hooks, `touch .claude/HALT` does nothing. Verify the hook is present after invocation.
- Removing `.claude/HALT` mid-task resumes agents that were blocked, but they resume with potentially **stale context** (conversation moved on, tool results orphaned). Prefer restarting the session cleanly if possible.

## When NOT to Use

- For cancelling a single agent — use the task's own stop mechanism
- For a production incident — use `/workflow incident-response`
- As a rollback tool — use `/rollback`
- To pause for a short clarification — just ask the question, do not halt the system
