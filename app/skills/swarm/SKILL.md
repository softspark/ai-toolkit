---
name: swarm
description: "Execute tasks via Map-Reduce, Consensus, or Relay swarms"
user-invocable: true
effort: max
argument-hint: "[map-reduce|consensus|relay] [task]"
context: fork
agent: orchestrator
model: opus
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate
---

# /swarm - Parallel Agent Swarm

$ARGUMENTS

## MANDATORY: You MUST use the Agent tool

**DO NOT do the work yourself.** Decompose the task and invoke agents via multiple parallel `Agent` tool calls. Single-agent execution = failure.

## Modes

### Map-Reduce (default)
Split task into N independent sub-tasks. Launch ALL agents **in a single response** (parallel execution).

```
# Single response with N Agent tool calls:
Agent(subagent_type="...", prompt="sub-task 1 — own files: path/a/")
Agent(subagent_type="...", prompt="sub-task 2 — own files: path/b/")
Agent(subagent_type="...", prompt="sub-task N — own files: path/n/")
```

After all complete: aggregate results with `hive-mind` skill, produce synthesis report.

### Consensus
Same problem, 3 independent agents from different angles. Launch all 3 **in a single response**.

```
Agent(subagent_type="backend-specialist",      prompt="[problem] — approach from data layer angle. Output: solution + confidence 0.0–1.0")
Agent(subagent_type="tech-lead",               prompt="[problem] — approach from architecture angle. Output: solution + confidence 0.0–1.0")
Agent(subagent_type="performance-optimizer",   prompt="[problem] — approach from performance angle. Output: solution + confidence 0.0–1.0")
```

After all complete: pick winner by confidence score, note dissents.

### Relay
Sequential chain — each agent depends on the previous output. Launch **one at a time**, wait for completion before next.

```
# Round 1
Agent(subagent_type="tech-lead", prompt="Design the API spec. Output to docs/api-spec.md")
# Wait for completion

# Round 2
Agent(subagent_type="backend-specialist", prompt="Implement based on docs/api-spec.md. Own files: src/")
# Wait for completion

# Round 3
Agent(subagent_type="test-engineer", prompt="Write tests for src/. Own files: tests/")
```

## File Ownership Rules (CRITICAL)

> **Each agent MUST own distinct file paths. No overlapping paths. No exceptions.**

## Agent Tool Call Format

```
Agent(
  subagent_type="<agent-name>",
  description="<3-5 word summary>",
  prompt="<full task description including: original request, specific sub-task, owned files, success criteria>"
)
```

## Aggregation (after all agents complete)

1. Collect all agent outputs
2. De-duplicate identical findings
3. Synthesize unique insights
4. Generate final swarm report
