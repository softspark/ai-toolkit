#!/usr/bin/env python3
"""Check required dependencies and tell the user what to install.

Detects OS/distro and provides ready-to-copy install commands.
Called automatically by install.py and doctor.py.

Exit codes:
    0  all required deps present
    1  missing required deps (printed to stderr)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Add scripts/ to path for _common import
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import detect_os


# ---------------------------------------------------------------------------
# Dependency definitions
# ---------------------------------------------------------------------------

REQUIRED = [
    {
        "name": "python3",
        "check": "python3",
        "min_version": "3.8",
        "packages": {
            "brew": "python3",
            "apt": "python3",
            "dnf": "python3",
            "pacman": "python3",
            "apk": "python3",
            "zypper": "python3",
            "winget": "Python.Python.3",
            "choco": "python",
            "scoop": "python",
        },
        "reason": "All toolkit scripts run on Python 3 (stdlib only, no pip needed)",
    },
    {
        "name": "git",
        "check": "git",
        "packages": {
            "brew": "git",
            "apt": "git",
            "dnf": "git",
            "pacman": "git",
            "apk": "git",
            "zypper": "git",
            "winget": "Git.Git",
            "choco": "git",
            "scoop": "git",
        },
        "reason": "Version control — hooks, commits, PR workflows",
    },
    {
        "name": "node",
        "check": "node",
        "min_version": "18",
        "packages": {
            "brew": "node",
            "apt": "nodejs",
            "dnf": "nodejs",
            "pacman": "nodejs",
            "apk": "nodejs",
            "zypper": "nodejs18",
            "winget": "OpenJS.NodeJS",
            "choco": "nodejs",
            "scoop": "nodejs",
        },
        "reason": "CLI entry point (bin/ai-toolkit.js)",
    },
]

OPTIONAL = [
    {
        "name": "sqlite3",
        "check": "sqlite3",
        "packages": {
            "brew": "sqlite",
            "apt": "sqlite3",
            "dnf": "sqlite",
            "pacman": "sqlite",
            "apk": "sqlite",
            "zypper": "sqlite3",
            "winget": "SQLite.SQLite",
            "choco": "sqlite",
            "scoop": "sqlite",
        },
        "reason": "Memory plugin pack (session persistence via SQLite + FTS5)",
    },
    {
        "name": "bats",
        "check": "bats",
        "packages": {
            "brew": "bats-core",
            "apt": "bats",
            "dnf": "bats",
            "pacman": "bash-bats",
            "apk": "bats",
            "zypper": "bats",
            "choco": "bats",
            "scoop": "bats",
        },
        "reason": "Running toolkit test suite (npm test)",
    },
    {
        "name": "pip-audit",
        "check": "pip-audit",
        "packages": {
            "brew": "pip-audit  # or: pip install pip-audit",
            "apt": "pip-audit  # pip install pip-audit",
            "dnf": "pip-audit  # pip install pip-audit",
            "pacman": "pip-audit  # pip install pip-audit",
            "apk": "pip-audit  # pip install pip-audit",
            "zypper": "pip-audit  # pip install pip-audit",
        },
        "reason": "CVE scanner (/cve-scan) for Python dependencies",
    },
    {
        "name": "cargo-audit",
        "check": "cargo-audit",
        "packages": {
            "brew": "cargo-audit  # or: cargo install cargo-audit",
            "apt": "cargo-audit  # cargo install cargo-audit",
            "dnf": "cargo-audit  # cargo install cargo-audit",
            "pacman": "cargo-audit  # cargo install cargo-audit",
            "apk": "cargo-audit  # cargo install cargo-audit",
            "zypper": "cargo-audit  # cargo install cargo-audit",
        },
        "reason": "CVE scanner (/cve-scan) for Rust dependencies",
    },
    {
        "name": "govulncheck",
        "check": "govulncheck",
        "packages": {
            "brew": "govulncheck  # go install golang.org/x/vuln/cmd/govulncheck@latest",
            "apt": "govulncheck  # go install golang.org/x/vuln/cmd/govulncheck@latest",
            "dnf": "govulncheck  # go install golang.org/x/vuln/cmd/govulncheck@latest",
            "pacman": "govulncheck  # go install golang.org/x/vuln/cmd/govulncheck@latest",
            "apk": "govulncheck  # go install golang.org/x/vuln/cmd/govulncheck@latest",
            "zypper": "govulncheck  # go install golang.org/x/vuln/cmd/govulncheck@latest",
        },
        "reason": "CVE scanner (/cve-scan) for Go dependencies",
    },
    {
        "name": "bundle-audit",
        "check": "bundle-audit",
        "packages": {
            "brew": "bundler-audit  # or: gem install bundler-audit",
            "apt": "bundler-audit  # gem install bundler-audit",
            "dnf": "bundler-audit  # gem install bundler-audit",
            "pacman": "bundler-audit  # gem install bundler-audit",
            "apk": "bundler-audit  # gem install bundler-audit",
            "zypper": "bundler-audit  # gem install bundler-audit",
        },
        "reason": "CVE scanner (/cve-scan) for Ruby dependencies",
    },
]


# ---------------------------------------------------------------------------
# Version check helpers
# ---------------------------------------------------------------------------

def get_version(binary: str) -> str:
    """Get version string from a binary."""
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = result.stdout.strip() or result.stderr.strip()
        # Extract version number pattern
        import re
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", output)
        return match.group(1) if match else "unknown"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def version_ge(actual: str, minimum: str) -> bool:
    """Check if actual version >= minimum version."""
    try:
        actual_parts = [int(x) for x in actual.split(".")[:3]]
        min_parts = [int(x) for x in minimum.split(".")[:3]]
        # Pad to same length
        while len(actual_parts) < len(min_parts):
            actual_parts.append(0)
        while len(min_parts) < len(actual_parts):
            min_parts.append(0)
        return actual_parts >= min_parts
    except (ValueError, IndexError):
        return True  # Can't parse, assume OK


# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------

def check_deps(verbose: bool = True) -> dict:
    """Check all dependencies and return status report.

    Returns:
        dict with keys: os_info, required, optional, all_ok, missing_cmds
    """
    os_info = detect_os()
    pkg_mgr = os_info["pkg_manager"]
    install_cmd = os_info["install_cmd"]

    results: dict = {
        "os_info": os_info,
        "required": [],
        "optional": [],
        "all_ok": True,
        "missing_cmds": [],
    }

    def check_one(dep: dict, required: bool) -> dict:
        binary = dep["check"]
        found = shutil.which(binary) is not None
        version = get_version(binary) if found else ""
        min_ver = dep.get("min_version", "")

        ok = found
        version_ok = True
        if found and min_ver and version and version != "unknown":
            version_ok = version_ge(version, min_ver)
            ok = version_ok

        install_hint = ""
        if not ok and install_cmd and pkg_mgr in dep.get("packages", {}):
            pkg = dep["packages"][pkg_mgr]
            install_hint = f"{install_cmd} {pkg}"

        return {
            "name": dep["name"],
            "found": found,
            "version": version,
            "version_ok": version_ok,
            "min_version": min_ver,
            "required": required,
            "reason": dep["reason"],
            "install_hint": install_hint,
        }

    for dep in REQUIRED:
        result = check_one(dep, required=True)
        results["required"].append(result)
        if not result["found"] or not result["version_ok"]:
            results["all_ok"] = False
            if result["install_hint"]:
                results["missing_cmds"].append(result["install_hint"])

    for dep in OPTIONAL:
        result = check_one(dep, required=False)
        results["optional"].append(result)

    return results


def print_report(results: dict) -> None:
    """Print human-readable dependency report."""
    os_info = results["os_info"]
    print(f"System: {os_info['os']} ({os_info.get('distro', 'unknown')})")
    print(f"Package manager: {os_info['pkg_manager']}")
    print()

    print("Required:")
    for dep in results["required"]:
        if dep["found"] and dep["version_ok"]:
            ver = f" ({dep['version']})" if dep["version"] else ""
            print(f"  OK  {dep['name']}{ver}")
        elif dep["found"] and not dep["version_ok"]:
            print(f"  !!  {dep['name']} ({dep['version']}) — need >= {dep['min_version']}")
            if dep["install_hint"]:
                print(f"      Fix: {dep['install_hint']}")
        else:
            print(f"  !!  {dep['name']} — NOT FOUND")
            print(f"      Why: {dep['reason']}")
            if dep["install_hint"]:
                print(f"      Fix: {dep['install_hint']}")

    print()
    print("Optional:")
    for dep in results["optional"]:
        if dep["found"]:
            ver = f" ({dep['version']})" if dep["version"] else ""
            print(f"  OK  {dep['name']}{ver}")
        else:
            print(f"  --  {dep['name']} — not installed")
            print(f"      Why: {dep['reason']}")
            if dep["install_hint"]:
                print(f"      Fix: {dep['install_hint']}")

    if not results["all_ok"]:
        print()
        print("Missing required dependencies! Install with:")
        for cmd in results["missing_cmds"]:
            print(f"  {cmd}")
        print()


def main() -> None:
    """CLI entry point."""
    json_mode = "--json" in sys.argv
    results = check_deps()

    if json_mode:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)

    sys.exit(0 if results["all_ok"] else 1)


if __name__ == "__main__":
    main()
