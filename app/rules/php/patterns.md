---
language: php
category: patterns
version: "1.0.0"
---

# PHP Patterns

## Error Handling
- Use custom exception hierarchies: `class DomainException extends RuntimeException`.
- Add context to exceptions: `throw new UserNotFoundException(userId: $id)`.
- Use `match` with `default => throw` for exhaustive error mapping.
- Use `set_exception_handler()` for global uncaught exception handling.
- Log exceptions with PSR-3 logger and structured context.

## Enums and Value Objects
- Use backed enums for database-persisted values: `enum Status: string`.
- Use `from()` for strict conversion, `tryFrom()` for nullable safe conversion.
- Implement methods on enums for behavior: `public function label(): string`.
- Use readonly classes for value objects: `readonly class Money { ... }`.
- Use constructor promotion for concise value object definitions.

## Repository Pattern
- Abstract data access behind repository interfaces.
- Repositories return domain entities, not Eloquent models or arrays.
- Use constructor injection for repository dependencies.
- Use specifications or criteria objects for complex query building.
- Keep repository methods focused: one query per method.

## Service Layer
- Use service classes for business logic. Keep controllers thin.
- Use action classes (single-method services) for discrete operations.
- Use DTOs for data transfer between layers. Never pass request objects to services.
- Use command/query separation: commands mutate, queries read.
- Inject dependencies via constructor. Never use `app()` helper in services.

## Collections and Iterators
- Use Laravel Collections or standalone `illuminate/collections` for data manipulation.
- Chain `map()`, `filter()`, `reduce()` for declarative data transformation.
- Use `LazyCollection` for memory-efficient processing of large datasets.
- Use generators (`yield`) for lazy iteration over large result sets.
- Prefer `collect()` pipeline over nested loops.

## Async Patterns
- Use Laravel Queues for background job processing.
- Use `dispatch()` for fire-and-forget. Use `Bus::chain()` for sequential jobs.
- Use `ShouldQueue` interface on jobs, listeners, and mailables.
- Set `$tries`, `$timeout`, `$backoff` on job classes.
- Use `batch()` for parallel job execution with completion callback.

## Event-Driven
- Use events and listeners for decoupled side effects.
- Use domain events for cross-boundary communication.
- Use `ShouldQueue` on listeners for async event handling.
- Use event subscribers for grouping related listeners.
- Keep event payloads minimal: IDs and timestamps, not full objects.

## Anti-Patterns
- Fat controllers: move logic to services/actions.
- God models: split into focused models with traits or separate classes.
- Using `DB::raw()` without parameterization: SQL injection risk.
- Static method calls for testable dependencies: use DI instead.
- Returning mixed types: use typed returns or Result objects.
