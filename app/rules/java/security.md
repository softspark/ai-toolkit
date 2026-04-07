---
language: java
category: security
version: "1.0.0"
---

# Java Security

## Input Validation
- Validate all input with Jakarta Bean Validation (`@NotNull`, `@Size`, `@Email`).
- Use `@Valid` on controller parameters to trigger validation automatically.
- Create custom validators for domain-specific rules.
- Never trust client-provided IDs. Verify resource ownership server-side.

## SQL Injection
- Use JPA/Hibernate parameterized queries. Never concatenate input into JPQL/SQL.
- Use `CriteriaBuilder` or Specifications for dynamic queries.
- For native queries, use named parameters: `@Query(value = "... WHERE id = :id", nativeQuery = true)`.
- Use `PreparedStatement` if using JDBC directly. Never `Statement` with concatenation.

## Authentication
- Use Spring Security with BCrypt (`BCryptPasswordEncoder`) for password hashing.
- Use JWT with short expiration (15 min) + refresh tokens for APIs.
- Implement account lockout after N failed attempts.
- Use `@AuthenticationPrincipal` to access the current user in controllers.

## Authorization
- Use `@PreAuthorize("hasRole('ADMIN')")` for role-based access control.
- Use method security for fine-grained authorization.
- Check resource ownership in service layer, not just role membership.
- Default deny: require explicit authorization for every endpoint.

## XSS and CSRF
- Spring auto-escapes Thymeleaf output. Do not use `th:utext` with user data.
- Enable CSRF protection for session-based auth. Disable only for stateless JWT APIs.
- Set `Content-Type` headers explicitly on responses.
- Use CSP headers to restrict script sources.

## Serialization
- Do not deserialize untrusted data with `ObjectInputStream` (RCE risk).
- Use Jackson with `@JsonIgnoreProperties(ignoreUnknown = true)`.
- Disable default typing in Jackson: never use `enableDefaultTyping()`.
- Validate deserialized objects with Bean Validation after parsing.

## Dependencies
- Run OWASP Dependency-Check in CI: `mvn verify -P owasp-check`.
- Update Spring Boot regularly -- security patches are frequent.
- Use `dependencyManagement` to control transitive dependency versions.
- Audit `mvn dependency:tree` for unexpected transitive dependencies.

## Secrets
- Use Spring Cloud Config or Vault for secrets management.
- Use `@Value("${secret}")` with env var placeholders, not hardcoded values.
- Never log request headers containing `Authorization` or session tokens.
- Use separate config profiles for dev/staging/prod with different secrets.

## Logging Security
- Use parameterized logging to prevent log injection.
- Sanitize user input before logging: remove newlines and control characters.
- Never log stack traces to API responses. Return generic error messages.
