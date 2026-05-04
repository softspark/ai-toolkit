---
name: swarm
description: "Execute tasks via Map-Reduce, Consensus, or Relay swarms"
user-invocable: true
effort: max
argument-hint: "[map-reduce|consensus|relay] [--with-kb] [--worktree] [task]"
context: fork
agent: orchestrator
model: opus
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, TeamCreate, TeamDelete, SendMessage, TaskCreate, TaskList, TaskUpdate, TaskGet, TaskOutput, TaskStop
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

## KB-First Mode (`--with-kb`)

When `$ARGUMENTS` contains `--with-kb`, every spawned agent MUST receive KB context grounded in the project knowledge base.

### Required pre-flight (run BEFORE spawning agents)

1. Call `mcp__rag-mcp__smart_query` with the original task as `query`. Use `use_multi_hop=true` if the task spans 2+ concepts.
2. Capture `results[*].kb_id`, `title`, `content`, and `source_documents_used`.
3. Build a `[KB CONTEXT]` block (max 10 entries, pruned to top scores).

### Per-agent prompt template (mandatory under `--with-kb`)

```
[KB CONTEXT — from rag-mcp smart_query, ground all decisions in these]
- {kb_id}: {title}
  {content excerpt, ≤300 chars}
- ...

[YOUR SUB-TASK]
{specific sub-task, owned files, success criteria}

[RULES]
- Cite KB entries as [PATH: kb_id] when you rely on them.
- If KB is silent on a decision, state that explicitly — do NOT invent.
- After producing your output, call mcp__rag-mcp__verify_answer with your answer + the cited kb_ids; include the verdict in your final report.
```

### Aggregation under `--with-kb`

The synthesis step MUST include a `## KB Coverage` section listing which `kb_id`s were actually cited and any agent that returned `verdict: unsupported`.

### When to skip `--with-kb`

- Pure code-mechanical tasks (rename, format, dependency bump) — KB adds noise.
- Tasks already scoped to one file with no cross-cutting concerns.

## Isolated Worktrees Mode (`--worktree`)

When `$ARGUMENTS` contains `--worktree`, every spawned agent in **Map-Reduce** mode runs in its own git worktree on a throwaway branch. Aggregation merges or copies the changes back into the lead workspace.

### Why

- Agents touching adjacent files (same module, different functions) can race.
- Writing to disjoint paths is not enough — file-locking, formatter cache, IDE indexers, and `.git/index.lock` all leak.
- Worktrees give each agent a real filesystem-level boundary plus a named branch for review.

### How (mandatory under `--worktree`)

Pass `isolation: "worktree"` to every `Agent` call:

```
Agent(
  subagent_type="...",
  description="...",
  prompt="...",
  isolation="worktree"
)
```

The Agent tool returns the worktree path and branch name on completion. **Empty worktrees are auto-cleaned** by the runtime when the agent made no changes — you don't have to.

### Aggregation under `--worktree`

After all agents return:

1. List the returned `(path, branch)` pairs.
2. For each non-empty result: `cd <main repo> && git merge --no-ff <branch>` (or cherry-pick the commits if the agent didn't commit).
3. If any merge conflicts → escalate, do NOT auto-resolve. Cite which two agents touched the same hunk.
4. After successful merge → delete the worktree: `git worktree remove <path>` and the throwaway branch.

### When `--worktree` is mandatory (not optional)

- Map-Reduce with N≥3 agents touching the same module tree
- Any task that runs the project formatter or codegen
- Any task that mutates lockfiles, migrations, or generated artifacts

### When to skip `--worktree`

- Consensus mode — agents return analysis text, not file changes.
- Relay mode — sequential by design, next agent reads prior agent's commit.
- Single-agent fallback or KB-only research swarms.
