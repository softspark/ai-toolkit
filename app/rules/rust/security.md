---
language: rust
category: security
version: "1.0.0"
---

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
