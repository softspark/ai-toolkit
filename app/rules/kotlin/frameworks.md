---
language: kotlin
category: frameworks
version: "1.0.0"
---

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
