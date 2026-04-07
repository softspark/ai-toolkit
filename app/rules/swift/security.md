---
language: swift
category: security
version: "1.0.0"
---

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
