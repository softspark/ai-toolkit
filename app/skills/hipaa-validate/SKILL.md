---
name: hipaa-validate
description: "Validate code against HIPAA policy: PHI exposure, missing audit logging, unencrypted transmission/storage, access control gaps, temp file exposure, and missing BAA references"
user-invocable: true
effort: medium
disable-model-invocation: true
context: fork
agent: security-auditor
argument-hint: "[path] [--mode developer|compliance] [--severity high|warn] [--keywords term1,term2] [--output json]"
allowed-tools: Read, Grep, Glob, Bash
---

# /hipaa-validate - HIPAA Compliance Scanner

$ARGUMENTS

Scan a codebase for HIPAA compliance issues using pattern-matching heuristics. Detects PHI exposure in logs, missing audit trails, unencrypted transmission/storage, hardcoded patient data, access control gaps, and missing Business Associate Agreement references. Read-only — never modifies files.

**Regulation basis**: 45 CFR Parts 160, 162, 164 (HIPAA Administrative Simplification, as amended through March 26, 2013). Covers Security Rule (§164.302-318), Privacy Rule (§164.500-534), Breach Notification Rule (§164.400-414), and enforcement penalties (§160.400-426).

## Usage

```
/hipaa-validate                              # Scan full project (developer mode — definitives only)
/hipaa-validate src/                         # Scan specific path
/hipaa-validate --mode compliance            # Full audit sweep including heuristic categories
/hipaa-validate --severity high              # Filter to HIGH findings only
/hipaa-validate --keywords member,enrollee   # Extend healthcare keyword list
/hipaa-validate --output json                # Structured JSON output for CI integration
```

**Modes:**
- `developer` (default): Categories 1, 3, 4, 7, 8 — definitive regex matches only, low false-positive rate, suited for daily use
- `compliance`: All 8 categories — includes heuristic checks (Cat 2, 5, 6) for audit sweep coverage, suited for pre-audit sweeps

**Severity filtering:** `--severity high` shows only HIGH findings, `--severity warn` shows HIGH + WARN. Default shows all.

## What This Command Does

1. **Run scanner script** — execute `scripts/hipaa_scan.py` with passed arguments
2. **Interpret results** — analyze findings, add context, suggest specific fixes
3. **Report** — present findings with file paths, line numbers, severity, confidence, and HIPAA rule citations

## Steps

### Step 1: Run the Scanner Script

Execute the Python scanner with the user's arguments:

```bash
python3 "$(dirname "$0")/../app/skills/hipaa-validate/scripts/hipaa_scan.py" [path] [--mode developer|compliance] [--severity high|warn] [--keywords term1,term2] [--output json]
```

The script handles all scanning logic deterministically:
- **Context gate** — identifies PHI-adjacent files via healthcare keyword matching
- **Language detection** — detects project languages from manifest files
- **8 check categories** — runs regex patterns and co-occurrence heuristics
- **Deduplication** — removes duplicate findings (same file+line+category)
- **`.hipaaignore` support** — honors exclusion patterns from project root
- **`.hipaa-config` support** — reads `covered_vendors` for BAA checks

If the script reports "No healthcare context detected", relay the message and suggest the `--keywords` flag with alternative terminology.

If `--output json` is used, the script outputs structured JSON suitable for CI pipelines. The exit code is 1 if any HIGH findings exist, 0 otherwise.

### Step 2: Interpret and Enrich Results

For each finding from the script output:

1. **Read the flagged file and line** to understand the actual code context
2. **Add a specific fix suggestion** — not generic advice, but concrete code changes based on what you see
3. **For heuristic findings** (confidence: "heuristic"), check if the concern is actually addressed elsewhere in the codebase (e.g., auth middleware at router level, audit logging in a shared module)
4. **Mark confirmed false positives** and suggest adding them to `.hipaaignore`

### Scanner Reference

The script implements the following scan categories. This reference is provided so you can explain findings to the user and verify edge cases.

**Modes:**
- `developer` (default): Categories 1, 3, 4, 7, 8 — definitive regex matches only, low false-positive rate
- `compliance`: All 8 categories — includes heuristic checks (Cat 2, 5, 6)

**Default keywords**: `patient`, `diagnosis`, `medication`, `clinical`, `healthcare`, `medical`, `fhir`, `hl7`, `hipaa`, `phi`, `protected.health`, `health-record`, `health-plan`, `health-insurance`

> **Note**: Bare `health` is deliberately excluded — it matches infrastructure health checks in nearly every codebase.

**Built-in exclusions**: Binary files, lock files, vendored directories (`node_modules/`, `vendor/`, `.git/`, `dist/`, `build/`, `out/`, `.next/`). Test directories (`test/`, `tests/`, `__tests__/`, `spec/`, `fixtures/`, `mocks/`) are excluded for Category 4 only.

Categories 1 and 2 scan the full project. Categories 3–8 scan only PHI-adjacent files.

---

#### Category 1: PHI in Logs/Console Output

Scan the full project for log/print statements that reference PHI keywords.

| Pattern | Severity | Language | Description |
|---------|----------|----------|-------------|
| `console\.log\(.*patient` | HIGH | JS/TS | Patient data in console |
| `console\.\w+\(.*req\.body` | WARN | JS/TS | Raw request body may contain PHI |
| `JSON\.stringify\(.*patient` | WARN | JS/TS | Full patient object serialization |
| `print\(.*\b(patient\|ssn\|social.security)` | HIGH | Python | PHI in print statements |
| `(logging\|logger\|pprint)\.\w+\(.*\b(patient\|ssn\|mrn\|dob)` | HIGH | Python | PHI in logger/named logger/pprint output |
| `print\(.*request\.(data\|json\|form\|POST\|body)` | WARN | Python | Raw request body may contain PHI (Django/Flask/FastAPI) |
| `(logging\|logger)\.\w+\(.*request\.(data\|json\|form\|POST\|body)` | WARN | Python | Raw request body in logger |
| `\brepr\(.*\b(patient\|ssn\|mrn)` | WARN | Python | repr() may expose PHI fields |
| `\bvars\(.*\b(patient\|ssn\|mrn)` | WARN | Python | vars() dumps all PHI fields |
| `fmt\.Print.*\b(patient\|ssn\|mrn)` | HIGH | Go | PHI in fmt output |
| `log\.\w+\(.*\b(patient\|ssn\|mrn)` | HIGH | Go/Any | PHI in log calls |
| `System\.out\.print.*\b(patient\|ssn\|mrn)` | HIGH | Java | PHI in stdout |
| `logger\.\w+\(.*\b(patient\|ssn\|mrn\|dob)` | HIGH | Java/Any | PHI fields in logger |
| `puts.*\b(patient\|ssn\|mrn)` | HIGH | Ruby | PHI in puts |
| `Rails\.logger.*\b(patient\|ssn\|mrn)` | HIGH | Ruby | PHI in Rails logger |
| `Console\.Write.*\b(patient\|ssn\|mrn)` | HIGH | C# | PHI in Console output |
| `_logger\.\w+\(.*\b(patient\|ssn\|mrn\|dob)` | HIGH | C# | PHI in ILogger calls |

> **Language coverage note**: JS/TS and Python patterns are the most comprehensive. Go, Ruby, and Java have baseline coverage for common log patterns. Contributions for additional language-specific patterns are welcome.

**Minimum Necessary violations** (§164.502(b)):

| Pattern | Severity | Language | Description |
|---------|----------|----------|-------------|
| `res\.(json\|send)\(.*patient` without field projection | WARN | JS/TS | Full patient object in API response |
| `return.*patient` in route handler without field selection | WARN | Any | May expose unnecessary PHI fields |
| `SELECT\s+\*.*FROM.*(patient\|member\|enrollee)` | WARN | SQL | SELECT * on PHI tables violates minimum necessary |
| `JSON\.stringify\(.*patient` | WARN | JS/TS | Full patient object serialization |
| `json\.dumps\(.*patient` | WARN | Python | Full patient object serialization |
| `JsonConvert\.Serialize.*patient` | WARN | C# | Full patient object serialization |

---

#### Category 2: Missing Audit Logging

*Compliance mode only. Heuristic — flags potential gaps, not definitive findings.*

> **Developer mode**: This category is skipped. Run with `--mode compliance` to include audit gap checks.

Scan the full project for files that handle PHI data operations but lack audit-related keywords.

**PHI route file definition**: A file qualifies if it contains BOTH:
1. A healthcare keyword from Step 0 (`patient`, `diagnosis`, `medication`, etc.)
2. A data operation pattern: `router`, `app.get`, `app.post`, `app.put`, `app.delete`, `@RequestMapping`, `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `Model.find`, `Model.save`, `Model.update`, `db.query`, `db.execute`, `cursor.execute`, `repository.`, `findBy`, `save(`, `delete(`, `@app.route`, `@blueprint.route`, `@api_view`, `ViewSet`, `APIView`, `\bsession.(query|add|execute|delete|merge)\b` (word-anchored — SQLAlchemy only, avoids matching Express `req.session.save`)

Files with a healthcare keyword but no data operation pattern are excluded.

**Audit keywords** (co-occurrence check): `audit`, `AuditEvent`, `auditLog`, `logAccess`, `logEvent`, `createAuditEntry`, `recordAccess`, `ActivityLog`, `trail`, `writeAudit`

| Pattern | Severity | Description |
|---------|----------|-------------|
| PHI route file without any audit keywords in same file | HIGH | §164.312(b) — POTENTIAL audit gap: verify audit controls exist in call chain |
| CRUD operations on patient resources without audit keywords in same file | HIGH | POTENTIAL gap: all PHI access must be logged |
| Admin operations without audit trail reference | WARN | POTENTIAL gap: administrative actions need recording |
| Bulk data operations (`export`, `download`, `bulk`, `batch`) on PHI resources without audit keywords in same file | HIGH | POTENTIAL gap: mass PHI access must be tracked |

> **Note**: This category uses co-occurrence heuristics — checking whether PHI route keywords and audit keywords appear in the same file. False positives are expected when audit logging is handled by middleware or a separate call chain. Use `.hipaaignore` to suppress confirmed false positives.

See: [reference/hipaa-rules.md](reference/hipaa-rules.md) §164.312(b) for audit control requirements.

---

#### Category 3: Unencrypted PHI Transmission

*Context-gated: scans PHI-adjacent files only.*

| Pattern | Severity | Language | Description |
|---------|----------|----------|-------------|
| `http://` in API calls (not `localhost`/`127.0.0.1`) | HIGH | Any | §164.312(e)(1) requires encryption in transit |
| Missing TLS/SSL config in database connections | HIGH | Any | Database connections must be encrypted |
| `rejectUnauthorized:\s*false` | HIGH | Any | TLS verification disabled |
| `ws://` (WebSocket without TLS) | WARN | Any | Unencrypted WebSocket may carry PHI |
| `verify\s*=\s*False` | HIGH | Python | TLS verification disabled (requests/httpx) |
| `InsecureRequestWarning` | WARN | Python | TLS warning suppressed |
| `[,(]\s*ssl\s*=\s*False\b` | HIGH | Python | SSL disabled in connector call (anchored to arg position to avoid matching `is_ssl_enabled = False`) |
| `ssl\.CERT_NONE` | HIGH | Python | TLS certificate verification disabled (anchored to `ssl.` module) |
| `check_hostname\s*=\s*False` | HIGH | Python | TLS hostname verification disabled |
| `urllib3\.disable_warnings` | WARN | Python | TLS warnings suppressed (urllib3) |
| `SECURE_SSL_REDIRECT\s*=\s*False` | WARN | Python | Django HTTPS redirect disabled (commonly False in dev settings — verify production config) |
| `NODE_TLS_REJECT_UNAUTHORIZED.*0` | HIGH | JS/TS | TLS rejection disabled globally |

See: [reference/hipaa-rules.md](reference/hipaa-rules.md) §164.312(e)(1) for transmission security requirements.

---

#### Category 4: Hardcoded PHI/Test Data

*Context-gated: scans PHI-adjacent files only.*

**Built-in test directory exclusions**: Skip files in `test/`, `tests/`, `__tests__/`, `spec/`, `fixtures/`, `mocks/`, `__mocks__/`, `testdata/`, `test-data/` — test fixtures legitimately contain synthetic PHI.

| Pattern | Severity | Description |
|---------|----------|-------------|
| `\d{3}-\d{2}-\d{4}` in PHI-adjacent source files | HIGH | Hardcoded SSNs |
| MRN patterns near healthcare keywords | HIGH | Medical record numbers in code |
| `\b\d{5}(-\d{4})?\b` near `zip\|postal\|address` keywords | WARN | ZIP codes in healthcare context (§164.514(b)(2)(i)(B)) |
| Real-looking patient names in seed/fixture data | WARN | Use synthetic data generators |
| Date of birth + name co-occurrence in same file | WARN | Combined identifiers = PHI |
| Phone/email/IP regex matches in PHI-adjacent files | WARN | HIPAA identifiers in healthcare context |
| `\d{3}[\s.-]?\d{3}[\s.-]?\d{4}` near `phone` keyword | WARN | Phone numbers in healthcare context |

See: [reference/phi-identifiers.md](reference/phi-identifiers.md) for the full list of 18 HIPAA identifiers and detection patterns.

---

#### Category 5: Access Control Gaps

*Context-gated: scans PHI-adjacent files only. Heuristic — flags potential gaps.*

**Auth keywords** (co-occurrence check): `auth`, `authenticate`, `requireAuth`, `isAuthenticated`, `protect`, `guard`, `Authorize`, `login_required`, `Permission`, `permission_required`, `LoginRequiredMixin`, `PermissionRequiredMixin`, `IsAuthenticated`, `Depends`, `Security`

**Data operation patterns** (Python frameworks): `@app.route`, `@blueprint.route`, `@api_view`, `ViewSet`, `APIView`, `cursor.execute`, `\bsession.(query|execute)\b` (word-anchored — SQLAlchemy only)

| Pattern | Severity | Language | Description |
|---------|----------|----------|-------------|
| PHI route file without any auth keywords in same file | WARN | Any | POTENTIAL access control gap — verify auth middleware covers these routes (§164.312(d)) |
| `Access-Control-Allow-Origin:\s*\*` or `origin:\s*(true\|\*)` in PHI-adjacent files | HIGH | Any | Unrestricted cross-origin access to PHI endpoints |
| Routes marked `public`, `noAuth`, `anonymous` exposing PHI keywords | HIGH | Any | PHI must require authentication |
| `permission_classes\s*=.*AllowAny` | WARN | Python | DRF AllowAny — verify no PHI exposed |

> **Note**: Auth middleware is commonly applied at router-level or app-level. The co-occurrence heuristic checks the same file only. False positives expected when auth is configured globally. Use `.hipaaignore` to suppress.

See: [reference/hipaa-rules.md](reference/hipaa-rules.md) §164.312(a)(1) and §164.312(d) for access control and authentication requirements.

---

#### Category 6: Missing BAA References

*Compliance mode only. Context-gated: scans PHI-adjacent files only.*

> **Developer mode**: This category is skipped. Run with `--mode compliance` to include BAA checks.

Instead of per-finding rows, emit a single **BAA Verification Checklist** in the compliance report:

1. Grep PHI-adjacent files for HTTP client calls (`fetch(`, `axios.`, `requests.`, `http.Get`, `HttpClient`, `RestTemplate`, `urllib`). Extract external domains.
2. Grep for cloud storage calls (`S3`, `GCS`, `BlobStorage`, `putObject`, `upload`). Note each service.
3. Grep for cloud database connections (`mongodb+srv://`, `postgres://`, `mysql://`, `firestore`, `dynamodb`, `CosmosClient`, `MongoClient`, connection strings with cloud hostnames). Note each service.
4. Grep for message queue / event streaming services (`SQS`, `SNS`, `RabbitMQ`, `redis://`, `kafka`, `EventBridge`, `PubSub`). Note each service.
5. Grep for CDN references (`CloudFront`, `Cloudflare`, `Akamai`, `Fastly`, `cdn.`) serving PHI-adjacent paths. Note each service.
6. Grep for observability / logging SDKs (`datadog`, `splunk`, `newrelic`, `sentry`, `logstash`, `elasticsearch`, `bugsnag`, `rollbar`). Note each SDK.
7. Grep for analytics SDK calls (`analytics.`, `gtag`, `mixpanel`, `segment`, `amplitude`, `posthog`). Note each SDK.
8. Read `.hipaa-config` at project root if it exists. Suppress vendors listed under `covered_vendors`.
9. Emit one checklist row per unverified domain/service.

**`.hipaa-config` format** (suppress known-covered vendors):
```json
{
  "covered_vendors": ["aws", "twilio", "sendgrid", "stripe"]
}
```

**Output format for compliance mode**:
```
### BAA Verification Checklist
| Service/Domain | Pattern Detected | BAA Status |
|----------------|-----------------|------------|
| AWS S3 | `putObject` in src/storage/patient-files.ts | ✓ covered (covered_vendors) |
| sendgrid.com | `axios.post` in src/notifications/email.ts | ⚠️ verify BAA exists |
| analytics.google.com | `gtag` in src/components/Dashboard.tsx | ❌ verify no PHI flows here |
```

> **Note**: This is a documentation checklist, not a legal review. Items marked ⚠️ or ❌ require human verification, not code changes.

---

#### Category 7: Encryption at Rest

*Context-gated: scans PHI-adjacent files only. Developer mode.*

Detects PHI storage patterns without encryption references. Per §164.312(a)(2)(iv), ePHI must be encrypted when stored.

| Pattern | Severity | Language | Description |
|---------|----------|----------|-------------|
| `encrypt\s*[:=]\s*false` in database config files | HIGH | Any | §164.312(a)(2)(iv) — Encryption explicitly disabled |
| File write operations (`writeFile`, `fs.write`, `open(.*w`, `File.Create`) in PHI-adjacent code without encryption references | WARN | Any | PHI written to disk may lack encryption at rest |
| Database connection without `ssl`, `encrypt`, or `tls` keywords in PHI-adjacent config | WARN | Any | Database storing PHI should enforce encrypted connections |
| `localStorage.setItem` or `sessionStorage.setItem` with PHI keywords | HIGH | JS/TS | Browser storage is unencrypted — PHI must not be stored client-side without encryption |
| `SharedPreferences` or `UserDefaults` with PHI keywords | HIGH | Java/Any | Mobile local storage is unencrypted by default |
| `pickle\.(dump\|dumps)\(` with PHI keywords | HIGH | Python | pickle serialization is unencrypted — PHI must be encrypted at rest |
| `shelve\.open\(` with PHI keywords | HIGH | Python | shelve storage is unencrypted — PHI must be encrypted at rest |

See: [reference/hipaa-rules.md](reference/hipaa-rules.md) §164.312(a)(2)(iv) for encryption requirements.

---

#### Category 8: PHI Temp File Exposure

*Context-gated: scans PHI-adjacent files only. Developer mode.*

Detects temporary file creation in PHI-adjacent code without secure deletion. Per §164.310(d)(2)(iii), media containing PHI must be sanitized before reuse or disposal.

| Pattern | Severity | Description |
|---------|----------|-------------|
| `/tmp/` or `tempfile\.` or `os\.tmpdir\(\)` or `Path\.GetTempPath` in PHI-adjacent code | WARN | §164.310(d)(2)(iii) — Temp files with PHI must be securely deleted |
| `mktemp` or `NamedTemporaryFile` or `createTempFile` near PHI keywords | WARN | Verify temp files are cleaned up after use |
| Cache directory writes (`cache/`, `.cache`, `Cache.set`) with PHI keywords | WARN | Cached PHI must be encrypted or purged on schedule |

See: [reference/hipaa-rules.md](reference/hipaa-rules.md) §164.310(d)(2)(iii) for disposal requirements.

### Step 3: Compile and Report

Present the scanner output to the user. Sort by severity (HIGH first), then by file path.

## Output Format

```markdown
## HIPAA Validation Report

### Summary
| Metric | Value |
|--------|-------|
| Mode | developer / compliance |
| PHI-adjacent files | N |
| Files scanned | N |
| Categories run | 1,3,4,7,8 (developer) / 1,2,3,4,5,6,7,8 (compliance) |
| Severity HIGH | N |
| Severity WARN | N |

### Findings

#### [HIGH] src/api/patients.ts:42
Category: PHI in Logs
Confidence: definitive (regex match)
Pattern: `console.log(patient.name)`
HIPAA Rule: §164.502(b) — Minimum Necessary Standard
Fix: Replace with `safeLog()` or remove PHI from log output

#### [HIGH] src/routes/patient-api.ts:15
Category: Missing Audit Logging
Confidence: heuristic (co-occurrence check — may be false positive)
Pattern: PHI route file without audit keywords
HIPAA Rule: §164.312(b) — Audit Controls
Fix: Verify audit logging exists in call chain; add AuditEvent creation if missing

#### [WARN] src/services/patient-sync.ts:88
Category: Unencrypted PHI Transmission
Confidence: definitive (regex match)
Pattern: `http://external-api.example.com/patients`
HIPAA Rule: §164.312(e)(1) — Transmission Security
Fix: Use HTTPS for all PHI transmission
```

**Confidence values**:
- `definitive` — Categories 1, 3, 4, 7, 8: regex matched actual code
- `heuristic` — Categories 2, 5, 6: co-occurrence/absence check, may be false positive

This distinction helps compliance officers prioritize immediate remediation (definitive) vs. investigation (heuristic).

## Rules

- **MUST** remain read-only — never modify any file. This skill reports findings only.
- **MUST** cite a specific HIPAA rule section (§ number) for every finding — uncited findings are not actionable
- **MUST** run the healthcare keyword context gate before applying PHI identifier regex (Category 4) — without it, false-positive rate is ~90%
- **NEVER** label a heuristic finding as "definitive" — clearly mark `POTENTIAL` and `confidence: heuristic`
- **NEVER** scan binary files, lock files (`*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`), or vendored dirs (`node_modules/`, `vendor/`, `.git/`, `dist/`, `build/`, `out/`, `.next/`) — noise and zero signal
- **CRITICAL**: respect `.hipaaignore` exclusion patterns — teams use it to mark known-safe data fixtures
- **MANDATORY**: flag PHI-adjacent config files without `.env` or secret-manager references as a WARN category, even when no PHI pattern matches
- **NEVER** auto-fix in this version. Auto-fixing requires project-specific knowledge of logging and audit infrastructure that regex alone cannot provide.

## Gotchas

- Test fixtures and seed data often contain **synthetic** PHI that looks real (SSN-shaped IDs, formatted phone numbers, sample email addresses). Flag them but lower severity — production code handling the same patterns is the actual risk.
- HIPAA §164.312(b) requires audit logging but does not specify a format. "Logs exist" is not evidence of compliance — the logs must capture WHO (authenticated user), WHAT (action), WHEN (timestamp), WHERE (resource), and they must be immutable (append-only or write-once storage).
- Encryption-at-rest varies silently by storage layer. RDS auto-encrypts new volumes since 2017, but older DB snapshots may not be; S3 bucket policies can override instance-level encryption. Treat "encryption enabled" as a claim to verify with the cloud provider, not a state to trust.
- PHI identifiers 1-18 differ from HIPAA's "limited data set" rules — date of service and city are permitted in a limited dataset but not in full PHI. Do not auto-flag any date as PHI without context; check for surrounding patient-name or diagnosis proximity.
- PHI detection via regex misses data encoded in BLOBs, base64-embedded JSON, or encrypted-at-application-layer columns. A clean regex scan does not prove absence of PHI — document this explicitly in the report.
- Healthcare keyword context gate has dialect drift: "patient" in a veterinary codebase is a dog, not a person under HIPAA. Review context before escalating findings from multi-tenant or vertical-adjacent codebases.

## When NOT to Use

- For generic security patterns (XSS, SQLi, CSRF) — use `/security-patterns`
- For dependency vulnerabilities — use `/cve-scan`
- For non-healthcare compliance regimes (PCI-DSS, SOC2, GDPR) — this skill is HIPAA-specific
- For **legal interpretation** of compliance — this skill flags technical controls; only a QSA or attorney interprets compliance status
- For PII/GDPR outside the HIPAA scope — overlapping but distinct; HIPAA covers PHI specifically

## Reference Documents

- [reference/hipaa-rules.md](reference/hipaa-rules.md) — HIPAA Security Rule, Privacy Rule, and Breach Notification Rule mapped to technical controls
- [reference/phi-identifiers.md](reference/phi-identifiers.md) — The 18 HIPAA identifiers with detection patterns and detectability status
