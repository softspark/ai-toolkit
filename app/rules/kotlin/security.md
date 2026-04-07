---
language: kotlin
category: security
version: "1.0.0"
---

# Kotlin Security

## Input Validation
- Validate all inputs at API boundaries using Bean Validation or manual checks.
- Use `require()` for argument validation: `require(age > 0) { "Age must be positive" }`.
- Use data class `init` blocks for domain validation on construction.
- Never trust client-provided IDs. Verify resource ownership server-side.
- Sanitize strings before using in HTML, SQL, or shell commands.

## Null Safety as Security
- Kotlin's null safety prevents null pointer exceptions. Do not circumvent with `!!`.
- Use `?.` and `?:` chains for safe fallback values at boundaries.
- Treat Java interop as untrusted: platform types can still be null.
- Use `@Nullable` / `@NotNull` annotations on Java code consumed by Kotlin.

## SQL Injection
- Use Exposed DSL or JPA with parameterized queries. Never concatenate input.
- Use `PreparedStatement` if writing raw JDBC.
- Use `CriteriaBuilder` or Exposed conditions for dynamic query construction.
- Audit `@Query(nativeQuery = true)` for parameter interpolation risks.

## Serialization
- Use `kotlinx.serialization` with `@Serializable` for compile-time safety.
- Use `Json { ignoreUnknownKeys = true }` but validate after deserialization.
- Never use Java `ObjectInputStream` for deserialization (RCE risk).
- Restrict polymorphic deserialization to known sealed class subtypes.

## Authentication
- Use Spring Security or Ktor Authentication plugin. Do not roll your own.
- Hash passwords with BCrypt or Argon2. Never store plaintext.
- Use short-lived JWTs (15 min) with refresh token rotation.
- Validate JWT signature, issuer, audience, and expiration on every request.

## Coroutine Security
- Use `withTimeout()` to prevent unbounded coroutine execution (DoS vector).
- Use `Mutex` for critical sections. Do not use `synchronized` in suspend functions.
- Propagate security context through `CoroutineContext` elements.
- Cancel coroutine scopes on authentication failure or session expiry.

## Secrets Management
- Use environment variables or Vault for secrets. Never hardcode.
- Use `@ConfigurationProperties` with injected secrets, not string literals.
- Never log request headers containing Authorization tokens.
- Use separate configuration profiles for dev/staging/prod secrets.

## Dependencies
- Use Dependabot or Renovate for automated dependency updates.
- Run OWASP Dependency-Check or Gradle `dependencyCheckAnalyze`.
- Audit transitive dependencies with `gradle dependencies`.
- Pin dependency versions. Avoid dynamic versions like `1.+`.

## Logging
- Use parameterized logging: `logger.info("User {} logged in", userId)`.
- Never log passwords, tokens, or PII.
- Sanitize user input before logging to prevent log injection.
- Use structured logging (JSON) for machine-parseable audit trails.
