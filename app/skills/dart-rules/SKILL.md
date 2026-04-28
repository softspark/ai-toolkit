---
name: dart-rules
description: "Dart/Flutter coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .dart, pubspec.yaml, Flutter, Riverpod, Bloc, widget, StatelessWidget, StatefulWidget. Load when writing, reviewing, or editing Dart/Flutter code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Dart/Flutter Rules

These rules come from `app/rules/dart/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Dart/Flutter. Apply them when writing or
reviewing Dart/Flutter code.

# Dart Coding Style

## Naming
- PascalCase: classes, enums, typedefs, extensions, mixins.
- camelCase: variables, functions, methods, parameters, named constants.
- snake_case: libraries, packages, directories, source files.
- UPPER_SNAKE: not used in Dart. Use camelCase for constants.
- Prefix private members with `_`: `_internalState`, `_helper()`.

## Null Safety
- Enable sound null safety (default since Dart 2.12).
- Use `?` types only when null is semantically meaningful.
- Use `!` operator sparingly. Prefer null checks or `??` fallback.
- Use `late` keyword only when initialization is guaranteed before access.
- Use `required` keyword for mandatory named parameters.

## Classes
- Use `const` constructors for immutable classes.
- Use factory constructors for caching, subtype selection, or validation.
- Use named constructors for clarity: `Point.fromJson(json)`.
- Use `final` fields for immutable properties.
- Use `@immutable` annotation on classes that should be immutable.

## Functions
- Use named parameters for functions with >2 parameters.
- Use `required` for mandatory named parameters.
- Use default values for optional parameters.
- Use fat arrow (`=>`) for single-expression functions.
- Always specify return types for public functions.

## Collections
- Use collection literals: `[]`, `{}`, `<String, int>{}`.
- Use `if` and `for` inside collection literals for conditional/iterative building.
- Use spread operator: `[...list1, ...list2]`.
- Use `whereType<T>()` for type-safe filtering.
- Prefer `const` collections when values are known at compile time.

## Async
- Use `async`/`await` for all asynchronous operations.
- Return `Future<T>` from async functions. Never return `void`.
- Use `Stream<T>` for continuous data (events, real-time updates).
- Use `Future.wait()` for concurrent independent operations.
- Use `Completer<T>` only when wrapping callback-based APIs.

## Imports
- Order: `dart:` SDK, `package:` external, relative project imports.
- Use `show`/`hide` to limit import scope when names conflict.
- Use `as` prefix for namespace conflicts: `import 'package:foo/foo.dart' as foo`.
- Prefer relative imports within the same package.

## Formatting
- Use `dart format` (line length 80) for consistent formatting.
- Use `dart analyze` for static analysis with default lint rules.
- Use `analysis_options.yaml` with recommended lints: `flutter_lints` or `lints`.
- Use trailing commas in multi-line argument lists for cleaner diffs.

# Dart Frameworks

## Flutter
- Use `StatelessWidget` by default. Use `StatefulWidget` only for local state.
- Use `const` constructors and `const` widgets for build optimization.
- Use `Key` parameters for widgets in lists for correct diffing.
- Extract large `build()` methods into smaller widget classes (not methods).
- Use `Theme.of(context)` and `TextTheme` for consistent styling.

## Navigation
- Use `GoRouter` for declarative, type-safe routing.
- Define routes as constants: `static const String home = '/home'`.
- Use `ShellRoute` for persistent navigation bars across routes.
- Use `context.go()` for navigation, `context.push()` for stacking.
- Pass arguments via path parameters or `extra` for complex objects.

## Networking
- Use `dio` for HTTP with interceptors, retry, and cancellation.
- Use `retrofit` (code gen) for type-safe REST client definitions.
- Use interceptors for auth token injection and refresh logic.
- Set timeouts on every request: `connectTimeout`, `receiveTimeout`.
- Use `CancelToken` for cancelling in-flight requests on navigation.

## JSON Serialization
- Use `json_serializable` (+ `build_runner`) for generated `fromJson`/`toJson`. Default `fieldRename: FieldRename.none` uses Dart property names as-is — combined with Effective Dart `lowerCamelCase`, this produces `camelCase` JSON keys with zero configuration.
- Flutter docs recommend: *"best if both server and client follow the same naming strategy"* ([Flutter — JSON and serialization](https://docs.flutter.dev/data-and-backend/serialization/json)). When they do, no mapping is needed.
- When server uses a different convention, prefer `@JsonSerializable(fieldRename: FieldRename.snake)` at the class level (or globally in `build.yaml`) over sprinkling `@JsonKey(name:)` on every field. Community recommendation from the `json_serializable` docs and pub.dev guides.
- Use individual `@JsonKey(name: '...')` only for exceptional cases: external API with mixed conventions, reserved Dart keyword collision (`class`, `is`, `new`), or legacy field rename during deprecation window. Document the reason in a comment.
- For enum / status / permission values on the wire: `UPPER_SNAKE_CASE` is the cross-language community consensus (see `common/coding-style.md` — JSON Wire Format Conventions). Dart enum case names themselves stay `lowerCamelCase` per Effective Dart; map them to uppercase strings in `fromJson`/`toJson` (`value.toUpperCase()` + `switch`).
- Write unit tests asserting both directions (`fromJson` + `toJson`) with explicit expected keys. Catches contract drift at CI time.

## Local Storage
- Use `shared_preferences` for simple key-value persistence.
- Use `drift` (formerly Moor) for type-safe SQLite with reactive queries.
- Use `hive` for fast, lightweight NoSQL local storage.
- Use `flutter_secure_storage` for sensitive data (tokens, passwords).
- Never store secrets in `shared_preferences` (not encrypted).

## Dependency Injection
- Use `get_it` for service locator pattern. Register at app startup.
- Use `injectable` (code gen) for automatic registration from annotations.
- Use Riverpod providers as DI containers for testable architecture.
- Register singletons for services, factories for per-use instances.

## Platform Channels
- Use `MethodChannel` for invoking native (iOS/Android) code.
- Use `EventChannel` for streaming data from native to Dart.
- Use `Pigeon` (code gen) for type-safe platform channel definitions.
- Handle `MissingPluginException` gracefully on unsupported platforms.

## Testing Frameworks
- Use `flutter_test` for widget tests with `WidgetTester`.
- Use `integration_test` package for full app integration tests.
- Use `patrol` for native-aware integration testing (permissions, notifications).
- Use `golden_toolkit` for advanced visual regression testing.

## Build and CI
- Use `flutter build` with `--release` and `--dart-define` for env configuration.
- Use flavors (`--flavor`) for dev/staging/prod build variants.
- Use `flutter analyze` in CI for static analysis enforcement.
- Use `flutter test --coverage` with `lcov` for coverage reporting.

# Dart Patterns

## Error Handling
- Use typed exceptions for domain errors: `class UserNotFoundException implements Exception`.
- Use `try-catch` with specific exception types. Avoid bare `catch (e)`.
- Use `rethrow` to preserve stack trace when re-raising exceptions.
- Use `Result<T, E>` pattern (e.g., `dartz` Either) for expected failures.
- Use `Future.catchError()` only when `async/await` is not applicable.

## State Management (Flutter)
- Use Riverpod for compile-safe, testable state management.
- Use BLoC pattern for event-driven state with clear input/output.
- Use `ChangeNotifier` / `ValueNotifier` for simple local state.
- Use `StateNotifier` (Riverpod) for immutable state transitions.
- Keep state classes immutable. Use `copyWith()` for updates.

## Riverpod
- Use `@riverpod` annotation (code gen) for provider definitions.
- Use `ref.watch()` for reactive dependencies. Use `ref.read()` for one-time access.
- Use `AsyncNotifier` for async state management.
- Use `autoDispose` for providers that should clean up when unused.
- Use `family` modifier for parameterized providers.

## BLoC Pattern
- Separate events (input), states (output), and logic (bloc).
- Use `sealed class` for events and states (exhaustive `switch`).
- Use `Emitter<State>` for emitting state transitions.
- Use `transformEvents()` for debouncing search inputs.
- Use `BlocObserver` for global logging and error tracking.

## Repository Pattern
- Abstract data sources behind repository interfaces.
- Repositories return domain models, not DTOs or raw data.
- Use `Future<T>` for single values, `Stream<T>` for real-time updates.
- Cache data in repository layer when appropriate.
- Inject repositories via constructor. Use Riverpod/GetIt for DI.

## Freezed (Code Generation)
- Use `@freezed` for immutable data classes with `copyWith`, equality, `toString`.
- Use `@freezed` sealed unions for state modeling: `factory State.loading()`.
- Use `when()` / `map()` for exhaustive pattern matching on freezed unions.
- Run `dart run build_runner build` after modifying freezed classes.

## Async Patterns
- Use `Stream.asyncMap()` for transforming streams with async operations.
- Use `StreamController<T>` for custom streams. Close in `dispose()`.
- Use `Completer<T>` to bridge callback APIs to Future-based APIs.
- Use `Timer.periodic()` for polling. Cancel in `dispose()`.
- Use `compute()` (Flutter) for CPU-intensive work on isolates.

## Anti-Patterns
- Using `dynamic` type: defeats type safety. Use `Object?` or generics.
- Not disposing controllers/subscriptions: causes memory leaks.
- Putting business logic in widgets: extract to services/blocs.
- Using `setState()` for global state: use proper state management.
- Deep widget nesting: extract sub-widgets as separate classes.

# Dart Security

## Input Validation
- Validate all user input in form fields with `TextFormField` validators.
- Use `RegExp` for pattern validation (email, phone, URL).
- Sanitize HTML content before rendering. Never use `Html` widget with raw user input.
- Validate deep link parameters before navigation or data loading.
- Limit text input length with `maxLength` on `TextFormField`.

## Network Security
- Use HTTPS exclusively. Configure `SecurityContext` for certificate pinning.
- Use `dio` interceptors for consistent auth header injection.
- Validate SSL certificates in production. Do not disable certificate checks.
- Set connection and read timeouts on all HTTP requests.
- Use `CancelToken` to abort requests when the user navigates away.

## Data Storage
- Use `flutter_secure_storage` for tokens, passwords, and API keys.
- Never store sensitive data in `shared_preferences` (stored in plaintext).
- Encrypt local databases (`drift` with `sqlcipher`, or `hive` with encryption).
- Clear secure storage on user logout.
- Use `kIsWeb` checks to handle web platform storage limitations.

## Authentication
- Use OAuth 2.0 / OIDC with PKCE flow for mobile authentication.
- Store refresh tokens in secure storage. Store access tokens in memory.
- Use `flutter_appauth` for standards-compliant OAuth flows.
- Implement biometric authentication with `local_auth` package.
- Never store credentials in Dart source code or asset files.

## Platform Channel Security
- Validate all data received from native code via platform channels.
- Do not pass sensitive data through `MethodChannel` logging-enabled calls.
- Use `Pigeon` for type-safe channel communication (prevents mismatched types).
- Handle `PlatformException` gracefully for missing native implementations.

## Obfuscation and Hardening
- Use `--obfuscate --split-debug-info=<dir>` for release builds.
- Use `--dart-define` for environment-specific configuration (not secrets).
- Do not embed API keys in the Dart source. Use server-side proxying.
- Use ProGuard rules (Android) and symbol stripping (iOS) for native code.

## WebView Security
- Use `webview_flutter` with JavaScript disabled unless explicitly needed.
- Restrict navigation to allowlisted domains with `NavigationDelegate`.
- Sanitize any data passed from WebView to Dart via JavaScript channels.
- Do not load untrusted URLs in WebViews.

## Dependency Security
- Run `dart pub outdated` regularly. Update dependencies promptly.
- Audit `pubspec.lock` for unexpected transitive dependencies.
- Use `dart pub audit` (when available) for vulnerability scanning.
- Prefer well-maintained packages with high pub.dev scores.
- Pin exact versions in `pubspec.yaml` for production apps.

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
