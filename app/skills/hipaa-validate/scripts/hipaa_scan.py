#!/usr/bin/env python3
"""HIPAA compliance scanner — pattern-matching heuristics for PHI exposure.

Stdlib only. No external dependencies.
Scans codebase for HIPAA violations across 8 check categories.
"""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_KEYWORDS = [
    "patient", "diagnosis", "medication", "clinical", "healthcare",
    "medical", "fhir", "hl7", "hipaa", "phi", "protected.health",
    "health-record", "health-plan", "health-insurance",
]

SKIP_DIRS = {
    "node_modules", "vendor", ".git", "dist", "build", "out", ".next",
    "__pycache__", ".venv", "venv", ".tox", ".mypy_cache",
}

SKIP_EXTENSIONS = {
    ".lock", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".zip",
    ".tar", ".gz", ".bin", ".exe", ".dll", ".so", ".dylib", ".pyc",
}

SKIP_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "Gemfile.lock", "poetry.lock", "composer.lock",
    # IDE/editor/AI tool configs (contain pattern examples, not source code)
    ".roomodes", ".cursorrules", ".windsurfrules",
    "llms.txt", "llms-full.txt", "AGENTS.md",
    "CLAUDE.md", "GEMINI.md", "COPILOT.md",
}

TEST_DIRS = {
    "test", "tests", "__tests__", "spec", "fixtures",
    "mocks", "__mocks__", "testdata", "test-data",
}

LANGUAGE_INDICATORS = {
    "package.json": "js",
    "tsconfig.json": "ts",
    "requirements.txt": "python",
    "pyproject.toml": "python",
    "setup.py": "python",
    "go.mod": "go",
    "Cargo.toml": "rust",
    "pom.xml": "java",
    "build.gradle": "java",
    "Gemfile": "ruby",
    "*.csproj": "csharp",
}

# ---------------------------------------------------------------------------
# Pattern definitions per category
# ---------------------------------------------------------------------------

# Category 1: PHI in Logs/Console Output
CAT1_PATTERNS = [
    # JS/TS
    (r"console\.log\(.*patient", "HIGH", "js", "Patient data in console.log", "1"),
    (r"console\.\w+\(.*req\.body", "WARN", "js", "Raw request body may contain PHI", "1"),
    (r"JSON\.stringify\(.*patient", "WARN", "js", "Full patient object serialization", "1"),
    # Python
    (r"print\(.*\b(patient|ssn|social.security)", "HIGH", "python", "PHI in print statement", "1"),
    (r"logging\.\w+\(.*\b(patient|ssn|mrn|dob)", "HIGH", "python", "PHI fields in logger", "1"),
    (r"logger\.\w+\(.*\b(patient|ssn|mrn|dob)", "HIGH", "python", "PHI fields in named logger", "1"),
    (r"pprint\.\w+\(.*\b(patient|ssn|mrn|dob)", "HIGH", "python", "PHI in pprint output", "1"),
    (r"print\(.*request\.(data|json|form|POST|body)", "WARN", "python", "Raw request body may contain PHI", "1"),
    (r"logging\.\w+\(.*request\.(data|json|form|POST|body)", "WARN", "python", "Raw request body in logger", "1"),
    (r"repr\(.*\b(patient|ssn|mrn)", "WARN", "python", "repr() may expose PHI fields", "1"),
    (r"vars\(.*\b(patient|ssn|mrn)", "WARN", "python", "vars() dumps all PHI fields", "1"),
    # Go
    (r"fmt\.Print.*\b(patient|ssn|mrn)", "HIGH", "go", "PHI in fmt output", "1"),
    (r"log\.\w+\(.*\b(patient|ssn|mrn)", "HIGH", "go", "PHI in log call", "1"),
    # Java
    (r"System\.out\.print.*\b(patient|ssn|mrn)", "HIGH", "java", "PHI in stdout", "1"),
    (r"logger\.\w+\(.*\b(patient|ssn|mrn|dob)", "HIGH", "java", "PHI in logger", "1"),
    # Ruby
    (r"puts.*\b(patient|ssn|mrn)", "HIGH", "ruby", "PHI in puts", "1"),
    (r"Rails\.logger.*\b(patient|ssn|mrn)", "HIGH", "ruby", "PHI in Rails logger", "1"),
    # C#
    (r"Console\.Write.*\b(patient|ssn|mrn)", "HIGH", "csharp", "PHI in Console output", "1"),
    (r"_logger\.\w+\(.*\b(patient|ssn|mrn|dob)", "HIGH", "csharp", "PHI in ILogger", "1"),
    # Minimum Necessary (any language)
    (r"SELECT\s+\*.*FROM.*(patient|member|enrollee)", "WARN", "any", "SELECT * on PHI table violates minimum necessary", "1"),
    (r"json\.dumps\(.*patient", "WARN", "python", "Full patient object serialization", "1"),
    (r"JsonConvert\.Serialize.*patient", "WARN", "csharp", "Full patient object serialization", "1"),
]

# Category 3: Unencrypted PHI Transmission
CAT3_PATTERNS = [
    (r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)", "HIGH", "any", "Unencrypted HTTP — use HTTPS", "3"),
    (r"rejectUnauthorized:\s*false", "HIGH", "any", "TLS verification disabled", "3"),
    (r"ws://(?!localhost|127\.0\.0\.1)", "WARN", "any", "Unencrypted WebSocket", "3"),
    (r"NODE_TLS_REJECT_UNAUTHORIZED.*0", "HIGH", "js", "TLS rejection disabled globally", "3"),
    (r"verify\s*=\s*False", "HIGH", "python", "TLS verification disabled (requests)", "3"),
    (r"InsecureRequestWarning", "WARN", "python", "TLS warning suppressed", "3"),
    (r"ssl\s*=\s*False", "HIGH", "python", "SSL explicitly disabled", "3"),
    (r"CERT_NONE", "HIGH", "python", "TLS certificate verification disabled", "3"),
    (r"check_hostname\s*=\s*False", "HIGH", "python", "TLS hostname verification disabled", "3"),
    (r"urllib3\.disable_warnings", "WARN", "python", "TLS warnings suppressed (urllib3)", "3"),
    (r"SECURE_SSL_REDIRECT\s*=\s*False", "HIGH", "python", "Django HTTPS redirect disabled", "3"),
]

# Category 4: Hardcoded PHI/Test Data
CAT4_PATTERNS = [
    (r"\d{3}-\d{2}-\d{4}", "HIGH", "any", "Possible hardcoded SSN", "4"),
    (r"\b(mrn|medical.record.number|medicalRecordNumber|medical_record)\b\s*[:=]", "HIGH", "any", "MRN assignment in source", "4"),
    (r"\b\d{5}(-\d{4})?\b(?=.*\b(zip|postal|address)\b)", "WARN", "any", "ZIP code near address context", "4"),
    (r"\b(dob|dateOfBirth|birthDate|birth_date|date_of_birth)\b\s*[:=]", "WARN", "any", "Date of birth assignment", "4"),
    (r"\d{3}[\s.-]?\d{3}[\s.-]?\d{4}(?=.*\b(phone|tel|mobile|cell|contact)\b)", "WARN", "any", "Phone number in healthcare context", "4"),
]

# Category 7: Encryption at Rest
CAT7_PATTERNS = [
    (r"encrypt\s*[:=]\s*false", "HIGH", "any", "Encryption explicitly disabled", "7"),
    (r"localStorage\.setItem\(.*\b(patient|ssn|mrn|phi|health)", "HIGH", "js", "PHI in unencrypted browser storage", "7"),
    (r"sessionStorage\.setItem\(.*\b(patient|ssn|mrn|phi|health)", "HIGH", "js", "PHI in session storage", "7"),
    (r"SharedPreferences.*\b(patient|ssn|mrn|phi|health)", "HIGH", "java", "PHI in unencrypted mobile storage", "7"),
    (r"UserDefaults.*\b(patient|ssn|mrn|phi|health)", "HIGH", "any", "PHI in unencrypted UserDefaults", "7"),
    # Python
    (r"pickle\.(dump|dumps)\(.*\b(patient|phi|health|ssn|mrn)", "HIGH", "python", "PHI in unencrypted pickle", "7"),
    (r"shelve\.open\(.*\b(patient|phi|health|ssn|mrn)", "HIGH", "python", "PHI in unencrypted shelve storage", "7"),
]

# Category 8: PHI Temp File Exposure
CAT8_PATTERNS = [
    (r"/tmp/.*\b(patient|phi|health|medical)", "WARN", "any", "Temp file with PHI — ensure secure deletion", "8"),
    (r"(tempfile\.|os\.tmpdir|Path\.GetTempPath|mktemp|NamedTemporaryFile|createTempFile)", "WARN", "any", "Temp file creation near PHI context", "8"),
    (r"(cache/|\.cache|Cache\.set).*\b(patient|phi|health)", "WARN", "any", "Cached PHI — ensure encryption or purge schedule", "8"),
]

# Category 5: Access Control Gaps (heuristic, compliance only)
CAT5_AUTH_KEYWORDS = [
    "auth", "authenticate", "requireAuth", "isAuthenticated",
    "protect", "guard", "Authorize", "login_required", "Permission",
    # Python frameworks
    "permission_required", "LoginRequiredMixin", "PermissionRequiredMixin",
    "IsAuthenticated", "Depends", "Security",
]

CAT5_PATTERNS = [
    (r"Access-Control-Allow-Origin:\s*\*", "HIGH", "any", "Unrestricted CORS on PHI endpoint", "5"),
    (r"origin:\s*(true|\*)", "HIGH", "any", "Unrestricted CORS origin", "5"),
    (r"\b(public|noAuth|anonymous)\b.*\b(patient|phi|health|medical)", "HIGH", "any", "Public route exposing PHI", "5"),
    # Python
    (r"permission_classes\s*=.*AllowAny", "WARN", "python", "DRF AllowAny — verify no PHI exposed", "5"),
]

# HIPAA rule citations per category
HIPAA_RULES = {
    "1": "§164.502(b) — Minimum Necessary Standard",
    "2": "§164.312(b) — Audit Controls",
    "3": "§164.312(e)(1) — Transmission Security",
    "4": "§164.514(b)(2) — De-identification (Safe Harbor)",
    "5": "§164.312(a)(1) / §164.312(d) — Access Control / Authentication",
    "6": "§164.308(b)(1) / §164.314(a) — Business Associate Contracts",
    "7": "§164.312(a)(2)(iv) — Encryption and Decryption",
    "8": "§164.310(d)(2)(iii) — Device and Media Controls: Disposal",
}


# ---------------------------------------------------------------------------
# File traversal
# ---------------------------------------------------------------------------

def _self_dir() -> Path:
    """Return the hipaa-validate skill directory (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


def should_skip_path(path: Path, self_exclude: Path | None = None) -> bool:
    """Check if a path should be skipped based on directory/file rules."""
    parts = path.parts
    for part in parts:
        if part in SKIP_DIRS:
            return True
    if path.name in SKIP_FILES:
        return True
    if path.suffix.lower() in SKIP_EXTENSIONS:
        return True
    # Self-exclusion: skip the scanner's own skill directory
    if self_exclude:
        try:
            path.resolve().relative_to(self_exclude)
            return True
        except ValueError:
            pass
    return False


def is_test_path(path: Path) -> bool:
    """Check if path is inside a test directory."""
    for part in path.parts:
        if part in TEST_DIRS:
            return True
    return False


def load_hipaaignore(root: Path) -> list[str]:
    """Load .hipaaignore patterns from project root."""
    ignore_file = root / ".hipaaignore"
    if not ignore_file.exists():
        return []
    patterns = []
    for line in ignore_file.read_text(errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            patterns.append(line)
    return patterns


def matches_ignore(rel_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any .hipaaignore pattern."""
    for pattern in patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        # Also check each path component for directory patterns
        if pattern.endswith("/**") and rel_path.startswith(pattern[:-3]):
            return True
    return False


def collect_source_files(root: Path, scan_path: Path | None = None) -> list[Path]:
    """Collect all source files under root, respecting skip rules."""
    target = scan_path or root
    self_dir = _self_dir()
    files = []
    for dirpath, dirnames, filenames in os.walk(target):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        # Prune self directory (scanner's own skill folder)
        dp = Path(dirpath).resolve()
        try:
            dp.relative_to(self_dir)
            continue
        except ValueError:
            pass
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if not should_skip_path(fpath, self_dir):
                files.append(fpath)
    return files


# ---------------------------------------------------------------------------
# Context gate (Step 0)
# ---------------------------------------------------------------------------

def context_gate(files: list[Path], keywords: list[str],
                 ignore_patterns: list[str], root: Path) -> list[Path]:
    """Identify PHI-adjacent files containing healthcare keywords."""
    phi_files = []
    kw_pattern = re.compile("|".join(re.escape(kw) for kw in keywords), re.IGNORECASE)

    for fpath in files:
        rel = str(fpath.relative_to(root))
        if matches_ignore(rel, ignore_patterns):
            continue
        try:
            content = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        if kw_pattern.search(content):
            phi_files.append(fpath)
    return phi_files


# ---------------------------------------------------------------------------
# Language detection (Step 1)
# ---------------------------------------------------------------------------

def detect_languages(root: Path) -> set[str]:
    """Detect project languages from manifest files."""
    langs = set()
    for indicator, lang in LANGUAGE_INDICATORS.items():
        if "*" in indicator:
            # Glob-style
            for _ in root.glob(indicator):
                langs.add(lang)
                break
        else:
            if (root / indicator).exists():
                langs.add(lang)
    return langs or {"any"}


# ---------------------------------------------------------------------------
# Category scanners (Step 2)
# ---------------------------------------------------------------------------

def scan_patterns(files: list[Path], patterns: list[tuple],
                  languages: set[str], root: Path) -> list[dict]:
    """Run regex patterns against files, return findings."""
    findings = []
    for fpath in files:
        try:
            lines = fpath.read_text(errors="replace").splitlines()
        except (OSError, PermissionError):
            continue
        rel = str(fpath.relative_to(root))

        for line_num, line in enumerate(lines, 1):
            for pat, severity, lang, desc, cat in patterns:
                if lang != "any" and lang not in languages:
                    continue
                if re.search(pat, line, re.IGNORECASE):
                    findings.append({
                        "file": rel,
                        "line": line_num,
                        "severity": severity,
                        "category": int(cat),
                        "category_name": _cat_name(int(cat)),
                        "confidence": "definitive",
                        "pattern": line.strip()[:120],
                        "description": desc,
                        "hipaa_rule": HIPAA_RULES.get(cat, ""),
                    })
    return findings


def _cat_name(cat: int) -> str:
    names = {
        1: "PHI in Logs",
        2: "Missing Audit Logging",
        3: "Unencrypted PHI Transmission",
        4: "Hardcoded PHI/Test Data",
        5: "Access Control Gaps",
        6: "Missing BAA References",
        7: "Encryption at Rest",
        8: "PHI Temp File Exposure",
    }
    return names.get(cat, f"Category {cat}")


def scan_cat2_audit_gaps(phi_files: list[Path], root: Path) -> list[dict]:
    """Category 2: Missing Audit Logging (heuristic)."""
    data_ops = re.compile(
        r"(router|app\.(get|post|put|delete|patch)|"
        r"@(Request|Get|Post|Put|Delete)Mapping|"
        r"Model\.(find|save|update|delete)|"
        r"db\.(query|execute)|cursor\.execute|"
        r"repository\.|findBy|\.save\(|\.delete\(|"
        # Python frameworks
        r"@app\.route|@blueprint\.route|"
        r"@api_view|ViewSet|APIView|"
        r"session\.(query|add|execute|delete|merge))",
        re.IGNORECASE,
    )
    audit_kw = re.compile(
        r"(audit|AuditEvent|auditLog|logAccess|logEvent|"
        r"createAuditEntry|recordAccess|ActivityLog|trail|writeAudit)",
        re.IGNORECASE,
    )
    bulk_ops = re.compile(r"\b(export|download|bulk|batch)\b", re.IGNORECASE)

    findings = []
    for fpath in phi_files:
        try:
            content = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        rel = str(fpath.relative_to(root))

        if not data_ops.search(content):
            continue
        if audit_kw.search(content):
            continue

        desc = "POTENTIAL audit gap: PHI route file without audit keywords"
        if bulk_ops.search(content):
            desc = "POTENTIAL audit gap: bulk PHI operation without audit trail"

        findings.append({
            "file": rel,
            "line": 1,
            "severity": "HIGH",
            "category": 2,
            "category_name": "Missing Audit Logging",
            "confidence": "heuristic",
            "pattern": "(co-occurrence check — may be false positive)",
            "description": desc,
            "hipaa_rule": HIPAA_RULES["2"],
        })
    return findings


def scan_cat5_access_gaps(phi_files: list[Path], languages: set[str],
                          root: Path) -> list[dict]:
    """Category 5: Access Control Gaps (heuristic + definitive patterns)."""
    auth_kw = re.compile(
        "|".join(re.escape(k) for k in CAT5_AUTH_KEYWORDS), re.IGNORECASE,
    )
    data_ops = re.compile(
        r"(router|app\.(get|post|put|delete)|"
        r"@(Request|Get|Post|Put|Delete)Mapping|"
        # Python frameworks
        r"@app\.route|@blueprint\.route|"
        r"@api_view|ViewSet|APIView|"
        r"cursor\.execute|session\.(query|execute))",
        re.IGNORECASE,
    )

    findings = []

    # Heuristic: PHI route files without auth keywords
    for fpath in phi_files:
        try:
            content = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        rel = str(fpath.relative_to(root))

        if not data_ops.search(content):
            continue
        if auth_kw.search(content):
            continue

        findings.append({
            "file": rel,
            "line": 1,
            "severity": "WARN",
            "category": 5,
            "category_name": "Access Control Gaps",
            "confidence": "heuristic",
            "pattern": "(co-occurrence check — may be false positive)",
            "description": "POTENTIAL access control gap — verify auth middleware covers these routes",
            "hipaa_rule": HIPAA_RULES["5"],
        })

    # Definitive patterns
    findings.extend(scan_patterns(phi_files, CAT5_PATTERNS, languages, root))
    return findings


def scan_cat6_baa(phi_files: list[Path], root: Path) -> list[dict]:
    """Category 6: Missing BAA References — BAA Verification Checklist."""
    # Load covered vendors
    covered = set()
    config_file = root / ".hipaa-config"
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text(errors="replace"))
            covered = {v.lower() for v in cfg.get("covered_vendors", [])}
        except (json.JSONDecodeError, ValueError):
            pass

    service_patterns = [
        (r"(fetch|axios|requests|http\.Get|HttpClient|RestTemplate|urllib)\s*\(", "HTTP client call"),
        (r"(S3|GCS|BlobStorage|putObject|upload)(?!\w)", "Cloud storage"),
        (r"(mongodb\+srv://|postgres://|mysql://|firestore|dynamodb|CosmosClient|MongoClient)", "Cloud database"),
        (r"(SQS|SNS|RabbitMQ|redis://|kafka|EventBridge|PubSub)(?!\w)", "Message queue / event streaming"),
        (r"(CloudFront|Cloudflare|Akamai|Fastly|cdn\.)", "CDN"),
        (r"(datadog|splunk|newrelic|sentry|logstash|elasticsearch|bugsnag|rollbar)", "Observability / logging"),
        (r"(analytics\.|gtag|mixpanel|segment|amplitude|posthog)", "Analytics"),
    ]

    services_found: dict[str, dict] = {}
    for fpath in phi_files:
        try:
            content = fpath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue
        rel = str(fpath.relative_to(root))

        for pat, svc_type in service_patterns:
            for m in re.finditer(pat, content, re.IGNORECASE):
                key = m.group(0).strip("( \t")
                if key.lower() not in services_found:
                    services_found[key.lower()] = {
                        "service": key,
                        "type": svc_type,
                        "file": rel,
                        "pattern": m.group(0),
                    }

    findings = []
    for key, info in services_found.items():
        is_covered = any(v in key for v in covered)
        status = "covered" if is_covered else "verify_baa"

        findings.append({
            "file": info["file"],
            "line": 1,
            "severity": "WARN" if not is_covered else "INFO",
            "category": 6,
            "category_name": "Missing BAA References",
            "confidence": "heuristic",
            "pattern": f"{info['type']}: {info['pattern']}",
            "description": f"BAA status: {'covered (covered_vendors)' if is_covered else 'verify BAA exists'} — {info['type']}",
            "hipaa_rule": HIPAA_RULES["6"],
            "baa_status": status,
        })
    return findings


# ---------------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------------

def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Render an aligned plain-text table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i < len(widths):
                parts.append(f" {str(cell):<{widths[i]}} ")
        return "|" + "|".join(parts) + "|"

    lines = [sep, fmt_row(headers), sep]
    for row in rows:
        lines.append(fmt_row(row))
    lines.append(sep)
    return lines


def format_text_report(findings: list[dict], mode: str,
                       phi_count: int, scanned_count: int,
                       categories_run: list[int]) -> str:
    """Format findings as a terminal-friendly report."""
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    warn_count = sum(1 for f in findings if f["severity"] == "WARN")
    info_count = sum(1 for f in findings if f["severity"] == "INFO")

    lines = ["", "=== HIPAA Validation Report ===", ""]

    # Summary table
    summary_rows = [
        ["Mode", mode],
        ["PHI-adjacent files", str(phi_count)],
        ["Files scanned", str(scanned_count)],
        ["Categories run", ",".join(str(c) for c in sorted(categories_run))],
        ["HIGH", str(high_count)],
        ["WARN", str(warn_count)],
    ]
    if info_count:
        summary_rows.append(["INFO", str(info_count)])
    lines.extend(_table(["Metric", "Value"], summary_rows))
    lines.append("")

    if not findings:
        lines.append("No HIPAA compliance issues found.")
        lines.append("")
        return "\n".join(lines)

    # Sort: HIGH first, then WARN, then INFO
    sev_order = {"HIGH": 0, "WARN": 1, "INFO": 2}
    findings_sorted = sorted(findings, key=lambda f: (sev_order.get(f["severity"], 9), f["file"]))

    # Findings
    for f in findings_sorted:
        lines.append(f"[{f['severity']}] {f['file']}:{f['line']}")
        lines.append(f"  Category: {f['category_name']} (Cat {f['category']})")
        lines.append(f"  Confidence: {f['confidence']}")
        lines.append(f"  Pattern: {f['pattern']}")
        lines.append(f"  HIPAA Rule: {f['hipaa_rule']}")
        lines.append(f"  Description: {f['description']}")
        lines.append("")

    return "\n".join(lines)


def format_json_report(findings: list[dict], mode: str,
                       phi_count: int, scanned_count: int,
                       categories_run: list[int], languages: list[str]) -> str:
    """Format findings as structured JSON for CI integration."""
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    warn_count = sum(1 for f in findings if f["severity"] == "WARN")

    report = {
        "summary": {
            "mode": mode,
            "phi_adjacent_files": phi_count,
            "files_scanned": scanned_count,
            "categories_run": sorted(categories_run),
            "languages": sorted(languages),
            "high": high_count,
            "warn": warn_count,
            "total": len(findings),
        },
        "findings": findings,
        "exit_code": 1 if high_count > 0 else 0,
    }
    return json.dumps(report, indent=2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="HIPAA compliance scanner")
    parser.add_argument("path", nargs="?", default=".",
                        help="Project root or subdirectory to scan")
    parser.add_argument("--mode", choices=["developer", "compliance"],
                        default="developer",
                        help="Scan mode (default: developer)")
    parser.add_argument("--severity", choices=["high", "warn", "all"],
                        default="all",
                        help="Minimum severity to report (default: all)")
    parser.add_argument("--keywords", type=str, default="",
                        help="Comma-separated additional healthcare keywords")
    parser.add_argument("--output", choices=["text", "json"],
                        default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    scan_path = Path(args.path).resolve()
    # Root is always the git root or the scan path
    root = scan_path
    git_root = _find_git_root(scan_path)
    if git_root:
        root = git_root

    if not scan_path.exists():
        print(f"Error: {scan_path} does not exist", file=sys.stderr)
        sys.exit(2)

    # Build keyword list
    keywords = list(DEFAULT_KEYWORDS)
    if args.keywords:
        extra = [k.strip() for k in args.keywords.split(",") if k.strip()]
        keywords.extend(extra)

    # Load .hipaaignore
    ignore_patterns = load_hipaaignore(root)

    # Collect files
    all_files = collect_source_files(root, scan_path)
    scanned_count = len(all_files)

    # Step 0: Context gate
    phi_files = context_gate(all_files, keywords, ignore_patterns, root)
    phi_count = len(phi_files)

    if phi_count == 0:
        msg = {
            "message": "No healthcare context detected.",
            "keywords_searched": keywords,
            "hint": "If your project uses different terminology, re-run with --keywords member,enrollee,...",
        }
        if args.output == "json":
            report = {
                "summary": {
                    "mode": args.mode,
                    "phi_adjacent_files": 0,
                    "files_scanned": scanned_count,
                    "categories_run": [],
                    "languages": [],
                    "high": 0,
                    "warn": 0,
                    "total": 0,
                },
                "findings": [],
                "exit_code": 0,
                "info": msg,
            }
            print(json.dumps(report, indent=2))
        else:
            print(f"\nNo healthcare context detected.")
            print(f"Keywords searched: {', '.join(keywords)}")
            print(f"If your project uses different terminology (e.g., member, enrollee, beneficiary),")
            print(f"re-run with: --keywords member,enrollee,...")
        sys.exit(0)

    # Scope warning
    if phi_count > 50 and args.output == "text":
        print(f"\nWarning: Large scope: {phi_count} PHI-adjacent files detected.",
              file=sys.stderr)
        print("Consider narrowing the scan path for targeted results.", file=sys.stderr)

    # Step 1: Detect languages
    languages = detect_languages(root)

    # Step 2: Run categories
    findings: list[dict] = []

    # Developer mode: 1, 3, 4, 7, 8
    # Compliance mode: all 8
    if args.mode == "developer":
        categories_run = [1, 3, 4, 7, 8]
    else:
        categories_run = [1, 2, 3, 4, 5, 6, 7, 8]

    # Cat 1: PHI in Logs (full project)
    if 1 in categories_run:
        findings.extend(scan_patterns(all_files, CAT1_PATTERNS, languages, root))

    # Cat 2: Missing Audit Logging (heuristic, compliance only)
    if 2 in categories_run:
        findings.extend(scan_cat2_audit_gaps(phi_files, root))

    # Cat 3: Unencrypted Transmission (PHI-adjacent only)
    if 3 in categories_run:
        findings.extend(scan_patterns(phi_files, CAT3_PATTERNS, languages, root))

    # Cat 4: Hardcoded PHI (PHI-adjacent, skip test dirs)
    if 4 in categories_run:
        non_test_phi = [f for f in phi_files if not is_test_path(f)]
        findings.extend(scan_patterns(non_test_phi, CAT4_PATTERNS, languages, root))

    # Cat 5: Access Control Gaps (heuristic, compliance only)
    if 5 in categories_run:
        findings.extend(scan_cat5_access_gaps(phi_files, languages, root))

    # Cat 6: BAA References (compliance only)
    if 6 in categories_run:
        findings.extend(scan_cat6_baa(phi_files, root))

    # Cat 7: Encryption at Rest (PHI-adjacent)
    if 7 in categories_run:
        findings.extend(scan_patterns(phi_files, CAT7_PATTERNS, languages, root))

    # Cat 8: Temp File Exposure (PHI-adjacent)
    if 8 in categories_run:
        findings.extend(scan_patterns(phi_files, CAT8_PATTERNS, languages, root))

    # Severity filter
    if args.severity == "high":
        findings = [f for f in findings if f["severity"] == "HIGH"]
    elif args.severity == "warn":
        findings = [f for f in findings if f["severity"] in ("HIGH", "WARN")]

    # Deduplicate (same file+line+category)
    seen = set()
    deduped = []
    for f in findings:
        key = (f["file"], f["line"], f["category"], f["description"])
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    findings = deduped

    # Output
    if args.output == "json":
        print(format_json_report(findings, args.mode, phi_count,
                                 scanned_count, categories_run,
                                 sorted(languages)))
    else:
        print(format_text_report(findings, args.mode, phi_count,
                                 scanned_count, categories_run))

    # Exit code: non-zero if HIGH findings
    high_count = sum(1 for f in findings if f["severity"] == "HIGH")
    sys.exit(1 if high_count > 0 else 0)


def _find_git_root(start: Path) -> Path | None:
    """Walk up to find .git directory."""
    current = start
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return None


if __name__ == "__main__":
    main()
