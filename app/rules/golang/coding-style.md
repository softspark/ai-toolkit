---
language: golang
category: coding-style
version: "1.0.0"
---

# Go Coding Style

## Naming
- MixedCaps/mixedCaps only. No underscores in Go names (except test functions).
- Exported: `PascalCase`. Unexported: `camelCase`. Acronyms: `HTTPClient`, `userID`.
- Short variable names in small scopes: `i`, `r`, `w`, `ctx`, `err`.
- Descriptive names in larger scopes: `userRepository`, `requestTimeout`.
- Package names: short, lowercase, singular (`auth`, `user`, not `utils`, `helpers`).

## Packages
- One package per directory. Package name = directory name.
- Avoid `util`, `common`, `helpers` packages. Name by what it provides.
- Keep package APIs small. Export only what consumers need.
- Use `internal/` directory for packages not meant for external consumption.

## Functions
- Accept interfaces, return structs.
- First parameter `ctx context.Context` if the function does I/O or may be cancelled.
- Return `(result, error)` tuple. Error is always last return value.
- Use named return values only for documentation, not for naked returns.
- Keep functions short. If >40 lines, consider splitting.

## Error Handling
- Always check errors. Never use `_` to discard errors silently.
- Wrap errors with context: `fmt.Errorf("fetching user %s: %w", id, err)`.
- Use sentinel errors (`var ErrNotFound = errors.New(...)`) for expected conditions.
- Use `errors.Is()` and `errors.As()` for error checking, not type assertions.

## Formatting
- Use `gofmt` / `goimports`. No formatting debates in Go.
- Use `golangci-lint` with a `.golangci.yml` config in CI.
- Use `go vet` as minimum static analysis.

## Struct Design
- Use struct embedding for composition, not inheritance.
- Prefer value receivers for small structs, pointer receivers for large or mutable.
- Be consistent: all methods on a type use the same receiver type.
- Use struct literals with field names: `User{Name: "Ada", Age: 30}`.

## Concurrency
- Do not start goroutines without a plan to stop them.
- Use `sync.WaitGroup` or `errgroup.Group` to coordinate goroutines.
- Use channels for communication, mutexes for state protection.
- Prefer `context.Context` for cancellation and timeouts over manual signaling.
