---
name: csharp-rules
description: "C#/.NET coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .cs, .csproj, .sln, ASP.NET, ASP.NET Core, EF Core, LINQ, NUnit, xUnit, dotnet. Load when writing, reviewing, or editing C#/.NET code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# C#/.NET Rules

These rules come from `app/rules/csharp/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in C#/.NET. Apply them when writing or
reviewing C#/.NET code.

# C# Coding Style

## Naming
- PascalCase: classes, structs, enums, interfaces, methods, properties, events.
- camelCase: local variables, parameters, private fields.
- Prefix interfaces with `I`: `IUserRepository`, `IDisposable`.
- Prefix private fields with `_`: `private readonly ILogger _logger;`.
- UPPER_SNAKE: not conventional in C#. Use PascalCase for constants.

## Nullable Reference Types
- Enable `<Nullable>enable</Nullable>` in all projects.
- Use `string?` only when null is semantically meaningful.
- Use `!` (null-forgiving) operator sparingly -- only when compiler cannot infer.
- Use `??` (null-coalescing) and `?.` (null-conditional) for safe navigation.
- Use `required` modifier (C# 11) on properties that must be set at initialization.

## Records and Types
- Use `record` for immutable value objects and DTOs.
- Use `record struct` for small, stack-allocated value types.
- Use `init` properties for immutable-after-construction objects.
- Use `with` expressions for non-destructive mutation of records.
- Use primary constructors (C# 12) for concise class definitions.

## Pattern Matching
- Use `is` pattern for type checks: `if (obj is string s)`.
- Use `switch` expressions for exhaustive matching over enums/types.
- Use property patterns: `user is { Age: > 18, Role: "admin" }`.
- Use relational patterns: `size is > 0 and < 100`.
- Use list patterns (C# 11): `numbers is [1, 2, .., var last]`.

## Async/Await
- Suffix async methods with `Async`: `GetUserAsync()`.
- Return `Task<T>` or `ValueTask<T>`, never `void` (except event handlers).
- Use `await` with `ConfigureAwait(false)` in library code.
- Use `CancellationToken` parameters in all async public APIs.
- Prefer `ValueTask<T>` when synchronous completion is common.

## File Organization
- One type per file. File name matches type name.
- Use file-scoped namespaces (C# 10): `namespace MyApp.Services;`.
- Order members: fields, constructors, properties, public methods, private methods.
- Use `global using` directives in a single `GlobalUsings.cs` file.

## Formatting
- Use `.editorconfig` with C# style rules committed to the repository.
- Use `dotnet format` for automated formatting.
- Use Roslyn analyzers for compile-time style enforcement.
- Max line length: 120 characters.

# C# Frameworks

## ASP.NET Core
- Use minimal APIs for simple endpoints. Use controllers for complex APIs.
- Use `[ApiController]` attribute for automatic model validation and error responses.
- Use `Results.Ok()`, `Results.NotFound()` for typed HTTP results.
- Use endpoint filters / middleware for cross-cutting concerns.
- Use `IHostedService` / `BackgroundService` for long-running background tasks.
- Map routes with `app.MapGet()`, `app.MapPost()` for minimal API style.

## Entity Framework Core
- Use code-first migrations: `dotnet ef migrations add`, `dotnet ef database update`.
- Use `DbContext` with scoped lifetime (one per request).
- Use `AsNoTracking()` for read-only queries. Use `AsTracking()` only for updates.
- Use `Include()` / `ThenInclude()` for eager loading related entities.
- Use shadow properties for audit fields (`CreatedAt`, `UpdatedAt`).
- Use `HasQueryFilter()` for soft-delete and multi-tenancy global filters.

## Blazor
- Use Blazor Server for internal tools. Use Blazor WASM for public-facing SPAs.
- Use `@inject` for dependency injection in components.
- Use `EventCallback<T>` for parent-child component communication.
- Use `CascadingValue` for deeply shared state (theme, auth).
- Use `StateContainer` pattern with events for cross-component state management.

## SignalR
- Use strongly-typed hubs: `Hub<IClientMethods>` for compile-time safety.
- Use `HubContext<T>` for sending messages from outside hubs.
- Use groups for targeted broadcasting: `Groups.AddToGroupAsync()`.
- Configure automatic reconnection on the client side.

## MassTransit / Messaging
- Use MassTransit for message bus abstraction over RabbitMQ/Azure Service Bus.
- Define messages as `record` types for immutability.
- Use consumers (`IConsumer<T>`) for message handling.
- Use sagas for long-running, multi-step workflows with state.
- Use retry and circuit breaker policies for transient failures.

## Logging
- Use `ILogger<T>` via DI. Never instantiate loggers manually.
- Use structured logging: `_logger.LogInformation("User {UserId} logged in", userId)`.
- Use Serilog with sinks for structured, centralized logging.
- Use log scopes for request correlation: `using (_logger.BeginScope(...))`.

## Configuration
- Use `appsettings.json` + environment-specific overrides + environment variables.
- Bind configuration sections to strongly-typed classes with `IOptions<T>`.
- Use `IOptionsMonitor<T>` for configuration that changes at runtime.
- Validate configuration at startup with `ValidateDataAnnotations()`.

## Health Checks
- Use `app.MapHealthChecks("/health")` for liveness probes.
- Register custom health checks for database, cache, and external service dependencies.
- Use `AspNetCore.HealthChecks.*` NuGet packages for common checks.

# C# Patterns

## Error Handling
- Use exceptions for truly exceptional conditions. Use `Result<T>` pattern for expected failures.
- Create domain exception hierarchies: `class DomainException : Exception`.
- Use `when` clause in catch: `catch (HttpRequestException e) when (e.StatusCode == 404)`.
- Use `ExceptionDispatchInfo.Capture(e).Throw()` to preserve original stack trace.
- Return `Result<T, Error>` types for operations with expected failure modes.

## Async Patterns
- Use `Task.WhenAll()` for concurrent independent operations.
- Use `SemaphoreSlim` for async-compatible resource limiting.
- Use `Channel<T>` for async producer-consumer patterns.
- Use `IAsyncEnumerable<T>` for streaming data from async sources.
- Use `Polly` for retry, circuit breaker, and timeout policies.
- Never use `.Result` or `.Wait()` on tasks (deadlock risk). Always `await`.

## Dependency Injection
- Use constructor injection exclusively. Avoid service locator pattern.
- Register services in `Program.cs` or `IServiceCollection` extension methods.
- Use `Scoped` for request-lifetime services, `Singleton` for stateless, `Transient` for lightweight.
- Use `IOptions<T>` pattern for configuration injection.
- Validate DI registrations at startup with `ValidateOnBuild = true`.

## LINQ
- Use method syntax for complex queries. Use query syntax for joins.
- Use `FirstOrDefault()` over `First()` for safe access.
- Use `AsNoTracking()` for read-only EF Core queries (performance).
- Avoid materializing large collections: use `IQueryable<T>` until final projection.
- Use `Select()` to project only needed columns from database queries.

## Disposable Pattern
- Implement `IAsyncDisposable` for async cleanup.
- Use `await using var resource = ...;` for deterministic async disposal.
- Use `IDisposable` with `using` declaration (C# 8) for scope-based cleanup.
- Register disposable services in DI container (auto-disposed at scope end).

## Mediator / CQRS
- Use MediatR for command/query separation and pipeline behaviors.
- Commands: `IRequest<Result>` for mutations. Queries: `IRequest<T>` for reads.
- Use pipeline behaviors for cross-cutting: validation, logging, transactions.
- Keep handlers thin: delegate to domain services for business logic.

## Value Objects
- Use `record` types for value objects with structural equality.
- Use factory methods with validation: `public static Result<Email> Create(string value)`.
- Override `ToString()` for logging-friendly representations.
- Use implicit/explicit operators sparingly for primitive wrapper conversions.

## Anti-Patterns
- Service locator: inject dependencies, do not resolve from container.
- `async void`: use only for event handlers. Everything else returns `Task`.
- Nested `try-catch`: flatten with early returns or guard clauses.
- Anemic domain model: put behavior in domain objects, not only services.
- Over-abstracting: do not create interfaces for classes with only one implementation.

# C# Security

## Input Validation
- Use data annotations (`[Required]`, `[StringLength]`, `[Range]`) on request models.
- Use `[ApiController]` for automatic 400 responses on validation failure.
- Use FluentValidation for complex, rule-based validation logic.
- Never trust client-provided IDs. Verify resource ownership server-side.
- Sanitize HTML input with a library like HtmlSanitizer. Never render raw user HTML.

## SQL Injection
- Use EF Core parameterized queries exclusively. Never concatenate SQL.
- Use `FromSqlInterpolated()` over `FromSqlRaw()` for raw SQL (auto-parameterized).
- Use stored procedures via `context.Database.ExecuteSqlInterpolatedAsync()`.
- Audit all `FromSqlRaw()` calls for parameter interpolation risks.
- Use Dapper with parameterized queries: `@param` syntax in SQL strings.

## Authentication
- Use ASP.NET Core Identity for user management and password hashing.
- Use `AddAuthentication().AddJwtBearer()` for JWT-based API auth.
- Use short-lived access tokens (15 min) with refresh token rotation.
- Use `[Authorize]` attribute globally. Use `[AllowAnonymous]` selectively.
- Use HTTPS redirection: `app.UseHttpsRedirection()`.

## Authorization
- Use policy-based authorization: `[Authorize(Policy = "AdminOnly")]`.
- Use `IAuthorizationHandler` for custom authorization logic.
- Use resource-based authorization for object-level access control.
- Default deny: apply `[Authorize]` at controller/app level, opt out per endpoint.
- Check ownership in service layer, not just role membership.

## CSRF and XSS
- Use anti-forgery tokens for form-based submissions.
- Razor/Blazor auto-encodes output. Never use `@Html.Raw()` with user data.
- Set `Content-Security-Policy` headers to restrict script sources.
- Use `SameSite=Strict` on cookies for CSRF mitigation.
- Enable CORS only for specific origins. Never use `AllowAnyOrigin()` with credentials.

## Data Protection
- Use `IDataProtectionProvider` for symmetric encryption of sensitive data.
- Use `SecureString` or `ProtectedData` for in-memory sensitive data (limited use).
- Use ASP.NET Core Data Protection API for token and cookie encryption.
- Hash passwords with `PasswordHasher<T>` (PBKDF2 with salt).

## Secrets Management
- Use `dotnet user-secrets` for local development. Use Azure Key Vault for production.
- Use `IConfiguration` with environment variable providers. Never hardcode secrets.
- Use `[SensitiveData]` attributes to exclude fields from logging and serialization.
- Never log request headers containing Authorization or cookie values.

## Dependency Security
- Run `dotnet list package --vulnerable` to check for known CVEs.
- Use Dependabot or NuGetAudit for automated vulnerability scanning.
- Pin package versions explicitly. Avoid floating version ranges.
- Update `Microsoft.AspNetCore.*` packages promptly for security patches.

# C# Testing

## Framework
- Use xUnit as the primary test framework (modern, extensible).
- Use NSubstitute for mocking (clean syntax, no setup boilerplate).
- Use FluentAssertions for readable, expressive assertions.
- Use Testcontainers for integration tests with databases and services.

## File Naming
- Test files: `FooTests.cs` in a separate `*.Tests` project.
- Mirror source project namespace structure in test project.
- Integration tests: separate `*.IntegrationTests` project.
- Use `[Collection("Database")]` for shared fixtures across test classes.

## Structure
- Use `[Fact]` for single test cases. Use `[Theory]` for parameterized tests.
- Use `[InlineData]` or `[MemberData]` for test data in theories.
- Use constructor injection for per-test setup. Use `IClassFixture<T>` for shared setup.
- Name tests: `MethodName_Scenario_ExpectedResult`.

## Assertions (FluentAssertions)
- Use `result.Should().Be(expected)` for value assertions.
- Use `action.Should().Throw<InvalidOperationException>()` for exception testing.
- Use `collection.Should().ContainSingle(x => x.Id == 1)` for collection assertions.
- Use `result.Should().BeEquivalentTo(expected)` for deep object comparison.
- Use `execution.Should().CompleteWithinAsync(5.Seconds())` for timeout assertions.

## Mocking (NSubstitute)
- Create mocks: `var repo = Substitute.For<IUserRepository>()`.
- Stub returns: `repo.GetAsync(1).Returns(user)`.
- Verify calls: `repo.Received(1).SaveAsync(Arg.Any<User>())`.
- Use `Arg.Is<T>(predicate)` for argument matching.
- Use `ReturnsForAnyArgs()` for lenient stubs in arrangement-focused tests.

## Integration Testing
- Use `WebApplicationFactory<Program>` for ASP.NET Core integration tests.
- Override services with `WithWebHostBuilder(b => b.ConfigureServices(...))`.
- Use `HttpClient` from factory for endpoint testing.
- Use `Respawn` for database cleanup between tests.
- Use `[Collection]` attribute to prevent parallel execution of shared-resource tests.

## Test Data
- Use Builder pattern for complex test data: `new UserBuilder().WithName("Ada").Build()`.
- Use `AutoFixture` for auto-generated test data.
- Use `Bogus` library for realistic fake data generation.
- Keep test data creation close to the test, not in distant shared files.

## Best Practices
- Test behavior, not implementation. Avoid testing private methods.
- Keep tests independent. No shared mutable state between tests.
- Use `CancellationToken.None` explicitly in async test calls.
- Run tests in CI with `dotnet test --blame-hang-timeout 60s`.
