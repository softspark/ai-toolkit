---
language: cpp
category: testing
version: "1.0.0"
---

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
