---
description: Safely refactor code with test protection
---

# Refactor Workflow

1. Ensure existing tests pass before starting
2. Identify the specific code smell or improvement target
3. Make one small, focused change at a time
4. Run tests after each change — never batch multiple refactors
5. Use IDE rename/extract features when available
6. Keep the same external behavior — tests must stay green
7. If tests break, revert the last change and try a smaller step
8. Commit each successful refactor step separately
