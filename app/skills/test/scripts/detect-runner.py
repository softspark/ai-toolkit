#!/usr/bin/env python3
"""Auto-detect test framework and runner from project configuration files.

Scans a project directory for well-known config files (pyproject.toml,
package.json, pubspec.yaml, go.mod, Cargo.toml, composer.json) and
returns a JSON object describing the detected test runner, suggested
command, test directories, estimated test-file count, and whether
coverage reporting is configured.

Usage::

    python3 detect-runner.py [project_directory]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from _lib.detect_utils import count_files, read_json, read_text, run_detector


def detect(project_dir: Path) -> dict[str, Any]:
    """Detect the test runner for the given project directory."""
    result: dict[str, Any] = {
        "runner": None, "command": None, "test_dirs": [],
        "test_count_estimate": 0, "coverage_enabled": False,
        "detected_from": None
    }

    # Python: pyproject.toml / setup.py
    pyproject = read_text(project_dir / "pyproject.toml")
    if pyproject or (project_dir / "setup.py").exists():
        result["runner"] = "pytest"
        result["command"] = "pytest --cov=src --cov-report=term-missing tests/"
        result["detected_from"] = "pyproject.toml" if pyproject else "setup.py"
        if pyproject and "pytest" in pyproject:
            result["coverage_enabled"] = "cov" in pyproject
        for d in ["tests", "test"]:
            if (project_dir / d).is_dir():
                result["test_dirs"].append(d)
        result["test_count_estimate"] = count_files(project_dir, [r'test_.*\.py$', r'.*_test\.py$'])
        return result

    # Node.js: package.json
    pkg = read_json(project_dir / "package.json")
    if pkg:
        dev_deps = {**pkg.get("devDependencies", {}), **pkg.get("dependencies", {})}
        scripts = pkg.get("scripts", {})
        test_cmd = scripts.get("test", "")

        if "vitest" in dev_deps or "vitest" in test_cmd:
            result["runner"] = "vitest"
            result["command"] = "npx vitest run --coverage"
        elif "jest" in dev_deps or "jest" in test_cmd:
            result["runner"] = "jest"
            result["command"] = "npx jest --coverage"
        elif "mocha" in dev_deps or "mocha" in test_cmd:
            result["runner"] = "mocha"
            result["command"] = "npx mocha"
        else:
            result["runner"] = "npm-test"
            result["command"] = "npm test"

        result["detected_from"] = "package.json"
        result["coverage_enabled"] = "coverage" in test_cmd or "c8" in dev_deps or "istanbul" in str(dev_deps)
        for d in ["__tests__", "test", "tests", "spec"]:
            if (project_dir / d).is_dir():
                result["test_dirs"].append(d)
        result["test_count_estimate"] = count_files(project_dir, [r'\.test\.[jt]sx?$', r'\.spec\.[jt]sx?$', r'test_.*\.[jt]s$'])
        return result

    # Flutter/Dart
    if (project_dir / "pubspec.yaml").exists():
        result.update(runner="flutter", command="flutter test --coverage",
                      detected_from="pubspec.yaml", coverage_enabled=True)
        if (project_dir / "test").is_dir():
            result["test_dirs"].append("test")
        result["test_count_estimate"] = count_files(project_dir, [r'_test\.dart$'])
        return result

    # Go
    if (project_dir / "go.mod").exists():
        result.update(runner="go", command="go test -cover ./...",
                      detected_from="go.mod", coverage_enabled=True)
        result["test_count_estimate"] = count_files(project_dir, [r'_test\.go$'])
        return result

    # Rust
    if (project_dir / "Cargo.toml").exists():
        result.update(runner="cargo", command="cargo test", detected_from="Cargo.toml")
        result["test_count_estimate"] = count_files(project_dir, [r'\.rs$'])
        return result

    # PHP
    if (project_dir / "composer.json").exists():
        result.update(runner="phpunit", command="./vendor/bin/phpunit --coverage-text",
                      detected_from="composer.json")
        for d in ["tests", "test"]:
            if (project_dir / d).is_dir():
                result["test_dirs"].append(d)
        result["test_count_estimate"] = count_files(project_dir, [r'Test\.php$', r'test_.*\.php$'])
        return result

    result["runner"] = "unknown"
    result["command"] = None
    result["detected_from"] = None
    return result


if __name__ == "__main__":
    run_detector(detect)
