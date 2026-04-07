---
language: dart
category: patterns
version: "1.0.0"
---

# Dart Patterns

## Error Handling
- Use typed exceptions for domain errors: `class UserNotFoundException implements Exception`.
- Use `try-catch` with specific exception types. Avoid bare `catch (e)`.
- Use `rethrow` to preserve stack trace when re-raising exceptions.
- Use `Result<T, E>` pattern (e.g., `dartz` Either) for expected failures.
- Use `Future.catchError()` only when `async/await` is not applicable.

## State Management (Flutter)
- Use Riverpod for compile-safe, testable state management.
- Use BLoC pattern for event-driven state with clear input/output.
- Use `ChangeNotifier` / `ValueNotifier` for simple local state.
- Use `StateNotifier` (Riverpod) for immutable state transitions.
- Keep state classes immutable. Use `copyWith()` for updates.

## Riverpod
- Use `@riverpod` annotation (code gen) for provider definitions.
- Use `ref.watch()` for reactive dependencies. Use `ref.read()` for one-time access.
- Use `AsyncNotifier` for async state management.
- Use `autoDispose` for providers that should clean up when unused.
- Use `family` modifier for parameterized providers.

## BLoC Pattern
- Separate events (input), states (output), and logic (bloc).
- Use `sealed class` for events and states (exhaustive `switch`).
- Use `Emitter<State>` for emitting state transitions.
- Use `transformEvents()` for debouncing search inputs.
- Use `BlocObserver` for global logging and error tracking.

## Repository Pattern
- Abstract data sources behind repository interfaces.
- Repositories return domain models, not DTOs or raw data.
- Use `Future<T>` for single values, `Stream<T>` for real-time updates.
- Cache data in repository layer when appropriate.
- Inject repositories via constructor. Use Riverpod/GetIt for DI.

## Freezed (Code Generation)
- Use `@freezed` for immutable data classes with `copyWith`, equality, `toString`.
- Use `@freezed` sealed unions for state modeling: `factory State.loading()`.
- Use `when()` / `map()` for exhaustive pattern matching on freezed unions.
- Run `dart run build_runner build` after modifying freezed classes.

## Async Patterns
- Use `Stream.asyncMap()` for transforming streams with async operations.
- Use `StreamController<T>` for custom streams. Close in `dispose()`.
- Use `Completer<T>` to bridge callback APIs to Future-based APIs.
- Use `Timer.periodic()` for polling. Cancel in `dispose()`.
- Use `compute()` (Flutter) for CPU-intensive work on isolates.

## Anti-Patterns
- Using `dynamic` type: defeats type safety. Use `Object?` or generics.
- Not disposing controllers/subscriptions: causes memory leaks.
- Putting business logic in widgets: extract to services/blocs.
- Using `setState()` for global state: use proper state management.
- Deep widget nesting: extract sub-widgets as separate classes.
