---
language: common
category: security
version: "1.0.0"
---

# Universal Security Rules

## Input Validation
- Validate ALL input at API boundaries. Trust nothing from clients.
- Use allowlists over denylists: define what IS valid, reject everything else.
- Validate type, length, format, and range for every input field.
- Sanitize output for the target context (HTML, SQL, shell, URL).

## Authentication
- Hash passwords with bcrypt, scrypt, or argon2. Never MD5/SHA for passwords.
- Use constant-time comparison for tokens and secrets.
- Implement rate limiting on auth endpoints (login, register, password reset).
- Enforce MFA for admin and sensitive operations.

## Authorization
- Check permissions on every request, not just at the UI level.
- Use principle of least privilege: default deny, explicitly grant.
- Validate resource ownership: user can only access their own data.
- Never rely on client-side authorization checks.

## Secrets Management
- Never hardcode secrets in source code. Use environment variables or vaults.
- Rotate secrets regularly. Automate rotation where possible.
- Use different secrets per environment (dev/staging/prod).
- Add `.env` to `.gitignore`. Use `.env.example` as a template.

## SQL Injection Prevention
- Always use parameterized queries or ORM query builders.
- Never concatenate user input into SQL strings.
- Validate and cast types before using in queries.

## XSS Prevention
- Escape all dynamic content rendered in HTML.
- Use Content Security Policy (CSP) headers.
- Set `HttpOnly` and `Secure` flags on authentication cookies.
- Avoid `innerHTML`, `eval()`, and `dangerouslySetInnerHTML`.

## API Security
- Use HTTPS everywhere. No exceptions.
- Implement rate limiting and request throttling.
- Set CORS headers explicitly. Never use `*` in production.
- Return generic error messages to clients. Log details server-side.
- Use security headers: HSTS, X-Content-Type-Options, X-Frame-Options.

## Dependencies
- Audit dependencies regularly (`npm audit`, `pip-audit`, `cargo audit`).
- Pin dependency versions. Use lockfiles.
- Remove unused dependencies. Each dependency is an attack surface.

## Logging
- Never log passwords, tokens, credit cards, or PII.
- Log security events: failed logins, permission denials, input validation failures.
- Use structured logging with correlation IDs for traceability.
