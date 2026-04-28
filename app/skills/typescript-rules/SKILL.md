---
name: typescript-rules
description: "TypeScript/JavaScript coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .ts, .tsx, .js, .jsx, package.json, tsconfig.json, React, Next.js, Vue, Vite, Vitest, Jest, ESLint. Load when writing, reviewing, or editing TypeScript/JavaScript code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# TypeScript/JavaScript Rules

These rules come from `app/rules/typescript/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in TypeScript/JavaScript. Apply them when writing or
reviewing TypeScript/JavaScript code.

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

# TypeScript Frameworks

## React
- Use function components exclusively. No class components.
- Colocate state with the component that owns it. Lift only when needed.
- Use `useCallback` and `useMemo` only when profiling shows a need.
- Use `React.lazy()` + Suspense for code-splitting routes.
- Avoid prop drilling past 2 levels -- use Context or state management.

## Next.js (App Router)
- Default to Server Components. Add `"use client"` only when needed.
- Use Server Actions for mutations. Never expose internal APIs to client.
- Use `loading.tsx` and `error.tsx` for streaming and error boundaries.
- Fetch data in Server Components, not in useEffect on client.
- Use `revalidatePath` / `revalidateTag` for cache invalidation.

## Express / Fastify / Hono
- Use layered architecture: route -> controller -> service -> repository.
- Validate request body/params/query with Zod middleware.
- Centralize error handling in a single error middleware.
- Use async route handlers with proper error forwarding.
- Return consistent response shapes: `{ data }` or `{ error }`.

## State Management
- Use Zustand or Jotai for client state. Redux only for complex existing apps.
- Use TanStack Query (React Query) for server state.
- Separate server state (fetched data) from client state (UI state).
- Never duplicate server data in client state stores.

## ORM / Database
- Use Drizzle for new projects (SQL-like, type-safe, lightweight).
- Use Prisma for rapid prototyping (schema-first, great DX).
- Always use migrations. Never modify schema manually in production.
- Use transactions for multi-table operations.

## Node.js Runtime
- Use `node:` prefix for built-in modules: `import { readFile } from 'node:fs/promises'`.
- Prefer `fetch` (built-in since Node 18) over axios/node-fetch.
- Use `structuredClone()` for deep cloning.
- Set `"type": "module"` in package.json for ESM.

## Monorepo
- Use Turborepo or Nx for monorepo orchestration.
- Share types via internal packages, not copy-paste.
- Use workspace protocols: `"@org/shared": "workspace:*"`.

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

# TypeScript Security

## Input Validation
- Validate ALL request data with Zod/Valibot at API boundary.
- Use `.strip()` / `.strict()` to reject unexpected fields.
- Validate URL params and query strings, not just request bodies.
- Never pass raw user input to `eval()`, `Function()`, or template literals in SQL.

## XSS Prevention
- Use framework auto-escaping (React JSX, Angular templates).
- Never use `dangerouslySetInnerHTML` without DOMPurify sanitization.
- Sanitize user content before storing, not just before rendering.
- Set CSP headers: `default-src 'self'; script-src 'self'`.

## Authentication
- Use `httpOnly`, `secure`, `sameSite: 'strict'` for auth cookies.
- Implement CSRF protection for cookie-based auth (double-submit or token).
- Use short-lived JWTs (15min) with refresh token rotation.
- Validate JWT signature, expiration, issuer, and audience on every request.

## SQL / NoSQL Injection
- Use parameterized queries with Drizzle/Prisma/TypeORM. Never concatenate.
- For raw queries, use tagged template literals: `sql\`SELECT * FROM users WHERE id = ${id}\``.
- Validate and cast IDs to expected types (UUID, integer) before queries.
- Use ORM query builders for dynamic filters.

## Dependency Security
- Run `npm audit` in CI. Fail on high/critical vulnerabilities.
- Use `npm audit signatures` to verify package provenance.
- Pin exact versions with lockfile. Review lockfile changes in PRs.
- Avoid packages with postinstall scripts unless trusted.

## Secrets
- Use `process.env` with Zod validation for env vars.
- Never import `.env` files in production -- use platform env injection.
- Never log `req.headers.authorization` or session tokens.
- Use `crypto.timingSafeEqual()` for comparing secrets.

## Server Hardening
- Set security headers: HSTS, X-Content-Type-Options, X-Frame-Options.
- Use `helmet` middleware in Express, built-in security in Fastify.
- Implement rate limiting on all endpoints (`express-rate-limit`, `@fastify/rate-limit`).
- Disable `X-Powered-By` header. Do not expose server technology.

## File Uploads
- Validate file type by magic bytes, not just extension or MIME type.
- Set maximum file size limits on the server.
- Store uploads outside the web root. Serve through a proxy with CDN.
- Generate random filenames. Never use user-provided filenames for storage.

# TypeScript Testing

## Framework
- Use Vitest for new projects (faster, native ESM, TypeScript-first).
- Use Jest only for existing projects already using it.
- Use Playwright for E2E browser testing.
- Use Supertest or built-in fetch for API integration tests.

## File Naming
- Test files: `*.test.ts` or `*.spec.ts` colocated with source.
- Test utilities: `tests/helpers/` or `tests/utils/`.
- Fixtures: `tests/fixtures/` with typed factory functions.

## Structure
- Use `describe` for grouping by function/class/feature.
- Use `it` with behavior descriptions: `it('returns 404 when user not found')`.
- Avoid deeply nested `describe` blocks (max 2 levels).
- Use `beforeEach` for setup, avoid `beforeAll` for mutable state.

## Type-Safe Mocking
- Use `vi.fn()` with type parameters: `vi.fn<[string], Promise<User>>()`.
- Use `vi.mock()` for module-level mocking.
- Prefer dependency injection over module mocking for testability.
- Use `vi.spyOn()` for partial mocks on existing objects.

## React/Component Testing
- Use React Testing Library. Query by role, label, text -- not test IDs.
- Use `userEvent` over `fireEvent` for realistic user interactions.
- Test behavior and rendered output, not component internals.
- Use `renderHook` for testing custom hooks in isolation.

## Assertions
- Use `expect().toBe()` for primitives, `expect().toEqual()` for objects.
- Use `expect().toMatchInlineSnapshot()` for complex output verification.
- Avoid `toBeTruthy/toBeFalsy` -- use specific matchers.
- Use `expect().rejects.toThrow()` for async error testing.

## Async Testing
- Always `await` async operations. Never use `done` callback.
- Use `vi.useFakeTimers()` for timer-dependent code.
- Use `waitFor` from Testing Library for async DOM updates.

## Performance
- Run tests in parallel (Vitest default). Isolate state to enable this.
- Use `vi.mock()` for heavy dependencies (DB, network) in unit tests.
- Keep unit test suite under 30 seconds.
