---
name: evolve
description: "Evolve agent definitions via meta-architect"
effort: medium
disable-model-invocation: true
context: fork
agent: meta-architect
allowed-tools: Read, Edit, Grep, Glob
---

# Evolve Command

Triggers the Meta-Architect to improve the system.

## Usage

```bash
/evolve [source]
# Example: /evolve learnings (Analyze kb/learnings)
# Example: /evolve last-failure (Analyze last error log)
```

## Protocol
1. **Analyze**: Read input source for patterns of failure/inefficiency.
2. **Design**: Draft changes to `.claude/agents/` or `.claude/skills/`.
3. **Implement**: Apply changes.
4. **Report**: Document what evolved.
