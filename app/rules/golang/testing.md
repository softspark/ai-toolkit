---
language: golang
category: testing
version: "1.0.0"
---

# Go Testing

## Framework
- Use the standard `testing` package. No external test frameworks required.
- Use `testify/assert` and `testify/require` for readable assertions.
- Use `testify/mock` or `mockgen` for generating mocks.
- Use `go test -race` in CI to detect data races.

## File Naming
- Test files: `*_test.go` in the same package.
- Black-box tests: use `package foo_test` to test only exported API.
- White-box tests: use `package foo` to test internals.
- Test helpers: `testutil_test.go` or `testdata/` directory.

## Table-Driven Tests
- Use table-driven tests for functions with multiple input/output cases.
- Name each case: `{name: "empty input returns error", input: "", wantErr: true}`.
- Use `t.Run(tc.name, func(t *testing.T) { ... })` for subtests.
- Use `t.Parallel()` in subtests when tests are independent.

## Test Helpers
- Use `t.Helper()` in helper functions for correct line reporting.
- Use `t.Cleanup()` for teardown instead of defer in test functions.
- Use `testing.TB` interface to share helpers between tests and benchmarks.
- Use `testdata/` directory for test fixtures (excluded from build).

## Mocking
- Define interfaces at the consumer, not the provider.
- Use `mockgen` to auto-generate mocks from interfaces.
- Use `httptest.NewServer()` for HTTP integration tests.
- Use `httptest.NewRecorder()` for handler unit tests.

## Integration Tests
- Use build tags: `//go:build integration` to separate from unit tests.
- Use `testcontainers-go` for database/service containers in tests.
- Use `t.Setenv()` (Go 1.17+) for environment variable testing.

## Benchmarks
- Use `func BenchmarkXxx(b *testing.B)` with `b.N` loop.
- Use `b.ResetTimer()` after expensive setup.
- Use `b.ReportAllocs()` to track allocations.
- Run: `go test -bench=. -benchmem`.

## Coverage
- Run: `go test -coverprofile=coverage.out ./...`.
- View: `go tool cover -html=coverage.out`.
- Set minimum coverage threshold in CI.
- Focus coverage on business logic, not generated code.
