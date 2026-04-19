---
name: typescript-patterns
description: "TypeScript type safety patterns: strict mode, generics, conditional types, template literals, discriminated unions, branded types, Zod, satisfies operator, const assertions. Triggers: TypeScript, TS, generics, conditional type, utility type, strict, Zod, satisfies, discriminated union, type safety, type narrowing, template literal type. Load when writing or reviewing TypeScript code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# TypeScript/JavaScript Patterns

## TypeScript Configuration

### Strict tsconfig.json
```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "exactOptionalPropertyTypes": true,
    "moduleResolution": "bundler",
    "module": "ESNext",
    "target": "ES2022",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}
```

## ESLint + Prettier

```json
// .eslintrc.json (flat config recommended for new projects)
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended-type-checked",
    "prettier"
  ],
  "parser": "@typescript-eslint/parser",
  "parserOptions": {
    "project": "./tsconfig.json"
  },
  "rules": {
    "@typescript-eslint/no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
    "@typescript-eslint/no-floating-promises": "error",
    "@typescript-eslint/no-misused-promises": "error"
  }
}
```

## React Patterns

### Functional Component
```tsx
interface UserCardProps {
  user: User;
  onSelect?: (id: string) => void;
}

export function UserCard({ user, onSelect }: UserCardProps) {
  const handleClick = useCallback(() => {
    onSelect?.(user.id);
  }, [user.id, onSelect]);

  return (
    <div onClick={handleClick} role="button" tabIndex={0}>
      <h3>{user.name}</h3>
      <p>{user.email}</p>
    </div>
  );
}
```

### Custom Hook
```tsx
function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<{
    data: T | null;
    error: Error | null;
    loading: boolean;
  }>({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    setState(prev => ({ ...prev, loading: true }));
    fn()
      .then(data => { if (!cancelled) setState({ data, error: null, loading: false }); })
      .catch(error => { if (!cancelled) setState({ data: null, error, loading: false }); });
    return () => { cancelled = true; };
  }, deps);

  return state;
}
```

### Context Pattern
```tsx
interface AuthContextType {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be within AuthProvider");
  return context;
}
```

## Next.js App Router

### Server Component (default)
```tsx
// app/users/page.tsx
export default async function UsersPage() {
  const users = await db.user.findMany();
  return <UserList users={users} />;
}
```

### Server Action
```tsx
"use server";

import { revalidatePath } from "next/cache";

export async function createUser(formData: FormData) {
  const name = formData.get("name") as string;
  await db.user.create({ data: { name } });
  revalidatePath("/users");
}
```

## Node.js/Express Patterns

### Type-safe Route Handler
```typescript
import { Router, Request, Response } from "express";
import { z } from "zod";

const CreateUserSchema = z.object({
  name: z.string().min(1).max(100),
  email: z.string().email(),
});

router.post("/users", async (req: Request, res: Response) => {
  const result = CreateUserSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({ errors: result.error.flatten() });
  }
  const user = await userService.create(result.data);
  res.status(201).json(user);
});
```

## State Management

### Zustand Store
```typescript
import { create } from "zustand";

interface CartStore {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  removeItem: (id: string) => void;
  total: () => number;
}

export const useCartStore = create<CartStore>((set, get) => ({
  items: [],
  addItem: (item) => set((state) => ({ items: [...state.items, item] })),
  removeItem: (id) => set((state) => ({ items: state.items.filter(i => i.id !== id) })),
  total: () => get().items.reduce((sum, item) => sum + item.price, 0),
}));
```

## Type-safe API (tRPC / Zod)

### Zod Schema Validation
```typescript
import { z } from "zod";

export const UserSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  email: z.string().email(),
  role: z.enum(["admin", "user", "guest"]),
  createdAt: z.coerce.date(),
});

export type User = z.infer<typeof UserSchema>;
```

## Error Handling

```typescript
class AppError extends Error {
  constructor(
    message: string,
    public statusCode: number = 500,
    public code: string = "INTERNAL_ERROR"
  ) {
    super(message);
    this.name = "AppError";
  }
}

// Result pattern (no exceptions)
type Result<T, E = Error> =
  | { success: true; data: T }
  | { success: false; error: E };

function parseUser(raw: unknown): Result<User> {
  const result = UserSchema.safeParse(raw);
  if (result.success) return { success: true, data: result.data };
  return { success: false, error: new Error(result.error.message) };
}
```

## Testing with Vitest

```typescript
import { describe, it, expect, vi } from "vitest";

describe("UserService", () => {
  it("creates user with valid data", async () => {
    const mockRepo = { create: vi.fn().mockResolvedValue({ id: "1", name: "Test" }) };
    const service = new UserService(mockRepo);
    const user = await service.create({ name: "Test", email: "t@t.com" });
    expect(user.id).toBe("1");
    expect(mockRepo.create).toHaveBeenCalledOnce();
  });
});
```

## Anti-Patterns
- `any` type usage (use `unknown` and narrow)
- Non-null assertions `!` without checks
- `as` type casting instead of type guards
- Mutable state in React (use immutable updates)
- Missing error boundaries in React
- Barrel exports that break tree-shaking
