# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Unit tests for scripts/check_deps.py dependency definitions.

Run: npm run test:py (pytest, config in pytest.ini).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import check_deps  # noqa: E402

DEBIAN = {"os": "Linux", "distro": "debian", "pkg_manager": "apt", "install_cmd": "sudo apt install -y"}


def test_gnu_parallel_is_an_optional_test_suite_dependency() -> None:
    assert all(dep["name"] != "parallel" for dep in check_deps.REQUIRED)
    dep = next(dep for dep in check_deps.OPTIONAL if dep["name"] == "parallel")
    assert dep["check"] == "parallel"
    assert "npm test" in dep["reason"]
    assert dep["packages"]["brew"] == "parallel"


def test_missing_parallel_gives_install_hint_without_failing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(check_deps, "detect_os", lambda: DEBIAN)
    monkeypatch.setattr(check_deps.shutil, "which",
                        lambda name: None if name == "parallel" else f"/usr/bin/{name}")
    monkeypatch.setattr(check_deps, "get_version", lambda _binary: "99.0")

    results = check_deps.check_deps(verbose=False)

    assert results["all_ok"] is True
    parallel = next(dep for dep in results["optional"] if dep["name"] == "parallel")
    assert parallel["found"] is False
    assert parallel["install_hint"] == "sudo apt install -y parallel"
