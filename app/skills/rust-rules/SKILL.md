---
name: rust-rules
description: "Rust coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .rs, Cargo.toml, Cargo.lock, Tokio, Axum, Serde, clippy, cargo test. Load when writing, reviewing, or editing Rust code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Rust Rules

These rules come from `app/rules/rust/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Rust. Apply them when writing or
reviewing Rust code.

# Rust Coding Style

## Naming
- snake_case: functions, methods, variables, modules, crates.
- PascalCase: types, traits, enums, structs, type parameters.
- SCREAMING_SNAKE: constants and statics.
- Short lifetimes: `'a`, `'b`. Descriptive only when multiple coexist: `'input`, `'output`.
- Crate names: kebab-case in Cargo.toml, snake_case in code.

## Ownership
- Borrow (`&T`) when you only need to read. Own (`T`) when storing or consuming.
- Use `&str` over `String` in function parameters when possible.
- Use `Cow<'_, str>` when you sometimes need to allocate.
- Avoid `.clone()` as a first resort -- restructure ownership instead.
- Use `Arc<T>` only when shared ownership across threads is required.

## Types
- Use newtypes for domain primitives: `struct UserId(Uuid)`.
- Use `#[derive(Debug, Clone, PartialEq)]` on data types.
- Implement `Display` for user-facing output, `Debug` for developer output.
- Use `#[non_exhaustive]` on public enums and structs for future compatibility.
- Prefer enums over boolean flags for state representation.

## Functions
- Return `Result<T, E>` for operations that can fail. Avoid panicking.
- Use `impl Trait` in argument position for flexibility, return position for simplicity.
- Use `where` clauses for complex bounds instead of inline.
- Prefer iterators over index-based loops.
- Use `let-else` (1.65+) for early-exit pattern matching.

## Modules
- Use `mod.rs` or filename-based modules. Be consistent within the project.
- Re-export public API from `lib.rs` for a clean surface.
- Keep modules focused. One major type or concept per module.
- Use `pub(crate)` for internal-only visibility.

## Formatting
- Use `rustfmt` with default settings. Do not fight the formatter.
- Use `clippy` with `-D warnings` in CI. Fix all warnings.
- Set MSRV (Minimum Supported Rust Version) in `Cargo.toml`.

## Cargo
- Use workspace dependencies to unify versions across crates.
- Use feature flags for optional functionality.
- Set `edition = "2021"` (or latest stable edition).
- Use `[profile.release]` with `lto = true` and `codegen-units = 1` for production.

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

# Rust Patterns

## Error Handling
- Use `thiserror` for library error types (structured, typed enums).
- Use `anyhow` for application/binary code (flexible, context-rich).
- Wrap errors with context: `.with_context(|| format!("loading {path}"))?`.
- Use `#[from]` attribute for automatic error conversion in thiserror enums.
- Map domain errors to HTTP/gRPC errors at API boundaries only.

## Builder Pattern
- Use builder for structs with many optional fields.
- Return `Result` from `build()` when validation is needed.
- Use `#[derive(Default)]` + `TypedBuilder` derive macro for compile-time safety.
- Chain setter methods returning `Self` for ergonomic API.

## Newtype Pattern
- Wrap primitive types for type safety: `struct Email(String)`.
- Validate in constructor: `Email::new(raw) -> Result<Self, ValidationError>`.
- Implement `Deref` only when the inner type's full API is appropriate.
- Use `#[repr(transparent)]` for zero-cost newtypes in FFI.

## Trait Design
- Keep traits small and focused. Compose with supertraits.
- Use associated types for output types: `type Output;`.
- Use default method implementations for common behavior.
- Use extension traits to add methods to foreign types.

## Async Patterns
- Use `tokio` as the async runtime for most applications.
- Use `tokio::spawn` for concurrent tasks, `tokio::select!` for racing.
- Use `tokio::sync::mpsc` for channels, `tokio::sync::Mutex` for async locks.
- Prefer `async fn` in traits (Rust 1.75+) over manual `Pin<Box<dyn Future>>`.
- Use `tower` middleware pattern for layered request processing.

## Iterator Patterns
- Use `.iter()` / `.into_iter()` / `.iter_mut()` appropriately.
- Chain: `filter().map().collect()` instead of manual loops.
- Use `collect::<Result<Vec<_>, _>>()` to short-circuit on first error.
- Implement `IntoIterator` for custom collections.

## State Machine
- Use enums with data variants for state machines.
- Use `match` exhaustively -- compiler prevents missing states.
- Encode valid transitions in the type system when possible.
- Use typestate pattern for compile-time state transition enforcement.

## Anti-Patterns
- `.unwrap()` in library code -- return `Result` or `Option`.
- `.clone()` to fix borrow checker -- restructure ownership.
- `Arc<Mutex<T>>` as first approach -- consider channels or actors.
- `Box<dyn Error>` in libraries -- use typed error enums.
- Ignoring `#[must_use]` warnings -- handle or explicitly discard with `let _ =`.

# Rust Security

## Memory Safety
- Rust's ownership system prevents most memory bugs. Do not circumvent it.
- Minimize `unsafe` blocks. Document every safety invariant with `// SAFETY:`.
- Use `#![forbid(unsafe_code)]` in library crates when possible.
- Audit all `unsafe` code during review. Treat it as a security boundary.
- Use `miri` in CI for detecting undefined behavior in unsafe code.

## Input Validation
- Validate all external input before processing. Use newtypes with validation.
- Use `serde` with `#[serde(deny_unknown_fields)]` for strict deserialization.
- Set size limits on deserialized data: `#[serde(deserialize_with = "...")]`.
- Validate string lengths, numeric ranges, and formats at API boundaries.

## SQL Injection
- Use `sqlx` parameterized queries: `sqlx::query!("SELECT * WHERE id = $1", id)`.
- Never build SQL strings with `format!()` using user input.
- Use `sqlx::query_builder::QueryBuilder` for dynamic query construction.
- Type-check queries at compile time with `sqlx::query!` macro.

## Cryptography
- Use `ring` or `rustcrypto` crates for cryptographic operations.
- Use `argon2` crate for password hashing.
- Use `subtle::ConstantTimeEq` for timing-safe comparisons.
- Use `rand` crate with `OsRng` for cryptographically secure random values.
- Never implement custom cryptographic algorithms.

## Dependencies
- Run `cargo audit` in CI to check for known vulnerabilities.
- Run `cargo deny check` for license compliance and advisory checking.
- Use `cargo tree -d` to find duplicate dependencies.
- Review `build.rs` scripts in dependencies -- they execute at compile time.
- Minimize dependency count. Each crate is a potential attack surface.

## Secrets
- Load secrets from environment: `std::env::var("SECRET")`.
- Use `secrecy` crate for values that should not be logged or displayed.
- Zeroize sensitive data after use with `zeroize` crate.
- Never hardcode secrets, tokens, or keys in source code.

## Panic Safety
- Use `Result` and `Option` instead of panicking in library code.
- Use `catch_unwind` at FFI boundaries to prevent unwinding across languages.
- Set `panic = "abort"` in release profile to prevent panic exploitation.
- Avoid `unwrap()` and `expect()` on user-controlled data.

## Network Security
- Use `rustls` over OpenSSL for TLS (pure Rust, memory-safe).
- Set timeouts on all network operations.
- Implement rate limiting on public endpoints.
- Validate and sanitize URLs before making outbound requests.

## Supply Chain
- Use `cargo-vet` to track third-party audit status.
- Use `cargo-crev` for community code reviews.
- Enable `Cargo.lock` in version control for applications (not libraries).
- Prefer well-maintained crates with recent activity and security audits.

# Rust Testing

## Unit Tests
- Place unit tests in `#[cfg(test)] mod tests` at the bottom of each file.
- Use `#[test]` attribute. Use `#[tokio::test]` for async tests.
- Name tests descriptively: `fn rejects_invalid_email()`.
- Access private items directly -- unit test modules are inside the parent module.

## Integration Tests
- Place in `tests/` directory. Each file compiles as a separate crate.
- Test only the public API from integration tests.
- Use `tests/common/mod.rs` for shared test utilities.
- Name files by feature area: `tests/api_test.rs`, `tests/auth_test.rs`.

## Assertions
- Use `assert_eq!(actual, expected)` with the actual value first.
- Use `assert!(matches!(result, Ok(_)))` for pattern matching in assertions.
- Use custom error messages: `assert_eq!(x, 5, "expected x to be 5, got {x}")`.
- Use `#[should_panic(expected = "message")]` for testing panics.

## Result Testing
- Use `-> Result<(), Box<dyn Error>>` return type in tests for `?` support.
- Test error variants: `assert!(matches!(result, Err(AppError::NotFound(_))))`.
- Use `.unwrap()` in tests when failure means a bug in the test.

## Mocking
- Use `mockall` crate with `#[automock]` on trait definitions.
- Use `expect_*` methods to set expectations on mock behavior.
- Prefer trait-based DI for testability. Accept `impl Trait` in constructors.
- Use `fake` crate for generating realistic test data.

## Property Testing
- Use `proptest` for property-based testing on parsing and validation.
- Define strategies: `prop::string::string_regex("[a-z]+@[a-z]+\\.[a-z]{2,4}")`.
- Use `proptest!` macro for concise property test definitions.
- Test invariants: serialization roundtrips, ordering consistency.

## Benchmarks
- Use `criterion` crate for statistical benchmarks (not built-in `#[bench]`).
- Use `black_box()` to prevent compiler optimization of benchmark code.
- Run benchmarks before and after optimization to measure impact.
- Use `cargo bench` with `-- --save-baseline` for regression tracking.

## CI Pipeline
- Minimum: `cargo fmt --check && cargo clippy -- -D warnings && cargo test`.
- Add `cargo audit` for vulnerability scanning.
- Use `cargo nextest` for parallel test execution and better output.
- Enable `-Z randomize-layout` in nightly CI to catch layout-dependent code.
