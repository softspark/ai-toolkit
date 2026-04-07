---
name: council
description: "4-perspective decision evaluation for architecture choices. Use when user wants multi-angle analysis, needs to decide between alternatives, or mentions 'council', 'evaluate decision', 'pros cons'."
user-invocable: true
effort: high
argument-hint: "[decision question or proposal to evaluate]"
agent: orchestrator
context: fork
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Decision Council

$ARGUMENTS

Evaluate a decision from 4 distinct perspectives using parallel sub-agents, then synthesize a weighted recommendation.

## Usage

```
/council [decision question or proposal to evaluate]
```

## What This Command Does

1. **Parses** the decision question from user input
2. **Gathers** codebase context relevant to the decision
3. **Spawns** 4 parallel sub-agents — each analyzing from a different perspective
4. **Synthesizes** all perspectives into a structured recommendation with decision matrix

## MANDATORY: You MUST use the Agent tool

**DO NOT analyze the decision yourself.** Your job is to parse the question, spawn 4 sub-agents in parallel via the `Agent` tool, and synthesize their outputs. If you attempt to provide all perspectives inline, you have failed.

## Process

### 1. Parse the Decision

Extract from the user's input:

- **The proposal** — what is being considered
- **The alternatives** — what the options are (if not stated, infer the implicit alternative: status quo)
- **The context** — what project/codebase/situation this applies to

If the question is too vague to evaluate, ask ONE clarifying question before proceeding.

### 2. Gather Context

Before spawning agents, quickly scan the codebase for relevant context:

- Current tech stack, dependencies, patterns in use
- Existing code related to the decision area
- Configuration, infrastructure, or architectural choices already made

Include this context in each sub-agent prompt so perspectives are grounded in reality.

### 3. Spawn 4 Sub-Agents in Parallel (REQUIRED)

Call the `Agent` tool **4 times in a single response** — all agents MUST launch in the same message to run in parallel.

| Agent | Role | Directive |
|-------|------|-----------|
| **Advocate** | Case FOR | Present the strongest case FOR the proposal. Find evidence, benefits, success stories. Reference relevant code/patterns in the codebase. Be persuasive but honest. |
| **Critic** | Case AGAINST | Present the strongest case AGAINST. Find risks, hidden costs, failure modes, alternatives that might be better. Be thorough but fair. |
| **Pragmatist** | Trade-offs | Evaluate practical trade-offs: implementation cost, timeline, team capacity, maintenance burden, migration risk, operational complexity. Ground estimates in the actual codebase size and patterns. |
| **User-Proxy** | User impact | Consider end-user and customer impact: UX changes, downtime during migration, performance implications, breaking changes, adoption friction, documentation needs. |

Each agent prompt MUST include:

1. The original decision question
2. The codebase context gathered in step 2
3. The specific perspective this agent owns
4. Instruction to search the codebase for supporting evidence
5. Constraint: 200-400 words, concrete evidence over abstract arguments

### 4. Synthesize

After all 4 agents complete, combine their outputs into the structured format below. Do NOT simply concatenate — identify agreements, contradictions, and conditional factors across perspectives.

## Output Format

```markdown
## Decision Council: [Question]

### Advocate (FOR)
[Summary of arguments for — key benefits and evidence]

### Critic (AGAINST)
[Summary of arguments against — key risks and alternatives]

### Pragmatist (TRADE-OFFS)
[Practical considerations — cost, timeline, complexity]

### User-Proxy (USER IMPACT)
[End-user perspective — UX, performance, breaking changes]

### Synthesis
**Recommendation:** [FOR / AGAINST / CONDITIONAL]
**Confidence:** [HIGH / MEDIUM / LOW]
**Key condition:** [Primary factor that would change the recommendation]

**Where perspectives agree:** [Common ground across agents]
**Where perspectives conflict:** [Key disagreements and why]

### Decision Matrix
| Factor | Weight | FOR score (1-5) | AGAINST score (1-5) |
|--------|--------|-----------------|---------------------|
| Technical merit | [H/M/L] | [score] | [score] |
| Risk | [H/M/L] | [score] | [score] |
| Cost | [H/M/L] | [score] | [score] |
| Timeline | [H/M/L] | [score] | [score] |
| User impact | [H/M/L] | [score] | [score] |
| **Weighted total** | | **[total]** | **[total]** |
```

## Rules

- Each sub-agent must search the codebase for relevant evidence — no purely abstract arguments
- Sub-agents must be honest within their role — the Advocate should acknowledge weaknesses, the Critic should acknowledge strengths
- Keep each perspective to 200-400 words — density over length
- The synthesis must add value beyond summarizing — identify the decisive factor
- If the decision is clearly one-sided after analysis, say so — don't manufacture false balance

## Anti-Patterns

- Don't skip the codebase scan — ungrounded opinions are worthless
- Don't let all 4 perspectives say the same thing — enforce distinct angles
- Don't give a wishy-washy "it depends" synthesis — commit to a recommendation with conditions
- Don't ignore the status quo — "do nothing" is always an alternative

## READ-ONLY

This skill evaluates decisions. It does NOT implement changes.
