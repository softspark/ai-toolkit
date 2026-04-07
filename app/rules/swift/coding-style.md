---
language: swift
category: coding-style
version: "1.0.0"
---

# Swift Coding Style

## Naming
- PascalCase: types, protocols, enums, struct, class.
- camelCase: functions, methods, properties, variables, enum cases.
- No prefixes: Swift has module namespacing (no `NS` or `UI` prefix for your types).
- Use descriptive names: `removeElement(at:)` not `remove(i:)`.
- Boolean properties read as assertions: `isEmpty`, `hasChildren`, `canSubmit`.

## Types
- Prefer `struct` over `class` by default (value semantics, no reference cycles).
- Use `class` only when reference semantics or inheritance is required.
- Use `enum` with associated values for modeling finite states.
- Use `protocol` for defining capabilities. Prefer protocol composition.
- Use `typealias` for complex generic signatures for readability.

## Optionals
- Use `guard let` for early exit on nil. Use `if let` for conditional binding.
- Never force-unwrap (`!`) unless failure is a programming error.
- Use `??` for default values: `let name = user?.name ?? "Unknown"`.
- Use optional chaining: `user?.address?.city`.
- Use `map` / `flatMap` on optionals for transformations.

## Properties
- Use `let` by default. Use `var` only when mutation is required.
- Use computed properties for derived values: `var fullName: String { ... }`.
- Use property observers (`willSet`, `didSet`) for side effects on change.
- Use `lazy var` for expensive initialization deferred until first access.
- Use `@Published` (Combine) for observable properties in classes.

## Functions
- Use argument labels for clarity: `func move(from source: Int, to destination: Int)`.
- Omit argument labels when the function name makes the role clear: `func contains(_ element: T)`.
- Use default parameter values instead of multiple overloads.
- Use `throws` / `async throws` for fallible operations.
- Use trailing closure syntax for the last closure parameter.

## Access Control
- Use `private` for implementation details. Use `fileprivate` sparingly.
- Use `internal` (default) for module-scoped access.
- Use `public` for framework API. Use `open` only when subclassing is intended.
- Prefer `private(set)` for read-only external access with internal mutation.

## Formatting
- Use SwiftLint for automated style enforcement.
- Use SwiftFormat for automated code formatting.
- Commit `.swiftlint.yml` and `.swiftformat` to the repository.
- Max line length: 120 characters (SwiftLint default).
- Use trailing commas in multi-line arrays and dictionaries.
