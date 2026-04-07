---
language: csharp
category: security
version: "1.0.0"
---

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
