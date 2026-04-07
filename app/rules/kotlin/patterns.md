---
language: kotlin
category: patterns
version: "1.0.0"
---

# Kotlin Patterns

## Error Handling
- Use `Result<T>` for operations that can fail without exceptions.
- Use `runCatching { }` to wrap exception-throwing code into `Result`.
- Use `sealed class` hierarchies for domain errors: `sealed class AppError`.
- Prefer `fold()`, `getOrElse()`, `getOrNull()` over `getOrThrow()`.
- Use `require()` / `check()` for preconditions; they throw `IllegalArgumentException` / `IllegalStateException`.

## Coroutines
- Use `suspend` functions for sequential async operations.
- Use `coroutineScope { }` for structured concurrency with parallel work.
- Use `async { }` + `await()` for concurrent independent operations.
- Use `supervisorScope { }` when child failures should not cancel siblings.
- Use `withContext(Dispatchers.IO)` for blocking I/O in coroutine context.
- Use `flow { }` for cold asynchronous streams. Collect in lifecycle-aware scope.

## Flow Patterns
- Use `stateIn()` and `shareIn()` to convert cold flows to hot shared state.
- Use `combine()` to merge multiple flows into derived state.
- Use `flatMapLatest` for search-as-you-type patterns (cancel previous).
- Use `catch { }` operator for upstream error handling in flows.
- Use `flowOn(Dispatchers.IO)` to shift upstream execution context.

## Sealed Hierarchies
- Use `sealed interface` over `sealed class` when no shared state is needed.
- Use `when` expressions exhaustively on sealed types (compiler-enforced).
- Combine sealed types with data classes for typed state machines.
- Use sealed hierarchies for API responses: `Success<T>`, `Error`, `Loading`.

## Delegation
- Use `by lazy { }` for thread-safe lazy initialization.
- Use `by map` for delegated properties backed by a `Map`.
- Use class delegation (`class Foo : Bar by impl`) to favor composition.
- Use `observable` / `vetoable` delegates for reactive property changes.

## Builder Patterns
- Use DSL-style builders with `@DslMarker` annotation to prevent scope leakage.
- Use trailing lambda syntax for configuration blocks.
- Use `apply { }` for inline object configuration without a dedicated builder.
- Use `buildList { }`, `buildMap { }`, `buildString { }` for collection construction.

## Anti-Patterns
- Overusing `!!`: masks null-safety guarantees. Use safe calls or require.
- Nesting scope functions: `foo.let { it.also { ... }.run { } }` -- flatten logic.
- Blocking the main thread: use `withContext(Dispatchers.IO)` for I/O.
- Using `GlobalScope.launch`: leaks coroutines. Use structured concurrency.
- Mutable shared state without synchronization: use `Mutex` or `StateFlow`.
