---
name: java-rules
description: "Java coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .java, pom.xml, build.gradle, Spring, Spring Boot, JPA, Hibernate, JUnit, Maven, Gradle. Load when writing, reviewing, or editing Java code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Java Rules

These rules come from `app/rules/java/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Java. Apply them when writing or
reviewing Java code.

# Java Coding Style

## Naming
- PascalCase: classes, interfaces, enums, records, annotations.
- camelCase: methods, variables, parameters.
- UPPER_SNAKE: constants (`static final`).
- Package names: lowercase, dot-separated, reverse domain (`com.company.project`).
- No Hungarian notation. No `I` prefix on interfaces.

## Modern Java (17+)
- Use `record` for immutable data carriers. No need for Lombok in most cases.
- Use `sealed` classes/interfaces for restricted hierarchies.
- Use pattern matching: `if (obj instanceof String s)` instead of cast.
- Use `switch` expressions with arrow syntax and exhaustiveness.
- Use text blocks (`"""`) for multiline strings (SQL, JSON, HTML).

## Types
- Use `var` for local variables when the type is obvious from the right-hand side.
- Use `Optional<T>` for return types that may be absent. Never for fields or params.
- Prefer `List.of()`, `Map.of()`, `Set.of()` for immutable collections.
- Use `Stream` for collection transformations. Avoid streams for simple iterations.

## Classes
- Prefer composition over inheritance. Use interfaces for abstraction.
- Keep classes focused: single responsibility.
- Use `final` on classes not designed for extension.
- Use `private` constructors + static factory methods for controlled instantiation.
- Records over POJOs for value types. Lombok only if records are insufficient.

## Methods
- Max 20-30 lines per method. Extract when longer.
- Use `@Override` on every overridden method.
- Return empty collections over `null`. Use `Collections.emptyList()` or `List.of()`.
- Avoid checked exceptions for programming errors. Use runtime exceptions.

## Formatting
- Use project formatter (Google Java Format or IDE-configured).
- Use `@SuppressWarnings` sparingly and with specific warning names.
- Use `final` for parameters and local variables where practical.

## Nullability
- Annotate with `@Nullable` / `@NonNull` from JSpecify or JetBrains.
- Use `Objects.requireNonNull()` at public API boundaries.
- Never return `null` from collections or arrays. Return empty.
- Use `Optional` for genuinely optional return values.

## Documentation
- Javadoc on all public classes and methods.
- Use `@param`, `@return`, `@throws` tags for public API methods.
- Skip Javadoc for obvious getters, `toString()`, and `equals()`.

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

# Java Patterns

## Error Handling
- Use unchecked exceptions for programming errors (`IllegalArgumentException`).
- Use checked exceptions only for recoverable conditions the caller must handle.
- Create domain exception hierarchy: `AppException` -> `NotFoundException`, etc.
- Never catch `Exception` or `Throwable` broadly. Catch specific types.
- Use `try-with-resources` for all `AutoCloseable` resources.

## Immutability
- Use `record` for immutable value objects (Java 16+).
- Use `List.copyOf()`, `Map.copyOf()` to create unmodifiable copies.
- Make fields `private final`. No setters unless mutation is required.
- Return defensive copies of mutable collections from getters.
- Use builder pattern for constructing immutable objects with many fields.

## Optional
- Use `Optional<T>` as return type for methods that may not return a value.
- Chain: `optional.map(...).orElseThrow(...)`. Avoid `isPresent()` + `get()`.
- Never use `Optional` for fields, method parameters, or collection elements.
- Use `Optional.empty()` over `null`. Use `Optional.ofNullable()` at boundaries.

## Streams
- Use streams for transformations: `filter`, `map`, `collect`.
- Avoid side effects in stream operations. Keep them pure.
- Use `Collectors.toUnmodifiableList()` for immutable results.
- Prefer `for` loop for simple iterations that do not transform data.
- Use `Stream.of()` or `IntStream.range()` for generating sequences.

## Dependency Injection
- Use constructor injection exclusively. No field or setter injection.
- Accept interfaces in constructors, not implementations.
- Use `@Component`, `@Service`, `@Repository` for Spring-managed beans.
- Keep the number of constructor dependencies under 5. Split if more.

## Concurrency
- Use `ExecutorService` and `CompletableFuture` for async operations.
- Use `virtual threads` (Java 21+) for I/O-bound concurrent work.
- Use `ConcurrentHashMap`, `AtomicInteger` for thread-safe operations.
- Avoid `synchronized` blocks when possible -- use higher-level concurrency.
- Use `ReentrantReadWriteLock` for read-heavy shared state.

## Design Patterns
- Use Strategy pattern (via interfaces) over switch/if-else chains.
- Use Factory methods for flexible object creation.
- Use Decorator pattern for composable behavior augmentation.
- Avoid Singleton pattern -- use DI container for lifecycle management.

## Anti-Patterns
- Returning `null` from methods -- use `Optional` or empty collections.
- Mutable DTOs with getters/setters -- use records.
- God classes with 20+ dependencies -- split by responsibility.
- String typing for domain values -- use types, enums, or value objects.

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

# Java Testing

## Framework
- Use JUnit 5 (Jupiter) for all new tests. No JUnit 4.
- Use AssertJ for fluent, readable assertions.
- Use Mockito for mocking dependencies.
- Use Testcontainers for integration tests with databases/services.

## File Naming
- Test classes: `FooTest.java` in `src/test/java/` mirroring source package.
- Integration tests: `FooIT.java` or use `@Tag("integration")`.
- Test utilities: `src/test/java/.../support/` or `TestUtils.java`.

## Structure
- Use `@Nested` classes to group related tests within a test class.
- Use `@DisplayName` for human-readable test descriptions.
- Use `@BeforeEach` for setup, `@AfterEach` for cleanup.
- Use `@ParameterizedTest` with `@ValueSource`, `@CsvSource`, `@MethodSource`.

## Assertions (AssertJ)
- Use `assertThat(actual).isEqualTo(expected)` over JUnit assertions.
- Use `assertThatThrownBy(() -> ...).isInstanceOf(FooException.class)`.
- Use `assertThat(list).hasSize(3).extracting("name").contains("Ada")`.
- Chain assertions for readable, self-documenting tests.

## Mocking (Mockito)
- Use `@Mock` + `@ExtendWith(MockitoExtension.class)` for injection.
- Use `when().thenReturn()` for stubbing. `verify()` for interaction checking.
- Use `@InjectMocks` to auto-inject mocks into the class under test.
- Prefer constructor injection in production code for testability.
- Use `ArgumentCaptor` to inspect complex arguments.

## Integration Testing
- Use Testcontainers for PostgreSQL, Redis, Kafka, etc.
- Use `@SpringBootTest` sparingly -- it starts the full context. Prefer slices.
- Use `@WebMvcTest` for controller tests, `@DataJpaTest` for repository tests.
- Use `@TestConfiguration` for test-specific bean overrides.

## Test Data
- Use test builders or factory methods for creating test objects.
- Use `@Sql` annotation to load test data from SQL files.
- Keep test data minimal. Only set fields relevant to the behavior under test.
- Use random UUIDs for IDs in tests to avoid collision.

## Performance
- Run tests in parallel: configure `junit.jupiter.execution.parallel.enabled=true`.
- Use `@SpringBootTest` only when integration context is needed.
- Mock external dependencies in unit tests for speed.
- Keep the full test suite under 5 minutes.
