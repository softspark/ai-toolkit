---
name: cpp-rules
description: "C++ coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .cpp, .cc, .cxx, .hpp, .h, CMakeLists.txt, Makefile, GoogleTest, clang-tidy. Load when writing, reviewing, or editing C++ code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# C++ Rules

These rules come from `app/rules/cpp/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in C++. Apply them when writing or
reviewing C++ code.

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

# C++ Frameworks

## CMake
- Use modern CMake (3.14+): target-based, not directory-based.
- Use `target_link_libraries` with `PUBLIC`/`PRIVATE`/`INTERFACE` visibility.
- Use `FetchContent` for dependency management. Avoid manual submodule vendoring.
- Set `CMAKE_CXX_STANDARD 20` (or 23) at the project level.
- Use `target_compile_options` for per-target flags, not global `add_compile_options`.
- Export targets with `install(TARGETS ... EXPORT ...)` for library consumers.

## Boost
- Use Boost.Asio for async networking and I/O.
- Use `boost::beast` for HTTP/WebSocket built on Asio.
- Use `boost::json` or `nlohmann/json` for JSON parsing.
- Prefer C++ stdlib equivalents when available (e.g., `std::optional` over `boost::optional`).
- Link only the Boost libraries you actually use. Many are header-only.

## Qt
- Use signals and slots for event-driven communication.
- Use `QObject` parent-child ownership for automatic memory management.
- Use `QML` for declarative UI. Keep business logic in C++ backend.
- Use `QThread` with worker objects (moveToThread), not subclassing QThread.
- Use smart pointers for non-QObject resources. QObject children are auto-deleted.

## gRPC
- Define services in `.proto` files. Generate C++ stubs with `protoc`.
- Use async server with `CompletionQueue` for high-throughput services.
- Use `grpc::ClientContext` for per-call deadlines and metadata.
- Use interceptors for logging, auth, and metrics.
- Set deadlines on every RPC call to prevent hanging.

## Networking (Asio)
- Use `io_context` as the event loop. Run from one or more threads.
- Use `co_await` (C++20 coroutines) with Asio for clean async code.
- Use `strand` for serializing access to shared state across handlers.
- Use `steady_timer` for timeouts and periodic tasks.
- Handle errors via `error_code` parameter, not exceptions, in async callbacks.

## Database
- Use `libpq` (PostgreSQL) or `SOCI` for database access.
- Use prepared statements exclusively. Never concatenate SQL strings.
- Use connection pooling for multi-threaded server applications.
- Use `SQLite` via `sqlite3` C API with RAII wrappers for embedded use cases.

## Package Management
- Use `vcpkg` or `Conan 2` for dependency management.
- Pin dependency versions in `vcpkg.json` or `conanfile.py`.
- Use CI caching for build artifacts and dependency downloads.
- Prefer pre-built binary packages for CI speed.

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

# C++ Testing

## Framework
- Use GoogleTest (gtest) as the primary test framework.
- Use GoogleMock (gmock) for mocking interfaces and virtual classes.
- Use Catch2 as a lightweight alternative (header-only, BDD-style).
- Use CTest for test discovery and execution via CMake.

## File Naming
- Test files: `foo_test.cpp` or `test_foo.cpp` in a dedicated `tests/` directory.
- Mirror source directory structure in test directory.
- One test file per source file or logical component.
- Use `CMakeLists.txt` with `add_test()` to register tests.

## Structure (GoogleTest)
- Use `TEST(SuiteName, TestName)` for simple tests.
- Use `TEST_F(FixtureName, TestName)` for tests sharing setup/teardown.
- Use `SetUp()` / `TearDown()` in fixtures for per-test initialization.
- Keep tests focused: one logical assertion per test case.

## Assertions
- Use `EXPECT_*` (non-fatal) by default. Use `ASSERT_*` only when continuation is meaningless.
- `EXPECT_EQ`, `EXPECT_NE`, `EXPECT_LT`, `EXPECT_GT` for comparisons.
- `EXPECT_TRUE`, `EXPECT_FALSE` for boolean conditions.
- `EXPECT_THROW(expr, ExceptionType)` for exception testing.
- `EXPECT_THAT(value, matcher)` with gmock matchers for complex assertions.

## Parameterized Tests
- Use `INSTANTIATE_TEST_SUITE_P` with `testing::Values(...)` for value-parameterized tests.
- Use `testing::Combine()` for multi-dimensional parameterization.
- Use `TYPED_TEST_SUITE` for type-parameterized tests across template types.
- Prefer parameterized tests over copy-pasting similar test bodies.

## Mocking (GoogleMock)
- Define mock classes: `MOCK_METHOD(ReturnType, MethodName, (Args), (Qualifiers))`.
- Use `EXPECT_CALL(mock, Method(matchers)).WillOnce(Return(value))`.
- Use `NiceMock<T>` to suppress uninteresting call warnings.
- Use `StrictMock<T>` to fail on any unexpected call.
- Use dependency injection (constructor) to pass mock objects.

## Build Integration
- Use `FetchContent` or `find_package` to integrate gtest in CMake.
- Enable `BUILD_TESTING` option to conditionally include tests.
- Use `ctest --output-on-failure` for CI runs.
- Use sanitizers in test builds: `-fsanitize=address,undefined`.

## Best Practices
- Test edge cases: empty input, max values, null pointers, boundary conditions.
- Use RAII test fixtures for resource cleanup (no manual teardown).
- Avoid testing private methods directly. Test through public API.
- Use `valgrind` or ASan/UBSan in CI to detect memory errors.
- Keep tests fast: mock I/O and external dependencies.
