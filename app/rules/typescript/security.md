---
language: typescript
category: security
version: "1.0.0"
---

# TypeScript Security

## Input Validation
- Validate ALL request data with Zod/Valibot at API boundary.
- Use `.strip()` / `.strict()` to reject unexpected fields.
- Validate URL params and query strings, not just request bodies.
- Never pass raw user input to `eval()`, `Function()`, or template literals in SQL.

## XSS Prevention
- Use framework auto-escaping (React JSX, Angular templates).
- Never use `dangerouslySetInnerHTML` without DOMPurify sanitization.
- Sanitize user content before storing, not just before rendering.
- Set CSP headers: `default-src 'self'; script-src 'self'`.

## Authentication
- Use `httpOnly`, `secure`, `sameSite: 'strict'` for auth cookies.
- Implement CSRF protection for cookie-based auth (double-submit or token).
- Use short-lived JWTs (15min) with refresh token rotation.
- Validate JWT signature, expiration, issuer, and audience on every request.

## SQL / NoSQL Injection
- Use parameterized queries with Drizzle/Prisma/TypeORM. Never concatenate.
- For raw queries, use tagged template literals: `sql\`SELECT * FROM users WHERE id = ${id}\``.
- Validate and cast IDs to expected types (UUID, integer) before queries.
- Use ORM query builders for dynamic filters.

## Dependency Security
- Run `npm audit` in CI. Fail on high/critical vulnerabilities.
- Use `npm audit signatures` to verify package provenance.
- Pin exact versions with lockfile. Review lockfile changes in PRs.
- Avoid packages with postinstall scripts unless trusted.

## Secrets
- Use `process.env` with Zod validation for env vars.
- Never import `.env` files in production -- use platform env injection.
- Never log `req.headers.authorization` or session tokens.
- Use `crypto.timingSafeEqual()` for comparing secrets.

## Server Hardening
- Set security headers: HSTS, X-Content-Type-Options, X-Frame-Options.
- Use `helmet` middleware in Express, built-in security in Fastify.
- Implement rate limiting on all endpoints (`express-rate-limit`, `@fastify/rate-limit`).
- Disable `X-Powered-By` header. Do not expose server technology.

## File Uploads
- Validate file type by magic bytes, not just extension or MIME type.
- Set maximum file size limits on the server.
- Store uploads outside the web root. Serve through a proxy with CDN.
- Generate random filenames. Never use user-provided filenames for storage.
