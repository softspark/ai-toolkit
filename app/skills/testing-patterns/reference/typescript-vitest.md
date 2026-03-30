# TypeScript Vitest/Jest Patterns

## Basic Test

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

## React Testing Library

```tsx
import { render, screen, fireEvent } from "@testing-library/react";

test("button click increments counter", () => {
  render(<Counter />);
  fireEvent.click(screen.getByRole("button"));
  expect(screen.getByText("Count: 1")).toBeInTheDocument();
});
```

## Mocking

```typescript
// Module mock
vi.mock("./api", () => ({ fetchUsers: vi.fn().mockResolvedValue([]) }));

// Spy
const spy = vi.spyOn(service, "save");
await service.process(data);
expect(spy).toHaveBeenCalledWith(data);
```

## Running

```bash
npx vitest run                    # All tests
npx vitest run --coverage         # With coverage
npx vitest run src/utils.test.ts  # Specific file
npx vitest --watch                # Watch mode
```
