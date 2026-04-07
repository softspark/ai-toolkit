---
language: rust
category: coding-style
version: "1.0.0"
---

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
