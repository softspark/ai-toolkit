---
language: golang
category: frameworks
version: "1.0.0"
---

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
