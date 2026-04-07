---
language: ruby
category: patterns
version: "1.0.0"
---

# Ruby Patterns

## Error Handling
- Rescue specific exceptions. Never bare `rescue` (catches `StandardError`).
- Create domain exception hierarchies: `class AppError < StandardError; end`.
- Use `raise` with message and optional cause: `raise AppError, "msg"`.
- Use `retry` with a counter for transient failures.
- Use `ensure` for cleanup. Use `else` for code that runs only on success.

## Service Objects
- Use single-purpose service classes with a `call` method.
- Use `Dry::Monads` Result type for operation outcomes.
- Return `Success(value)` or `Failure(error)` from service calls.
- Chain services with `bind` / `fmap` for pipeline composition.
- Keep services stateless. Pass all data through method parameters.

## Value Objects
- Use `Data.define` (Ruby 3.2+) for immutable value objects.
- Use `Struct` with `keyword_init: true` for lightweight data containers.
- Use `freeze` on objects that should not be mutated after creation.
- Override `==` and `hash` for value-based equality when needed.

## Metaprogramming (Use Sparingly)
- Use `define_method` over `method_missing` when possible.
- Always define `respond_to_missing?` alongside `method_missing`.
- Use `class_attribute` (Rails) for inheritable class-level configuration.
- Prefer explicit code over DSL magic for maintainability.
- Document metaprogrammed methods with YARD `@!method` directives.

## Concurrency
- Use `Concurrent::Future` (concurrent-ruby) for parallel operations.
- Use `Concurrent::Promise` for composable async chains.
- Use thread pools (`Concurrent::FixedThreadPool`) for bounded concurrency.
- Use `Ractor` (Ruby 3+) for true parallel execution without GVL.
- Use `Mutex` and `Queue` for thread-safe shared state access.

## Module Patterns
- Use `include` for shared behavior (instance methods).
- Use `prepend` for wrapping/overriding existing methods (decorating).
- Use `extend` for adding class-level methods from a module.
- Use `Concern` (ActiveSupport) for Rails modules with class methods.
- Keep modules focused: one responsibility per module.

## Decorator Pattern
- Use `SimpleDelegator` for transparent object wrapping.
- Use `Draper` gem for view-layer decorators in Rails.
- Prefer composition (wrapping) over inheritance for adding behavior.
- Use `Module#prepend` for method-level decoration without wrapper classes.

## Anti-Patterns
- Monkey-patching core classes: use refinements or wrapper methods.
- Callbacks for business logic (Rails): use service objects.
- God objects: split into focused classes with single responsibility.
- N+1 queries: use `includes()`, `preload()`, `eager_load()`.
- Using `eval` or `send` with user input: remote code execution risk.
