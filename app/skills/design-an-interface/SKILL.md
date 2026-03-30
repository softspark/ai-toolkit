---
name: design-an-interface
description: "Generate multiple radically different interface designs using parallel sub-agents, then compare on simplicity, depth, and correctness. Based on 'Design It Twice' from Ousterhout. Use when user wants to design an API, explore interface options, compare module shapes, or mentions 'design it twice'."
user-invocable: true
effort: high
argument-hint: "[module or interface to design]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Design an Interface

$ARGUMENTS

Generate 3+ radically different interface designs using parallel sub-agents, then compare. Based on "Design It Twice" from "A Philosophy of Software Design."

## Usage

```
/design-an-interface [module or interface to design]
```

## What This Command Does

1. **Gathers** requirements and constraints
2. **Spawns** 3+ parallel sub-agents with different design constraints
3. **Presents** each design with signatures, usage examples, and trade-offs
4. **Compares** on simplicity, depth, efficiency, and correctness
5. **Synthesizes** best elements into final recommendation

## Process

### 1. Gather Requirements

Before designing, understand:

- [ ] What problem does this module solve?
- [ ] Who are the callers? (other modules, external users, tests)
- [ ] What are the key operations?
- [ ] Any constraints? (performance, compatibility, existing patterns)
- [ ] What should be hidden inside vs exposed?

### 2. Generate Designs (Parallel Sub-Agents)

Spawn 3+ sub-agents simultaneously using Agent tool. Each gets a **radically different** constraint:

| Agent | Constraint |
|-------|-----------|
| Agent 1 | Minimize method count — aim for 1-3 methods max |
| Agent 2 | Maximize flexibility — support many use cases |
| Agent 3 | Optimize for the most common case |
| Agent 4 | Take inspiration from a specific paradigm/library |

Each agent outputs:
1. Interface signature (types/methods)
2. Usage example (how caller uses it)
3. What this design hides internally
4. Trade-offs of this approach

### 3. Present Designs

Show each design sequentially so user can absorb each approach before comparison:
1. **Interface signature** — types, methods, params
2. **Usage examples** — how callers actually use it
3. **What it hides** — complexity kept internal

### 4. Compare Designs

Compare in prose (not tables) on:

| Criterion | Description |
|-----------|-------------|
| Interface simplicity | Fewer methods, simpler params |
| General-purpose vs specialized | Flexibility vs focus |
| Implementation efficiency | Does shape allow efficient internals? |
| Depth | Small interface hiding significant complexity (good) vs large interface with thin implementation (bad) |
| Ease of correct use | vs ease of misuse |

### 5. Synthesize

Often the best design combines insights from multiple options. Give an opinionated recommendation. Ask:
- Which design best fits the primary use case?
- Any elements from other designs worth incorporating?

## Visual Companion (Optional)

When upcoming design explorations will involve visual content (mockups, layout comparisons, architecture diagrams), offer the browser companion:

> "Some of these interface designs might be easier to compare visually. I can show diagrams and side-by-side comparisons in a browser. Want to try it?"

**This offer MUST be its own message.** Do not combine with other questions. Wait for response.

If accepted, start the server and use it for visual comparisons only. Text/conceptual questions stay in terminal.

See [../write-a-prd/reference/visual-companion.md](../write-a-prd/reference/visual-companion.md) for details.

## Anti-Patterns

- Don't let sub-agents produce similar designs — enforce radical difference
- Don't skip comparison — the value is in contrast
- Don't implement — this is purely about interface shape
- Don't evaluate based on implementation effort

## READ-ONLY

This skill designs interfaces. It does NOT write implementation code.
