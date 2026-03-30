# Quality Gates & Mandatory Practices

## MANDATORY PRACTICES
1.  **Plan First:** Tasks >1h require Plan, Success Criteria, and Pre-Mortem.
2.  **Quality Gates:**
    *   `ruff check .` (0 errors)
    *   `mypy --strict src/` (0 errors)
    *   `pytest --cov=src` (>70% coverage)
    *   **Type Safety:** 100% public APIs, >60% internal.
3.  **Security:** No secrets in code, sanitization, auth z/n.
