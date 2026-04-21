---
name: verification-before-completion
description: "Loaded when agent is about to claim work is complete, fixed, or passing — requires running verification commands and confirming output before making any success claims. Evidence before assertions, always."
user-invocable: false
allowed-tools: Read
---

# Verification Before Completion

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

Claiming work is complete without verification is dishonesty, not efficiency.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction ("Great!", "Perfect!", "Done!")
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |
| No dead code (Art. VI.1) | Grep for every removed/renamed symbol: 0 references | "I cleaned up what I touched" |
| Behavior change covered (Art. VI.2) | Integration test for the API surface + unit test + docs updated | Unit test on the helper only |
| Diff is clean (Art. VI.4) | Re-read full diff: no orphaned imports, no stale docs, no skipped fixes | "I only changed what I needed" |

## Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification
- About to commit/push/PR without verification
- Trusting agent success reports without independent check
- Relying on partial verification
- Thinking "just this once"

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence is not evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter is not compiler |
| "Agent said success" | Verify independently |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
CORRECT:  [Run test command] [See: 34/34 pass] "All tests pass"
WRONG:    "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
CORRECT:  Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
WRONG:    "I've written a regression test" (without red-green verification)
```

**Requirements:**
```
CORRECT:  Re-read plan → Create checklist → Verify each → Report gaps or completion
WRONG:    "Tests pass, phase complete"
```

**Agent delegation:**
```
CORRECT:  Agent reports success → Check VCS diff → Verify changes → Report actual state
WRONG:    Trust agent report at face value
```

## Constitutional Anchors

This skill enforces **Constitution Art. VI.4 (Verify Before Claiming Done)**. The diff re-read is not optional: before any completion claim, confirm no orphaned references, no missing test coverage for changed paths, no stale docs. A task is not done while any of those exist.

## The Bottom Line

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
