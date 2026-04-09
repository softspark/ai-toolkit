# HIPAA Rules Reference

Technical controls mapping for the HIPAA Security Rule, Privacy Rule, and Breach Notification Rule. Used by the `hipaa-validate` skill to cite specific regulatory sections in findings.

## Enforcement — 45 CFR Part 160, §160.404

The enforcement rule establishes civil money penalty tiers for HIPAA violations. Understanding penalty exposure helps teams prioritize remediation.

### Penalty Tiers (§160.404(b)(2))

| Tier | Knowledge Level | Per Violation | Annual Maximum |
|------|----------------|---------------|----------------|
| 1 | Did not know (and reasonable diligence would not have revealed) | $100 – $50,000 | $1,500,000 |
| 2 | Reasonable cause, not willful neglect | $1,000 – $50,000 | $1,500,000 |
| 3 | Willful neglect, corrected within 30 days | $10,000 – $50,000 | $1,500,000 |
| 4 | Willful neglect, not timely corrected | $50,000 minimum | $1,500,000 |

**How this maps to scan findings**:
- HIGH findings with `definitive` confidence (Categories 1, 3, 4, 7, 8) typically represent Tier 2-3 exposure — the organization "should have known" via reasonable diligence
- Unresolved findings after notification represent potential Tier 3-4 exposure
- Heuristic findings (Categories 2, 5, 6) require investigation before tier assessment

### Statute of Limitations (§160.414)

Actions must be commenced within **6 years** from the date of occurrence. Continuing violations accrue a separate violation each day (§160.406).

## Security Rule — 45 CFR §164.302-318

The Security Rule establishes national standards for protecting electronic Protected Health Information (ePHI).

### §164.306 — General Rules (Flexibility of Approach)

**Requirement**: Covered entities must assess potential risks and vulnerabilities and implement security measures sufficient to reduce risks to a reasonable and appropriate level. The rule allows flexibility — entities may use any security measures that allow them to reasonably and appropriately implement the standards.

**Why this matters for scanning**:
- Heuristic findings (Categories 2, 5, 6) flag *potential* gaps — organizations may satisfy the requirement through alternative means not detectable by file-level co-occurrence checks
- The standard is "reasonable and appropriate" — not prescriptive technology mandates
- Entity size, complexity, and capabilities should be factored when assessing findings

**Detectable by**: Not directly scanned. Referenced in heuristic confidence disclaimers to prevent over-weighting.

### §164.308 — Administrative Safeguards

**Requirement**: Administrative actions, policies, and procedures to manage the selection, development, implementation, and maintenance of security measures to protect ePHI.

This is the most frequently cited section in HIPAA enforcement actions. While primarily policy-driven, several subsections have code-detectable implications.

#### §164.308(a)(1)(i) — Security Management Process

Implement policies to prevent, detect, contain, and correct security violations. Includes risk analysis and risk management.

**Code implications**:
- Security scanning should be part of CI/CD pipeline
- Risk assessment documentation should exist for PHI-handling systems
- Vulnerability management process for dependencies

**Detectable by**: Not directly scanned. Presence of security policy docs (`SECURITY.md`, `security-policy.*`) may be checked in compliance mode.

#### §164.308(a)(3) — Workforce Security

Implement policies to ensure workforce members have appropriate access to ePHI and prevent unauthorized access.

**Code implications**:
- Role-based access control (RBAC) implementation
- Principle of least privilege in permission models
- Access termination procedures when workforce members leave

**Detectable by**: Category 5 (Access Control Gaps — partial). Auth keyword checks detect missing access control but cannot verify least-privilege enforcement.

#### §164.308(a)(5) — Security Awareness and Training

Implement a security awareness and training program for all workforce members.

**Code implications**:
- Not directly code-scannable
- Security documentation and onboarding materials should reference PHI handling procedures

**Detectable by**: Not directly scanned. Informational reference.

#### §164.308(a)(6) — Security Incident Procedures

Implement policies and procedures to address security incidents. Includes identifying, responding to, mitigating, and documenting incidents.

**Code implications**:
- Incident response runbooks should exist
- Security event monitoring and alerting should be configured
- Incident logging should be separate from application logging

**Detectable by**: Not directly scanned. Compliance officers should verify incident response documentation exists.

#### §164.308(b)(1) — Business Associate Contracts

Covered entities must obtain satisfactory assurances from business associates that they will appropriately safeguard ePHI, implemented through BAA contracts.

**Code implications**:
- Every third-party service that receives, creates, maintains, or transmits PHI requires a BAA
- This includes cloud providers, analytics services, email services, database providers, CDN services, message queues, and observability platforms

**Detectable by**: Category 6 (Missing BAA References)

### §164.310 — Physical Safeguards

**Requirement**: Physical measures, policies, and procedures to protect electronic information systems and related buildings and equipment from natural and environmental hazards and unauthorized intrusion.

While primarily about physical security, several subsections have code implications.

#### §164.310(d)(2)(iii) — Device and Media Controls: Disposal

**Requirement**: Implement procedures for removal of ePHI from electronic media before the media are made available for re-use.

**Code implications**:
- Temporary files containing PHI must be securely deleted after use
- Cache files with PHI must be purged on schedule
- Application teardown/cleanup must not leave PHI artifacts on disk
- Database exports and backups must follow secure disposal procedures

**Detectable by**: Category 8 (PHI Temp File Exposure)

#### §164.310(d)(2)(iv) — Device and Media Controls: Data Backup and Storage

**Requirement**: Create a retrievable, exact copy of ePHI when needed, before movement of equipment.

**Code implications**:
- Backup procedures for PHI data stores
- Not directly code-scannable — operational procedure

**Detectable by**: Not directly scanned. Informational reference.

### §164.312(a)(1) — Access Control

**Requirement**: Implement technical policies and procedures that allow only authorized persons to access ePHI.

**Technical controls**:
- Authentication middleware on all PHI-serving routes
- Role-Based Access Control (RBAC) or Attribute-Based Access Control (ABAC)
- Session management with appropriate timeouts
- No wildcard CORS (`Access-Control-Allow-Origin: *`) on PHI endpoints
- No `public`, `noAuth`, or `anonymous` route decorators on PHI endpoints

**Detectable by**: Category 5 (Access Control Gaps)

### §164.312(a)(2)(iv) — Encryption and Decryption (Access Control Implementation)

**Requirement**: Implement a mechanism to encrypt and decrypt ePHI.

**Technical controls**:
- Encryption at rest for all PHI data stores (database-level or application-level encryption)
- Encrypted file storage for PHI documents
- No plaintext PHI in browser `localStorage` or `sessionStorage`
- No plaintext PHI in mobile local storage (`SharedPreferences`, `UserDefaults`) without encryption layer
- Encryption keys managed via KMS, not hardcoded
- `encrypt: false` explicitly disabling encryption in database configs

**Detectable by**: Category 7 (Encryption at Rest)

### §164.312(b) — Audit Controls

**Requirement**: Implement hardware, software, and/or procedural mechanisms to record and examine access and other activity in information systems that contain or use ePHI.

**Technical controls**:
- AuditEvent / audit log creation on every PHI read, write, update, delete
- Audit trail for administrative operations (user management, permission changes)
- Audit logging for bulk data exports and batch operations
- Log retention policies (minimum 6 years per §164.530(j))
- Tamper-evident audit storage (append-only, separate from application data)

**Detectable by**: Category 2 (Missing Audit Logging)

### §164.312(c)(1) — Integrity Controls

**Requirement**: Implement policies and procedures to protect ePHI from improper alteration or destruction.

**Technical controls**:
- Input validation and sanitization on PHI fields
- Data integrity checksums for stored PHI
- Database constraints (NOT NULL, CHECK, foreign keys) on PHI tables
- Version control / soft-delete for PHI records
- Optimistic concurrency control for PHI updates

**Detectable by**: Partially detectable — `DELETE FROM.*patient` without soft-delete pattern, missing input validation on PHI route handlers. Full coverage planned for future category.

### §164.312(d) — Person or Entity Authentication

**Requirement**: Implement procedures to verify that a person or entity seeking access to ePHI is who they claim to be.

**Technical controls**:
- Multi-factor authentication (MFA) for PHI access
- Strong password policies
- Token-based authentication (JWT, OAuth2) with appropriate expiration
- Session invalidation on logout
- Failed login attempt limiting

**Detectable by**: Category 5 (Access Control Gaps — partial)

### §164.312(e)(1) — Transmission Security

**Requirement**: Implement technical security measures to guard against unauthorized access to ePHI being transmitted over an electronic communications network.

**Technical controls**:
- TLS 1.2+ for all API calls transmitting PHI
- HTTPS (never HTTP) for PHI endpoints
- `wss://` (never `ws://`) for WebSocket connections carrying PHI
- TLS-enabled database connections (`ssl: true`, `sslmode: require`)
- TLS for email transport when PHI is included
- `rejectUnauthorized: true` (never `false`) for TLS certificate verification

**Detectable by**: Category 3 (Unencrypted PHI Transmission)

### §164.314(a) — Organizational Requirements: Business Associate Contracts

**Requirement**: A covered entity may permit a business associate to create, receive, maintain, or transmit ePHI on its behalf only if the covered entity obtains satisfactory assurances, in the form of a written contract (BAA), that the business associate will appropriately safeguard the information.

**Scope of BAA requirement** (per §164.314(a)(2)(i)):
- Every subcontractor that creates, receives, maintains, or transmits PHI
- Cloud infrastructure providers (AWS, GCP, Azure) storing PHI
- Database-as-a-service providers (MongoDB Atlas, RDS, Firestore)
- Message queue / event services handling PHI events
- CDN services delivering PHI content
- Email / SMS services transmitting PHI notifications
- Observability platforms receiving PHI in logs or traces
- Analytics services if any PHI flows to them

**Detectable by**: Category 6 (Missing BAA References — BAA Verification Checklist)

### §164.316 — Policies and Procedures and Documentation Requirements

**Requirement**: Implement reasonable and appropriate policies and procedures to comply with the Security Rule standards and implementation specifications. Maintain written (which may be electronic) documentation of policies and procedures. Retain documentation for **6 years** from the date of its creation or the date when it last was in effect, whichever is later.

**Code implications**:
- Security policies should be documented and version-controlled
- Policy documents (`SECURITY.md`, `HIPAA.md`, `security-policy.*`, `hipaa-policy.*`) should exist in the project
- Audit log retention must be configured for minimum 6 years
- Changes to security configurations should be tracked in version control
- Documentation must be available to persons responsible for implementing the procedures

**Detectable by**: Compliance mode — check for presence of security policy documents in project root. Informational for developer mode.

## Privacy Rule — 45 CFR §164.502, §164.514, §164.530

The Privacy Rule establishes standards for the use and disclosure of PHI. While primarily administrative, several provisions have direct code implications.

### §164.502(b) — Minimum Necessary Standard

**Requirement**: When using or disclosing PHI, a covered entity or business associate must make reasonable efforts to limit PHI to the minimum necessary to accomplish the intended purpose of the use, disclosure, or request.

**Code implications**:
- API responses should return only required PHI fields, not entire patient objects
- Log output must not contain PHI unless explicitly needed for debugging (and then only via safe logging)
- Database queries should SELECT specific columns, not `SELECT *` on PHI tables
- Data exports should filter to requested fields only
- Full-object serialization (`JSON.stringify(patient)`, `json.dumps(patient)`) in responses or logs violates minimum necessary

**Detectable by**: Category 1 (PHI in Logs — detects full-object serialization and PHI keyword patterns; also detects SELECT * and full-object API responses)

### §164.514 — De-identification

**Requirement**: PHI can be de-identified via Safe Harbor method (removing all 18 identifiers) or Expert Determination method.

**Code implications**:
- No hardcoded real patient data in source code, seed files, or fixtures
- Test data must use synthetic generators, not real patient records
- Analytics and reporting pipelines must de-identify before transmission to third parties
- The 18 HIPAA identifiers define what constitutes PHI — see [phi-identifiers.md](phi-identifiers.md)

**Detectable by**: Category 4 (Hardcoded PHI/Test Data)

### §164.530(j)(2) — Documentation and Record Retention

**Requirement**: Retain required documentation for 6 years from the date of its creation or the date when it was last in effect, whichever is later.

**Code implications**:
- Audit log retention policies must be configured for minimum 6-year retention
- PHI-related documentation (BAAs, policies) must be version-controlled
- Log rotation must not delete audit records prematurely

**Detectable by**: Not directly scanned. Informational reference for audit logging findings.

## Breach Notification Rule — 45 CFR §164.408-414

The Breach Notification Rule requires covered entities and business associates to notify affected individuals, HHS, and (in some cases) media following a breach of unsecured PHI.

### §164.408-410 — Notification Requirements

**Requirement**: Following discovery of a breach of unsecured PHI:
- Individual notification within 60 days of discovery
- HHS notification (annually if < 500 affected; within 60 days if ≥ 500)
- Media notification if ≥ 500 individuals in a single state/jurisdiction

### §164.412 — Law Enforcement Delay

**Requirement**: Notification may be delayed if law enforcement determines it would impede a criminal investigation.

### §164.414 — Administrative Requirements

**Requirement**: Maintain documentation of breach investigations, risk assessments, and notifications for 6 years.

**Code implications**:
- Not directly code-scannable, but included for awareness
- PHI exposure findings from this skill represent *potential* breach vectors
- Teams should understand that unresolved HIGH findings could lead to breach notification obligations if exploited
- Encryption of PHI at rest and in transit is the primary defense — "unsecured PHI" means unencrypted PHI

> **Note**: This rule is not scanned programmatically. It is referenced here so development teams understand the downstream consequences of PHI exposure findings detected by other categories.
