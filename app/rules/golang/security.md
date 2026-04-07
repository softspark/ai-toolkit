---
language: golang
category: security
version: "1.0.0"
---

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
