---
name: golang-rules
description: "Go coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .go, go.mod, go.sum, Gin, Echo, Gorilla, testing, gofmt. Load when writing, reviewing, or editing Go code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Go Rules

These rules come from `app/rules/golang/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Go. Apply them when writing or
reviewing Go code.

# Go Coding Style

## Naming
- MixedCaps/mixedCaps only. No underscores in Go names (except test functions).
- Exported: `PascalCase`. Unexported: `camelCase`. Acronyms: `HTTPClient`, `userID`.
- Short variable names in small scopes: `i`, `r`, `w`, `ctx`, `err`.
- Descriptive names in larger scopes: `userRepository`, `requestTimeout`.
- Package names: short, lowercase, singular (`auth`, `user`, not `utils`, `helpers`).

## Packages
- One package per directory. Package name = directory name.
- Avoid `util`, `common`, `helpers` packages. Name by what it provides.
- Keep package APIs small. Export only what consumers need.
- Use `internal/` directory for packages not meant for external consumption.

## Functions
- Accept interfaces, return structs.
- First parameter `ctx context.Context` if the function does I/O or may be cancelled.
- Return `(result, error)` tuple. Error is always last return value.
- Use named return values only for documentation, not for naked returns.
- Keep functions short. If >40 lines, consider splitting.

## Error Handling
- Always check errors. Never use `_` to discard errors silently.
- Wrap errors with context: `fmt.Errorf("fetching user %s: %w", id, err)`.
- Use sentinel errors (`var ErrNotFound = errors.New(...)`) for expected conditions.
- Use `errors.Is()` and `errors.As()` for error checking, not type assertions.

## Formatting
- Use `gofmt` / `goimports`. No formatting debates in Go.
- Use `golangci-lint` with a `.golangci.yml` config in CI.
- Use `go vet` as minimum static analysis.

## Struct Design
- Use struct embedding for composition, not inheritance.
- Prefer value receivers for small structs, pointer receivers for large or mutable.
- Be consistent: all methods on a type use the same receiver type.
- Use struct literals with field names: `User{Name: "Ada", Age: 30}`.

## Concurrency
- Do not start goroutines without a plan to stop them.
- Use `sync.WaitGroup` or `errgroup.Group` to coordinate goroutines.
- Use channels for communication, mutexes for state protection.
- Prefer `context.Context` for cancellation and timeouts over manual signaling.

# Go Frameworks

## Standard Library HTTP
- Use `http.NewServeMux()` (Go 1.22+ with method patterns) for simple APIs.
- Use `http.HandlerFunc` for handlers. Compose with middleware pattern.
- Use `context.Context` from `r.Context()` in all handlers.
- Use `http.TimeoutHandler` to prevent slow handlers from hanging.

## Chi / Gorilla Mux
- Use Chi for routing with middleware chains and URL params.
- Use `chi.URLParam(r, "id")` to extract path parameters.
- Use middleware groups: `r.Group(func(r chi.Router) { r.Use(authMiddleware) })`.
- Prefer Chi over Gorilla Mux (Gorilla was archived, Chi actively maintained).

## Gin / Echo
- Use Gin for high-performance APIs with built-in validation.
- Use binding tags: `binding:"required,email"` on struct fields.
- Use middleware for cross-cutting: logging, recovery, CORS, auth.
- Use `c.ShouldBindJSON()` over `c.BindJSON()` to handle errors yourself.

## GORM / sqlx / pgx
- Use `sqlx` for SQL-first with struct scanning (lightweight).
- Use `pgx` directly for PostgreSQL-specific features and performance.
- Use GORM only when rapid prototyping outweighs SQL control.
- Always use prepared statements or parameterized queries.
- Use `sqlx.In()` for dynamic IN clauses safely.

## gRPC
- Define services in `.proto` files. Generate Go code with `protoc`.
- Use interceptors for auth, logging, and tracing (equivalent to middleware).
- Use deadlines (context timeout) on every RPC call.
- Use streaming RPCs for real-time data, unary for request-response.

## Configuration
- Use `envconfig` or `viper` for configuration from env/files.
- Use struct tags for env mapping: `envconfig:"DATABASE_URL"`.
- Validate config at startup. Fail fast on invalid configuration.
- Use `flag` package for CLI arguments in tools and utilities.

## Observability
- Use `slog` (Go 1.21+) for structured logging. Replace `log` package.
- Use OpenTelemetry for distributed tracing and metrics.
- Export metrics via Prometheus endpoint.
- Use `pprof` for CPU and memory profiling in development.

## Project Layout
- Follow Standard Go Project Layout: `cmd/`, `internal/`, `pkg/`.
- Entry points in `cmd/appname/main.go`.
- Business logic in `internal/`. Shared libraries in `pkg/`.
- Use `Makefile` for common tasks: build, test, lint, run.

# Go Patterns

## Error Handling
- Wrap errors with context at each call site: `fmt.Errorf("loading config: %w", err)`.
- Define domain error types with `errors.New()` or custom error structs.
- Use `errors.Is()` for sentinel errors, `errors.As()` for typed errors.
- Return errors, do not panic. Reserve `panic` for truly unrecoverable states.
- Handle errors immediately after the call. No deferred error checking.

## Concurrency
- Use `errgroup.Group` for concurrent operations that may fail.
- Use `sync.Once` for one-time initialization (singleton pattern).
- Use `sync.Map` only for append-mostly maps with concurrent access.
- Use buffered channels as semaphores: `sem := make(chan struct{}, maxConcurrency)`.
- Prefer `context.WithTimeout` over manual timers for deadline management.

## Interface Design
- Keep interfaces small: 1-3 methods. Compose larger interfaces from smaller ones.
- Define interfaces where they are consumed, not where they are implemented.
- Use `io.Reader`, `io.Writer`, `fmt.Stringer` and standard interfaces where applicable.
- Avoid returning interfaces from functions. Return concrete types.

## Options Pattern
- Use functional options for constructors with many optional parameters.
- Pattern: `func WithTimeout(d time.Duration) Option { return func(c *Client) { c.timeout = d } }`.
- Provide sensible defaults. Options override defaults.
- Use `Option` type alias: `type Option func(*Config)`.

## Dependency Injection
- Pass dependencies through constructor functions, not global variables.
- Accept interfaces in constructors: `func NewService(repo UserRepo) *Service`.
- Use `wire` or manual wiring in `main()` for dependency graph.
- Avoid init() functions for anything other than simple registration.

## Resource Management
- Use `defer` for cleanup immediately after acquiring a resource.
- Use `context.Context` for cancellation propagation across goroutines.
- Close channels from the sender side, never the receiver.
- Use `sync.Pool` for frequently allocated temporary objects (buffers).

## Anti-Patterns
- Global mutable state: use dependency injection instead.
- `interface{}` / `any` everywhere: use generics (Go 1.18+) or specific types.
- Goroutine leaks: always ensure goroutines can exit.
- Ignoring `context.Context`: propagate it through all I/O paths.
- Large interfaces: split into focused, composable pieces.

# Go Security

## Input Validation
- Validate all input at API boundaries. Use struct tags or manual validation.
- Use `validator` package for struct validation: `validate:"required,email"`.
- Parse and validate numeric IDs: `strconv.Atoi()` with error checking.
- Limit request body size: `http.MaxBytesReader(w, r.Body, maxBytes)`.

## SQL Injection
- Always use parameterized queries: `db.Query("SELECT * FROM users WHERE id = $1", id)`.
- Never concatenate user input into SQL strings.
- Use `sqlx.In()` for safe dynamic IN clauses.
- Use ORM query builders (GORM, Ent) for dynamic query construction.

## Command Injection
- Use `exec.Command("binary", args...)` with separate arguments, not shell strings.
- Never use `exec.Command("sh", "-c", userInput)`.
- Validate and sanitize file paths against traversal attacks.
- Use `filepath.Clean()` and verify paths are within allowed directories.

## Cryptography
- Use `crypto/rand` for random values, never `math/rand` for security.
- Use `bcrypt` or `argon2` for password hashing: `golang.org/x/crypto/bcrypt`.
- Use `crypto/subtle.ConstantTimeCompare()` for timing-safe comparisons.
- Use `crypto/tls` with `tls.Config{MinVersion: tls.VersionTLS12}`.

## Secrets
- Load secrets from environment variables: `os.Getenv("SECRET_KEY")`.
- Never hardcode secrets, tokens, or API keys in source code.
- Use `go-envconfig` or similar for validated env var loading.
- Use Go build tags or ldflags for build-time configuration.

## HTTP Security
- Set `ReadTimeout`, `WriteTimeout`, `IdleTimeout` on `http.Server`.
- Use `helmet`-equivalent headers: HSTS, X-Content-Type-Options, X-Frame-Options.
- Implement rate limiting with `golang.org/x/time/rate` or middleware.
- Use `net/http` with TLS. Never serve production HTTP without encryption.

## Concurrency Safety
- Use `sync.Mutex` or `sync.RWMutex` for shared mutable state.
- Run `go test -race` in CI to detect data races.
- Avoid shared state where possible. Prefer channels for communication.
- Use `atomic` package for simple counters and flags.

## Dependencies
- Run `govulncheck ./...` in CI to check for known vulnerabilities.
- Use `go mod tidy` to remove unused dependencies.
- Pin dependencies via `go.sum`. Review dependency changes in PRs.
- Audit transitive dependencies. Use `go mod graph` to inspect the tree.

## Error Information Disclosure
- Never expose internal error messages to clients.
- Log detailed errors server-side, return generic messages to clients.
- Use error codes for machine-readable error classification.
- Do not include stack traces in production API responses.

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
