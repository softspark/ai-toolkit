---
language: dart
category: frameworks
version: "1.1.0"
---

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
