---
language: common
category: testing
version: "1.0.0"
---

# Universal Testing Rules

## Test Structure
- Use Arrange-Act-Assert (AAA) pattern in every test.
- One logical assertion per test. Multiple `assert` calls are fine if testing one behavior.
- Test names describe behavior: `test_returns_404_when_user_not_found`.
- Keep tests independent: no shared mutable state between tests.

## Test Organization
- Mirror source structure: `src/auth/login.ts` -> `tests/auth/login.test.ts`.
- Separate unit, integration, and e2e tests into distinct directories or markers.
- Shared fixtures go in `conftest.py`, `test-utils.ts`, or equivalent.

## What to Test
- Test behavior, not implementation. Tests should survive refactors.
- Cover: happy path, error cases, edge cases, boundary values.
- New code: 100% coverage. Overall project: >70%.
- Critical paths (auth, payments, data mutations): always tested.

## What NOT to Test
- Framework internals (ORM save, HTTP library send).
- Trivial getters/setters with no logic.
- Third-party library correctness.
- Private methods directly: test through public API.

## Mocking
- Mock at boundaries: HTTP clients, databases, file systems, clocks.
- Prefer fakes over mocks when logic is complex.
- Never mock the thing you are testing.
- Reset mocks between tests to prevent leakage.

## Test Quality
- Tests must be deterministic: no flaky tests allowed.
- Tests must be fast: unit tests <100ms each, test suite <60s.
- Avoid `sleep` in tests: use polling, events, or test clocks.
- Do not test implementation details (private methods, internal state).

## Coverage
- Measure coverage but do not chase 100%: focus on critical paths.
- Coverage gaps in error handling and edge cases are worse than gaps in happy paths.
- New PRs must not decrease overall coverage.

## Test Data
- Use factories/builders to create test data, not raw constructors.
- Keep test data minimal: only set fields relevant to the test.
- Do not share mutable test data across tests.
- Use realistic but not real data (no production data in tests).
