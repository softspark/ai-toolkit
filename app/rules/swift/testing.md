---
language: swift
category: testing
version: "1.0.0"
---

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
