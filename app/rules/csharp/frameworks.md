---
language: csharp
category: frameworks
version: "1.0.0"
---

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
