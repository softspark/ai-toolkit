---
name: architecture-decision
description: "Loaded when user asks about architecture decisions or architecture note writing"
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
