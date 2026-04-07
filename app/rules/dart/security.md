---
language: dart
category: security
version: "1.0.0"
---

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
