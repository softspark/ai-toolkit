---
language: common
category: security
version: "1.1.0"
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

## Secrets at Rest
- Never store a token, password, API key, client secret or licence key in the database in plaintext. A leaked dump must not hand out working credentials.
- Value only compared (reset, verification, invitation, refresh, API tokens): store a keyed HMAC and look rows up by hashing the presented value. Passwords: a password hash.
- Value read back (integration credentials, card tokens): authenticated encryption (AES-GCM, XChaCha20-Poly1305) with a key from the environment, never from the database.
- Value read back and looked up: encrypt it, plus a keyed-HMAC blind-index column that carries the lookup and the unique constraint.
- Put a key id in every ciphertext and hash, accept a previous key during rotation, and back the key up with the database. A lost key is lost data.
- Queued and failed job payloads count: encrypt them when they carry live links or tokens. Redact the same values from audit and request logs.
- Enforce it with a test that walks the ORM mapping and fails on a secret-looking column that is neither encrypted nor hashed. Recipes and the test template: `security-patterns` skill, `reference/secrets-at-rest.md`.

## Commercial Messages (GDPR / ePrivacy)
- Marketing e-mail/SMS goes only under the person's current consent for that channel and always carries a working opt-out; transactional messages need neither. Enforce both at the single send choke point (`security-patterns` skill, `reference/commercial-messages.md`).

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
- Return safe, actionable messages for known failures; use a neutral fallback when the cause is unknown or disclosure would reveal protected information.
- Keep SQL, stack traces and provider internals out of ordinary client responses, including 4xx and background-job error fields. Preserve original causes in access-controlled, redacted diagnostics.
- Use security headers: HSTS, X-Content-Type-Options, X-Frame-Options.

## Dependencies
- Audit dependencies regularly (`npm audit`, `pip-audit`, `cargo audit`).
- Pin dependency versions. Use lockfiles.
- Remove unused dependencies. Each dependency is an attack surface.

## Logging
- Never log passwords, tokens, credit cards, or PII.
- Log security events: failed logins, permission denials, input validation failures.
- Use structured logging with correlation IDs for traceability.
