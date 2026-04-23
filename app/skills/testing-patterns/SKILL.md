---
name: testing-patterns
description: "Testing strategy and craft: pyramid vs trophy, unit/integration/e2e split, fixtures, mocks vs fakes vs stubs, AAA pattern, flaky test diagnosis, coverage goals, property-based testing. Triggers: test, testing strategy, fixture, mock, stub, AAA, unit test, integration test, e2e, Playwright, Cypress, flaky, coverage, TDD, test pyramid. Load when writing, reviewing, or designing test suites."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Testing Patterns Skill

## Test Structure (AAA Pattern)

```python
def test_function_does_expected_thing():
    """Test description explaining what and why."""
    # Arrange - Set up test data and preconditions
    input_data = {"key": "value"}
    expected = "result"

    # Act - Execute the code under test
    result = function_under_test(input_data)

    # Assert - Verify the outcome
    assert result == expected
```

---

## Test Organization

```
tests/
├── conftest.py           # Shared fixtures
├── unit/                 # Unit tests (isolated)
│   ├── test_search_core.py
│   └── test_utils.py
├── integration/          # Integration tests
│   └── test_api.py
└── e2e/                  # End-to-end tests
    └── test_workflow.py
```

---

## Quality Targets

| Metric | Target |
|--------|--------|
| Coverage | >70% overall |
| New code | 100% |
| Core modules | >80% |
| No flaky tests | 0 |

---

## Language-Specific References

| Language | Reference | Key Topics |
|----------|-----------|------------|
| Python | [reference/python-pytest.md](reference/python-pytest.md) | Fixtures, mocking, parametrize, markers, conftest, running tests |
| TypeScript | [reference/typescript-vitest.md](reference/typescript-vitest.md) | Vitest/Jest, React Testing Library, mocking, running tests |
| PHP | [reference/php-phpunit.md](reference/php-phpunit.md) | PHPUnit test cases, mocking, running tests |
| Go | [reference/go-testing.md](reference/go-testing.md) | Table-driven tests, testify mocking, running tests |
| Flutter/Dart | [reference/flutter-testing.md](reference/flutter-testing.md) | Widget tests, unit tests, running tests |

For Python pytest patterns, see [reference/python-pytest.md](reference/python-pytest.md).

For TypeScript Vitest/Jest patterns, see [reference/typescript-vitest.md](reference/typescript-vitest.md).

For PHP PHPUnit patterns, see [reference/php-phpunit.md](reference/php-phpunit.md).

For Go testing patterns, see [reference/go-testing.md](reference/go-testing.md).

For Flutter/Dart testing patterns, see [reference/flutter-testing.md](reference/flutter-testing.md).

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It's too simple to test" | Simple code breaks in integration — test the contract, not the complexity |
| "Tests slow down development" | Tests slow down bugs reaching production — that's the point |
| "We'll add tests later" | Untested code accumulates — later means never, and coverage gaps compound |
| "Mocking everything is fine" | Over-mocking tests the mocks, not the code — mock at boundaries only |
| "100% coverage means no bugs" | Coverage measures execution, not correctness — focus on behavior assertions |

## Rules

- **MUST** follow Arrange-Act-Assert (AAA) structure in every test — unstructured tests degrade into procedural smoke tests
- **MUST** test behavior through the public interface, not internal implementation — tests coupled to internals break on every refactor
- **NEVER** test implementation details (private method return values, internal state flags) — they are not the contract
- **NEVER** hit real external services in unit tests — use fakes/stubs for boundaries; save real integration for integration tests
- **CRITICAL**: integration tests must hit real dependencies (database, message queue, external API) when mock-vs-prod divergence is a real risk. Mocked integration tests create false confidence.
- **MANDATORY**: flaky tests are bugs, not noise. Quarantine or delete them — a tolerated flaky test erodes the suite's credibility.

## Gotchas

- Coverage numbers are easy to game: include generated code, test files that import but do not assert, or wide `# pragma: no cover` usage. A 95% reported coverage with 60% real behavior assertion is common.
- Snapshot tests (Jest `.toMatchSnapshot()`, pytest-regressions) accept any output as "correct" on first run. An incorrect initial snapshot becomes the accepted baseline — review snapshots as carefully as code.
- Mocks configured with `any` matchers (e.g., `.mock.calls[0][0]` without a schema) pass even when the production call shape changes. Assert on specific arguments, not just "was called".
- Test isolation fails when globals leak (module-level mutable state, module-scoped fixtures, env vars set in one test). Flakiness that appears only under `pytest -n auto` or `jest --parallel` is usually shared state.
- Property-based tests (Hypothesis, fast-check) shrink failing examples to minimal reproducers, but shrinking time can dominate the run. For complex generators, cap shrink deadlines or seed the failing example for next-run reproducibility.
- Test pyramid vs trophy: the "right" ratio depends on stack. Frontend apps with rendering concerns benefit from more integration tests (trophy); pure backend services align better with pyramid. Don't cargo-cult one model.

## When NOT to Load

- For **running** the test suite — use `/test`
- For test-first development workflow — use `/tdd`
- For debugging a specific test failure — use `/debug` on the failure output
- For test framework choice in a new project — use `/app-builder`
- For performance/load testing — this skill covers correctness tests, not load
