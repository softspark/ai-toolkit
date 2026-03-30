---
name: tdd
description: "Test-driven development with red-green-refactor loop and vertical slices. Use when user wants TDD, test-first development, red-green-refactor, or building features with tests driving the implementation."
user-invocable: true
effort: high
argument-hint: "[feature or behavior to implement]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
---

# Test-Driven Development

$ARGUMENTS

Build features using strict RED → GREEN → REFACTOR cycles with vertical slices.

## Usage

```
/tdd [feature or behavior to implement]
```

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? **Delete it. Start over.**

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

**Violating the letter of this rule is violating the spirit of this rule.**

## Philosophy

**Core principle**: Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't.

**Good tests**: Integration-style, exercise real code paths through public APIs. Describe _what_ the system does, not _how_. Read like specifications. Survive refactors.

**Bad tests**: Coupled to implementation. Mock internal collaborators, test private methods, verify through external means. Warning sign: test breaks on refactor but behavior is unchanged.

See [reference/tests.md](reference/tests.md) for examples, [reference/mocking.md](reference/mocking.md) for mocking guidelines.

## Anti-Pattern: Horizontal Slices

**DO NOT write all tests first, then all implementation.**

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  RED→GREEN: test3→impl3
```

Tests written in bulk test _imagined_ behavior. Vertical slices let each test respond to what you learned from the previous cycle.

## Workflow

### 1. Planning

Before writing any code:

- [ ] Confirm with user what interface changes are needed
- [ ] Confirm which behaviors to test (prioritize — you can't test everything)
- [ ] Identify opportunities for [deep modules](reference/deep-modules.md)
- [ ] Design interfaces for [testability](reference/interface-design.md)
- [ ] List behaviors to test (not implementation steps)
- [ ] Get user approval

### 2. Tracer Bullet

Write ONE test that confirms ONE thing:

```
RED:   Write test for first behavior → test fails
GREEN: Write minimal code to pass → test passes
```

This proves the path works end-to-end.

### 3. Incremental Loop

For each remaining behavior:

```
RED:   Write next test → fails
GREEN: Minimal code to pass → passes
```

| Rule | Description |
|------|-------------|
| One at a time | One test per cycle |
| Minimal | Only enough code to pass current test |
| No anticipation | Don't code for future tests |
| Behavioral | Tests focus on observable behavior |

### 4. Refactor

After all tests pass, look for [refactor candidates](reference/refactoring.md):

- [ ] Extract duplication
- [ ] Deepen modules (complexity behind simple interfaces)
- [ ] Apply SOLID where natural
- [ ] Run tests after each refactor step

**Never refactor while RED.** Get to GREEN first.

## Checklist Per Cycle

```
[ ] Test describes behavior, not implementation
[ ] Test uses public interface only
[ ] Test would survive internal refactor
[ ] Code is minimal for this test
[ ] No speculative features added
```

## Rules

- One RED→GREEN cycle at a time — never batch
- Tests assert on observable outcomes, not internal state
- Mock only at system boundaries (see [reference/mocking.md](reference/mocking.md))
- Each cycle leaves the codebase in a working state

## Red Flags — STOP and Start Over

If you catch yourself doing ANY of these, **delete the code and restart with TDD**:

- Writing production code before a failing test
- Writing tests after implementation
- Test passes immediately (you're testing existing behavior — fix the test)
- Can't explain why the test failed
- Tests added "later"
- Rationalizing "just this once"
- "I already manually tested it"
- "Keep as reference" or "adapt existing code"

## Common Rationalizations

| Excuse | Reality |
|--------|---------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. |
| "I'll test after" | Tests passing immediately prove nothing. |
| "Tests after achieve same goals" | Tests-after = "what does this do?" Tests-first = "what should this do?" |
| "Already manually tested" | Ad-hoc ≠ systematic. No record, can't re-run. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Keeping unverified code is technical debt. |
| "Need to explore first" | Fine. Throw away exploration, start with TDD. |
| "TDD will slow me down" | TDD faster than debugging. Pragmatic = test-first. |
| "This is different because..." | No. Apply the Iron Law. |

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only at system boundaries)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.
