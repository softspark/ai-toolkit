---
name: briefing
description: "Generate executive daily briefing across all agents"
effort: medium
disable-model-invocation: true
agent: chief-of-staff
context: fork
allowed-tools: Read, Grep, Glob
---

# Briefing Command

Triggers the Chief of Staff to generate an executive summary.

## Usage

```bash
/briefing [period]
# Example: /briefing today
# Example: /briefing week
```

## Protocol
1. **Collect**: Gather logs from `kb/learnings/`, `maintenance/` logs, and recent runs.
2. **Synthesize**: Group by category (Ops, Strategy, Actions).
3. **Filter**: Remove low-priority success logs.
4. **Present**: Render the Daily Brief.
