#!/usr/bin/env python3
"""Skill & Agent Security Auditor.

Deterministic scanner for ai-toolkit skills and agents.
Detects dangerous code patterns, hardcoded secrets, and permission issues.

Stdlib-only. JSON output to stdout. Non-zero exit on HIGH findings.

Usage:
    python3 scripts/audit_skills.py [toolkit-dir]          # scan all
    python3 scripts/audit_skills.py [toolkit-dir] --json   # JSON output
    python3 scripts/audit_skills.py [toolkit-dir] --ci     # exit 1 on HIGH

Exit codes:
    0  no HIGH findings
    1  HIGH findings detected (or errors)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir as default_toolkit_dir
from frontmatter import frontmatter_field

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

PYTHON_HIGH = [
    (r'\beval\s*\(', "eval() — arbitrary code execution"),
    (r'\bexec\s*\(', "exec() — arbitrary code execution"),
    (r'\bos\.system\s*\(', "os.system() — shell injection risk"),
    (r'subprocess\.[a-z]+\(.*shell\s*=\s*True', "subprocess with shell=True — shell injection"),
    (r'\b__import__\s*\(', "__import__() — dynamic import"),
    (r'\bpickle\.loads?\s*\(', "pickle.load/loads — deserialization attack"),
    (r'\bmarshall?\.loads?\s*\(', "marshal.load/loads — deserialization attack"),
]

PYTHON_WARN = [
    (r'open\s*\(.*["\']w["\']', "open() with write mode — verify path is validated"),
    (r'\bcompile\s*\(.*\bexec\b', "compile() with exec — dynamic code generation"),
    (r'\bgetattr\s*\(.*input', "getattr with user input — attribute injection risk"),
]

BASH_HIGH = [
    (r'curl\s+.*\|\s*(ba)?sh', "curl | bash — remote code execution"),
    (r'wget\s+.*\|\s*(ba)?sh', "wget | bash — remote code execution"),
    (r'rm\s+-rf\s+/', "rm -rf / — destructive"),
    (r'rm\s+-rf\s+~', "rm -rf ~ — destructive"),
    (r'rm\s+-rf\s+\$HOME', "rm -rf $HOME — destructive"),
]

BASH_WARN = [
    (r'chmod\s+(-R\s+)?777', "chmod 777 — overly permissive"),
    (r'eval\s+"\$', "eval with variable — injection risk"),
]

SECRET_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', "HIGH", "AWS access key"),
    (r'sk-[a-zA-Z0-9]{20,}', "HIGH", "API key (sk-* pattern)"),
    (r'ghp_[a-zA-Z0-9]{36}', "HIGH", "GitHub personal access token"),
    (r'gho_[a-zA-Z0-9]{36}', "HIGH", "GitHub OAuth token"),
    (r'-----BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE\s+KEY', "HIGH", "Private key"),
    (r'password\s*=\s*["\'][^"\']{4,}["\']', "WARN", "Hardcoded password"),
    (r'token\s*=\s*["\'][^"\']{8,}["\']', "WARN", "Hardcoded token"),
    (r'secret\s*=\s*["\'][^"\']{8,}["\']', "WARN", "Hardcoded secret"),
    (r'api_key\s*=\s*["\'][^"\']{8,}["\']', "WARN", "Hardcoded API key"),
]

# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

class Finding:
    __slots__ = ("severity", "file", "line", "pattern", "description")

    def __init__(self, severity: str, file: str, line: int,
                 pattern: str, description: str) -> None:
        self.severity = severity
        self.file = file
        self.line = line
        self.pattern = pattern
        self.description = description

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "pattern": self.pattern,
            "description": self.description,
        }


def scan_file_patterns(filepath: Path, patterns: list[tuple],
                       severity: str, findings: list[Finding]) -> None:
    """Scan a single file against a list of regex patterns."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    rel = str(filepath)
    for lineno, line in enumerate(text.splitlines(), 1):
        for regex, desc in patterns:
            if re.search(regex, line, re.IGNORECASE):
                findings.append(Finding(severity, rel, lineno, regex, desc))


def scan_secrets(filepath: Path, findings: list[Finding]) -> None:
    """Scan a file for hardcoded secrets."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    rel = str(filepath)
    for lineno, line in enumerate(text.splitlines(), 1):
        for regex, severity, desc in SECRET_PATTERNS:
            if re.search(regex, line):
                findings.append(Finding(severity, rel, lineno, regex, desc))


def check_frontmatter(skill_dir: Path, findings: list[Finding]) -> None:
    """Check SKILL.md frontmatter for permission issues."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return
    rel = str(skill_md)

    allowed = frontmatter_field(skill_md, "allowed-tools")
    user_invocable = frontmatter_field(skill_md, "user-invocable")
    disable_model = frontmatter_field(skill_md, "disable-model-invocation")

    # Knowledge skill with Bash = suspicious
    if user_invocable == "false" and "Bash" in allowed:
        findings.append(Finding(
            "HIGH", rel, 0,
            "knowledge-skill-with-bash",
            "Knowledge skill (user-invocable: false) has Bash access — "
            "auto-loaded skills should not execute shell commands",
        ))

    # No allowed-tools at all = unrestricted
    if not allowed and not disable_model:
        findings.append(Finding(
            "WARN", rel, 0,
            "missing-allowed-tools",
            "No allowed-tools declared — skill has unrestricted tool access. "
            "Add allowed-tools with principle of least privilege.",
        ))

    # Overly permissive: Bash + Write + Edit without justification
    if allowed:
        tools = {t.strip() for t in allowed.split(",")}
        if {"Bash", "Write", "Edit"}.issubset(tools) and len(tools) >= 5:
            findings.append(Finding(
                "INFO", rel, 0,
                "broad-tool-access",
                f"Skill has broad tool access ({len(tools)} tools including Bash+Write+Edit). "
                "Verify this is necessary.",
            ))


def check_agent(agent_md: Path, findings: list[Finding]) -> None:
    """Check agent definition for issues."""
    rel = str(agent_md)
    tools = frontmatter_field(agent_md, "tools")
    if tools == "*":
        findings.append(Finding(
            "INFO", rel, 0,
            "agent-all-tools",
            "Agent has access to all tools (*). Consider restricting.",
        ))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def audit(toolkit_root: Path) -> list[Finding]:
    """Run full audit and return findings."""
    findings: list[Finding] = []
    app = toolkit_root / "app"
    skills = app / "skills"
    agents = app / "agents"

    # Scan skills
    if skills.is_dir():
        for skill_dir in sorted(skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            # Frontmatter checks
            check_frontmatter(skill_dir, findings)

            # Python scripts
            for py in skill_dir.rglob("*.py"):
                scan_file_patterns(py, PYTHON_HIGH, "HIGH", findings)
                scan_file_patterns(py, PYTHON_WARN, "WARN", findings)
                scan_secrets(py, findings)

            # Bash scripts
            for sh in skill_dir.rglob("*.sh"):
                scan_file_patterns(sh, BASH_HIGH, "HIGH", findings)
                scan_file_patterns(sh, BASH_WARN, "WARN", findings)
                scan_secrets(sh, findings)

            # Secrets in any text file
            for md in skill_dir.rglob("*.md"):
                scan_secrets(md, findings)

    # Scan agents
    if agents.is_dir():
        for agent_md in sorted(agents.glob("*.md")):
            check_agent(agent_md, findings)
            scan_secrets(agent_md, findings)

    # Sort: HIGH first, then WARN, then INFO
    order = {"HIGH": 0, "WARN": 1, "INFO": 2}
    findings.sort(key=lambda f: (order.get(f.severity, 9), f.file, f.line))
    return findings


def print_text(findings: list[Finding]) -> None:
    """Print human-readable report."""
    high = sum(1 for f in findings if f.severity == "HIGH")
    warn = sum(1 for f in findings if f.severity == "WARN")
    info = sum(1 for f in findings if f.severity == "INFO")

    print("Skill Security Audit")
    print("=" * 40)
    print(f"HIGH: {high} | WARN: {warn} | INFO: {info}")
    print()

    if not findings:
        print("No findings. All clear.")
        return

    for f in findings:
        loc = f"{f.file}:{f.line}" if f.line else f.file
        print(f"[{f.severity}] {loc}")
        print(f"  {f.description}")
        print()


def print_json(findings: list[Finding]) -> None:
    """Print JSON report."""
    high = sum(1 for f in findings if f.severity == "HIGH")
    report = {
        "summary": {
            "high": high,
            "warn": sum(1 for f in findings if f.severity == "WARN"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
            "total": len(findings),
        },
        "findings": [f.to_dict() for f in findings],
    }
    print(json.dumps(report, indent=2))


def main() -> None:
    args = sys.argv[1:]
    toolkit_root = default_toolkit_dir
    json_mode = False
    ci_mode = False

    for arg in args:
        if arg == "--json":
            json_mode = True
        elif arg == "--ci":
            ci_mode = True
        elif not arg.startswith("-"):
            toolkit_root = Path(arg)

    findings = audit(toolkit_root)

    if json_mode:
        print_json(findings)
    else:
        print_text(findings)

    high_count = sum(1 for f in findings if f.severity == "HIGH")
    if ci_mode and high_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
