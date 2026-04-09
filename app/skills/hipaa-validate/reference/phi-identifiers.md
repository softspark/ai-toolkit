# HIPAA PHI Identifiers

The 18 identifiers defined by HIPAA's Safe Harbor de-identification method (45 CFR §164.514(b)(2)). Removing all 18 from a dataset renders it de-identified under Safe Harbor.

Used by the `hipaa-validate` skill (Category 4) to detect hardcoded PHI in source code.

## Identifier Reference

| # | Identifier | Detectable | Detection Pattern | Notes |
|---|-----------|------------|-------------------|-------|
| 1 | Names | Partial | Co-occurrence of name-like strings (`firstName`, `lastName`, `patientName`) near healthcare keywords | Cannot detect arbitrary proper names; detects field names referencing patient names |
| 2 | Geographic data (smaller than state) | Partial | `\b\d{5}(-\d{4})?\b` near `zip\|postal\|address\|zipCode\|zip_code` keywords in PHI-adjacent files | Detects ZIP codes near address-related keywords; cannot detect arbitrary city/street names. Context-gated to reduce false positives |
| 3 | Dates (except year) | Partial | `\b(dob\|dateOfBirth\|birthDate\|birth_date\|date_of_birth)\b` near assignment/value | Detects date-of-birth field references; cannot distinguish real vs. synthetic dates |
| 4 | Phone numbers | Yes | `\d{3}[\s.-]?\d{3}[\s.-]?\d{4}` near `phone\|tel\|mobile\|cell\|contact` keywords | Context-gated to PHI-adjacent files to reduce false positives |
| 5 | Fax numbers | Partial | Same pattern as phone, near `fax` keyword | Rarely seen in modern code |
| 6 | Email addresses | Yes | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` in PHI-adjacent files | High false-positive rate without context gating |
| 7 | Social Security Numbers | Yes | `\d{3}-\d{2}-\d{4}` in PHI-adjacent files | Primary detection target. Context gate critical — pattern matches version strings and dates |
| 8 | Medical Record Numbers | Yes | `\b(mrn\|medical.record.number\|medicalRecordNumber\|medical_record)\b` near alphanumeric values | Detects MRN field references and assignments |
| 9 | Health plan beneficiary numbers | No | — | Plan-specific formats vary. Manual review required |
| 10 | Account numbers | No | — | Too generic to detect without healthcare context. Manual review required |
| 11 | Certificate/license numbers | No | — | State-specific formats. Manual review required |
| 12 | Vehicle identifiers (VIN, plates) | No | — | Not typically in healthcare code. Manual review required |
| 13 | Device identifiers (UDI, serial numbers) | No | — | Medical device context required. Manual review required |
| 14 | Web URLs | No | — | Too common in code. Manual review required for patient-specific URLs |
| 15 | IP addresses | Yes | `\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b` in PHI-adjacent files, excluding `127.0.0.1`, `0.0.0.0`, `localhost` | Context-gated; only flagged in healthcare files |
| 16 | Biometric identifiers | No | — | Fingerprints, voiceprints, retinal scans. Manual review required |
| 17 | Full-face photographs | No | — | Image content analysis out of scope. Manual review required |
| 18 | Any other unique identifying number | No | — | Catch-all category. Manual review required |

## Detection Summary

| Category | Count | Detection Method |
|----------|-------|-----------------|
| Detectable by regex | 7 | SSN, phone, email, IP, MRN, DOB, ZIP code patterns with context gating |
| Policy-only (manual review) | 11 | Listed for awareness — no automated detection possible |

## Usage in hipaa-validate

Category 4 (Hardcoded PHI/Test Data) applies these patterns only to files identified as PHI-adjacent by the Step 0 context gate. This two-phase approach prevents false positives from:
- Email addresses in user authentication code
- IP addresses in infrastructure/networking code
- Phone number patterns in non-healthcare validation logic
- SSN-like patterns in version strings or date formats

Test directories (`test/`, `tests/`, `__tests__/`, `spec/`, `fixtures/`, `mocks/`) are automatically excluded since test fixtures legitimately contain synthetic PHI data.
