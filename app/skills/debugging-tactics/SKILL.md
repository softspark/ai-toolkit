---
name: debugging-tactics
description: "Loaded when user is debugging an issue or needs root cause analysis"
effort: medium
user-invocable: false
allowed-tools: Bash, Grep, Read
---

# Debugging Tactics Skill

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1 (Root Cause Investigation), you cannot propose fixes.

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Violating the letter of this process is violating the spirit of debugging.**

## The Four Phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root Cause Investigation

**BEFORE attempting ANY fix:**

1. **Read Error Messages Carefully**
   - Don't skip past errors or warnings — they often contain the answer
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - If not reproducible, gather more data — don't guess

3. **Check Recent Changes**
   - `git diff`, recent commits, new dependencies
   - Config changes, environmental differences

4. **Gather Evidence in Multi-Component Systems**
   For each component boundary: log what enters, log what exits, verify state at each layer.
   Run once to gather evidence showing WHERE it breaks, THEN investigate that specific component.

5. **Trace Data Flow**
   Where does the bad value originate? Trace backward through call stack to the source. Fix at source, not at symptom.

### Phase 2: Pattern Analysis

1. **Find Working Examples** — locate similar working code in same codebase
2. **Compare Against References** — read reference implementations COMPLETELY, not skimming
3. **Identify Differences** — list every difference, however small
4. **Understand Dependencies** — what other components, settings, config does this need?

### Phase 3: Hypothesis and Testing

1. **Form Single Hypothesis** — "I think X is the root cause because Y" (be specific)
2. **Test Minimally** — smallest possible change, one variable at a time
3. **Verify Before Continuing** — did it work? If not, form NEW hypothesis. Don't add more fixes on top.

### Phase 4: Implementation

1. **Create Failing Test Case** — MUST have before fixing (use TDD skill)
2. **Implement Single Fix** — address root cause, ONE change at a time, no "while I'm here" improvements
3. **Verify Fix** — test passes? No regressions? Issue resolved?
4. **If Fix Doesn't Work** — count your attempts:
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If >= 3: STOP and question the architecture** (see below)

### Architecture Escalation (3+ Failed Fixes)

**Pattern indicating architectural problem:**
- Each fix reveals new shared state/coupling in different places
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**STOP and question fundamentals:**
- Is this pattern fundamentally sound?
- Should we refactor architecture vs. continue fixing symptoms?
- Discuss with user before attempting more fixes

This is NOT a failed hypothesis — this is a wrong architecture.

## Red Flags — STOP and Follow Process

| Excuse | Reality |
|--------|---------|
| "Quick fix for now, investigate later" | Systematic is faster than thrashing |
| "Just try changing X and see" | One variable at a time, with hypothesis |
| "I'll skip the test, I'll manually verify" | Untested fixes don't stick |
| "It's probably X, let me fix that" | Seeing symptoms is not understanding root cause |
| "One more fix attempt" (after 2+) | 3+ failures = architectural problem. STOP. |
| "Here are the main problems: [list]" | You're proposing fixes without investigation |

## Legacy Reference

## Language-Specific Tactics

### Python
- **Debugger**: `import pdb; pdb.set_trace()` (or `ipdb`)
- **Trace**: `traceback.print_stack()`
- **Memory**: `tracemalloc` for leaks.
```python
import tracemalloc
tracemalloc.start()
# ... code ...
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
```

### Node.js / TypeScript
- **Debugger**: `node --inspect-brk app.js` -> Open `chrome://inspect`.
- **Memory**: `heapdump` or built-in inspector.
- **Async Traces**: Ensure `Error.stackTraceLimit = Infinity`.

### PHP (Laravel/Symfony)
- **Debugger**: Xdebug (`xdebug_break()`).
- **Logs**: `Log::info('State:', $data);`.
- **Query Log**: `DB::enableQueryLog(); ... dd(DB::getQueryLog());`.

### Flutter / Dart
- **Debugger**: `debugger()` statement.
- **Inspector**: Flutter DevTools (Widget Inspector).
- **Network**: Network tab in DevTools for API calls.

## "5 Whys" Root Cause Analysis
Ask "Why?" 5 times to find the real issue:
- "The app crashed." -> Why? -> "Null pointer exception."
- -> Why? -> "User object was null."
- -> Why? -> "API returned 404."
- -> Why? -> "User ID was invalid."
- -> Why? -> "Frontend validation allowed negative IDs." (ROOT CAUSE)
