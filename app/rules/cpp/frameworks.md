---
language: cpp
category: frameworks
version: "1.0.0"
---

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
