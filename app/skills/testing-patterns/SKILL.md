---
name: testing-patterns
description: "Loaded when user asks about testing strategy, fixtures, or mocking"
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
