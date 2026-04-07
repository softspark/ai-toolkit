---
name: introspect
description: "Agent self-debugging and recovery. Use when stuck in loops, making repeated errors, or quality degrades. Triggers: introspect, self-debug, stuck, loop, why failing."
user-invocable: true
effort: low
argument-hint: "[symptom or 'stuck']"
agent: debugger
context: fork
allowed-tools: Read, Grep
---

# Agent Self-Debugging

$ARGUMENTS

Structured self-analysis for when the agent is stuck, looping, or producing degraded output.

---

## Step 1: Capture Failure State

Before diagnosing, gather the facts. Answer each question concisely:

| Question | Answer |
|----------|--------|
| **Last goal/task** | What was the agent trying to accomplish? |
| **Actions taken** | List the last 3-5 actions in order |
| **Errors or unexpected results** | What went wrong? What was expected vs actual? |
| **Attempt count** | How many times has this been tried? |
| **Time spent** | Rough estimate of effort so far |

---

## Step 2: Classify the Failure Pattern

Identify which pattern matches the current situation:

| Pattern | Symptoms | Common Cause |
|---------|----------|--------------|
| **Loop** | Same action repeated 3+ times | Missing exit condition, wrong approach |
| **Drift** | Actions diverge from original goal | Lost context, scope creep |
| **Assumption Error** | Working with wrong mental model | Didn't read code, assumed behavior |
| **Tool Misuse** | Wrong tool for the job | Grep when should Read, Bash when should Edit |
| **Context Overflow** | Forgetting earlier findings | Too much context, need compaction |
| **Wrong Abstraction** | Over-engineering simple task | Premature abstraction, YAGNI violation |
| **Missing Information** | Can't proceed without data | Need to ask user, read more code |

Pick the **single best match**. If multiple apply, pick the root cause pattern (the one that, if fixed, would resolve the others).

---

## Step 3: Diagnose Root Cause

Answer these three questions:

1. **What assumption was wrong?** — Identify the specific belief that led to failure.
2. **What information was missing?** — What would have prevented the failure if known earlier?
3. **What would a fresh start look like?** — If starting over with current knowledge, what would the first action be?

---

## Step 4: Select Recovery Action

Apply the **smallest possible fix** — do not restart from scratch unless absolutely necessary:

| Pattern | Recovery Action |
|---------|----------------|
| **Loop** | Stop. Change approach entirely — different tool, different strategy, different angle. |
| **Drift** | Re-read the original user request verbatim. Reset scope to exactly what was asked. |
| **Assumption Error** | Read the actual code, file, or docs. Do not guess. Verify the mental model. |
| **Tool Misuse** | Switch to the correct tool. Read instead of Grep for full context. Edit instead of Bash for file changes. |
| **Context Overflow** | Summarize all findings so far in 5 bullet points. Compact and continue. |
| **Wrong Abstraction** | Delete the abstraction. Do the simplest, most direct thing that works. |
| **Missing Information** | Ask the user exactly ONE specific question. Do not guess. |

---

## Step 5: Produce the Introspection Report

Output exactly this format:

```markdown
## Introspection Report

**Pattern:** [Loop|Drift|Assumption Error|Tool Misuse|Context Overflow|Wrong Abstraction|Missing Information]
**Root Cause:** [1-2 sentence diagnosis]
**Recovery Action:** [Specific next step]
**Confidence:** [HIGH|MEDIUM|LOW]

### What happened
[Brief timeline of actions taken — 3-5 bullet points max]

### What went wrong
[Specific diagnosis — what assumption failed, what was missed]

### What to do next
[ONE concrete action — not a plan, a single next step]
```

---

## Self-Correction Rules

These rules are non-negotiable during recovery:

1. **Never retry the exact same action.** If it failed once, it will fail again. Change something.
2. **Never continue a loop "hoping it will work this time."** Hope is not a strategy.
3. **Prefer reading code over guessing behavior.** Open the file. Read the function. Check the types.
4. **When in doubt, ask the user** rather than making assumptions. One specific question beats three wrong guesses.
5. **A 2-line fix is better than a 50-line refactor.** Solve the immediate problem first.
6. **Check if the goal is still correct** before optimizing the approach. Sometimes the task itself needs clarification.
7. **If stuck for more than 3 attempts, escalate.** Tell the user what you tried, what failed, and what you need.

---

## Quick Self-Check (Use Before Retrying Anything)

Before taking the next action after introspection, answer:

- [ ] Is this action **different** from what I already tried?
- [ ] Am I working on the **original goal**, not a tangent?
- [ ] Do I have **enough information** to succeed, or am I guessing?
- [ ] Is this the **simplest** approach that could work?

If any answer is "no", stop and address that first.
