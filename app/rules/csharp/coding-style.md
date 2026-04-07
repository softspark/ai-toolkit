---
language: csharp
category: coding-style
version: "1.0.0"
---

# C# Coding Style

## Naming
- PascalCase: classes, structs, enums, interfaces, methods, properties, events.
- camelCase: local variables, parameters, private fields.
- Prefix interfaces with `I`: `IUserRepository`, `IDisposable`.
- Prefix private fields with `_`: `private readonly ILogger _logger;`.
- UPPER_SNAKE: not conventional in C#. Use PascalCase for constants.

## Nullable Reference Types
- Enable `<Nullable>enable</Nullable>` in all projects.
- Use `string?` only when null is semantically meaningful.
- Use `!` (null-forgiving) operator sparingly -- only when compiler cannot infer.
- Use `??` (null-coalescing) and `?.` (null-conditional) for safe navigation.
- Use `required` modifier (C# 11) on properties that must be set at initialization.

## Records and Types
- Use `record` for immutable value objects and DTOs.
- Use `record struct` for small, stack-allocated value types.
- Use `init` properties for immutable-after-construction objects.
- Use `with` expressions for non-destructive mutation of records.
- Use primary constructors (C# 12) for concise class definitions.

## Pattern Matching
- Use `is` pattern for type checks: `if (obj is string s)`.
- Use `switch` expressions for exhaustive matching over enums/types.
- Use property patterns: `user is { Age: > 18, Role: "admin" }`.
- Use relational patterns: `size is > 0 and < 100`.
- Use list patterns (C# 11): `numbers is [1, 2, .., var last]`.

## Async/Await
- Suffix async methods with `Async`: `GetUserAsync()`.
- Return `Task<T>` or `ValueTask<T>`, never `void` (except event handlers).
- Use `await` with `ConfigureAwait(false)` in library code.
- Use `CancellationToken` parameters in all async public APIs.
- Prefer `ValueTask<T>` when synchronous completion is common.

## File Organization
- One type per file. File name matches type name.
- Use file-scoped namespaces (C# 10): `namespace MyApp.Services;`.
- Order members: fields, constructors, properties, public methods, private methods.
- Use `global using` directives in a single `GlobalUsings.cs` file.

## Formatting
- Use `.editorconfig` with C# style rules committed to the repository.
- Use `dotnet format` for automated formatting.
- Use Roslyn analyzers for compile-time style enforcement.
- Max line length: 120 characters.
