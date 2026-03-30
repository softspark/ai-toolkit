---
name: panic
description: "Emergency stabilization via system-governor agent"
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
