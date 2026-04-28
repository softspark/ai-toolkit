---
name: swift-rules
description: "Swift coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .swift, Package.swift, .xcodeproj, SwiftUI, Combine, async/await, XCTest. Load when writing, reviewing, or editing Swift code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Swift Rules

These rules come from `app/rules/swift/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Swift. Apply them when writing or
reviewing Swift code.

# Swift Coding Style

## Naming
- PascalCase: types, protocols, enums, struct, class.
- camelCase: functions, methods, properties, variables, enum cases.
- No prefixes: Swift has module namespacing (no `NS` or `UI` prefix for your types).
- Use descriptive names: `removeElement(at:)` not `remove(i:)`.
- Boolean properties read as assertions: `isEmpty`, `hasChildren`, `canSubmit`.

## Types
- Prefer `struct` over `class` by default (value semantics, no reference cycles).
- Use `class` only when reference semantics or inheritance is required.
- Use `enum` with associated values for modeling finite states.
- Use `protocol` for defining capabilities. Prefer protocol composition.
- Use `typealias` for complex generic signatures for readability.

## Optionals
- Use `guard let` for early exit on nil. Use `if let` for conditional binding.
- Never force-unwrap (`!`) unless failure is a programming error.
- Use `??` for default values: `let name = user?.name ?? "Unknown"`.
- Use optional chaining: `user?.address?.city`.
- Use `map` / `flatMap` on optionals for transformations.

## Properties
- Use `let` by default. Use `var` only when mutation is required.
- Use computed properties for derived values: `var fullName: String { ... }`.
- Use property observers (`willSet`, `didSet`) for side effects on change.
- Use `lazy var` for expensive initialization deferred until first access.
- Use `@Published` (Combine) for observable properties in classes.

## Functions
- Use argument labels for clarity: `func move(from source: Int, to destination: Int)`.
- Omit argument labels when the function name makes the role clear: `func contains(_ element: T)`.
- Use default parameter values instead of multiple overloads.
- Use `throws` / `async throws` for fallible operations.
- Use trailing closure syntax for the last closure parameter.

## Access Control
- Use `private` for implementation details. Use `fileprivate` sparingly.
- Use `internal` (default) for module-scoped access.
- Use `public` for framework API. Use `open` only when subclassing is intended.
- Prefer `private(set)` for read-only external access with internal mutation.

## Formatting
- Use SwiftLint for automated style enforcement.
- Use SwiftFormat for automated code formatting.
- Commit `.swiftlint.yml` and `.swiftformat` to the repository.
- Max line length: 120 characters (SwiftLint default).
- Use trailing commas in multi-line arrays and dictionaries.

# Swift Frameworks

## SwiftUI
- Use `VStack`, `HStack`, `ZStack` for layout composition.
- Use `List` with `ForEach` for dynamic content. Use `LazyVStack` for large lists.
- Use `NavigationStack` (iOS 16+) with `navigationDestination(for:)` for type-safe navigation.
- Use `.task { }` modifier for async data loading tied to view lifecycle.
- Use `@ViewBuilder` for conditional view composition in custom containers.
- Use `PreviewProvider` or `#Preview` macro for rapid UI iteration.

## UIKit (Legacy / Hybrid)
- Use `UIHostingController` to embed SwiftUI views in UIKit.
- Use `UIViewRepresentable` to wrap UIKit views in SwiftUI.
- Use Auto Layout with constraints or `UIStackView` for layout.
- Use `UICollectionViewCompositionalLayout` for complex collection layouts.
- Use `Coordinator` pattern for delegate-based UIKit interop in SwiftUI.

## Combine
- Use `Publisher` / `Subscriber` for reactive data streams.
- Use `sink` for subscribing. Store cancellables in `Set<AnyCancellable>`.
- Use `map`, `filter`, `flatMap`, `combineLatest` for stream transformation.
- Use `@Published` on class properties for automatic publisher generation.
- Prefer `AsyncSequence` (async/await) over Combine for new code.

## Swift Data
- Use `@Model` macro for persistent model definitions.
- Use `@Query` in SwiftUI views for automatic fetching and observation.
- Use `ModelContext` for CRUD operations: `context.insert(item)`, `context.delete(item)`.
- Use `#Predicate` macro for type-safe query filtering.
- Use `ModelConfiguration` for custom store locations and migration options.

## Core Data (Legacy)
- Use `NSPersistentContainer` for stack setup.
- Use `NSFetchRequest` with `NSPredicate` for querying.
- Use `performBackgroundTask` for background context operations.
- Use lightweight migrations for schema changes when possible.
- Prefer SwiftData for new projects (iOS 17+).

## Vapor (Server-Side)
- Use `routes.get("users")` for route definitions.
- Use `Content` protocol for request/response body codable conformance.
- Use Fluent ORM with migrations for database access.
- Use middleware for authentication, CORS, and error handling.
- Use `async`/`await` natively (Vapor 4+ is fully async).

## Networking
- Use `URLSession` with `async/await` for HTTP requests.
- Use `Codable` with `JSONDecoder` for response parsing.
- Use `URLCache` and `ETag` for response caching.
- Set `timeoutIntervalForRequest` on `URLSessionConfiguration`.
- Use `TaskLocal` for request-scoped values (tracing, auth context).

## Package Management
- Use Swift Package Manager (SPM) for dependency management.
- Define dependencies in `Package.swift` with exact version or version ranges.
- Use `Package.resolved` committed to the repository for reproducible builds.
- Prefer SPM over CocoaPods/Carthage for new projects.

# Swift Patterns

## Error Handling
- Use `enum AppError: Error` for typed, exhaustive error handling.
- Use `throws` functions with `do-catch` for recoverable errors.
- Use `Result<Success, Failure>` for asynchronous error propagation.
- Use `try?` for optional conversion. Use `try!` only in tests or guaranteed paths.
- Add `LocalizedError` conformance for user-facing error messages.

## Protocol-Oriented Design
- Define capabilities as protocols: `protocol Fetchable { func fetch() async throws -> Data }`.
- Use protocol extensions for default implementations.
- Use protocol composition: `func process(_ item: Sendable & Codable)`.
- Use associated types for generic protocols: `associatedtype Output`.
- Use `some Protocol` (opaque types) for return types hiding concrete implementations.

## Async/Await
- Use `async` functions for all asynchronous operations.
- Use `async let` for concurrent, independent operations.
- Use `TaskGroup` for dynamic parallelism with collected results.
- Use `Task { }` to bridge sync to async. Avoid `.task { }` in views for complex logic.
- Use `withThrowingTaskGroup` for concurrent operations that can fail.

## Actors
- Use `actor` for thread-safe mutable state (replaces manual locks).
- Use `@MainActor` for UI-related state and methods.
- Use `nonisolated` for actor methods that do not access mutable state.
- Use `GlobalActor` for custom isolation domains.
- Minimize `await` calls on actors to reduce suspension points.

## SwiftUI Patterns
- Use `@State` for view-local mutable state.
- Use `@Binding` for child-to-parent state communication.
- Use `@Observable` (Observation framework) for model objects (preferred over `@ObservedObject`).
- Use `@Environment` for dependency injection: `@Environment(\.modelContext)`.
- Use `ViewModifier` for reusable view transformations.
- Extract subviews into separate structs for readability and performance.

## Codable
- Use `Codable` for JSON serialization/deserialization.
- Use `CodingKeys` enum for custom key mapping.
- Use `JSONDecoder` with `.convertFromSnakeCase` for API compatibility.
- Use `@propertyWrapper` for custom decoding strategies (e.g., date formats).
- Use `nestedContainer` for flattening nested JSON structures.

## Dependency Injection
- Use initializer injection for required dependencies.
- Use `@Environment` in SwiftUI for framework-provided values.
- Use `swift-dependencies` library for testable, controlled dependency management.
- Use `@Dependency(\.apiClient) var apiClient` for automatic resolution.

## Anti-Patterns
- Force-unwrapping optionals: use `guard let` or `??`.
- Massive view controllers/views: split into subviews and view models.
- Reference cycles: use `[weak self]` in closures capturing `self`.
- Blocking the main thread: use `Task` or `DispatchQueue.global()`.
- Stringly-typed APIs: use enums, protocols, and strong types.

# Swift Security

## Keychain
- Use Keychain Services for storing passwords, tokens, and cryptographic keys.
- Use `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` for sensitive items.
- Use `KeychainAccess` or similar wrapper libraries for cleaner API.
- Never store secrets in `UserDefaults` (unencrypted plist on disk).
- Delete keychain items on user logout.

## App Transport Security (ATS)
- Use HTTPS for all network connections. ATS enforces this by default.
- Never add blanket `NSAllowsArbitraryLoads` exception.
- Use per-domain exceptions only when connecting to legacy servers.
- Implement certificate pinning for high-security connections.
- Validate server certificates in `URLSessionDelegate` for custom pinning.

## Input Validation
- Validate all user input before processing or displaying.
- Use `NSRegularExpression` or Swift Regex for pattern validation.
- Sanitize strings before using in URL construction, SQL, or HTML.
- Validate deep link URL parameters before navigation.
- Limit input lengths in `UITextField` / `TextField` to prevent abuse.

## Data Protection
- Use `Data Protection` API: set `FileProtectionType.complete` on sensitive files.
- Use `CryptoKit` for hashing (`SHA256`), encryption (`AES.GCM`), and signing.
- Use `SecureEnclave` for hardware-backed key storage on supported devices.
- Zero sensitive data in memory after use: `withUnsafeMutableBytes { $0.initializeMemory(as: UInt8.self, repeating: 0) }`.
- Use `@Sendable` closures to prevent data races in concurrent access.

## Authentication
- Use `AuthenticationServices` for Sign in with Apple and passkeys.
- Use `LocalAuthentication` (Face ID / Touch ID) for biometric auth.
- Store authentication tokens in Keychain, not in memory or UserDefaults.
- Use short-lived access tokens with refresh token rotation.
- Implement session timeout for inactive users.

## Network Security
- Use `URLSession` with certificate pinning for sensitive API calls.
- Validate response `Content-Type` headers before parsing.
- Use `Codable` for structured deserialization (prevents injection).
- Set request timeouts to prevent hanging connections.
- Do not log request/response bodies containing sensitive data.

## Code Security
- Use `[weak self]` in closures to prevent retain cycles and memory leaks.
- Use `@Sendable` and actor isolation for thread-safe concurrent code.
- Avoid `UnsafePointer` / `UnsafeMutablePointer` unless absolutely necessary.
- Use `#if DEBUG` guards for debug-only code. Never ship debug features.
- Enable Xcode hardened runtime for macOS apps.

## Dependency Security
- Audit SPM dependencies before adding. Check maintainer reputation.
- Pin dependency versions in `Package.resolved`.
- Review `Package.swift` of dependencies for unusual build plugins.
- Prefer dependencies with active security response and disclosure processes.
- Minimize third-party dependencies for security-critical modules.

# Swift Testing

## Framework
- Use Swift Testing (`import Testing`) for new projects (Swift 5.10+).
- Use XCTest for existing projects and UIKit-based UI tests.
- Use swift-snapshot-testing for visual regression testing.
- Use swift-dependencies for controlled dependency injection in tests.

## File Naming
- Test files: `FooTests.swift` in `Tests/` target.
- Mirror source module structure in test target.
- Use `@Test` attribute (Swift Testing) or `test` prefix (XCTest) for test methods.
- Use `@Suite` (Swift Testing) for test grouping.

## Structure (Swift Testing)
- Use `@Test("description")` for individual test cases.
- Use `@Test(arguments: [...])` for parameterized tests.
- Use `#expect(condition)` for assertions. Use `#require(condition)` for preconditions.
- Use `#expect(throws: FooError.self) { try riskyOperation() }` for error testing.
- Use `@Suite` structs for grouping. Properties serve as shared setup.

## Structure (XCTest)
- Use `setUp()` / `tearDown()` for per-test initialization and cleanup.
- Use `setUpWithError()` for throwing setup code.
- Use `XCTAssertEqual`, `XCTAssertTrue`, `XCTAssertNil` for assertions.
- Use `XCTAssertThrowsError` for exception testing.
- Use `expectation(description:)` + `wait(for:timeout:)` for async assertions.

## Async Testing
- Use `async` test functions: `@Test func fetchUser() async throws { ... }`.
- Use `confirmation()` (Swift Testing) for event-based async assertions.
- XCTest: use `XCTestExpectation` with `fulfillment()` for callback-based async.
- Test `AsyncSequence` with `for await` loops and assertion on collected values.

## Mocking
- Use protocol-based dependency injection for testability.
- Create manual mock implementations conforming to protocols.
- Use `swift-dependencies` for environment-controlled dependency overrides.
- Use `@Dependency` property wrapper for automatic mock injection in tests.
- Avoid mocking frameworks when protocol mocks are straightforward.

## UI Testing (XCTest)
- Use `XCUIApplication` for UI automation tests.
- Use accessibility identifiers for reliable element lookup.
- Use `app.buttons["Submit"].tap()` for interaction simulation.
- Use `waitForExistence(timeout:)` for async UI element appearance.
- Keep UI tests focused on critical user flows only (slow to run).

## Best Practices
- Test behavior through public API. Avoid `@testable import` when possible.
- Use `@testable import Module` only when testing internal members is necessary.
- Use `withDependencies { }` for scoped dependency overrides in tests.
- Test on multiple platforms (iOS, macOS) when shipping cross-platform.
- Run tests with `swift test` or `xcodebuild test` in CI.
