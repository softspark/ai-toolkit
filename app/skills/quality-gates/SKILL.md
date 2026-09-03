---
name: quality-gates
description: "Plan before work over an hour, and hold the gates: ruff clean, mypy --strict clean, pytest coverage above 70 percent, no secrets in code. Triggers: quality, lint, mypy, pytest, coverage, gate, definition of done."
effort: low
user-invocable: false
allowed-tools: Read
---

# Quality Gates

This rule comes from `app/rules/quality-gates.md` in ai-toolkit. It applies to
every task in this workspace, not only when it is loaded.

# Quality Gates & Mandatory Practices

## MANDATORY PRACTICES
1.  **Plan First:** Tasks >1h require Plan, Success Criteria, and Pre-Mortem.
2.  **Quality Gates:**
    *   `ruff check .` (0 errors)
    *   `mypy --strict src/` (0 errors)
    *   `pytest --cov=src` (>70% coverage)
    *   **Type Safety:** 100% public APIs, >60% internal.
3.  **Security:** No secrets in code, sanitization, auth z/n.
