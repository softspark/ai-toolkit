---
language: java
category: coding-style
version: "1.0.0"
---

# Java Coding Style

## Naming
- PascalCase: classes, interfaces, enums, records, annotations.
- camelCase: methods, variables, parameters.
- UPPER_SNAKE: constants (`static final`).
- Package names: lowercase, dot-separated, reverse domain (`com.company.project`).
- No Hungarian notation. No `I` prefix on interfaces.

## Modern Java (17+)
- Use `record` for immutable data carriers. No need for Lombok in most cases.
- Use `sealed` classes/interfaces for restricted hierarchies.
- Use pattern matching: `if (obj instanceof String s)` instead of cast.
- Use `switch` expressions with arrow syntax and exhaustiveness.
- Use text blocks (`"""`) for multiline strings (SQL, JSON, HTML).

## Types
- Use `var` for local variables when the type is obvious from the right-hand side.
- Use `Optional<T>` for return types that may be absent. Never for fields or params.
- Prefer `List.of()`, `Map.of()`, `Set.of()` for immutable collections.
- Use `Stream` for collection transformations. Avoid streams for simple iterations.

## Classes
- Prefer composition over inheritance. Use interfaces for abstraction.
- Keep classes focused: single responsibility.
- Use `final` on classes not designed for extension.
- Use `private` constructors + static factory methods for controlled instantiation.
- Records over POJOs for value types. Lombok only if records are insufficient.

## Methods
- Max 20-30 lines per method. Extract when longer.
- Use `@Override` on every overridden method.
- Return empty collections over `null`. Use `Collections.emptyList()` or `List.of()`.
- Avoid checked exceptions for programming errors. Use runtime exceptions.

## Formatting
- Use project formatter (Google Java Format or IDE-configured).
- Use `@SuppressWarnings` sparingly and with specific warning names.
- Use `final` for parameters and local variables where practical.

## Nullability
- Annotate with `@Nullable` / `@NonNull` from JSpecify or JetBrains.
- Use `Objects.requireNonNull()` at public API boundaries.
- Never return `null` from collections or arrays. Return empty.
- Use `Optional` for genuinely optional return values.

## Documentation
- Javadoc on all public classes and methods.
- Use `@param`, `@return`, `@throws` tags for public API methods.
- Skip Javadoc for obvious getters, `toString()`, and `equals()`.
