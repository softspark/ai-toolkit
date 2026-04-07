---
language: typescript
category: testing
version: "1.0.0"
---

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
