---
language: rust
category: frameworks
version: "1.0.0"
---

# Rust Frameworks

## Axum
- Use extractors for typed request parsing: `Path`, `Query`, `Json`, `State`.
- Use `Router::new().route("/path", get(handler))` for route definitions.
- Share state via `State(Arc<AppState>)` extractor.
- Implement `IntoResponse` on error types for clean error handling.
- Use Tower middleware layers for auth, logging, tracing, rate limiting.

## Actix-web
- Use extractors: `web::Path`, `web::Json`, `web::Data`.
- Use `App::new().service()` for route configuration.
- Share state with `web::Data<Arc<State>>`.
- Use `actix-web::middleware` for logging and error handling.

## Tokio
- Use `#[tokio::main]` for the entry point. Use `tokio::spawn` for tasks.
- Use `tokio::select!` for waiting on multiple futures.
- Use `tokio::time::timeout()` for operation deadlines.
- Use `tokio::sync::broadcast` for pub/sub, `mpsc` for work queues.
- Use `tokio::task::spawn_blocking()` for CPU-intensive work in async context.

## SQLx
- Use compile-time checked queries: `sqlx::query_as!(User, "SELECT ...")`.
- Use `PgPool` for connection pooling. Pass as shared state.
- Use migrations: `sqlx migrate add` and `sqlx migrate run`.
- Use `sqlx::FromRow` derive for automatic struct mapping.
- Set `DATABASE_URL` for compile-time query verification.

## Serde
- Use `#[derive(Serialize, Deserialize)]` on all DTOs.
- Use `#[serde(rename_all = "camelCase")]` for JSON API compatibility.
- Use `#[serde(deny_unknown_fields)]` for strict deserialization.
- Use `#[serde(default)]` for optional fields with defaults.
- Use `#[serde(skip_serializing_if = "Option::is_none")]` for clean output.

## Clap
- Use `#[derive(Parser)]` for CLI argument parsing.
- Use subcommands with enum variants: `#[derive(Subcommand)]`.
- Use `#[arg(env = "VAR_NAME")]` for env var fallback.
- Use `value_parser` for custom validation of arguments.

## Tracing
- Use `tracing` crate over `log` for structured, async-aware logging.
- Use `#[instrument]` attribute on functions for automatic span creation.
- Use `tracing_subscriber` with `EnvFilter` for runtime log level control.
- Add `trace_id` to all log entries for distributed tracing correlation.

## Testing Crates
- `mockall`: auto-generate mocks from traits.
- `wiremock`: HTTP mock server for integration tests.
- `testcontainers`: Docker containers for database tests.
- `proptest` / `quickcheck`: property-based testing.
