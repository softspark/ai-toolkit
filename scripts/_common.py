#!/usr/bin/env python3
"""Shared library for ai-toolkit Python scripts.

This module is a **facade** that re-exports from focused sub-modules:
  - frontmatter.py — YAML frontmatter parsing
  - injection.py  — marker-based section injection and rule management
  - emission.py   — markdown emission, counting, and generator helpers

All functions are stdlib-only. Import and use from any scripts/*.py file.

Usage:
    from _common import toolkit_dir, frontmatter_field, inject_section
"""
from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path

# ---------------------------------------------------------------------------
# Re-exports from frontmatter module
# ---------------------------------------------------------------------------
from frontmatter import frontmatter_field, frontmatter_block  # noqa: F401

# ---------------------------------------------------------------------------
# Re-exports from injection module
# ---------------------------------------------------------------------------
from injection import (  # noqa: F401
    markers_start,
    markers_end,
    inject_section,
    inject_rule,
    remove_rule_section,
    # Internal helpers re-exported for backwards compat (install.py uses them)
    strip_section as _strip_section,
    trim_trailing_blanks as _trim_trailing_blanks,
    collapse_blank_runs as _collapse_blank_runs,
)

# ---------------------------------------------------------------------------
# Re-exports from emission module
# ---------------------------------------------------------------------------
from emission import (  # noqa: F401
    agent_count,
    skill_count,
    count_agents_and_skills,
    emit_agents_headings,
    emit_agents_bullets,
    emit_skills_headings,
    emit_skills_bullets,
    print_toolkit_start,
    print_toolkit_end,
    generate_general_guidelines,
    generate_quality_standards,
    generate_workflow_guidelines,
    generate_quality_guidelines,
)

# ---------------------------------------------------------------------------
# Path constants (canonical source — emission.py also resolves these)
# ---------------------------------------------------------------------------

def _resolve_toolkit_dir() -> Path:
    """Resolve the toolkit root directory (parent of scripts/)."""
    return Path(__file__).resolve().parent.parent


toolkit_dir: Path = _resolve_toolkit_dir()
app_dir: Path = toolkit_dir / "app"
agents_dir: Path = app_dir / "agents"
skills_dir: Path = app_dir / "skills"


# ---------------------------------------------------------------------------
# Default Claude model IDs (single source of truth — bump on Anthropic release)
# Consumed by generators that need to emit a concrete model string.
# Aliases like "opus"/"sonnet"/"haiku" in agent frontmatter are resolved by
# the client at runtime and do NOT need updating here.
# ---------------------------------------------------------------------------
DEFAULT_CLAUDE_MODELS: dict[str, str] = {
    "opus": "claude-opus-4-7",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
}


# ---------------------------------------------------------------------------
# Component filtering (for install/update)
# ---------------------------------------------------------------------------

def should_install(component: str, only: str = "", skip: str = "") -> bool:
    """Check if a component should be installed (respects --only and --skip)."""
    if only:
        allowed = [c.strip() for c in only.split(",")]
        if component not in allowed:
            return False
    if skip:
        skipped = [c.strip() for c in skip.split(",")]
        if component in skipped:
            return False
    return True


# ---------------------------------------------------------------------------
# OS detection (for dependency checker)
# ---------------------------------------------------------------------------

def detect_os() -> dict[str, str]:
    """Detect operating system and package manager.

    Returns dict with keys: os, distro, pkg_manager, install_cmd.
    """
    system = platform.system().lower()

    if system == "darwin":
        return {
            "os": "macOS",
            "distro": platform.mac_ver()[0],
            "pkg_manager": "brew" if shutil.which("brew") else "none",
            "install_cmd": "brew install",
        }

    if system == "linux":
        distro = ""
        pkg_manager = "none"
        install_cmd = ""

        # Read os-release
        for path in ("/etc/os-release", "/usr/lib/os-release"):
            if os.path.isfile(path):
                with open(path) as f:
                    for line in f:
                        if line.startswith("ID="):
                            distro = line.strip().split("=", 1)[1].strip('"')
                        elif line.startswith("ID_LIKE="):
                            if not distro:
                                distro = line.strip().split("=", 1)[1].strip('"').split()[0]
                break

        # Map distro to package manager
        if distro in ("ubuntu", "debian", "linuxmint", "pop"):
            pkg_manager = "apt"
            install_cmd = "sudo apt install -y"
        elif distro in ("fedora", "rhel", "centos", "rocky", "alma"):
            pkg_manager = "dnf" if shutil.which("dnf") else "yum"
            install_cmd = f"sudo {pkg_manager} install -y"
        elif distro in ("arch", "manjaro", "endeavouros"):
            pkg_manager = "pacman"
            install_cmd = "sudo pacman -S --noconfirm"
        elif distro == "alpine":
            pkg_manager = "apk"
            install_cmd = "sudo apk add"
        elif distro in ("opensuse", "suse"):
            pkg_manager = "zypper"
            install_cmd = "sudo zypper install -y"

        # Check for WSL
        is_wsl = "microsoft" in platform.release().lower()

        return {
            "os": "WSL" if is_wsl else "Linux",
            "distro": distro,
            "pkg_manager": pkg_manager,
            "install_cmd": install_cmd,
        }

    if system == "windows":
        managers = (
            ("winget", "winget install"),
            ("choco", "choco install -y"),
            ("scoop", "scoop install"),
        )
        for manager, install_cmd in managers:
            if shutil.which(manager):
                return {
                    "os": "Windows",
                    "distro": platform.version(),
                    "pkg_manager": manager,
                    "install_cmd": install_cmd,
                }
        return {
            "os": "Windows",
            "distro": platform.version(),
            "pkg_manager": "none",
            "install_cmd": "",
        }

    return {
        "os": system,
        "distro": "",
        "pkg_manager": "none",
        "install_cmd": "",
    }
