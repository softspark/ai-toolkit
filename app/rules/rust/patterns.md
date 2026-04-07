---
language: rust
category: patterns
version: "1.0.0"
---

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
