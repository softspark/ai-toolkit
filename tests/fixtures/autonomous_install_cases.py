# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Execute detached native skill resources against an isolated Git fixture."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLKIT = Path(__file__).resolve().parents[2]


class NativeSkillInstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="autonomous-install-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.project = self.root / "project"
        self.project.mkdir()
        self.command("git", "init", "-q", "-b", "main", str(self.project))
        self.git("config", "user.name", "Install Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.root / "no-hooks"))
        (self.project / "source.txt").write_text("fixture source\n", encoding="utf-8")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "test: fixture")
        self.git("checkout", "-qb", "feat/fixture")

    def command(self, *arguments: str) -> str:
        result = subprocess.run(arguments, capture_output=True, text=True, timeout=90, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def git(self, *arguments: str) -> str:
        return self.command("git", "-C", str(self.project), *arguments)

    def verify_emitted_skills(self, generator: str, surface: str, *flags: str) -> None:
        target = self.root / "installed"
        target.mkdir()
        self.command(sys.executable, str(TOOLKIT / "scripts" / generator), str(target), *flags)
        detached = self.root / "detached"
        for skill in ("autonomous-dev", "prepare-test-env"):
            native_name = f"ai-toolkit-{skill}" if generator == "generate_copilot.py" else skill
            source = target / surface / native_name
            destination = detached / skill
            shutil.copytree(source, destination, symlinks=False)
            body = (destination / "SKILL.md").read_text(encoding="utf-8")
            for reference in re.findall(r"\]\(((?:reference|references)/[^)]+)\)", body):
                self.assertTrue((destination / reference).is_file(), reference)
            for script in (destination / "scripts").glob("*.py"):
                self.command(sys.executable, str(script), "--help")

        plan = self.root / "plan.md"
        plan.write_text("Implement the fixture and run its real checks.\n", encoding="utf-8")
        journal = detached / "autonomous-dev/scripts/run-state.py"
        common = (sys.executable, str(journal), "--repo", str(self.project),
                  "--store", str(self.root / "state"))
        initialized = json.loads(self.command(
            *common, "init", "--subject", "brief:fixture", "--objective", "Verify installed helper",
            "--source-kind", "brief", "--source", "fixture", "--target-branch", "main", "--plan", str(plan),
        ))
        self.assertTrue(initialized["ok"])
        listed = json.loads(self.command(*common, "list"))
        self.assertEqual(listed["runs"][0]["run_id"], initialized["run"]["run_id"])
        resumed = json.loads(self.command(*common, "status", "--run", initialized["run"]["run_id"]))
        self.assertEqual(resumed["run"]["objective"], "Verify installed helper")
        profile = self.root / "autonomous.json"
        profile.write_text(json.dumps({
            "version": 1, "baseBranch": "main",
            "validation": {"commands": ["python3 -m unittest"]},
            "issueTracker": {"provider": "jira-mcp", "projectKey": "APP",
                             "instanceUrl": "https://jira.example.invalid"},
            "codeHost": {"provider": "github", "repository": "example/project"},
            "knowledge": {"provider": "rag-mcp", "services": ["project"], "required": True},
            "qa": {"required": False}, "ci": {"required": True},
        }), encoding="utf-8")
        preflight = json.loads(self.command(
            sys.executable, str(detached / "autonomous-dev/scripts/delivery-config.py"),
            "--config", str(profile), "--task", "APP-123",
        ))
        self.assertEqual(preflight["task"]["subject"], "jira:https://jira.example.invalid/browse/APP-123")
        snapshot = json.loads(self.command(
            sys.executable, str(detached / "prepare-test-env/scripts/env-check.py"),
            "snapshot", "--worktree", str(self.project),
        ))
        self.assertEqual(snapshot["headSha"], self.git("rev-parse", "HEAD").strip())
        self.assertTrue(snapshot["ok"])

    def test_codex_installed_helpers_and_references_execute(self) -> None:
        self.verify_emitted_skills("generate_codex_skills.py", ".agents/skills", "--enable")

    def test_opencode_materialized_helpers_execute_without_source_links(self) -> None:
        self.verify_emitted_skills("generate_opencode_skills.py", ".opencode/skills")

    def test_copilot_materialized_helpers_execute_without_source_links(self) -> None:
        self.verify_emitted_skills("generate_copilot.py", ".github/skills")


if __name__ == "__main__":
    unittest.main()
