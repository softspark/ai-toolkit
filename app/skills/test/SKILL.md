---
name: test
description: "Run the project's test suite with coverage reporting, auto-detecting the framework (pytest, vitest, jest, flutter test, go test, cargo test, phpunit). Use when the user asks to run existing tests — not to author new ones test-first."
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

## Rules

- **MUST** detect the framework automatically via `detect-runner.py` — do not assume
- **NEVER** modify tests to make them pass
- **CRITICAL**: coverage reporting must use the project's configured tool (`--cov=src`, `--coverage`, etc.) — do not invent flags
- **MANDATORY**: when a test fails, report the failure exactly; do not paraphrase

## Gotchas

- `pytest --cov=src` inflates coverage when `tests/` lives under `src/` — test files count toward covered lines. Either move `tests/` out, or use `--cov=src --cov-branch --cov-report=term-missing` with an explicit `[tool.coverage.run] omit = ["tests/*"]` in `pyproject.toml`.
- `go test ./...` runs packages in parallel by default; a test depending on shared global state may pass alone and fail in the suite. If flakiness appears only under `./...`, suspect shared state, not a bug in the test.
- `flutter test` without an emulator falls back to the headless "null platform" — widget tests that require a render surface are **silently skipped**. CI without a display must add `flutter test --platform vm` or a virtual framebuffer.
- `vitest run` and `jest` interpret glob patterns differently: `*.test.ts` in vitest matches filenames, in jest matches paths. Passing the same CLI arg to both produces different test sets — use the framework-native config file when possible.
- `pytest --lf` (last-failed) silently runs **all** tests if there is no cache from a prior run. First-time runs in CI therefore ignore `--lf` and re-run everything, which can hide "only failed tests" bugs in local runs.

## When NOT to Use

- To write new tests test-first — use `/tdd`
- To author test design patterns — use `/testing-patterns` (knowledge skill)
- To debug a failing test — use `/debug` after `/test` surfaces the failure
- For performance/load testing — use dedicated tooling, not `/test`
