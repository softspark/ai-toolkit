---
language: typescript
category: coding-style
version: "1.0.0"
---

# TypeScript Coding Style

## Strict Mode
- Always use `strict: true` in tsconfig.json.
- Never use `any` -- use `unknown` + type guards instead.
- Prefer `interface` over `type` for object shapes (extendable).
- Use `as const` for literal types and readonly tuples.

## Naming
- PascalCase: types, interfaces, enums, classes, components.
- camelCase: variables, functions, methods, properties.
- UPPER_SNAKE: constants, env vars.
- Prefix interfaces with `I` only if project convention requires it.

## Functions
- Prefer arrow functions for callbacks and inline.
- Use `function` declarations for hoisted, named functions.
- Max 3 parameters -- use options object beyond that.
- Always type return values for public/exported functions.

## Imports
- Group: node builtins, external, internal, relative.
- Use `type` imports: `import type { Foo } from './foo'`.
- No barrel exports unless at package boundary.
- Prefer named exports over default exports.

## Types
- Use discriminated unions over class hierarchies for state.
- Use `readonly` for arrays and objects that should not be mutated.
- Use `satisfies` operator to validate types without widening.
- Prefer `unknown` over `any` at API boundaries.
- Use template literal types for string patterns.

## Avoid
- `enum` -- use `as const` objects or union types.
- `namespace` -- use ES modules.
- `private` keyword -- use `#` private fields.
- Non-null assertion `!` -- use proper type narrowing.
- `as` type casting -- use type guards and narrowing.

## Configuration
- Enable `noUncheckedIndexedAccess` for safer array/object access.
- Enable `exactOptionalPropertyTypes` to distinguish `undefined` from missing.
- Use `moduleResolution: "bundler"` for modern projects.
- Set `isolatedModules: true` for bundler compatibility.
