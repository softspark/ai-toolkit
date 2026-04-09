---
name: hipaa-validate
description: "Validate code against HIPAA policy: PHI exposure, missing audit logging, unencrypted transmission/storage, access control gaps, temp file exposure, and missing BAA references"
effort: medium
disable-model-invocation: true
argument-hint: "[path] [--mode developer|compliance] [--severity high|warn] [--keywords term1,term2]"
allowed-tools: Read, Grep, Glob
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
```

**Modes:**
- `developer` (default): Categories 1, 3, 4, 7, 8 — definitive regex matches only, low false-positive rate, suited for daily use
- `compliance`: All 8 categories — includes heuristic checks (Cat 2, 5, 6) for audit sweep coverage, suited for pre-audit sweeps

**Severity filtering:** `--severity high` shows only HIGH findings, `--severity warn` shows HIGH + WARN. Default shows all.

## What This Command Does

1. **Context gate** — identify PHI-adjacent files via healthcare keyword grep
2. **Detect** project language/framework from manifest files
3. **Scan** for HIPAA violations across 8 check categories
4. **Report** findings with file paths, line numbers, severity, confidence, and HIPAA rule citations

## Steps

### Step 0: Context Gate

Grep the entire project for healthcare keywords to build a PHI-adjacent file set:

**Default keywords**: `patient`, `diagnosis`, `medication`, `clinical`, `healthcare`, `medical`, `fhir`, `hl7`, `hipaa`, `phi`, `protected.health`, `health-record`, `health-plan`, `health-insurance`

> **Note**: Bare `health` is deliberately excluded — it matches infrastructure health checks (`healthCheck`, `/health`, `isHealthy`) in nearly every codebase. Only compound healthcare terms are used.

If `--keywords` is passed, merge those terms into the default list.

If **zero files match**, report:

```
No healthcare context detected.
Keywords searched: patient, diagnosis, medication, clinical, healthcare, medical, fhir, hl7, hipaa, phi, protected.health, health-record, health-plan, health-insurance
If your project uses different terminology (e.g., member, enrollee, beneficiary, subscriber, resident, subject, claimant), re-run with:
  /hipaa-validate --keywords member,enrollee,...
```

And exit clean — no findings.

**Built-in file exclusions** (always skipped):
- Binary files, lock files (`*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`)
- Vendored directories (`node_modules/`, `vendor/`, `.git/`, `dist/`, `build/`, `out/`, `.next/`)

**`.hipaaignore` support**: If a `.hipaaignore` file exists at project root, read it and exclude matching paths. Format follows `.gitignore` syntax — one glob pattern per line, `#` for comments. Example:

```
# Synthetic test data
tests/fixtures/**
seed/demo-data.sql
```

**Scope check**: After building the PHI-adjacent file set, count files. If count > 50, emit this warning in the Summary header before proceeding:

> ⚠️ Large scope: N PHI-adjacent files detected. Analysis may be incomplete due to context limits. Consider narrowing: `/hipaa-validate src/api/` for targeted results.

### Step 1: Detect Language/Framework

| Indicator | Language | Log Patterns | Framework Hints |
|-----------|----------|--------------|-----------------|
| `package.json` | JS/TS | `console.*`, `logger.*` | Express, Next.js, Fastify |
| `requirements.txt` / `pyproject.toml` | Python | `print(`, `logging.*` | Django, FastAPI, Flask |
| `*.go` / `go.mod` | Go | `fmt.Print`, `log.*` | net/http, gin, echo |
| `*.java` / `pom.xml` | Java | `System.out`, `Logger.*` | Spring Boot |
| `*.rb` / `Gemfile` | Ruby | `puts`, `Rails.logger` | Rails |
| `*.cs` / `*.csproj` | C# | `Console.Write`, `ILogger` | ASP.NET |

### Step 2: Run Check Categories

**Mode: developer (default)**: Run Categories 1, 3, 4, 7, 8 only — definitive regex matches, minimal false positives.
**Mode: compliance**: Run all 8 categories — Categories 2, 5, 6 are heuristic and expected to produce false positives.

Categories 1 and 2 scan the full project (patterns are inherently healthcare-scoped).
Categories 3, 4, 5, 6, 7, and 8 scan only the PHI-adjacent file set from Step 0.

---

#### Category 1: PHI in Logs/Console Output

Scan the full project for log/print statements that reference PHI keywords.

| Pattern | Severity | Language | Description |
|---------|----------|----------|-------------|
| `console\.log\(.*patient` | HIGH | JS/TS | Patient data in console |
| `console\.\w+\(.*req\.body` | WARN | JS/TS | Raw request body may contain PHI |
| `JSON\.stringify\(.*patient` | WARN | JS/TS | Full patient object serialization |
| `print\(.*\b(patient\|ssn\|social.security)` | HIGH | Python | PHI in print statements |
| `logging\.\w+\(.*\b(patient\|ssn\|mrn\|dob)` | HIGH | Python | PHI fields in logger calls |
| `fmt\.Print.*\b(patient\|ssn\|mrn)` | HIGH | Go | PHI in fmt output |
| `log\.\w+\(.*\b(patient\|ssn\|mrn)` | HIGH | Go/Any | PHI in log calls |
| `System\.out\.print.*\b(patient\|ssn\|mrn)` | HIGH | Java | PHI in stdout |
| `logger\.\w+\(.*\b(patient\|ssn\|mrn\|dob)` | HIGH | Java/Any | PHI fields in logger |
| `puts.*\b(patient\|ssn\|mrn)` | HIGH | Ruby | PHI in puts |
| `Rails\.logger.*\b(patient\|ssn\|mrn)` | HIGH | Ruby | PHI in Rails logger |
| `Console\.Write.*\b(patient\|ssn\|mrn)` | HIGH | C# | PHI in Console output |
| `_logger\.\w+\(.*\b(patient\|ssn\|mrn\|dob)` | HIGH | C# | PHI in ILogger calls |

> **Language coverage note**: JS/TS patterns are the most comprehensive. Go, Ruby, and Java have baseline coverage for common log patterns. Contributions for additional language-specific patterns are welcome.

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
2. A data operation pattern: `router`, `app.get`, `app.post`, `app.put`, `app.delete`, `@RequestMapping`, `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `Model.find`, `Model.save`, `Model.update`, `db.query`, `db.execute`, `cursor.execute`, `repository.`, `findBy`, `save(`, `delete(`

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

| Pattern | Severity | Description |
|---------|----------|-------------|
| `http://` in API calls (not `localhost`/`127.0.0.1`) | HIGH | §164.312(e)(1) requires encryption in transit |
| Missing TLS/SSL config in database connections | HIGH | Database connections must be encrypted |
| `rejectUnauthorized:\s*false` | HIGH | TLS verification disabled |
| `ws://` (WebSocket without TLS) | WARN | Unencrypted WebSocket may carry PHI |
| Email sending without TLS config | WARN | PHI in email must use TLS |

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

**Auth keywords** (co-occurrence check): `auth`, `authenticate`, `requireAuth`, `isAuthenticated`, `protect`, `guard`, `Authorize`, `login_required`, `Permission`

| Pattern | Severity | Description |
|---------|----------|-------------|
| PHI route file without any auth keywords in same file | WARN | POTENTIAL access control gap — verify auth middleware covers these routes (§164.312(d)) |
| `Access-Control-Allow-Origin:\s*\*` or `origin:\s*(true\|\*)` in PHI-adjacent files | HIGH | Unrestricted cross-origin access to PHI endpoints |
| Routes marked `public`, `noAuth`, `anonymous` exposing PHI keywords | HIGH | PHI must require authentication |

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

| Pattern | Severity | Description |
|---------|----------|-------------|
| `encrypt\s*[:=]\s*false` in database config files | HIGH | §164.312(a)(2)(iv) — Encryption explicitly disabled |
| File write operations (`writeFile`, `fs.write`, `open(.*w`, `File.Create`) in PHI-adjacent code without encryption references | WARN | PHI written to disk may lack encryption at rest |
| Database connection without `ssl`, `encrypt`, or `tls` keywords in PHI-adjacent config | WARN | Database storing PHI should enforce encrypted connections |
| `localStorage.setItem` or `sessionStorage.setItem` with PHI keywords | HIGH | Browser storage is unencrypted — PHI must not be stored client-side without encryption |
| `SharedPreferences` or `UserDefaults` with PHI keywords | HIGH | Mobile local storage is unencrypted by default |

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

Parse all findings into the unified output format below. Sort by severity (HIGH first), then by file path.

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

- **Read-only**: Never modify any files. Report findings only.
- **HIPAA rule citation**: Every finding must reference a specific HIPAA section (§ number).
- **Skip non-source files**: Binary files, lock files (`*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`), vendored directories (`node_modules/`, `vendor/`, `.git/`, `dist/`, `build/`, `out/`, `.next/`).
- **Respect `.hipaaignore`**: Honor exclusion patterns in the project's `.hipaaignore` file.
- **No false confidence**: Clearly label heuristic findings as `POTENTIAL` and mark confidence as `heuristic`.
- **Context before identifiers**: Always run the healthcare keyword context gate before applying PHI identifier regex patterns (Category 4) to avoid false positives.
- **Warn on missing secrets management**: Flag PHI-adjacent config files without `.env` or secret manager references.
- **No auto-fix in v1**: Auto-fixing HIPAA issues requires project-specific knowledge of logging/audit infrastructure. Planned for v2.

## Reference Documents

- [reference/hipaa-rules.md](reference/hipaa-rules.md) — HIPAA Security Rule, Privacy Rule, and Breach Notification Rule mapped to technical controls
- [reference/phi-identifiers.md](reference/phi-identifiers.md) — The 18 HIPAA identifiers with detection patterns and detectability status
