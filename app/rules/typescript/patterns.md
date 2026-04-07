---
language: typescript
category: patterns
version: "1.0.0"
---

# TypeScript Patterns

## Error Handling
- Use Result type pattern: `{ success: true; data: T } | { success: false; error: E }`.
- Use Zod `.safeParse()` for validation -- returns typed result, never throws.
- Create domain-specific error classes extending `Error` with error codes.
- Centralize error handling in middleware, not in each handler.
- Never catch errors silently. Log or rethrow with context.

## Discriminated Unions
- Use discriminated unions for state machines and polymorphic data.
- Always include a `type` or `kind` literal field as discriminant.
- Use `switch` with exhaustive checking (`never` in default) on unions.
- Prefer unions over optional fields for mutually exclusive states.

## Async Patterns
- Use `async/await` everywhere. Never use raw `.then()` chains.
- Use `Promise.all()` for independent concurrent operations.
- Use `Promise.allSettled()` when some failures are acceptable.
- Implement cancellation with `AbortController` for long operations.
- Wrap callbacks in Promises at the boundary, then use async/await.

## Validation
- Validate at API boundaries with Zod, Valibot, or ArkType.
- Derive TypeScript types from schemas: `z.infer<typeof Schema>`.
- Never trust runtime data to match TypeScript types without validation.
- Use branded types for domain primitives: `UserId`, `Email`, `Slug`.

## Dependency Injection
- Use constructor injection for services and repositories.
- Accept interfaces, not concrete classes, in constructors.
- Use factory functions for creating configured instances.
- Avoid service locator pattern and global singletons.

## Immutability
- Use `readonly` on interface properties by default.
- Use `Readonly<T>`, `ReadonlyArray<T>` for function parameters.
- Use `Object.freeze()` only for runtime safety in config objects.
- Prefer spread/map/filter over mutating methods (push, splice).

## Type Guards
- Use `is` return type for custom type guards: `(x: unknown): x is User`.
- Use `in` operator for discriminating object shapes.
- Prefer `satisfies` over `as` for type validation without casting.
- Use assertion functions (`asserts x is T`) for preconditions.
