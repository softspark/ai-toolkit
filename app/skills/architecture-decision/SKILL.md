---
name: architecture-decision
description: "Architecture decision making via trade-off analysis in RFC/RFD/ADR format: context, constraints, 3+ options, comparison, recommendation. Triggers: architecture decision, ADR, RFC, RFD, trade-offs, options comparison, design choice, pick between, should we use, evaluate approach. Load when weighing 2+ architectural options or writing decision records."
effort: medium
user-invocable: false
allowed-tools: Read, Write
---

# Architecture Decision Skill

## Core Philosophy: "Everything is a Trade-off"
There are no "best solutions", only solutions with the right set of trade-offs for the specific context.

## Decision Making Process (RFD / RFC)
1. **Context**: What is the problem? Why now?
2. **Constraints**: Budget, Time, Skillset, Legacy.
3. **Options**: Propose at least 3 viable options.
4. **Trade-off Analysis**: Compare constraints vs options.
5. **Recommendation**: Choose one and justify.

## Trade-off Analysis Matrix (Template)

| Feature | Option A (e.g. SQL) | Option B (e.g. NoSQL) | Option C (e.g. File) |
|---------|---------------------|-----------------------|----------------------|
| **Scalability** | Medium (Vertical) | High (Horizontal) | Low |
| **Consistency** | Strong (ACID) | Eventual (BASE) | N/A |
| **Complexity** | Low (Known) | Medium (New tech) | Low |
| **Cost** | $$ | $$$ | $ |

## Architecture Note
When a decision is made, document it.

```markdown
# Architecture Note: Use PostgreSQL for Main Database

## Status
Accepted

## Context
We need a reliable, relational database for user data...

## Decision
We will use PostgreSQL 16.

## Consequences
- Positive: ACID compliance, rich ecosystem.
- Negative: Scaling writes requires sharding later.
```

## Critical Factors to Evaluate
- **Reliability** (Availability, Fault tolerance)
- **Scalability** (Throughput, Latency)
- **Maintainability** (Simple vs Easy, Ecosystem)
- **Security** (AuthN/Z, Encryption)
- **Cost** (Infrastructure, License, Cognitive load)

## Rules

- **MUST** present at least 3 viable options, including "status quo / do nothing" when relevant
- **MUST** state constraints (budget, time, team skillset, legacy) **before** enumerating options — options without constraints are arbitrary
- **NEVER** recommend an option without explicitly naming its failure mode and what would trigger revisiting the decision
- **CRITICAL**: the output is a document (ADR / RFC / RFD), not code changes. Code work belongs in `/plan` or `/refactor-plan`.
- **MANDATORY**: `Consequences` section names both Positive and Negative effects. A decision with only upside is not honestly analysed.

## Gotchas

- "Status quo" is a genuine option and often the right one for constrained teams. Omitting it biases the analysis toward change for change's sake.
- ADRs are **append-only**. A reversed decision gets a new ADR with `Status: Supersedes ADR-N`, not an in-place edit of the original — the history of thinking matters more than the current state.
- Qualitative scales (High / Medium / Low) without anchors are hand-waving. When scoring, pin each level to a measurable threshold (e.g., "High scalability = 10k req/s at p95 < 100ms on 2 nodes").
- "We might use X" and "We will try X" are not decisions — they are deferrals. A valid ADR states the chosen option unconditionally; if you cannot, the decision is not ready.
- Political constraints (team expertise, vendor relationships, executive preferences) are first-class constraints. Hiding them behind technical language produces ADRs that get silently ignored — name them explicitly in the Constraints section.

## When NOT to Load

- To find **what** architectural problems exist — use `/architecture-audit` (discovery) before this skill (decision)
- To plan implementation of an already-decided option — use `/plan` or `/refactor-plan`
- To design a single module's interface — use `/design-an-interface`
- When fewer than 2 options exist — there is no decision to make; document the constraint instead
- For runtime configuration choices (flag values, timeouts) — those are operational, not architectural
