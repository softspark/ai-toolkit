# TypeScript Clean Code Patterns

## Configuration

```json
// tsconfig.json - strict mode
{ "compilerOptions": { "strict": true, "noUncheckedIndexedAccess": true } }

// .eslintrc - recommended rules
{ "extends": ["eslint:recommended", "plugin:@typescript-eslint/recommended-type-checked", "prettier"] }
```

## Patterns

```typescript
// Type-safe function signatures
function getUser(id: string): Promise<User | null> { ... }

// Prefer `unknown` over `any`
function parseData(raw: unknown): Result { ... }

// Use discriminated unions
type Result = { success: true; data: User } | { success: false; error: string };

// Avoid: `any`, non-null assertions `!`, type casting `as` without guards
```
