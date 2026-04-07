---
language: cpp
category: security
version: "1.0.0"
---

# C++ Security

## Buffer Overflow Prevention
- Use `std::string`, `std::vector`, `std::array` instead of C arrays and `char[]`.
- Use `std::span` (C++20) for safe, bounds-checked views over contiguous data.
- Never use `strcpy`, `strcat`, `sprintf`. Use `std::string` operations or `snprintf`.
- Enable `-D_FORTIFY_SOURCE=2` in release builds for runtime buffer checks.
- Use `at()` for bounds-checked container access in untrusted input paths.

## Memory Safety
- Use smart pointers exclusively. Zero raw `new`/`delete` in application code.
- Enable AddressSanitizer (`-fsanitize=address`) in development and CI builds.
- Enable UndefinedBehaviorSanitizer (`-fsanitize=undefined`) in test builds.
- Use `-fstack-protector-strong` for stack buffer overflow detection.
- Use Valgrind for memory leak detection in integration tests.

## Integer Safety
- Check for overflow before arithmetic on untrusted integers.
- Use `std::numeric_limits<T>::max()` for boundary checks.
- Use unsigned types only for bit manipulation. Prefer signed for arithmetic.
- Use `static_cast` explicitly. Never rely on implicit narrowing conversions.
- Enable `-Wconversion` and `-Wsign-conversion` warnings.

## Input Validation
- Validate all external input: file data, network packets, command-line arguments.
- Use `std::stoi` / `std::stol` with exception handling for string-to-number conversion.
- Set maximum sizes for dynamic allocations based on untrusted input.
- Validate file paths to prevent directory traversal (`../`).
- Use allowlist validation for format specifiers and command strings.

## Secure Coding
- Use `std::fill` or `explicit_bzero()` to zero sensitive memory before deallocation.
- Use constant-time comparison for secrets (avoid timing side-channels).
- Use `mlock()` to prevent sensitive memory from being swapped to disk.
- Compile with `-fPIE -pie` for position-independent executables (ASLR).
- Enable `-Werror` in CI to prevent warnings from becoming vulnerabilities.

## Dependencies
- Audit third-party C libraries for known CVEs before inclusion.
- Use `vcpkg` or `Conan` with pinned versions for reproducible builds.
- Prefer well-maintained libraries with active security response teams.
- Minimize C library usage. Prefer C++ standard library equivalents.

## Concurrency Safety
- Use `std::mutex` with `std::scoped_lock` for all shared data access.
- Use `std::atomic` for lock-free single-variable operations.
- Enable ThreadSanitizer (`-fsanitize=thread`) in test builds for race detection.
- Avoid `volatile` for synchronization. It does not provide atomicity or ordering.
- Use RAII lock guards. Never manually `lock()`/`unlock()`.

## Compiler Hardening
- Enable all warnings: `-Wall -Wextra -Wpedantic`.
- Use `-D_GLIBCXX_ASSERTIONS` for debug iterator and container checks.
- Use `-fno-exceptions` only when exception safety is not required.
- Link with `-Wl,-z,relro,-z,now` for full RELRO (GOT hardening).
