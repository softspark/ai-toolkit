---
language: rust
category: testing
version: "1.0.0"
---

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
