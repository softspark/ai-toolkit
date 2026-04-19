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
