#!/usr/bin/env python3
"""Detect CI platform, analyze configuration, and suggest improvements.

Scans a project directory for CI/CD configuration files (GitHub Actions,
GitLab CI, Jenkins, Bitbucket Pipelines, CircleCI), detects the project
type, extracts job/stage names, identifies which best-practice stages
are present, and reports any missing stages with a pointer to the
``ci-cd-patterns`` skill for templates.

Usage::

    python3 ci-detect.py [directory]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from _lib.detect_utils import detect_project_type, run_detector

CI_PLATFORMS: dict[str, str] = {
    "github-actions": ".github/workflows",
    "gitlab-ci": ".gitlab-ci.yml",
    "jenkins": "Jenkinsfile",
    "bitbucket": "bitbucket-pipelines.yml",
    "circleci": ".circleci/config.yml",
}

BEST_PRACTICE_STAGES: dict[str, list[str]] = {
    "python": ["lint", "test", "build", "deploy"],
    "node": ["lint", "test", "build", "deploy"],
    "flutter": ["analyze", "test", "build", "deploy"],
    "go": ["vet", "test", "build", "deploy"],
    "rust": ["clippy", "test", "build", "deploy"],
    "php": ["lint", "test", "build", "deploy"],
    "docker": ["build", "test", "push", "deploy"],
}

STAGE_PATTERNS: dict[str, str] = {
    "lint": r"(?i)(lint|ruff|eslint|flake8|pylint|phpstan|rubocop|golangci)",
    "test": r"(?i)(test|pytest|jest|vitest|phpunit|go\s+test|cargo\s+test|flutter\s+test)",
    "build": r"(?i)(build|compile|bundle|docker\s+build|cargo\s+build|go\s+build|flutter\s+build)",
    "deploy": r"(?i)(deploy|release|publish|push|upload|heroku|aws|gcp|azure)",
    "analyze": r"(?i)(analyze|dart\s+analyze|static.?analysis)",
    "vet": r"(?i)(go\s+vet|vet)",
    "clippy": r"(?i)(clippy|cargo\s+clippy)",
    "push": r"(?i)(docker\s+push|push.*registry|push.*image)",
}


def detect_platform(project_dir: Path) -> tuple[str | None, list[str]]:
    """Detect the CI platform and return its config file paths."""
    for platform, path_pattern in CI_PLATFORMS.items():
        full_path = project_dir / path_pattern
        if platform == "github-actions":
            if full_path.is_dir():
                configs = sorted(str(f.relative_to(project_dir)) for f in full_path.glob("*.yml"))
                configs += sorted(str(f.relative_to(project_dir)) for f in full_path.glob("*.yaml"))
                if configs:
                    return platform, configs
        elif full_path.exists():
            return platform, [str(full_path.relative_to(project_dir))]
    return None, []


def extract_stages_from_config(config_path: Path) -> list[str]:
    """Extract job/stage names from a CI config file using regex."""
    try:
        content = config_path.read_text()
    except (OSError, UnicodeDecodeError):
        return []

    stages: list[str] = []
    for match in re.finditer(r"^\s{2}(\w[\w-]*):\s*$", content, re.MULTILINE):
        stages.append(match.group(1))
    for match in re.finditer(r"^(\w[\w-]*):\s*$", content, re.MULTILINE):
        name = match.group(1)
        if name not in ("on", "true", "false", "name", "env", "permissions", "concurrency"):
            stages.append(name)
    return list(dict.fromkeys(stages))


def detect_present_stages(config_files: list[Path], project_type: str | None) -> list[str]:
    """Detect which best-practice stages are present in the CI config."""
    all_content = ""
    for cf in config_files:
        try:
            all_content += cf.read_text() + "\n"
        except (OSError, UnicodeDecodeError):
            continue

    expected = BEST_PRACTICE_STAGES.get(project_type or "", ["lint", "test", "build", "deploy"])
    found: list[str] = []
    for stage in expected:
        pattern = STAGE_PATTERNS.get(stage)
        if pattern and re.search(pattern, all_content):
            found.append(stage)
    return found


def detect(project_dir: Path) -> dict:
    """Detect CI platform and analyze pipeline stages."""
    platform, config_files = detect_platform(project_dir)
    project_type = detect_project_type(project_dir)
    expected_stages = BEST_PRACTICE_STAGES.get(project_type or "", ["lint", "test", "build", "deploy"])

    config_paths = [project_dir / cf for cf in config_files]
    stages_detected = detect_present_stages(config_paths, project_type)
    missing_stages = [s for s in expected_stages if s not in stages_detected]

    job_names: list[str] = []
    for cp in config_paths:
        job_names.extend(extract_stages_from_config(cp))

    suggested_template: str | None = None
    if missing_stages and project_type:
        suggested_template = f"ci-cd-patterns skill: {project_type} pipeline template"

    return {
        "platform": platform,
        "config_files": config_files,
        "project_type": project_type,
        "jobs_found": job_names,
        "stages_detected": stages_detected,
        "expected_stages": expected_stages,
        "missing_stages": missing_stages,
        "suggested_template": suggested_template,
    }


if __name__ == "__main__":
    run_detector(detect)
