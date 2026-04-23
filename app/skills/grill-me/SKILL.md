---
name: grill-me
description: "Stress-test a plan or design through relentless Socratic questioning, walking down each decision branch until reaching shared understanding. Use when user wants to stress-test a plan, get grilled, validate assumptions, or mentions 'grill me'."
user-invocable: true
effort: medium
argument-hint: "[plan or design to stress-test]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Grill Me

$ARGUMENTS

Interview relentlessly about every aspect of the plan until reaching shared understanding.

## Usage

```
/grill-me [plan or design to stress-test]
```

## What This Command Does

1. **Reads** the plan or design (from context, file, or user description)
2. **Walks** down each branch of the decision tree
3. **Resolves** dependencies between decisions one-by-one
4. **Provides** recommended answers for each question
5. **Continues** until shared understanding is reached

## Rules

- **MUST** ask questions one at a time — batching defeats the Socratic process
- **MUST** provide a recommended answer with every question so the user can accept, refine, or reject
- **NEVER** settle for vague or hand-wavy answers — press for specifics ("what does 'scale' mean here — 10k req/s or 10M?")
- **NEVER** skip ahead before the current branch is resolved — dependencies between decisions matter
- **CRITICAL**: if a question can be answered by **exploring the codebase**, explore instead of asking. Do not outsource verifiable facts to the user.
- **MANDATORY**: apply Devil's Advocate critique to every major decision — the default answer ("let's ship it") is almost always the one that needs challenging

## Gotchas

- Grilling can feel adversarial. Frame questions as "what if X happens" not "your plan is wrong because X" — the goal is shared understanding, not winning.
- Fatigue kicks in around 10 questions deep. For larger plans, pause and summarize every ~7 questions so the user can reorient before continuing.
- Some disagreements cannot be resolved by argument — they need data. If a question loops (user defends A, grill defends B, repeat), recommend a spike or experiment instead of more questions.
- The user's "final answer" after heavy grilling may be reluctant compliance, not genuine agreement. Watch for hedging language ("I guess", "sure, fine") and probe once more.
- Grilling a plan that is already detailed and well-vetted produces diminishing returns and annoyance. Know when to stop — exit condition is "shared understanding", not "exhaustive coverage".

## When NOT to Use

- For **implementation** — use `/plan`, `/refactor-plan`, or `/prd-to-plan`
- For code review after the code is written — use `/review`
- For architecture decisions with 2-3 named options — use `/architecture-decision` (structured trade-off) rather than open-ended grilling
- When the plan is crystal-clear and the user just needs a sanity check — grilling overkills trivial decisions
- In a production incident — use `/workflow incident-response`, speed beats thoroughness there
