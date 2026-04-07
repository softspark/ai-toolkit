---
language: dart
category: testing
version: "1.0.0"
---

# Dart Testing

## Framework
- Use `package:test` for pure Dart unit tests.
- Use `package:flutter_test` for Flutter widget and integration tests.
- Use `package:mockito` with `@GenerateMocks` for mock generation.
- Use `package:mocktail` as a simpler alternative (no code generation).

## File Naming
- Test files: `foo_test.dart` in `test/` mirroring `lib/` structure.
- Widget tests: `test/widgets/` for Flutter widget tests.
- Integration tests: `integration_test/` directory (Flutter convention).
- Golden tests: `test/goldens/` for visual regression snapshots.

## Structure
- Use `group()` for organizing related tests.
- Use `setUp()` / `tearDown()` for per-test setup and cleanup.
- Use `setUpAll()` / `tearDownAll()` for expensive one-time setup.
- Name tests descriptively: `test('returns null when user is not found', ...)`.

## Assertions
- Use `expect(actual, matcher)` with built-in matchers.
- Use `equals()`, `isNull`, `isNotNull`, `isA<T>()` for type/value checks.
- Use `throwsA(isA<FormatException>())` for exception testing.
- Use `completion(expected)` for Future assertions.
- Use `emitsInOrder([...])` for Stream emission testing.

## Mocking (Mockito)
- Annotate: `@GenerateMocks([UserRepository])`. Run `build_runner`.
- Stub: `when(mock.getUser(any)).thenAnswer((_) async => user)`.
- Verify: `verify(mock.saveUser(captureAny)).called(1)`.
- Use `verifyNever()` to assert a method was not called.
- Use `throwOnMissingStub()` to catch unstubbed method calls.

## Widget Testing (Flutter)
- Use `testWidgets('description', (tester) async { ... })`.
- Use `tester.pumpWidget(MaterialApp(home: MyWidget()))` to render.
- Use `tester.pump()` to trigger rebuilds after state changes.
- Use `tester.pumpAndSettle()` to wait for animations to complete.
- Use `find.byType()`, `find.text()`, `find.byKey()` for widget lookups.
- Use `tester.tap()`, `tester.enterText()` for interaction simulation.

## Golden Tests
- Use `matchesGoldenFile('goldens/my_widget.png')` for visual comparison.
- Run `flutter test --update-goldens` to regenerate baseline images.
- Use golden tests for complex UI components, not simple widgets.
- Keep golden tests platform-specific (render output varies by OS).

## Best Practices
- Test public API behavior, not implementation details.
- Use `fake` classes (implementing interfaces) for simple test doubles.
- Use `addTearDown()` to register cleanup in the test body.
- Run `flutter test --coverage` and check `coverage/lcov.info`.
- Use `blocTest()` from `bloc_test` package for BLoC testing.
