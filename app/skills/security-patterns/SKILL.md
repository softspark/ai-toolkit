---
name: security-patterns
description: "Application security: OWASP Top 10, authN/authZ, input validation, secrets management, TLS, CSRF/XSS/SQLi, session handling, JWT, rate limiting, CSP. Triggers: security, OWASP, auth, JWT, CSRF, XSS, SQL injection, secrets, encryption, TLS, authentication, authorization, CSP, CORS, password hashing. Load when touching auth code, handling user input, or doing security review."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Security Patterns Skill

## OWASP Top 10 Prevention

| Risk | Prevention |
|------|------------|
| Injection | Parameterized queries, ORM |
| Broken Auth | MFA, secure sessions |
| Sensitive Data | Encryption, HTTPS |
| XXE | Disable external entities |
| Broken Access | RBAC, resource validation |
| Security Misconfig | Security headers, defaults |
| XSS | Escaping, CSP |
| Insecure Deserialization | Signed tokens, validation |
| Vulnerable Components | Dependency scanning |
| Insufficient Logging | Audit logs, monitoring |

---

## Security Headers

```python
# FastAPI middleware
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

## Secrets Management

### Environment Variables
```bash
# .env (never commit)
DATABASE_URL=postgresql://...
API_SECRET=...

# .env.example (commit this)
DATABASE_URL=postgresql://user:pass@localhost/db
API_SECRET=your-secret-here
```

### Secret Scanning
```yaml
# pre-commit hook
- repo: https://github.com/Yelp/detect-secrets
  hooks:
    - id: detect-secrets
```

---

## Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/resource")
@limiter.limit("100/minute")
async def resource():
    pass
```

---

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It's an internal API, security doesn't matter" | Internal APIs get exposed — lateral movement is attackers' primary technique |
| "The framework handles security" | Frameworks provide tools, not guarantees — misconfiguration is OWASP #5 |
| "We'll add auth later" | Unauthenticated endpoints in production get discovered within hours |
| "Nobody would exploit this" | Automated scanners don't care about your threat model — they scan everything |
| "It's behind a VPN" | VPNs are perimeter defense — zero trust assumes breach already happened |

## Reference Guides

For authentication patterns (JWT, passwords, token strategy), see [reference/authentication.md](reference/authentication.md).

For authorization patterns (RBAC, ABAC), see [reference/authorization.md](reference/authorization.md).

For input validation patterns (SQL injection, XSS, Pydantic), see [reference/input-validation.md](reference/input-validation.md).

For OAuth2 flows, CSRF protection, and audit logging, see [reference/oauth-csrf-audit.md](reference/oauth-csrf-audit.md).

## Rules

- **MUST** validate all input at the trust boundary, not inside business logic — deep validation allows bad data to spread before rejection
- **MUST** use parameterized queries (prepared statements) for every SQL interaction — string concatenation is SQL injection
- **NEVER** store secrets (API keys, tokens, passwords) in code, config files, or git history — use the platform's secret manager
- **NEVER** log passwords, tokens, PII, or PHI — even at debug level. Logs reach aggregation systems, backups, and disk snapshots.
- **NEVER** roll your own crypto. Use vetted libraries (bcrypt/argon2 for passwords, libsodium for crypto) and accept their defaults.
- **CRITICAL**: authentication (who you are) and authorization (what you can do) are distinct concerns. Confusing them produces privilege escalation bugs; AuthN passes → AuthZ still runs.
- **MANDATORY**: every endpoint is authenticated and authorized by default. Public endpoints are explicit opt-outs, not unmarked defaults.

## Gotchas

- JWT tokens signed with `none` algorithm are valid-looking tokens with no signature. Libraries that trust the `alg` header field accept them — always validate `alg` against an allowlist, never use the token's own declaration.
- `bcrypt` has a 72-byte password length cap; longer passwords are silently truncated, making "UniqueLongPassword..." collide with "UniqueLong...". Pre-hash with SHA-256 before bcrypt for >72 char passwords.
- `SameSite=Lax` cookies are **sent** on top-level navigations (including POST from a malicious site) in some browsers. CSRF protection requires either `SameSite=Strict` or explicit CSRF tokens; relying on `Lax` alone is insufficient for state-changing endpoints.
- `Content-Security-Policy` with `unsafe-inline` allows any inline script to run — negating most of CSP's value. Remove `unsafe-inline` and refactor to external scripts, even if it means extra files.
- Environment variables leak via `printenv` in debug endpoints, `/proc/<pid>/environ` on Linux, and process listings. Prefer mounting secrets as files (Docker secrets, Kubernetes secrets) for defense in depth.
- Rate limiting by IP address is bypassed by CDN proxies and legitimate shared NAT. Apply rate limits at the **authenticated user** level when possible; IP-level is a coarse last resort.

## When NOT to Load

- For dependency vulnerability scanning — use `/cve-scan`
- For HIPAA-specific healthcare compliance — use `/hipaa-validate`
- For threat modeling of a new architecture — delegate to the `security-architect` agent
- For penetration testing and CVE exploitation — delegate to `security-auditor` agent
- For content moderation (LLM safety filters) — use `/content-moderation-patterns`
