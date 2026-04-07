---
language: java
category: frameworks
version: "1.0.0"
---

# Java Frameworks

## Spring Boot
- Use Spring Boot 3+ with Java 17+ minimum.
- Use `@RestController` for REST APIs. Return `ResponseEntity` for status control.
- Use `@Valid` + Jakarta Bean Validation for request validation.
- Use profiles (`@Profile`) for environment-specific configuration.
- Use `application.yml` over `application.properties` for readability.
- Externalize config: env vars > config files > hardcoded defaults.

## Spring Data JPA
- Use repository interfaces extending `JpaRepository`.
- Use `@Query` with JPQL for custom queries. Use native queries only when needed.
- Use `@EntityGraph` to prevent N+1 queries in associations.
- Use `Specification` for dynamic query building.
- Always use `@Transactional` at the service layer, not repository.

## Spring Security
- Use `SecurityFilterChain` bean configuration (not `WebSecurityConfigurerAdapter`).
- Use `@PreAuthorize` / `@Secured` for method-level authorization.
- Use BCrypt for password encoding: `new BCryptPasswordEncoder()`.
- Configure CORS, CSRF, and session management explicitly.
- Use OAuth2 Resource Server for JWT validation in APIs.

## Hibernate / JPA
- Use `FetchType.LAZY` by default on all associations.
- Use `@BatchSize` or `@Fetch(FetchMode.SUBSELECT)` to avoid N+1.
- Use `@Version` for optimistic locking on entities.
- Use DTOs (records) for read queries. Do not expose entities in APIs.
- Use Flyway or Liquibase for schema migrations.

## Quarkus / Micronaut
- Use for microservices and serverless where startup time matters.
- Use compile-time DI (Micronaut) or build-time optimization (Quarkus).
- Use reactive patterns with Mutiny (Quarkus) or Reactor (Micronaut).
- Use native image builds with GraalVM for production deployments.

## Build Tools
- Use Gradle (Kotlin DSL) for new projects. Maven for enterprise legacy.
- Use dependency management to unify versions across modules.
- Use Bill of Materials (BOM) imports for consistent Spring versions.
- Use Spotless or Checkstyle for enforced code formatting.

## Logging
- Use SLF4J facade with Logback or Log4j2 backend.
- Use structured logging with MDC for correlation IDs.
- Use parameterized logging: `log.info("User {} created", userId)`.
- Never log sensitive data (passwords, tokens, PII).
