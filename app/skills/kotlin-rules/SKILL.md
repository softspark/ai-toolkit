---
name: kotlin-rules
description: "Kotlin coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .kt, .kts, build.gradle.kts, Ktor, Jetpack Compose, coroutines, kotlinx. Load when writing, reviewing, or editing Kotlin code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Kotlin Rules

These rules come from `app/rules/kotlin/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Kotlin. Apply them when writing or
reviewing Kotlin code.

# Kotlin Coding Style

## Naming
- PascalCase: classes, interfaces, objects, type aliases, enum entries.
- camelCase: functions, properties, local variables, parameters.
- UPPER_SNAKE: compile-time constants (`const val`), top-level `val` constants.
- Backing properties: prefix with `_` (`private val _items`, `val items: List<T>`).
- Package names: lowercase, no underscores (`com.company.project.feature`).

## Null Safety
- Use nullable types only when nullability is semantically meaningful.
- Prefer `?.let { }`, `?:` (Elvis), and safe calls over `!!`.
- Never use `!!` except in tests or when null is truly impossible.
- Use `requireNotNull()` and `require()` for preconditions at public API boundaries.
- Use `checkNotNull()` and `check()` for state assertions.

## Data Classes
- Use `data class` for DTOs, value objects, and state containers.
- Use `copy()` for immutable updates. Avoid mutable `var` in data classes.
- Use `sealed class` / `sealed interface` for restricted hierarchies.
- Use `value class` (inline class) for type-safe wrappers with zero overhead.
- Use `object` for singletons and namespace-like utility groupings.

## Functions
- Use expression body (`= expr`) for single-expression functions.
- Use named arguments for functions with >2 parameters of the same type.
- Use default parameter values instead of overloaded functions.
- Use extension functions to add behavior without inheritance.
- Use `suspend` functions for async operations, not callbacks.

## Collections
- Prefer `listOf`, `mapOf`, `setOf` (immutable) over `mutableListOf`.
- Use collection operators: `map`, `filter`, `groupBy`, `associate`.
- Use `sequence {}` for lazy evaluation on large collections.
- Prefer `firstOrNull()` over `first()` for safe access.
- Use destructuring: `val (name, age) = user`.

## Scope Functions
- `let`: null-safe chaining and local scoping.
- `apply`: configure object after creation.
- `also`: side effects (logging, validation) in chains.
- `run`: compute a result using receiver's context.
- `with`: multiple operations on an object without chaining.
- Avoid nesting scope functions more than 1 level deep.

## Formatting
- Use ktlint or detekt for automated formatting and linting.
- Use trailing commas in multi-line parameter/argument lists.
- Max line length: 120 characters (Kotlin convention).
- Use `when` expression over if-else chains for 3+ branches.

# Kotlin Frameworks

## Ktor (Server)
- Use routing DSL: `routing { get("/users") { call.respond(users) } }`.
- Use `install()` for plugins: ContentNegotiation, Authentication, CORS.
- Use `call.receive<T>()` for typed request body parsing with kotlinx.serialization.
- Use `StatusPages` plugin for centralized error handling.
- Use `Routing` with nested `route("/api/v1") { }` blocks for URL grouping.

## Ktor (Client)
- Use `HttpClient` with engine configuration (CIO, OkHttp, Apache).
- Use `install(ContentNegotiation) { json() }` for JSON serialization.
- Use `client.get<T>()` with reified type for typed responses.
- Use `HttpTimeout` plugin for connection and request timeouts.
- Close `HttpClient` when done or use DI lifecycle management.

## Spring Boot (Kotlin)
- Use constructor injection (Kotlin classes are `final` by default).
- Apply `kotlin-spring` plugin for open classes (required for proxying).
- Use `@ConfigurationProperties` with data classes for typed config.
- Use `WebFlux` with coroutines: `coRouter { }` and `suspend` handler functions.
- Use `spring-boot-starter-validation` with `@Valid` on Kotlin data classes.

## Exposed (ORM)
- Use DSL API for type-safe queries: `Users.select { Users.name eq "Ada" }`.
- Use DAO API for Active Record-style: `User.find { Users.age greaterEq 18 }`.
- Wrap database operations in `transaction { }` blocks.
- Use `SchemaUtils.create(Users)` for schema management in development.

## kotlinx.serialization
- Use `@Serializable` annotation on data classes for compile-time serialization.
- Use `@SerialName("field_name")` for JSON field name mapping.
- Use `Json { ignoreUnknownKeys = true }` for lenient deserialization.
- Use polymorphic serialization with `sealed class` and `@Polymorphic`.
- Prefer `kotlinx.serialization` over Jackson for pure Kotlin projects.

## Koin (DI)
- Define modules: `module { single { UserService(get()) } }`.
- Use `by inject<T>()` for lazy injection in Android/Ktor.
- Use `factory { }` for new instance per injection, `single { }` for singleton.
- Use `checkModules()` in tests to verify DI graph completeness.

## Compose (Multiplatform UI)
- Use `@Composable` functions for UI components. Keep them stateless.
- Use `remember { }` and `mutableStateOf()` for local state.
- Hoist state to callers: pass state down, events up.
- Use `LaunchedEffect` for side effects tied to composition lifecycle.
- Use `ViewModel` with `StateFlow` for screen-level state management.

# Kotlin Patterns

## Error Handling
- Use `Result<T>` for operations that can fail without exceptions.
- Use `runCatching { }` to wrap exception-throwing code into `Result`.
- Use `sealed class` hierarchies for domain errors: `sealed class AppError`.
- Prefer `fold()`, `getOrElse()`, `getOrNull()` over `getOrThrow()`.
- Use `require()` / `check()` for preconditions; they throw `IllegalArgumentException` / `IllegalStateException`.

## Coroutines
- Use `suspend` functions for sequential async operations.
- Use `coroutineScope { }` for structured concurrency with parallel work.
- Use `async { }` + `await()` for concurrent independent operations.
- Use `supervisorScope { }` when child failures should not cancel siblings.
- Use `withContext(Dispatchers.IO)` for blocking I/O in coroutine context.
- Use `flow { }` for cold asynchronous streams. Collect in lifecycle-aware scope.

## Flow Patterns
- Use `stateIn()` and `shareIn()` to convert cold flows to hot shared state.
- Use `combine()` to merge multiple flows into derived state.
- Use `flatMapLatest` for search-as-you-type patterns (cancel previous).
- Use `catch { }` operator for upstream error handling in flows.
- Use `flowOn(Dispatchers.IO)` to shift upstream execution context.

## Sealed Hierarchies
- Use `sealed interface` over `sealed class` when no shared state is needed.
- Use `when` expressions exhaustively on sealed types (compiler-enforced).
- Combine sealed types with data classes for typed state machines.
- Use sealed hierarchies for API responses: `Success<T>`, `Error`, `Loading`.

## Delegation
- Use `by lazy { }` for thread-safe lazy initialization.
- Use `by map` for delegated properties backed by a `Map`.
- Use class delegation (`class Foo : Bar by impl`) to favor composition.
- Use `observable` / `vetoable` delegates for reactive property changes.

## Builder Patterns
- Use DSL-style builders with `@DslMarker` annotation to prevent scope leakage.
- Use trailing lambda syntax for configuration blocks.
- Use `apply { }` for inline object configuration without a dedicated builder.
- Use `buildList { }`, `buildMap { }`, `buildString { }` for collection construction.

## Anti-Patterns
- Overusing `!!`: masks null-safety guarantees. Use safe calls or require.
- Nesting scope functions: `foo.let { it.also { ... }.run { } }` -- flatten logic.
- Blocking the main thread: use `withContext(Dispatchers.IO)` for I/O.
- Using `GlobalScope.launch`: leaks coroutines. Use structured concurrency.
- Mutable shared state without synchronization: use `Mutex` or `StateFlow`.

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

# Kotlin Testing

## Framework
- Use JUnit 5 as the test runner.
- Use Kotest for Kotlin-idiomatic BDD-style testing (alternative).
- Use MockK for mocking (Kotlin-native, supports coroutines).
- Use Testcontainers for integration tests with external services.

## File Naming
- Test files: `FooTest.kt` in `src/test/kotlin/` mirroring source package.
- Integration tests: `FooIT.kt` or use `@Tag("integration")`.
- Use `@Nested` inner classes to group related test cases.

## Structure
- Use `@DisplayName` for human-readable test names.
- Use backtick function names for readable test names: `` `returns 404 when user not found` ``.
- Use `@BeforeEach` for per-test setup. Avoid shared mutable state.
- Use `@ParameterizedTest` with `@MethodSource` for table-driven tests.

## MockK
- Use `mockk<UserRepository>()` to create mocks.
- Use `every { mock.find(any()) } returns user` for stubbing.
- Use `coEvery { ... }` and `coVerify { ... }` for coroutine mocking.
- Use `spyk()` for partial mocks on real objects.
- Use `slot<T>()` and `captured` to inspect arguments.
- Clear mocks in `@AfterEach` to prevent state leakage.

## Coroutine Testing
- Use `runTest { }` from `kotlinx-coroutines-test` for coroutine tests.
- Use `TestDispatcher` to control coroutine execution timing.
- Use `advanceUntilIdle()` to complete all pending coroutines.
- Use `turbine` library for testing `Flow` emissions.

## Assertions
- Use AssertJ or Kotest assertions for fluent, readable checks.
- Use `shouldBe`, `shouldThrow`, `shouldContain` (Kotest matchers).
- Use `assertSoftly { }` to collect multiple assertion failures.
- Use `assertThrows<FooException> { ... }` for exception testing.

## Test Data
- Use factory functions for test data: `fun aUser(name: String = "Ada") = User(...)`.
- Use default parameters for minimal test data setup.
- Use `copy()` on data classes for variations of base test objects.
- Use `faker` library for realistic test data generation.

## Spring Integration
- Use `@SpringBootTest` with `@AutoConfigureMockMvc` for API tests.
- Use `@WebMvcTest` for controller-only tests (faster).
- Use `@MockkBean` instead of `@MockBean` for MockK integration.
- Use `@Transactional` on test classes for automatic rollback.
