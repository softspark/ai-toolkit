---
language: typescript
category: frameworks
version: "1.0.0"
---

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
