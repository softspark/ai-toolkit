---
language: cpp
category: coding-style
version: "1.0.0"
---

# C++ Coding Style

## Naming
- PascalCase: classes, structs, enums, type aliases, concepts.
- camelCase or snake_case: functions, methods, variables (be consistent per project).
- UPPER_SNAKE: macros, compile-time constants.
- Prefix member variables with `m_` or suffix with `_` (pick one convention).
- Namespace names: lowercase, short (`namespace io`, `namespace util`).

## Modern C++ (17/20/23)
- Use `auto` for iterator types and complex template deductions.
- Use `std::optional<T>` instead of sentinel values or pointers for optional returns.
- Use `std::variant` over union types. Use `std::visit` for dispatch.
- Use `std::string_view` for non-owning string parameters.
- Use structured bindings: `auto [key, value] = *map.begin();`.
- Use `constexpr` for compile-time evaluation. Prefer over macros.

## Memory Management
- Use RAII exclusively. Every resource acquisition is an initialization.
- Use `std::unique_ptr` for exclusive ownership (default choice).
- Use `std::shared_ptr` only when ownership is genuinely shared.
- Never use raw `new`/`delete`. Use `std::make_unique` / `std::make_shared`.
- Use `std::span<T>` (C++20) for non-owning views over contiguous data.

## Functions
- Pass small types by value. Pass large types by `const&`.
- Use `[[nodiscard]]` on functions whose return value must not be ignored.
- Use `noexcept` on functions that do not throw (move constructors, destructors).
- Limit function parameters to 4. Use structs for configuration objects.
- Use trailing return types for complex template return deductions.

## Includes and Dependencies
- Use `#pragma once` or include guards. Prefer `#pragma once` for simplicity.
- Order: corresponding header, C++ stdlib, third-party, project headers.
- Forward-declare in headers when possible to reduce compile times.
- Minimize header dependencies. Use the Pimpl idiom for ABI stability.

## Avoid
- Raw pointers for ownership. Use smart pointers.
- C-style casts. Use `static_cast`, `dynamic_cast`, `const_cast`.
- Macros for constants or functions. Use `constexpr` and templates.
- `using namespace std;` in headers. Acceptable in .cpp files with caution.
- `std::endl` -- use `'\n'` (endl flushes the buffer unnecessarily).

## Formatting
- Use clang-format with a committed `.clang-format` file.
- Use clang-tidy for static analysis and automated modernization.
- Max line length: 100-120 characters.
- Braces: use Allman or K&R consistently per project.
