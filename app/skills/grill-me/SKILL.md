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

- Ask questions **one at a time**
- For each question, provide your **recommended answer**
- If a question can be answered by **exploring the codebase**, explore instead of asking
- Resolve dependencies between decisions — don't skip ahead
- Be relentless — don't settle for vague or hand-wavy answers
- Challenge assumptions, not just surface decisions
- Apply Devil's Advocate critique to every major decision
