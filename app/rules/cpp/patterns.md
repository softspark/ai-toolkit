---
language: cpp
category: patterns
version: "1.0.0"
---

# C++ Patterns

## Error Handling
- Use exceptions for truly exceptional conditions. Use return types for expected failures.
- Use `std::expected<T, E>` (C++23) or `Result<T, E>` pattern for recoverable errors.
- Use `std::error_code` / `std::error_category` for system-level errors.
- Use `noexcept` on functions that must not throw (destructors, move operations).
- Catch by `const&`. Never catch by value (slicing) or pointer.

## RAII Patterns
- Wrap every resource (memory, file, lock, socket) in an RAII type.
- Use `std::lock_guard` or `std::scoped_lock` for mutex management.
- Use `std::unique_lock` when deferred locking or condition variables are needed.
- Use `std::fstream` (auto-closes) instead of `fopen`/`fclose`.
- Write custom RAII wrappers for C library resources (file descriptors, handles).

## Smart Pointer Patterns
- `unique_ptr`: default ownership model. Transfer with `std::move`.
- `shared_ptr`: use only for genuinely shared ownership graphs.
- `weak_ptr`: break cycles in `shared_ptr` graphs. Use `lock()` to access.
- Factory functions should return `unique_ptr`. Let callers upgrade to `shared_ptr`.
- Never pass smart pointers by reference. Pass `T&` or `T*` to non-owning consumers.

## Concurrency
- Use `std::thread` with `std::jthread` (C++20) for auto-joining threads.
- Use `std::mutex` + `std::scoped_lock` for shared data protection.
- Use `std::atomic<T>` for lock-free single-variable synchronization.
- Use `std::condition_variable` for producer-consumer patterns.
- Use `std::async` / `std::future` for simple parallel computation.
- Use `std::counting_semaphore` (C++20) for resource pool limiting.

## Template Patterns
- Use CRTP for compile-time polymorphism (static dispatch).
- Use `concepts` (C++20) to constrain template parameters with clear error messages.
- Use `if constexpr` for compile-time branching in templates.
- Use variadic templates and fold expressions for parameter packs.
- Prefer `constexpr` functions over template metaprogramming when possible.

## Design Patterns
- Use `std::variant` + `std::visit` for type-safe visitor pattern.
- Use `std::function` for type-erased callbacks and strategy pattern.
- Use Pimpl idiom (`unique_ptr<Impl>`) for ABI stability and compilation firewall.
- Use Builder pattern with method chaining for complex object construction.
- Use `std::move` semantics in move constructors for efficient resource transfer.

## Anti-Patterns
- Raw `new`/`delete`: use smart pointers and containers.
- Returning raw pointers from factory functions: return `unique_ptr`.
- `const_cast` to remove constness: redesign the interface.
- Deep inheritance hierarchies: prefer composition and templates.
- Premature optimization over readability: profile first, optimize second.
