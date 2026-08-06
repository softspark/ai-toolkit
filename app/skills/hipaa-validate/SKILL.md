---
name: hipaa-validate
description: "HIPAA validator: PHI exposure, audit logging, encryption, access control, BAA refs. Triggers: HIPAA, PHI, healthcare compliance, audit log, BAA."
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
python3 ${CLAUDE_SKILL_DIR}/scripts/hipaa_scan.py [path] [--mode developer|compliance] [--severity high|warn] [--keywords term1,term2] [--output json]
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

Read [reference/scanner-categories.md](reference/scanner-categories.md) once before
starting — you cannot judge a heuristic finding without the pattern that produced it.

For each finding from the script output:

1. **Read the flagged file and line** to understand the actual code context
2. **Add a specific fix suggestion** — not generic advice, but concrete code changes based on what you see
3. **For heuristic findings** (confidence: "heuristic"), check if the concern is actually addressed elsewhere in the codebase (e.g., auth middleware at router level, audit logging in a shared module)
4. **Mark confirmed false positives** and suggest adding them to `.hipaaignore`

### Scanner Reference

The eight scan categories are implemented in `scripts/hipaa_scan.py`. The pattern
tables, severities, per-language coverage and rule citations live in
[reference/scanner-categories.md](reference/scanner-categories.md).

Read that file once, in full, before enriching findings in Step 2 — it is what lets
you explain *why* a line matched and judge whether a heuristic hit is a false
positive. The scan itself does not need it; the script already holds the patterns.

| # | Category | Scope | Mode |
|---|----------|-------|------|
| 1 | PHI in logs / console output (+ minimum-necessary violations) | full project | developer |
| 2 | Missing audit logging | full project | compliance only, heuristic |
| 3 | Unencrypted transmission | PHI-adjacent | developer |
| 4 | Hardcoded PHI test data | PHI-adjacent | developer |
| 5 | Access control gaps | PHI-adjacent | compliance only, heuristic |
| 6 | Missing BAA references | PHI-adjacent | compliance only, heuristic |
| 7 | Encryption at rest | PHI-adjacent | developer |
| 8 | PHI temp file exposure | PHI-adjacent | developer |

Categories 1 and 2 scan the full project; categories 3–8 scan only PHI-adjacent
files. Compliance mode adds the heuristic categories 2, 5 and 6 to the developer set.

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

- **Check `language_detection` in the summary before trusting a zero.** Category 1, 3, 4 and 7 patterns are language-tagged and only fire for a detected language. Manifests decide first (`pyproject.toml`, `package.json`, `go.mod`, …); without one the scanner falls back to file extensions. If it reports `languages: ["any"]` with `language_detection: "none"`, the language rules never ran and `HIGH: 0` means *unscanned*, not *compliant* — the scanner prints that warning to stderr, so a run whose stderr is discarded loses it.
- Scanning a monorepo package or a subdirectory can put you below the manifest. The extension fallback covers the common case, but a directory of `.sql`, `.yaml` or templates resolves to no language at all — scan from the level that holds the manifest.

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
