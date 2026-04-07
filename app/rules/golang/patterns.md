---
language: golang
category: patterns
version: "1.0.0"
---

# Go Patterns

## Error Handling
- Wrap errors with context at each call site: `fmt.Errorf("loading config: %w", err)`.
- Define domain error types with `errors.New()` or custom error structs.
- Use `errors.Is()` for sentinel errors, `errors.As()` for typed errors.
- Return errors, do not panic. Reserve `panic` for truly unrecoverable states.
- Handle errors immediately after the call. No deferred error checking.

## Concurrency
- Use `errgroup.Group` for concurrent operations that may fail.
- Use `sync.Once` for one-time initialization (singleton pattern).
- Use `sync.Map` only for append-mostly maps with concurrent access.
- Use buffered channels as semaphores: `sem := make(chan struct{}, maxConcurrency)`.
- Prefer `context.WithTimeout` over manual timers for deadline management.

## Interface Design
- Keep interfaces small: 1-3 methods. Compose larger interfaces from smaller ones.
- Define interfaces where they are consumed, not where they are implemented.
- Use `io.Reader`, `io.Writer`, `fmt.Stringer` and standard interfaces where applicable.
- Avoid returning interfaces from functions. Return concrete types.

## Options Pattern
- Use functional options for constructors with many optional parameters.
- Pattern: `func WithTimeout(d time.Duration) Option { return func(c *Client) { c.timeout = d } }`.
- Provide sensible defaults. Options override defaults.
- Use `Option` type alias: `type Option func(*Config)`.

## Dependency Injection
- Pass dependencies through constructor functions, not global variables.
- Accept interfaces in constructors: `func NewService(repo UserRepo) *Service`.
- Use `wire` or manual wiring in `main()` for dependency graph.
- Avoid init() functions for anything other than simple registration.

## Resource Management
- Use `defer` for cleanup immediately after acquiring a resource.
- Use `context.Context` for cancellation propagation across goroutines.
- Close channels from the sender side, never the receiver.
- Use `sync.Pool` for frequently allocated temporary objects (buffers).

## Anti-Patterns
- Global mutable state: use dependency injection instead.
- `interface{}` / `any` everywhere: use generics (Go 1.18+) or specific types.
- Goroutine leaks: always ensure goroutines can exit.
- Ignoring `context.Context`: propagate it through all I/O paths.
- Large interfaces: split into focused, composable pieces.
