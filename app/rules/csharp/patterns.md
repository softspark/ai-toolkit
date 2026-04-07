---
language: csharp
category: patterns
version: "1.0.0"
---

# C# Patterns

## Error Handling
- Use exceptions for truly exceptional conditions. Use `Result<T>` pattern for expected failures.
- Create domain exception hierarchies: `class DomainException : Exception`.
- Use `when` clause in catch: `catch (HttpRequestException e) when (e.StatusCode == 404)`.
- Use `ExceptionDispatchInfo.Capture(e).Throw()` to preserve original stack trace.
- Return `Result<T, Error>` types for operations with expected failure modes.

## Async Patterns
- Use `Task.WhenAll()` for concurrent independent operations.
- Use `SemaphoreSlim` for async-compatible resource limiting.
- Use `Channel<T>` for async producer-consumer patterns.
- Use `IAsyncEnumerable<T>` for streaming data from async sources.
- Use `Polly` for retry, circuit breaker, and timeout policies.
- Never use `.Result` or `.Wait()` on tasks (deadlock risk). Always `await`.

## Dependency Injection
- Use constructor injection exclusively. Avoid service locator pattern.
- Register services in `Program.cs` or `IServiceCollection` extension methods.
- Use `Scoped` for request-lifetime services, `Singleton` for stateless, `Transient` for lightweight.
- Use `IOptions<T>` pattern for configuration injection.
- Validate DI registrations at startup with `ValidateOnBuild = true`.

## LINQ
- Use method syntax for complex queries. Use query syntax for joins.
- Use `FirstOrDefault()` over `First()` for safe access.
- Use `AsNoTracking()` for read-only EF Core queries (performance).
- Avoid materializing large collections: use `IQueryable<T>` until final projection.
- Use `Select()` to project only needed columns from database queries.

## Disposable Pattern
- Implement `IAsyncDisposable` for async cleanup.
- Use `await using var resource = ...;` for deterministic async disposal.
- Use `IDisposable` with `using` declaration (C# 8) for scope-based cleanup.
- Register disposable services in DI container (auto-disposed at scope end).

## Mediator / CQRS
- Use MediatR for command/query separation and pipeline behaviors.
- Commands: `IRequest<Result>` for mutations. Queries: `IRequest<T>` for reads.
- Use pipeline behaviors for cross-cutting: validation, logging, transactions.
- Keep handlers thin: delegate to domain services for business logic.

## Value Objects
- Use `record` types for value objects with structural equality.
- Use factory methods with validation: `public static Result<Email> Create(string value)`.
- Override `ToString()` for logging-friendly representations.
- Use implicit/explicit operators sparingly for primitive wrapper conversions.

## Anti-Patterns
- Service locator: inject dependencies, do not resolve from container.
- `async void`: use only for event handlers. Everything else returns `Task`.
- Nested `try-catch`: flatten with early returns or guard clauses.
- Anemic domain model: put behavior in domain objects, not only services.
- Over-abstracting: do not create interfaces for classes with only one implementation.
