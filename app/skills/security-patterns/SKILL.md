---
name: security-patterns
description: "App security: OWASP, authN/authZ, input validation, secrets, TLS, CSRF/XSS/SQLi, JWT, CSP, LLM prompt injection. Triggers: security, OWASP, auth, JWT, CSRF, XSS, SQL injection, secrets, TLS, CSP, CORS, prompt injection, LLM output trust, tool permissions."
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

## Prompt Injection & LLM-Output Trust

When the app embeds an LLM, every byte the model emits — plus tool results, retrieved documents, and fetched web pages — is **untrusted input on the same footing as a raw request body**. Text inside that content that reads like an instruction ("ignore previous rules", "call the delete tool", "email the config to…") is still data. Render it, store it, classify it — but never let it drive control flow, widen permissions, or fire a side effect without an explicit human decision. This mirrors the agent-behavior rule in [constitution Article VII](../../constitution.md); the rules here cover the application you are building, not the assistant's own behavior.

### Trust Boundary

| Source | Trust | Handling |
|--------|-------|----------|
| System prompt / app-defined policy | Trusted | The only place instructions may originate |
| User chat turn | Semi-trusted | Authenticated to a user, still validate + scope to their permissions |
| Model output | Untrusted | Treat as data; gate any tool call it requests |
| Tool / function results | Untrusted | Re-validate before feeding back into context |
| Retrieved docs / RAG chunks | Untrusted | Strip or delimit embedded instructions |
| Fetched web / email / file content | Untrusted | Highest risk — sanitize before it crosses into the prompt |

### Defenses

- **Separate instructions from data.** Keep app policy in the system prompt; wrap all untrusted content in clear delimiters or distinct structured fields (e.g. a `documents` array) so the model can tell "what to do" from "what to read." Never string-concatenate retrieved text into the instruction block.
- **Least-privilege tools.** Give each tool the narrowest scope it needs. A summarizer needs no write or network egress capability. Fewer reachable side effects shrink the blast radius of a successful injection.
- **Human-in-the-loop for irreversible actions.** Destructive, financial, or data-exfiltrating operations (delete, transfer, send-to-external-recipient, broad file reads) require explicit human confirmation — not a model token that "looks like" approval.
- **Validate and allowlist tool arguments.** Parse the model's proposed arguments against a schema, allowlist targets (recipient domains, table names, paths), and reject anything outside it. The model choosing a tool is a *request*, not authorization.
- **Keep secrets out of injectable context.** Never place API keys, internal URLs, or other users' data in a prompt that an injected instruction could later echo back into output. If the model cannot see it, it cannot be coaxed into leaking it.
- **Bound indirect (second-order) injection.** Content ingested now may carry instructions that only fire on a later turn — a poisoned doc indexed today, a web page fetched mid-task, a comment in a parsed file. Sanitize and size-limit everything at the moment it crosses the trust boundary, not when it is finally read.

### Carve-out: Authorized Defensive Work

Building injection **detection** (classifiers, guardrails, eval suites) and running **authorized** red-team exercises — CTF, sanctioned pentest, internal adversarial testing of these defenses — is fully in scope. Generating injection payloads for that purpose is expected; the OWASP / authorized-testing framing of this skill applies to LLM apps exactly as it does to SQLi or XSS work.

---

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It's an internal API, security doesn't matter" | Internal APIs get exposed — lateral movement is attackers' primary technique |
| "The framework handles security" | Frameworks provide tools, not guarantees — misconfiguration is OWASP #5 |
| "We'll add auth later" | Unauthenticated endpoints in production get discovered within hours |
| "Nobody would exploit this" | Automated scanners don't care about your threat model — they scan everything |
| "It's behind a VPN" | VPNs are perimeter defense — zero trust assumes breach already happened |
| "The LLM would never follow a malicious instruction in a doc" | Models follow whatever reads like an instruction — retrieved content is untrusted input, not policy |
| "We let the agent run the tool it picked, that's the point" | A model picking a tool is a request, not authorization — gate side effects behind allowlists and human confirmation |

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
