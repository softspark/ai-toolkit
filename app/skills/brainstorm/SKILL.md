---
name: brainstorm
description: "Pre-artifact conversation that prices the zero option and can end in 'do not build this'. Triggers: brainstorm, should we build, is this worth it, explore idea, thinking out loud, half-formed idea."
user-invocable: true
effort: high
argument-hint: "[the idea, problem, or half-formed thought]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Brainstorm

$ARGUMENTS

The conversation that happens *before* an artifact exists. Every other planning
skill here produces something — a PRD, a plan, issues, a design. This one is
allowed to produce nothing, and that is its point.

## The zero option is a real candidate

Price "build nothing" against the proposal properly. Not as a strawman, not as a
sentence acknowledged and moved past — as a genuine option with its own costs:

- what breaks or stays broken if nobody does this
- who currently absorbs that, and how much it costs them
- how long the problem has existed without being fixed, and what that says about it
- what the codebase carries forever once this exists: another surface, another
  migration path, another thing that has to keep working

If the zero option wins, say so and stop. **Do not invent a deliverable to justify
the conversation.** A brainstorm that ends in "this is not worth building, and
here is what it would have cost" has done its job.

## Steps

### Step 1: Understand before proposing

Explore the actual codebase before shaping anything. Read what exists, grep for
prior attempts, check whether the problem is already solved somewhere.

Ask what the user is trying to achieve, not what they want built. The stated
request is a proposed solution; the problem behind it is what matters. Keep
asking until you can state the problem without naming the solution.

### Step 2: Shape the options

Produce at least three genuinely different approaches, one of which is always
"do nothing / do it manually / wait". Different means different in kind, not
three variants of the same shape.

For each: what it costs, what it forecloses, what has to stay true for it to keep
working.

### Step 3: Resolve the unknowns

List what nobody in the conversation actually knows. For each, decide whether it
can be resolved now (read the code, check the data, run something) or whether it
stays open and becomes a risk the next stage inherits.

Resolve what is cheap to resolve. An unknown carried into a PRD becomes an Open
Question; an unknown carried past a PRD becomes a bug.

### Step 4: Challenge the conclusion

Before routing anywhere, spawn a **separate** agent to attack the conclusion. Not
you re-reading your own reasoning — a different context that did not fall in love
with the idea.

```
Use the Agent tool with subagent_type: general-purpose.

Your job is to break the conclusion below, not to improve it. Assume it is wrong
and find out where. If you cannot break it, say what specifically held.

Conclusion reached: <one paragraph>
Options rejected, with reasons: <list — the zero option is always one of them>
Unknowns still open: <list>

Work through these in order:

1. Restate the problem without naming any solution. If you cannot, the problem
   was never separated from the proposal and everything below is downstream of
   that.
2. Who pays for the problem today, how often, and how much? If nobody can be
   named, the cost is assumed rather than observed.
3. The problem has existed until now without this being built. What changed —
   or is the trigger just that someone thought of it?
4. Take the zero-option reasoning and argue the opposite side as well as you can.
   If that argument is stronger than the one that won, the zero option was
   dismissed rather than priced.
5. What does the codebase carry permanently once this exists? Count the surface,
   the migration path, the thing that must keep working.
6. Name the single assumption that, if false, wastes the most work — and the
   cheapest thing that would prove it false today.
7. Hand the brief to someone who was not here. What do they ask first?

Report as: BLOCKER (the conclusion or the chosen next step does not survive),
CONCERN (holds, but on an assumption worth naming), HOLDS (what you tried to
break and could not).

Write plainly and skip the closing summary. Do not soften findings to be
agreeable — agreement you did not test is worth nothing here. A first pass over
a fresh idea that produces no BLOCKER and no CONCERN almost always means the
attack was shallow; go back to question 4.
```

Any BLOCKER goes back to Step 2 or Step 3. Do not route past one.

### Step 5: Take an exit ramp

Pick exactly one and say which, in the user's words, before invoking anything.

| # | When | Next |
|---|------|------|
| 1 | Nothing worth building, or the question is answered | **stop** — no artifact, no handoff |
| 2 | Worth doing, not now | write a brief to `kb/planning/`, stop |
| 3 | Feature, unknowns resolved | `/write-a-prd` |
| 4 | Feature, user wants to co-design | `/design-an-interface`, then `/write-a-prd` |
| 5 | Small and obvious, no spec needed | `/tdd` or `/fix` directly |
| 6 | Already tracked somewhere | point at the existing issue or task, stop |

Ramp 1 and ramp 6 are the two most likely to be correct and the two most likely to
be skipped. Check both before considering the others.

## Rules

- **MUST** price the zero option explicitly and state why it lost, before any ramp
  other than 1 is taken
- **MUST** spawn the challenger as a separate agent — self-review at Step 4 does
  not count and is the failure mode this skill exists to prevent
- **NEVER** invoke a downstream skill without naming the ramp and the reason first
- **NEVER** produce a PRD, plan, or issue from inside this skill — it routes, it
  does not build
- **CRITICAL**: ending at ramp 1 is a success, and is reported as one, not as an
  apology
- **MANDATORY**: at least one of the three options in Step 2 is always the zero
  option

## Gotchas

- The challenger only works from a **separate** context. Re-reading your own
  reasoning in the same conversation reproduces the same blind spots and returns
  OK on everything, which reads as validation and is nothing of the kind.
- A challenger that never returns BLOCKER or CONCERN is broken, not agreeable. If
  several runs come back clean, check that the conclusion, the rejected options
  and the open unknowns are actually being passed in — an attacker given nothing
  to attack reports that everything holds.
- "The user asked for it" is not the problem statement. Users arrive with a
  solution already chosen; Step 1 is not finished until the problem stands without
  it.
- Sunk conversation is not evidence. Forty minutes of good discussion does not make
  the idea worth building, and the pull toward a handoff gets stronger the longer
  the conversation ran. That pull is exactly what ramp 1 resists.
- Ramp 6 loses to novelty. Searching the tracker feels like admitting the
  conversation was wasted, so it gets skipped — do it early, in Step 1.
- This skill costs roughly double a plain planning session, because of the
  challenger. That is only worth paying if ramp 1 or ramp 6 sometimes wins. If
  every run of this skill routes to `/write-a-prd`, stop using it — it has become
  ceremony.

## When NOT to Use

- The decision is already made and you want it executed — use `/plan` or `/write-a-prd`
- A concrete plan exists and needs stress-testing — use `/grill-me`
- An architectural choice needs several expert perspectives — use `/council`
- A bug needs a root cause — use `/debug` or `/triage-issue`
- The change is one obvious line — just make it; a brainstorm about a typo is the
  same waste as a PRD about one

## Related Skills

- Chose to build it? → `/write-a-prd` for the requirements, then `/prd-to-plan`
- Need to compare interface shapes first? → `/design-an-interface`
- Want the plan attacked instead of the idea? → `/grill-me`
- Want four expert lenses on a decision? → `/council`
