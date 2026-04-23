---
name: architecture-audit
description: "Explore codebase organically for architectural friction, discover shallow modules, and propose module-deepening refactors as GitHub issue RFCs using parallel sub-agent interface designs. Use when user wants to improve architecture, find shallow modules, deepen modules, or reduce coupling."
user-invocable: true
effort: high
argument-hint: "[area to audit or 'full codebase']"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Architecture Audit

$ARGUMENTS

Explore a codebase organically, surface architectural friction, and propose module-deepening refactors as GitHub issue RFCs.

## Usage

```
/architecture-audit [area to audit or 'full codebase']
```

## What This Command Does

1. **Explores** codebase organically — friction IS the signal
2. **Presents** deepening candidates to user
3. **Frames** problem space for chosen candidate
4. **Spawns** 3+ parallel sub-agents for radically different interface designs
5. **Compares** and recommends
6. **Files** RFC as GitHub issue

## Key Concept

A **deep module** (Ousterhout) has a small interface hiding a large implementation. Deep modules enhance testability, AI navigation, and enable boundary testing.

A **shallow module** has a large interface with thin implementation — avoid.

## Process

### 1. Organic Exploration

Use Agent (subagent_type=Explore) to navigate the codebase naturally. Note friction:

- Where does understanding one concept require bouncing between many small files?
- Where are modules so shallow the interface is nearly as complex as the implementation?
- Where have pure functions been extracted just for testability but real bugs hide in how they're called?
- Where do tightly-coupled modules create integration risk in the seams?
- What is untested or hard to test?

### 2. Present Candidates

Numbered list. For each candidate show:

| Field | Content |
|-------|---------|
| Cluster | Which modules/concepts are involved |
| Why coupled | Shared types, call patterns, co-ownership |
| Dependency category | In-process, Local-substitutable, Ports & Adapters, or True external (see reference/) |
| Test impact | What existing tests would be replaced by boundary tests |

Do NOT propose interfaces yet. Ask: "Which would you like to explore?"

### 3. Frame the Problem Space

For the chosen candidate, write a user-facing explanation:
- Constraints any new interface would satisfy
- Dependencies it would rely on
- Rough illustrative code sketch (not a proposal — just grounding)

Show to user, then immediately proceed to step 4.

### 4. Design Multiple Interfaces

Spawn 3+ sub-agents in parallel via Agent tool. Each gets a different constraint:

| Agent | Constraint |
|-------|-----------|
| Agent 1 | Minimize interface — 1-3 entry points max |
| Agent 2 | Maximize flexibility — many use cases and extension |
| Agent 3 | Optimize for most common caller — default case trivial |
| Agent 4 | Ports & adapters pattern (if cross-boundary) |

Each outputs: interface signature, usage example, what it hides, dependency strategy, trade-offs.

Present sequentially, compare in prose, give opinionated recommendation.

### 5. Create GitHub Issue RFC

Use `gh issue create` with template below. Don't ask for review.

## Issue Template

<issue-template>

## Problem

Architectural friction:
- Which modules are shallow and tightly coupled
- Integration risk in the seams
- Why this makes the codebase harder to navigate/maintain

## Proposed Interface

- Interface signature (types, methods, params)
- Usage example
- What complexity it hides

## Dependency Strategy

- **In-process**: merged directly
- **Local-substitutable**: tested with [specific stand-in]
- **Ports & adapters**: port definition, production adapter, test adapter
- **Mock**: mock boundary for external services

## Testing Strategy

- New boundary tests to write
- Old shallow tests to delete
- Test environment needs

## Implementation Recommendations

Durable guidance NOT coupled to file paths:
- What the module should own
- What it should hide
- What it should expose
- How callers migrate

</issue-template>

## Dependency Categories

| Category | Description | Deepenable? |
|----------|-------------|-------------|
| In-process | Pure computation, no I/O | Always |
| Local-substitutable | Has local test stand-ins (PGLite, in-memory FS) | If stand-in exists |
| Remote but owned | Your services across network (Ports & Adapters) | Via port injection |
| True external | Third-party (Stripe, Twilio) — mock at boundary | Via mock injection |

## Testing Principle

**Replace, don't layer.** Old unit tests on shallow modules are waste once boundary tests exist — delete them. Tests assert on observable outcomes through public interface, not internal state.

## Rules

- **MUST** explore the codebase organically (Explore sub-agent) before proposing deepening targets — do not anchor on what you already know
- **MUST** present numbered candidates to the user and wait for selection before step 3 — auto-picking skips the product decision
- **NEVER** design interfaces in step 2; interface work only happens in step 4 after the problem space is framed
- **CRITICAL**: step 4 spawns **parallel** sub-agents with genuinely different constraints (minimize / maximize-flexibility / optimize-common / ports-adapters). Sequential variations of the same idea defeat the purpose.
- **MANDATORY**: deliverable is a GitHub issue RFC created via `gh issue create`. Never open a PR from this skill.

## Gotchas

- "Depth" is measured against **actual call patterns**, not the method count. A module exporting 20 functions where callers only use 2 is effectively 2-deep — the other 18 are dead interface, not richness.
- Shared TypeScript types and Python protocols count as coupling. A "just types" file imported by 30 modules creates a deep blast radius; deleting or renaming it is structurally significant even though no runtime code moves.
- Parallel sub-agents collapse into echo chambers when their constraints are not sharply different. Spell out the **opposing** tensions ("minimize interface" vs "maximize flexibility") — soft variations produce near-identical designs.
- `gh issue create` without `--body` or `--body-file` opens `$EDITOR`. In automated flows this hangs the skill indefinitely. Always pass the body explicitly.
- Ports & Adapters introduces indirection that IDE "find references" and static analysis sometimes miss (dynamic dispatch via interface). Count on broken tooling during the transition period and compensate with runtime smoke tests.

## When NOT to Use

- For executing a known refactor plan — use `/refactor` (direct edits) or `/refactor-plan` (incremental)
- For designing a single module's interface from scratch — use `/design-an-interface`
- For deciding between 2-3 named architectural options — use `/architecture-decision`
- For code-quality metrics (complexity, duplication, coverage) — use `/analyze`
- For understanding a codebase without proposing changes — use `/explore`
