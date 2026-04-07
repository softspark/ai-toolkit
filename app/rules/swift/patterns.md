---
language: swift
category: patterns
version: "1.0.0"
---

# Swift Patterns

## Error Handling
- Use `enum AppError: Error` for typed, exhaustive error handling.
- Use `throws` functions with `do-catch` for recoverable errors.
- Use `Result<Success, Failure>` for asynchronous error propagation.
- Use `try?` for optional conversion. Use `try!` only in tests or guaranteed paths.
- Add `LocalizedError` conformance for user-facing error messages.

## Protocol-Oriented Design
- Define capabilities as protocols: `protocol Fetchable { func fetch() async throws -> Data }`.
- Use protocol extensions for default implementations.
- Use protocol composition: `func process(_ item: Sendable & Codable)`.
- Use associated types for generic protocols: `associatedtype Output`.
- Use `some Protocol` (opaque types) for return types hiding concrete implementations.

## Async/Await
- Use `async` functions for all asynchronous operations.
- Use `async let` for concurrent, independent operations.
- Use `TaskGroup` for dynamic parallelism with collected results.
- Use `Task { }` to bridge sync to async. Avoid `.task { }` in views for complex logic.
- Use `withThrowingTaskGroup` for concurrent operations that can fail.

## Actors
- Use `actor` for thread-safe mutable state (replaces manual locks).
- Use `@MainActor` for UI-related state and methods.
- Use `nonisolated` for actor methods that do not access mutable state.
- Use `GlobalActor` for custom isolation domains.
- Minimize `await` calls on actors to reduce suspension points.

## SwiftUI Patterns
- Use `@State` for view-local mutable state.
- Use `@Binding` for child-to-parent state communication.
- Use `@Observable` (Observation framework) for model objects (preferred over `@ObservedObject`).
- Use `@Environment` for dependency injection: `@Environment(\.modelContext)`.
- Use `ViewModifier` for reusable view transformations.
- Extract subviews into separate structs for readability and performance.

## Codable
- Use `Codable` for JSON serialization/deserialization.
- Use `CodingKeys` enum for custom key mapping.
- Use `JSONDecoder` with `.convertFromSnakeCase` for API compatibility.
- Use `@propertyWrapper` for custom decoding strategies (e.g., date formats).
- Use `nestedContainer` for flattening nested JSON structures.

## Dependency Injection
- Use initializer injection for required dependencies.
- Use `@Environment` in SwiftUI for framework-provided values.
- Use `swift-dependencies` library for testable, controlled dependency management.
- Use `@Dependency(\.apiClient) var apiClient` for automatic resolution.

## Anti-Patterns
- Force-unwrapping optionals: use `guard let` or `??`.
- Massive view controllers/views: split into subviews and view models.
- Reference cycles: use `[weak self]` in closures capturing `self`.
- Blocking the main thread: use `Task` or `DispatchQueue.global()`.
- Stringly-typed APIs: use enums, protocols, and strong types.
