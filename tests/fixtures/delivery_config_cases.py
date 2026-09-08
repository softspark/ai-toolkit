#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Offline real-CLI fixtures for autonomous project configuration preflight."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parents[2] / "app/skills/autonomous-dev/scripts/delivery-config.py"
SPEC = importlib.util.spec_from_file_location("delivery_config", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
CONFIG = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONFIG)


def project() -> dict[str, Any]:
    return {
        "version": 1,
        "baseBranch": "develop",
        "validation": {
            "commands": [
                "make api-stan",
                "make api-test",
                "make flutter-analyze",
                "make flutter-test",
            ]
        },
        "qa": {"required": True},
        "ci": {"required": True},
    }


def integrated_project() -> dict[str, Any]:
    config = project()
    config.update(
        issueTracker={
            "provider": "jira-mcp",
            "projectKey": "APP",
            "instanceUrl": "https://jira.example.invalid/team",
        },
        codeHost={"provider": "github", "repository": "example/application"},
        knowledge={
            "provider": "rag-mcp",
            "services": ["application", "infrastructure"],
            "required": True,
        },
    )
    return config


class DeliveryConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="delivery-config-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.path = self.directory / "autonomous.json"

    def cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

    def check(self, config: object, task: str | None = None, expected: int = 0) -> dict[str, Any]:
        contents = (json.dumps(config, indent=3) + "\n").encode()
        self.path.write_bytes(contents)
        arguments = ["--config", str(self.path)]
        if task is not None:
            arguments.extend(("--task", task))
        process = self.cli(*arguments)
        self.assertEqual(process.returncode, expected, process.stdout + process.stderr)
        self.assertEqual(process.stderr, "")
        self.assertEqual(self.path.read_bytes(), contents)
        report: dict[str, Any] = json.loads(process.stdout)
        self.assertEqual(report["ok"], expected == 0)
        self.assertTrue(report["liveChecks"])
        if expected:
            self.assertIsNone(report["config"])
            self.assertIsNone(report["task"])
            self.assertEqual(report["diagnostics"][0]["level"], "error")
        return report

    def test_legacy_github_matches_explicit_issue_and_code_roles(self) -> None:
        legacy = project()
        legacy["tracker"] = {"provider": "github", "repository": "Example/Application"}
        explicit = project()
        explicit["issueTracker"] = {
            "provider": "github",
            "repository": "example/application",
        }
        explicit["codeHost"] = {
            "provider": "github",
            "repository": "example/application",
        }
        self.assertEqual(self.check(legacy)["config"], self.check(explicit)["config"])
        combined = {**legacy, **explicit}
        self.assertEqual(self.check(legacy)["config"], self.check(combined)["config"])

    def test_missing_roles_support_local_work_without_publication(self) -> None:
        normalized = self.check(project())["config"]
        self.assertEqual(normalized["issueTracker"], {"provider": "none"})
        self.assertEqual(normalized["codeHost"], {"provider": "none"})
        self.assertEqual(normalized["knowledge"], {"provider": "local", "required": False})
        self.assertEqual(normalized["ci"]["maxWaitMinutes"], 20)
        self.assertEqual(normalized["labels"]["enabled"], False)
        legacy_none = {**project(), "tracker": {"provider": "none"}}
        self.assertEqual(self.check(legacy_none)["config"], normalized)

    def test_jira_rag_and_github_roles_remain_separate(self) -> None:
        config = integrated_project()
        config["issueTracker"]["statusMapping"] = {
            "implement": "Development",
            "readyPr": None,
        }
        config["qa"].update(
            browserProvider="available",
            startCommand="make flutter-serve",
            healthPath="/",
        )
        normalized = self.check(config)["config"]
        self.assertEqual(normalized["issueTracker"], config["issueTracker"])
        self.assertEqual(normalized["codeHost"], config["codeHost"])
        self.assertEqual(normalized["knowledge"], config["knowledge"])
        self.assertEqual(normalized["qa"], config["qa"])
        self.assertEqual(normalized["validation"], config["validation"])

    def test_github_issue_repository_can_differ_from_code_repository(self) -> None:
        config = project()
        config.update(
            issueTracker={"provider": "github", "repository": "example/requests"},
            codeHost={"provider": "github", "repository": "example/application"},
        )
        normalized = self.check(config)["config"]
        self.assertNotEqual(
            normalized["issueTracker"]["repository"],
            normalized["codeHost"]["repository"],
        )

    def test_conflicting_legacy_roles_fail_instead_of_overriding(self) -> None:
        for role in ("issueTracker", "codeHost"):
            for explicit in (
                {"provider": "none"},
                {"provider": "github", "repository": "example/other"},
            ):
                with self.subTest(role=role, explicit=explicit):
                    config = {
                        **project(),
                        "tracker": {
                            "provider": "github",
                            "repository": "example/application",
                        },
                    }
                    config[role] = explicit
                    self.assertEqual(
                        self.check(config, expected=2)["diagnostics"][0]["code"],
                        "role_conflict",
                    )

    def test_key_and_browse_url_share_canonical_resume_subject(self) -> None:
        config = integrated_project()
        config["issueTracker"]["instanceUrl"] = "HTTPS://JIRA.EXAMPLE.INVALID:443/team/"
        by_key = self.check(config, "APP-123")["task"]
        by_url = self.check(config, "https://jira.example.invalid/team/browse/APP-123")["task"]
        self.assertEqual(by_key, by_url)
        self.assertEqual(
            by_key,
            {
                "provider": "jira-mcp",
                "key": "APP-123",
                "url": "https://jira.example.invalid/team/browse/APP-123",
                "subject": "jira:https://jira.example.invalid/team/browse/APP-123",
            },
        )

    def test_same_key_on_other_instances_gets_distinct_subject(self) -> None:
        config = integrated_project()
        first = self.check(config, "APP-123")["task"]["subject"]
        config["issueTracker"]["instanceUrl"] = "https://other.example.invalid"
        second = self.check(config, "APP-123")["task"]["subject"]
        self.assertNotEqual(first, second)

    def test_cross_project_and_instance_task_inputs_fail(self) -> None:
        inputs = (
            "OTHER-1",
            "https://jira.example.invalid/team/browse/OTHER-1",
            "https://other.example.invalid/team/browse/APP-1",
            "https://jira.example.invalid/other/browse/APP-1",
            "https://jira.example.invalid/team/issues/APP-1",
            "https://jira.example.invalid:8443/team/browse/APP-1",
        )
        for task in inputs:
            with self.subTest(task=task):
                self.check(integrated_project(), task, expected=2)

    def test_missing_instance_allows_config_but_blocks_task_resolution(self) -> None:
        config = integrated_project()
        del config["issueTracker"]["instanceUrl"]
        self.check(config)
        for task in ("APP-1", "https://jira.example.invalid/team/browse/APP-1"):
            report = self.check(config, task, expected=2)
            self.assertEqual(report["diagnostics"][0]["code"], "instance_required")
            self.assertIn("jira-mcp", report["diagnostics"][0]["message"])

    def test_tasks_require_explicit_jira_provider(self) -> None:
        self.assertEqual(
            self.check(project(), "APP-1", expected=2)["diagnostics"][0]["code"],
            "task_provider",
        )

    def test_unsafe_or_noncanonical_urls_fail_without_echoing_credentials(self) -> None:
        for instance in (
            "http://jira.example.invalid",
            "https://user:credential-value@jira.example.invalid",
            "https://jira.example.invalid/a/../team",
            "https://jira.example.invalid/a//team",
            "https://jira.example.invalid/team?token=credential-value",
            "https://jira.example.invalid/team#part",
            "https://jira.example.invalid/team%2fbrowse",
            "https://jira.example.invalid\\other",
            "https://jira.example.invalid:99999",
            "https://jira.example.invalid/team\nother",
        ):
            with self.subTest(instance=instance):
                config = integrated_project()
                config["issueTracker"]["instanceUrl"] = instance
                report = self.check(config, expected=2)
                self.assertNotIn("credential-value", json.dumps(report))

    def test_invalid_known_field_types_and_providers_fail(self) -> None:
        cases: tuple[tuple[str, object], ...] = (
            ("version", True),
            ("version", 1.0),
            ("version", "1"),
            ("version", 2),
            ("baseBranch", " "),
            ("validation", {"commands": []}),
            ("validation", {"commands": [" "]}),
            ("validation", {"commands": [42]}),
            ("validation", {"commands": "make test"}),
            ("validation", {"commands": ["make test", False]}),
            ("qa", {"required": 1}),
            ("qa", {"required": True, "browserProvider": False}),
            ("qa", {"required": True, "startCommand": ""}),
            ("qa", {"required": True, "healthPath": []}),
            ("ci", {"required": "true"}),
            ("ci", {"required": True, "maxWaitMinutes": True}),
            ("ci", {"required": True, "maxWaitMinutes": -1}),
            ("ci", {"required": True, "maxWaitMinutes": 61}),
            ("ci", {"required": True, "maxWaitMinutes": 1.5}),
            ("labels", {"enabled": "false"}),
            ("issueTracker", {"provider": "jira"}),
            ("issueTracker", {"provider": "jira-mcp", "projectKey": "app"}),
            ("issueTracker", {"provider": "jira-mcp", "projectKey": ""}),
            ("codeHost", {"provider": "gitlab"}),
            ("codeHost", {"provider": "github"}),
            ("knowledge", {"provider": "unsupported"}),
            ("knowledge", {"provider": "rag-mcp", "services": []}),
            ("knowledge", {"provider": "rag-mcp", "services": "application"}),
            ("knowledge", {"provider": "rag-mcp", "services": ["application", None]}),
            ("knowledge", {"provider": "local", "required": "true"}),
            ("tracker", {"provider": "jira-mcp"}),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                config = project()
                config[field] = value
                self.check(config, expected=2)

    def test_ci_bounds_and_explicit_optional_flags_are_preserved(self) -> None:
        for wait in (0, 60):
            config = {
                **project(),
                "qa": {"required": False},
                "ci": {"required": False, "maxWaitMinutes": wait},
            }
            normalized = self.check(config)["config"]
            self.assertFalse(normalized["qa"]["required"])
            self.assertEqual(normalized["ci"], config["ci"])

    def test_status_mapping_requires_explicit_supported_stages_and_strings(
        self,
    ) -> None:
        mappings: tuple[object, ...] = ({"implement": 1}, {"readyPr": " "}, {"done": "Closed"}, [])
        for mapping in mappings:
            config = integrated_project()
            config["issueTracker"]["statusMapping"] = mapping
            self.check(config, expected=2)
        normalized = self.check(integrated_project())["config"]
        self.assertNotIn("statusMapping", normalized["issueTracker"])

    def test_unknown_fields_remain_on_disk_without_being_echoed(self) -> None:
        config = integrated_project()
        config["custom"] = {"token": "fixture-secret-value"}
        config["issueTracker"]["credentials"] = "fixture-secret-value"
        config["qa"]["environment"] = {"TOKEN": "fixture-secret-value"}
        report = self.check(config)
        self.assertNotIn("fixture-secret-value", json.dumps(report))
        self.assertIn("fixture-secret-value", self.path.read_text())

    def test_commands_are_never_executed(self) -> None:
        marker = self.directory / "must-not-exist"
        config = project()
        command = f"touch '{marker}'"
        config["validation"]["commands"] = [command]
        config["qa"]["startCommand"] = command
        normalized = self.check(config)["config"]
        self.assertEqual(normalized["validation"]["commands"], [command])
        self.assertFalse(marker.exists())
        self.assertEqual(list(self.directory.iterdir()), [self.path])

    def test_malformed_duplicate_and_nonfinite_json_fail_safely(self) -> None:
        for contents in (
            b'{"fixture-secret-key": 1, "fixture-secret-key": 2}',
            b'{"secret": "fixture-secret-value",',
            b'{"secret": NaN}',
            b"[]",
            b'{"secret": Infinity}',
            b'{"secret": 1e9999}',
            b"\xff",
            b"[" * 1500 + b"]" * 1500,
        ):
            with self.subTest(contents=contents[:50]):
                self.path.write_bytes(contents)
                process = self.cli("--config", str(self.path))
                self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
                self.assertEqual(process.stderr, "")
                self.assertFalse(json.loads(process.stdout)["ok"])
                self.assertNotIn("fixture-secret", process.stdout)
                self.assertEqual(self.path.read_bytes(), contents)

    def test_bounded_loader_rejects_large_files_and_special_files(self) -> None:
        self.path.write_bytes(b" " * (CONFIG.MAX_CONFIG_BYTES + 1))
        self.assertEqual(CONFIG.check_config(self.path)["diagnostics"][0]["code"], "config_size")
        fifo = self.directory / "pipe"
        os.mkfifo(fifo)
        process = self.cli("--config", str(fifo))
        self.assertEqual(process.returncode, 2)
        self.assertEqual(json.loads(process.stdout)["diagnostics"][0]["code"], "config_file")
        missing = self.cli("--config", str(self.directory / "missing.json"))
        self.assertEqual(missing.returncode, 2)
        self.assertEqual(json.loads(missing.stdout)["diagnostics"][0]["code"], "config_read")

    def test_help_and_argument_errors_have_no_tracebacks_or_raw_values(self) -> None:
        help_result = self.cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--task", help_result.stdout)
        for arguments in ((), ("--unknown=fixture-secret-value",), ("--config",)):
            process = self.cli(*arguments)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stderr, "")
            self.assertNotIn("fixture-secret-value", process.stdout)
            self.assertEqual(json.loads(process.stdout)["diagnostics"][0]["code"], "arguments")


if __name__ == "__main__":
    unittest.main()
