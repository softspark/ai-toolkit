---
language: kotlin
category: coding-style
version: "1.0.0"
---

# Kotlin Coding Style

## Naming
- PascalCase: classes, interfaces, objects, type aliases, enum entries.
- camelCase: functions, properties, local variables, parameters.
- UPPER_SNAKE: compile-time constants (`const val`), top-level `val` constants.
- Backing properties: prefix with `_` (`private val _items`, `val items: List<T>`).
- Package names: lowercase, no underscores (`com.company.project.feature`).

## Null Safety
- Use nullable types only when nullability is semantically meaningful.
- Prefer `?.let { }`, `?:` (Elvis), and safe calls over `!!`.
- Never use `!!` except in tests or when null is truly impossible.
- Use `requireNotNull()` and `require()` for preconditions at public API boundaries.
- Use `checkNotNull()` and `check()` for state assertions.

## Data Classes
- Use `data class` for DTOs, value objects, and state containers.
- Use `copy()` for immutable updates. Avoid mutable `var` in data classes.
- Use `sealed class` / `sealed interface` for restricted hierarchies.
- Use `value class` (inline class) for type-safe wrappers with zero overhead.
- Use `object` for singletons and namespace-like utility groupings.

## Functions
- Use expression body (`= expr`) for single-expression functions.
- Use named arguments for functions with >2 parameters of the same type.
- Use default parameter values instead of overloaded functions.
- Use extension functions to add behavior without inheritance.
- Use `suspend` functions for async operations, not callbacks.

## Collections
- Prefer `listOf`, `mapOf`, `setOf` (immutable) over `mutableListOf`.
- Use collection operators: `map`, `filter`, `groupBy`, `associate`.
- Use `sequence {}` for lazy evaluation on large collections.
- Prefer `firstOrNull()` over `first()` for safe access.
- Use destructuring: `val (name, age) = user`.

## Scope Functions
- `let`: null-safe chaining and local scoping.
- `apply`: configure object after creation.
- `also`: side effects (logging, validation) in chains.
- `run`: compute a result using receiver's context.
- `with`: multiple operations on an object without chaining.
- Avoid nesting scope functions more than 1 level deep.

## Formatting
- Use ktlint or detekt for automated formatting and linting.
- Use trailing commas in multi-line parameter/argument lists.
- Max line length: 120 characters (Kotlin convention).
- Use `when` expression over if-else chains for 3+ branches.
