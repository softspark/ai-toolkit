---
description: Systematically debug an issue and find root cause
---

# Debug Workflow

1. Reproduce the issue — get exact error message, stack trace, or unexpected behavior
2. Read the error carefully — understand what it actually says before guessing
3. Check recent changes (`git log`, `git diff`) for potential causes
4. Add targeted logging or breakpoints around the suspected area
5. Form a hypothesis and test it with the smallest possible change
6. If hypothesis fails, gather more data — do not guess repeatedly
7. Fix the root cause, not the symptom
8. Add a regression test that fails without the fix
9. Verify the fix doesn't break other tests
