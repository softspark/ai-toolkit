---
language: dart
category: coding-style
version: "1.0.0"
---

# Dart Coding Style

## Naming
- PascalCase: classes, enums, typedefs, extensions, mixins.
- camelCase: variables, functions, methods, parameters, named constants.
- snake_case: libraries, packages, directories, source files.
- UPPER_SNAKE: not used in Dart. Use camelCase for constants.
- Prefix private members with `_`: `_internalState`, `_helper()`.

## Null Safety
- Enable sound null safety (default since Dart 2.12).
- Use `?` types only when null is semantically meaningful.
- Use `!` operator sparingly. Prefer null checks or `??` fallback.
- Use `late` keyword only when initialization is guaranteed before access.
- Use `required` keyword for mandatory named parameters.

## Classes
- Use `const` constructors for immutable classes.
- Use factory constructors for caching, subtype selection, or validation.
- Use named constructors for clarity: `Point.fromJson(json)`.
- Use `final` fields for immutable properties.
- Use `@immutable` annotation on classes that should be immutable.

## Functions
- Use named parameters for functions with >2 parameters.
- Use `required` for mandatory named parameters.
- Use default values for optional parameters.
- Use fat arrow (`=>`) for single-expression functions.
- Always specify return types for public functions.

## Collections
- Use collection literals: `[]`, `{}`, `<String, int>{}`.
- Use `if` and `for` inside collection literals for conditional/iterative building.
- Use spread operator: `[...list1, ...list2]`.
- Use `whereType<T>()` for type-safe filtering.
- Prefer `const` collections when values are known at compile time.

## Async
- Use `async`/`await` for all asynchronous operations.
- Return `Future<T>` from async functions. Never return `void`.
- Use `Stream<T>` for continuous data (events, real-time updates).
- Use `Future.wait()` for concurrent independent operations.
- Use `Completer<T>` only when wrapping callback-based APIs.

## Imports
- Order: `dart:` SDK, `package:` external, relative project imports.
- Use `show`/`hide` to limit import scope when names conflict.
- Use `as` prefix for namespace conflicts: `import 'package:foo/foo.dart' as foo`.
- Prefer relative imports within the same package.

## Formatting
- Use `dart format` (line length 80) for consistent formatting.
- Use `dart analyze` for static analysis with default lint rules.
- Use `analysis_options.yaml` with recommended lints: `flutter_lints` or `lints`.
- Use trailing commas in multi-line argument lists for cleaner diffs.
