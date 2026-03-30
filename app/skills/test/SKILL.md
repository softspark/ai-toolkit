---
name: test
description: "Run tests with coverage analysis and reporting"
effort: medium
disable-model-invocation: true
argument-hint: "[file or pattern]"
allowed-tools: Bash, Read, Grep
hooks:
  PostToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'Reminder: check test coverage meets threshold (>70%)'"
---

# Test Runner

$ARGUMENTS

Run tests based on detected project type.

## Project context

- Project config: !`cat package.json 2>/dev/null || cat pyproject.toml 2>/dev/null || cat pubspec.yaml 2>/dev/null || echo "unknown"`

## Auto-Detection

Run the bundled script to detect test framework:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/detect-runner.py .
```

| File Found | Runner | Command |
|------------|--------|---------|
| `pyproject.toml` / `setup.py` | pytest | `pytest --cov=src --cov-report=term-missing tests/` |
| `package.json` (vitest) | vitest | `npx vitest run --coverage` |
| `package.json` (jest) | jest | `npx jest --coverage` |
| `pubspec.yaml` | flutter test | `flutter test --coverage` |
| `go.mod` | go test | `go test -cover ./...` |
| `Cargo.toml` | cargo test | `cargo test` |
| `composer.json` | phpunit | `./vendor/bin/phpunit --coverage-text` |

## Usage

```
/test                        # Run all tests
/test path/to/test_file      # Run specific test file
/test -k "test_name"         # Run tests matching pattern
/test --coverage             # Run with coverage report
```

## Common Options by Runner

### Python (pytest)
```bash
pytest tests/                          # All tests
pytest tests/unit/test_example.py      # Specific file
pytest -k "test_search"               # Pattern match
pytest --lf                            # Last failed only
pytest -v                              # Verbose
```

### JavaScript/TypeScript (vitest/jest)
```bash
npx vitest run                         # All tests
npx vitest run src/utils.test.ts       # Specific file
npx vitest run --reporter=verbose      # Verbose
npx jest --testPathPattern=utils       # Pattern match
```

### PHP (phpunit)
```bash
./vendor/bin/phpunit                   # All tests
./vendor/bin/phpunit tests/Unit/ExampleTest.php  # Specific
./vendor/bin/phpunit --filter testName # Pattern match
```

### Flutter/Dart
```bash
flutter test                           # All tests
flutter test test/widget_test.dart     # Specific file
dart test --name="pattern"             # Pattern match
```

### Go
```bash
go test ./...                          # All tests
go test ./pkg/utils/                   # Specific package
go test -run TestName ./...            # Pattern match
go test -v ./...                       # Verbose
```

## Coverage Targets

- Overall: >70%
- Core modules: >80%
- New code: 100% (for PRs)

## Test Structure Convention

```
tests/               # or test/, spec/, __tests__/
├── unit/            # Fast, isolated tests
├── integration/     # Tests with external dependencies
└── e2e/             # End-to-end tests
```
