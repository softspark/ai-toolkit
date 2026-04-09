"""Shared content and helpers for directory-based rule generators.

Used by: Antigravity, Cursor .mdc, Windsurf, Cline, Roo Code.
All generators produce prefixed files (ai-toolkit-*) to avoid
overwriting user content. Re-running is idempotent.

Stdlib-only.
"""
from __future__ import annotations

from pathlib import Path

from emission import (
    count_agents_and_skills,
    emit_agents_bullets,
    emit_skills_bullets,
    generate_general_guidelines,
    generate_quality_standards,
    generate_workflow_guidelines,
)

PREFIX = "ai-toolkit-"


# ---------------------------------------------------------------------------
# Rule content generators (shared across all directory-based generators)
# ---------------------------------------------------------------------------

def rule_code_style() -> str:
    return """\
# Code Style

* Follow language-specific conventions: PEP 8 (Python), StandardJS/Prettier (TypeScript), gofmt (Go), rustfmt (Rust)
* Use descriptive names: functions as verbs (`calculateTotal`), booleans as questions (`isValid`), constants as UPPER_SNAKE
* Keep functions short — single responsibility, max ~30 lines
* Prefer immutability: use `const`/`final`/`let` over mutable variables where possible
* No magic numbers — extract to named constants
* Avoid deep nesting (max 3 levels) — use early returns and guard clauses
* DRY: extract shared logic only when used 3+ times; premature abstraction is worse than duplication
* YAGNI: do not build features or abstractions for hypothetical future requirements
"""


def rule_testing() -> str:
    return """\
# Testing

* Every new feature or bug fix must include tests
* Use Arrange-Act-Assert pattern for unit tests
* Test behavior, not implementation — tests should survive refactoring
* Use descriptive test names: `test_<what>_<when>_<expected>`
* Prefer real dependencies over mocks at integration boundaries
* Target >70% code coverage for new code
* Never skip or disable tests without a linked issue explaining why
* Run the full test suite before marking work as done
"""


def rule_security() -> str:
    return """\
# Security

* Never commit secrets, API keys, credentials, or tokens — use environment variables
* Validate and sanitize all external input (user input, API responses, file uploads)
* Use parameterized queries — never concatenate SQL strings
* Escape output to prevent XSS in web contexts
* Apply principle of least privilege for file permissions and API scopes
* Keep dependencies updated — audit regularly for known CVEs
* Use HTTPS for all external communication
* Log security events without logging sensitive data (passwords, tokens, PII)
"""


def rule_workflow() -> str:
    return """\
# Workflow

* Plan before implementing: tasks >1 hour need a plan, success criteria, and pre-mortem
* Research before acting: check existing code and documentation before proposing changes
* Use structured commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:` (Conventional Commits)
* Prefer editing existing files over creating new ones to avoid file bloat
* Read-only exploration first, then targeted changes — never explore and write simultaneously
* Quality gates must pass before done: lint, type-check, tests green
* Cite sources when making decisions based on existing knowledge or documentation
* No destructive commands (`rm -rf`, `DROP TABLE`, `--force`) without explicit user confirmation
"""


def rule_quality_standards() -> str:
    return """\
# Quality Standards

* "Green tests" is the only definition of Done — forced merges on red tests are unacceptable
* All public APIs must have type annotations/signatures
* No data loss: never delete files without backup verification or using reversible operations
* No blind execution: never run generated code without review
* No infinite loops: all autonomous loops must have a maximum iteration count
* Commands like `rm -rf`, `DROP TABLE`, `FORMAT` require explicit user confirmation
* Never delete audit logs or archives without explicit approval and backup
"""


def rule_agents_and_skills() -> str:
    """Full listing of agents and skills — same content all platforms get."""
    agents_count, skills_count = count_agents_and_skills()
    lines = [
        f"# AI Toolkit — {agents_count} Agents, {skills_count} Skills",
        "",
        "Shared AI development toolkit with specialized agents, skills, quality hooks, and a safety constitution.",
        "",
        "## Available Agents",
        "",
        "Specialized agent personas — apply their expertise for relevant tasks:",
        "",
        emit_agents_bullets(),
        "",
        "## Available Skills",
        "",
        "Skills are invocable slash commands or auto-loaded knowledge sources:",
        "",
        emit_skills_bullets(),
        "",
        generate_general_guidelines(),
        "",
        generate_quality_standards(),
        "",
        generate_workflow_guidelines(),
    ]
    return "\n".join(lines) + "\n"


# Standard rule files every platform gets
STANDARD_RULES: dict[str, callable] = {
    f"{PREFIX}agents-and-skills.md": rule_agents_and_skills,
    f"{PREFIX}code-style.md": rule_code_style,
    f"{PREFIX}testing.md": rule_testing,
    f"{PREFIX}security.md": rule_security,
    f"{PREFIX}workflow.md": rule_workflow,
    f"{PREFIX}quality-standards.md": rule_quality_standards,
}


# ---------------------------------------------------------------------------
# Workflow content generators
# ---------------------------------------------------------------------------

def workflow_code_review() -> str:
    return """\
---
description: Review code for quality, security, and correctness
---

# Code Review Workflow

1. Read all changed files and understand the context
2. Check for security vulnerabilities (OWASP Top 10)
3. Verify test coverage for new/changed code
4. Check naming conventions and code style consistency
5. Look for performance issues (N+1 queries, unnecessary allocations)
6. Verify error handling covers edge cases
7. Ensure no secrets or credentials in code
8. Provide actionable feedback with specific file:line references
"""


def workflow_feature_development() -> str:
    return """\
---
description: Implement a new feature end-to-end with tests and documentation
---

# Feature Development Workflow

1. Understand the requirements — ask clarifying questions if ambiguous
2. Research existing code to find relevant patterns and integration points
3. Plan the implementation: list files to create/modify, identify risks
4. Write failing tests first (TDD red phase)
5. Implement the feature in small, incremental steps
6. Make tests pass (TDD green phase)
7. Refactor if needed (TDD refactor phase)
8. Run full test suite and lint checks
9. Update documentation if behavior changed
10. Create a structured commit with descriptive message
"""


def workflow_debug() -> str:
    return """\
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
"""


def workflow_refactor() -> str:
    return """\
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
"""


def workflow_security_audit() -> str:
    return """\
---
description: Multi-vector security assessment of codebase
---

# Security Audit Workflow

1. Scan dependencies for known CVEs (npm audit, pip audit, etc.)
2. Check for hardcoded secrets, API keys, and credentials
3. Review authentication and authorization logic
4. Test input validation — look for SQL injection, XSS, SSTI
5. Check file upload handling and path traversal risks
6. Review error handling — ensure no sensitive data in error messages
7. Verify HTTPS usage for all external communication
8. Check access control — principle of least privilege
9. Document findings with severity (HIGH/MEDIUM/LOW)
10. Create issues for each finding with fix recommendations
"""


def workflow_test_coverage() -> str:
    return """\
---
description: Boost test coverage for a module or feature
---

# Test Coverage Workflow

1. Run coverage report to identify untested code
2. Prioritize: critical paths > edge cases > happy paths already covered
3. Write tests for uncovered public APIs first
4. Add edge case tests: null inputs, empty collections, boundary values
5. Add error path tests: invalid inputs, network failures, timeouts
6. Run coverage again — verify improvement
7. Do not write tests just for coverage numbers — each test should catch real bugs
"""


def workflow_api_design() -> str:
    return """\
---
description: Design and implement a new API endpoint
---

# API Design Workflow

1. Define the resource and its relationships
2. Choose HTTP methods (GET/POST/PUT/PATCH/DELETE) following REST conventions
3. Define request/response schemas with types
4. Plan error responses (400, 401, 403, 404, 422, 500)
5. Implement validation for all input fields
6. Write integration tests covering happy path and error cases
7. Add rate limiting and authentication if needed
8. Document the endpoint (OpenAPI/Swagger or inline docs)
9. Test with real HTTP client (curl, httpie, Postman)
"""


def workflow_database_migration() -> str:
    return """\
---
description: Safely evolve database schema with zero-downtime migration
---

# Database Migration Workflow

1. Write the migration script (up and down)
2. Test migration on a copy of production data
3. Check for breaking changes: column renames, type changes, NOT NULL on existing data
4. Plan backfill strategy for new columns with defaults
5. Consider index impact on large tables (concurrent index creation)
6. Update ORM models/entities to match new schema
7. Run the full test suite against the migrated schema
8. Document rollback procedure
"""


def workflow_incident_response() -> str:
    return """\
---
description: Respond to production incidents systematically
---

# Incident Response Workflow

1. Acknowledge the incident — assign severity (P1-P4)
2. Identify impact: which users, which features, since when
3. Check monitoring dashboards and recent deployments
4. If recent deploy is the cause, consider rollback first
5. Gather logs, stack traces, and error rates
6. Implement a fix or workaround — prioritize restoring service
7. Verify the fix in production
8. Write a postmortem: timeline, root cause, action items
9. Create follow-up issues to prevent recurrence
"""


def workflow_performance_optimization() -> str:
    return """\
---
description: Profile and optimize performance bottlenecks
---

# Performance Optimization Workflow

1. Measure first — establish baseline metrics (latency, throughput, memory)
2. Profile to find the actual bottleneck — do not guess
3. Check for N+1 queries, unnecessary allocations, blocking I/O
4. Implement the smallest change that addresses the bottleneck
5. Measure again — verify improvement with same benchmark
6. If no improvement, revert and investigate further
7. Document the optimization and its measured impact
"""


def workflow_tdd() -> str:
    return """\
---
description: Test-driven development with red-green-refactor loop
---

# TDD Workflow

1. Write a failing test that describes the expected behavior (RED)
2. Write the minimum code to make the test pass (GREEN)
3. Refactor to improve code quality while keeping tests green (REFACTOR)
4. Repeat for the next behavior
5. Keep each cycle small — one behavior per iteration
6. Run the full test suite after each green phase
7. Commit after each successful refactor
"""


def workflow_codebase_onboarding() -> str:
    return """\
---
description: Understand an unfamiliar codebase (read-only exploration)
---

# Codebase Onboarding Workflow

1. Read README, CLAUDE.md, and any architecture docs
2. Identify the tech stack: language, framework, database, build tools
3. Map the directory structure — locate entry points, configs, tests
4. Trace a request end-to-end: from entry point through layers to response
5. Read the test suite to understand expected behavior
6. Check git log for recent activity and active contributors
7. Note any patterns, conventions, or anti-patterns observed
8. Do NOT write or modify any code during onboarding
"""


def workflow_docs() -> str:
    return """\
---
description: Generate or update documentation for code changes
---

# Documentation Workflow

1. Identify what changed: new feature, API change, config change, bug fix
2. Update inline code comments only where logic is non-obvious
3. Update README if setup, usage, or prerequisites changed
4. Update API docs if endpoints, params, or responses changed
5. Add examples for new features
6. Remove documentation for deleted features — no stale docs
7. Run any doc generation tools (typedoc, sphinx, etc.)
"""


STANDARD_WORKFLOWS: dict[str, callable] = {
    f"{PREFIX}code-review.md": workflow_code_review,
    f"{PREFIX}feature-development.md": workflow_feature_development,
    f"{PREFIX}debug.md": workflow_debug,
    f"{PREFIX}refactor.md": workflow_refactor,
    f"{PREFIX}security-audit.md": workflow_security_audit,
    f"{PREFIX}test-coverage.md": workflow_test_coverage,
    f"{PREFIX}api-design.md": workflow_api_design,
    f"{PREFIX}database-migration.md": workflow_database_migration,
    f"{PREFIX}incident-response.md": workflow_incident_response,
    f"{PREFIX}performance-optimization.md": workflow_performance_optimization,
    f"{PREFIX}tdd.md": workflow_tdd,
    f"{PREFIX}codebase-onboarding.md": workflow_codebase_onboarding,
    f"{PREFIX}docs.md": workflow_docs,
}


# ---------------------------------------------------------------------------
# Shared file generation helpers
# ---------------------------------------------------------------------------

def cleanup_stale(directory: Path, current_files: set[str]) -> None:
    """Remove ai-toolkit-* files that are no longer in the registry."""
    if not directory.is_dir():
        return
    for f in directory.iterdir():
        if f.name.startswith(PREFIX) and f.name not in current_files:
            f.unlink()
            print(f"  Removed stale: {f.relative_to(directory.parent.parent)}")


def write_rules(target_dir: Path, rules: dict[str, callable],
                subdir: str = "rules", label: str = "") -> None:
    """Write rule files to target_dir/<subdir>/.

    Only writes ai-toolkit-* files. User files are never touched.
    """
    out_dir = target_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    cleanup_stale(out_dir, set(rules.keys()))

    for filename, content_fn in rules.items():
        (out_dir / filename).write_text(content_fn(), encoding="utf-8")
        tag = f" ({label})" if label else ""
        print(f"  Generated: {subdir}/{filename}{tag}")
