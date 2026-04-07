---
language: kotlin
category: testing
version: "1.0.0"
---

# Kotlin Testing

## Framework
- Use JUnit 5 as the test runner.
- Use Kotest for Kotlin-idiomatic BDD-style testing (alternative).
- Use MockK for mocking (Kotlin-native, supports coroutines).
- Use Testcontainers for integration tests with external services.

## File Naming
- Test files: `FooTest.kt` in `src/test/kotlin/` mirroring source package.
- Integration tests: `FooIT.kt` or use `@Tag("integration")`.
- Use `@Nested` inner classes to group related test cases.

## Structure
- Use `@DisplayName` for human-readable test names.
- Use backtick function names for readable test names: `` `returns 404 when user not found` ``.
- Use `@BeforeEach` for per-test setup. Avoid shared mutable state.
- Use `@ParameterizedTest` with `@MethodSource` for table-driven tests.

## MockK
- Use `mockk<UserRepository>()` to create mocks.
- Use `every { mock.find(any()) } returns user` for stubbing.
- Use `coEvery { ... }` and `coVerify { ... }` for coroutine mocking.
- Use `spyk()` for partial mocks on real objects.
- Use `slot<T>()` and `captured` to inspect arguments.
- Clear mocks in `@AfterEach` to prevent state leakage.

## Coroutine Testing
- Use `runTest { }` from `kotlinx-coroutines-test` for coroutine tests.
- Use `TestDispatcher` to control coroutine execution timing.
- Use `advanceUntilIdle()` to complete all pending coroutines.
- Use `turbine` library for testing `Flow` emissions.

## Assertions
- Use AssertJ or Kotest assertions for fluent, readable checks.
- Use `shouldBe`, `shouldThrow`, `shouldContain` (Kotest matchers).
- Use `assertSoftly { }` to collect multiple assertion failures.
- Use `assertThrows<FooException> { ... }` for exception testing.

## Test Data
- Use factory functions for test data: `fun aUser(name: String = "Ada") = User(...)`.
- Use default parameters for minimal test data setup.
- Use `copy()` on data classes for variations of base test objects.
- Use `faker` library for realistic test data generation.

## Spring Integration
- Use `@SpringBootTest` with `@AutoConfigureMockMvc` for API tests.
- Use `@WebMvcTest` for controller-only tests (faster).
- Use `@MockkBean` instead of `@MockBean` for MockK integration.
- Use `@Transactional` on test classes for automatic rollback.
