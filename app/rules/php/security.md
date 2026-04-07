---
language: php
category: security
version: "1.0.0"
---

# PHP Security

## SQL Injection
- Use PDO prepared statements with bound parameters for all queries.
- Use Eloquent/Doctrine ORM for type-safe query building.
- Never concatenate user input into SQL strings. Never use `DB::raw($input)`.
- Use `whereIn()` with arrays, not string interpolation for IN clauses.
- Audit raw queries: `DB::select(DB::raw(...))` must use `?` placeholders.

## XSS Prevention
- Blade templates auto-escape with `{{ }}`. Never use `{!! !!}` with user data.
- Use `htmlspecialchars()` with `ENT_QUOTES` when outputting outside Blade.
- Set `Content-Security-Policy` headers to restrict inline scripts.
- Sanitize rich-text input with HTMLPurifier before storage.
- Use `strip_tags()` only as a secondary measure, not primary defense.

## CSRF Protection
- Use `@csrf` directive in all Blade forms.
- Use `VerifyCsrfToken` middleware (enabled by default in Laravel).
- Use `X-CSRF-TOKEN` header for AJAX requests from SPA frontends.
- Exclude only webhook endpoints from CSRF verification (with careful validation).

## Authentication
- Use `password_hash()` with `PASSWORD_ARGON2ID` or `PASSWORD_BCRYPT`.
- Use Laravel Sanctum for SPA/mobile API authentication.
- Use Laravel Passport for full OAuth2 server implementation.
- Implement rate limiting on login endpoints: `ThrottleRequests` middleware.
- Use multi-factor authentication for admin accounts.

## Authorization
- Use Laravel Gates and Policies for authorization logic.
- Use `$this->authorize('update', $post)` in controllers.
- Check resource ownership in policies, not just role membership.
- Default deny: use `Gate::before()` for super-admin bypass, nothing else.
- Use middleware `can:permission` for route-level authorization.

## File Upload
- Validate file MIME type server-side. Do not trust `Content-Type` header.
- Store uploads outside the web root. Use `storage/` with `Storage::disk()`.
- Generate random filenames. Never use original user-provided filenames.
- Set maximum file size limits in validation and PHP `upload_max_filesize`.
- Scan uploaded files for malware in production environments.

## Mass Assignment
- Use `$fillable` on Eloquent models. Never use `$guarded = []`.
- Use Form Requests to whitelist fields before model assignment.
- Use DTOs for data transfer. Never pass `$request->all()` to `create()`.
- Audit `forceFill()` and `forceCreate()` usage (bypasses guarding).

## Secrets and Configuration
- Use `.env` files for local secrets. Use Vault or SSM for production.
- Never commit `.env` to version control. Commit `.env.example` as template.
- Use `config()` helper, never `env()` outside of config files (caching issue).
- Never log request content containing passwords or tokens.
- Use `APP_DEBUG=false` in production. Debug mode leaks sensitive data.
