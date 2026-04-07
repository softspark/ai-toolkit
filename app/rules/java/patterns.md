---
language: java
category: patterns
version: "1.0.0"
---

# Java Patterns

## Error Handling
- Use unchecked exceptions for programming errors (`IllegalArgumentException`).
- Use checked exceptions only for recoverable conditions the caller must handle.
- Create domain exception hierarchy: `AppException` -> `NotFoundException`, etc.
- Never catch `Exception` or `Throwable` broadly. Catch specific types.
- Use `try-with-resources` for all `AutoCloseable` resources.

## Immutability
- Use `record` for immutable value objects (Java 16+).
- Use `List.copyOf()`, `Map.copyOf()` to create unmodifiable copies.
- Make fields `private final`. No setters unless mutation is required.
- Return defensive copies of mutable collections from getters.
- Use builder pattern for constructing immutable objects with many fields.

## Optional
- Use `Optional<T>` as return type for methods that may not return a value.
- Chain: `optional.map(...).orElseThrow(...)`. Avoid `isPresent()` + `get()`.
- Never use `Optional` for fields, method parameters, or collection elements.
- Use `Optional.empty()` over `null`. Use `Optional.ofNullable()` at boundaries.

## Streams
- Use streams for transformations: `filter`, `map`, `collect`.
- Avoid side effects in stream operations. Keep them pure.
- Use `Collectors.toUnmodifiableList()` for immutable results.
- Prefer `for` loop for simple iterations that do not transform data.
- Use `Stream.of()` or `IntStream.range()` for generating sequences.

## Dependency Injection
- Use constructor injection exclusively. No field or setter injection.
- Accept interfaces in constructors, not implementations.
- Use `@Component`, `@Service`, `@Repository` for Spring-managed beans.
- Keep the number of constructor dependencies under 5. Split if more.

## Concurrency
- Use `ExecutorService` and `CompletableFuture` for async operations.
- Use `virtual threads` (Java 21+) for I/O-bound concurrent work.
- Use `ConcurrentHashMap`, `AtomicInteger` for thread-safe operations.
- Avoid `synchronized` blocks when possible -- use higher-level concurrency.
- Use `ReentrantReadWriteLock` for read-heavy shared state.

## Design Patterns
- Use Strategy pattern (via interfaces) over switch/if-else chains.
- Use Factory methods for flexible object creation.
- Use Decorator pattern for composable behavior augmentation.
- Avoid Singleton pattern -- use DI container for lifecycle management.

## Anti-Patterns
- Returning `null` from methods -- use `Optional` or empty collections.
- Mutable DTOs with getters/setters -- use records.
- God classes with 20+ dependencies -- split by responsibility.
- String typing for domain values -- use types, enums, or value objects.
