from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.tool_output_filter.recovery import EphemeralRecoveryStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPOSITORY_ROOT / "scripts" / "output_filter_cli.py"


def claude_payload(stdout: str, command: str = "bats tests") -> dict[str, object]:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "session_id": "native-session-id",
        "cwd": str(REPOSITORY_ROOT),
        "tool_input": {"command": command},
        "tool_response": {
            "stdout": stdout,
            "stderr": "",
            "interrupted": False,
            "isImage": False,
        },
    }


class OutputFilterCliTests(unittest.TestCase):
    def run_hook(
        self,
        policy: dict[str, object],
        payload: dict[str, object],
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            policy_path = temporary_path / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            environment = dict(os.environ)
            environment["PYTHONDONTWRITEBYTECODE"] = "1"
            temporary_home = temporary_path / "home"
            cwd = str(payload["cwd"])
            repo_key = "-" + cwd.replace("/", "-").lstrip("-")
            session_root = (
                temporary_home
                / ".softspark"
                / "ai-toolkit"
                / "sessions"
                / repo_key
            )
            session_root.mkdir(parents=True, mode=0o700)
            session_root.chmod(0o700)
            environment["HOME"] = str(temporary_home)
            return subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "hook",
                    "--policy",
                    str(policy_path),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env=environment,
                check=False,
            )

    def test_hook_off_mode_emits_nothing(self) -> None:
        result = self.run_hook(
            {
                "mode": "off",
                "profiles": ["repeat-lines", "tap-success"],
                "maxInputBytes": 8 * 1024 * 1024,
                "minSavingsBytes": 1024,
                "minSavingsRatio": 0.15,
                "recovery": {
                    "ttlMinutes": 60,
                    "maxSessionBytes": 32 * 1024 * 1024,
                },
            },
            claude_payload("same\n" * 500),
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_safe_hook_replaces_only_stdout_in_native_response_object(self) -> None:
        tap_output = "".join(
            [
                "TAP version 13\n",
                "1..200\n",
                *[
                    f"ok {number} - synthetic case {number}\n"
                    for number in range(1, 201)
                ],
                "# tests 200\n",
                "# pass 200\n",
                "# duration_ms 25\n",
            ]
        )
        payload = claude_payload(tap_output)
        response = payload["tool_response"]
        assert isinstance(response, dict)
        response["nativeMetadata"] = {"requestId": "preserve-me"}

        result = self.run_hook(
            {
                "mode": "safe",
                "profiles": ["tap-success", "repeat-lines"],
                "maxInputBytes": 8 * 1024 * 1024,
                "minSavingsBytes": 1,
                "minSavingsRatio": 0.01,
                "recovery": {
                    "ttlMinutes": 60,
                    "maxSessionBytes": 32 * 1024 * 1024,
                },
            },
            payload,
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stderr)
        hook_output = json.loads(result.stdout)
        updated_response = hook_output["hookSpecificOutput"]["updatedToolOutput"]
        self.assertEqual("", updated_response["stderr"])
        self.assertFalse(updated_response["interrupted"])
        self.assertFalse(updated_response["isImage"])
        self.assertEqual(
            {"requestId": "preserve-me"},
            updated_response["nativeMetadata"],
        )
        self.assertNotEqual(tap_output, updated_response["stdout"])
        self.assertEqual(
            "PostToolUse",
            hook_output["hookSpecificOutput"]["hookEventName"],
        )

    def test_hook_passes_through_failure_markers_despite_empty_stderr(
        self,
    ) -> None:
        failing_output = (
            ("not ok 1 - flaky assertion failed\n" * 300)
            + "# 300 tests, 300 failures\n"
        )
        result = self.run_hook(
            {
                "mode": "safe",
                "profiles": ["repeat-lines"],
                "minSavingsBytes": 1,
                "minSavingsRatio": 0.01,
            },
            claude_payload(failing_output),
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_passes_through_nonzero_exit_code_field(self) -> None:
        payload = claude_payload("benign line\n" * 300)
        response = payload["tool_response"]
        assert isinstance(response, dict)
        response["exitCode"] = 1

        result = self.run_hook(
            {
                "mode": "safe",
                "profiles": ["repeat-lines"],
                "minSavingsBytes": 1,
                "minSavingsRatio": 0.01,
            },
            payload,
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_status_prints_materialized_policy_without_raw_data(self) -> None:
        policy = {
            "mode": "observe",
            "profiles": ["tap-success", "repeat-lines"],
            "maxInputBytes": 4096,
            "minSavingsBytes": 256,
            "minSavingsRatio": 0.2,
            "recovery": {
                "mode": "ephemeral",
                "ttlMinutes": 30,
                "maxSessionBytes": 8192,
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            policy_path = Path(temporary_directory) / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "status",
                    "--policy",
                    str(policy_path),
                ],
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

        self.assertEqual(0, result.returncode)
        self.assertEqual(policy, json.loads(result.stdout))
        self.assertEqual("", result.stderr)

    def test_status_resolves_trusted_managed_project_policy(self) -> None:
        policy = {
            "mode": "observe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 4096,
            "minSavingsBytes": 256,
            "minSavingsRatio": 0.2,
            "recovery": {
                "mode": "ephemeral",
                "ttlMinutes": 30,
                "maxSessionBytes": 8192,
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_home = Path(temporary_directory) / "home"
            registry_directory = temporary_home / ".softspark" / "ai-toolkit"
            project_directory = Path(temporary_directory) / "project"
            managed_directory = project_directory / ".claude"
            registry_directory.mkdir(parents=True)
            managed_directory.mkdir(parents=True)
            (registry_directory / "projects.json").write_text(
                json.dumps({"projects": [{"path": str(project_directory)}]}),
                encoding="utf-8",
            )
            (managed_directory / "ai-toolkit-output-filter.json").write_text(
                json.dumps(policy),
                encoding="utf-8",
            )
            (
                managed_directory / ".ai-toolkit-output-filter.owner"
            ).write_text(
                "ai-toolkit-output-filter-policy-v1\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI_PATH), "status"],
                text=True,
                capture_output=True,
                cwd=project_directory,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "HOME": str(temporary_home),
                    "CLAUDE_PROJECT_DIR": str(project_directory),
                },
                check=False,
            )

        self.assertEqual(0, result.returncode)
        self.assertEqual(policy, json.loads(result.stdout))
        self.assertEqual("", result.stderr)

    def test_status_ignores_project_policy_without_registration(self) -> None:
        policy = {"mode": "safe", "profiles": ["repeat-lines"]}
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_home = Path(temporary_directory) / "home"
            project_directory = Path(temporary_directory) / "cloned"
            managed_directory = project_directory / ".claude"
            temporary_home.mkdir(parents=True)
            managed_directory.mkdir(parents=True)
            (managed_directory / "ai-toolkit-output-filter.json").write_text(
                json.dumps(policy),
                encoding="utf-8",
            )
            (
                managed_directory / ".ai-toolkit-output-filter.owner"
            ).write_text(
                "ai-toolkit-output-filter-policy-v1\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(CLI_PATH), "status"],
                text=True,
                capture_output=True,
                cwd=project_directory,
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "HOME": str(temporary_home),
                    "CLAUDE_PROJECT_DIR": str(project_directory),
                },
                check=False,
            )

        self.assertEqual(0, result.returncode)
        self.assertEqual("off", json.loads(result.stdout)["mode"])
        self.assertEqual("", result.stderr)

    def test_inspect_reports_metadata_without_echoing_output(self) -> None:
        secret = "SECRET-CANARY-INSPECT"
        raw_output = f"{secret}\n" * 200

        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "inspect",
                "--profile",
                "repeat-lines",
                "--min-savings-bytes",
                "1",
                "--min-savings-ratio",
                "0.01",
            ],
            input=raw_output,
            text=True,
            capture_output=True,
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )

        self.assertEqual(0, result.returncode)
        report = json.loads(result.stdout)
        self.assertTrue(report["eligible"])
        self.assertEqual("repeat-lines", report["profile"])
        self.assertLess(report["candidateBytes"], report["inputBytes"])
        self.assertNotIn(secret, result.stdout)
        self.assertEqual("", result.stderr)

    def test_inspect_bounds_input_before_reporting_oversize(self) -> None:
        secret = "SECRET-CANARY-OVERSIZED-INSPECT"
        raw_output = f"{secret}\n" * 100

        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "inspect",
                "--profile",
                "repeat-lines",
                "--max-input-bytes",
                "64",
            ],
            input=raw_output,
            text=True,
            capture_output=True,
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )

        self.assertEqual(0, result.returncode)
        report = json.loads(result.stdout)
        self.assertFalse(report["eligible"])
        self.assertEqual("passthrough", report["outcome"])
        self.assertEqual("input-too-large", report["fallbackReason"])
        self.assertEqual(65, report["inputBytesAtLeast"])
        self.assertEqual(64, report["maxInputBytes"])
        self.assertNotIn(secret, result.stdout)
        self.assertEqual("", result.stderr)

    def test_inspect_rejects_invalid_limits_before_reading_input(self) -> None:
        invalid_arguments = (
            ("--max-input-bytes", "0"),
            ("--max-input-bytes", str(8 * 1024 * 1024 + 1)),
            ("--min-savings-bytes", "-1"),
            ("--min-savings-ratio", "nan"),
            ("--min-savings-ratio", "1.1"),
        )
        for option, value in invalid_arguments:
            with self.subTest(option=option, value=value):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(CLI_PATH),
                        "inspect",
                        "--profile",
                        "repeat-lines",
                        option,
                        value,
                    ],
                    input="SECRET-CANARY-INVALID-LIMIT\n",
                    text=True,
                    capture_output=True,
                    cwd=REPOSITORY_ROOT,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                    check=False,
                )

                self.assertEqual(2, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertNotIn("SECRET-CANARY", result.stderr)

    def test_inspect_rejects_unknown_profile(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(CLI_PATH),
                "inspect",
                "--profile",
                "unknown-profile",
            ],
            input="SECRET-CANARY-UNKNOWN-PROFILE\n",
            text=True,
            capture_output=True,
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            check=False,
        )

        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertNotIn("SECRET-CANARY", result.stderr)

    def test_safe_marker_handle_recovers_exact_native_response(self) -> None:
        raw_output = "same\n" * 500
        payload = claude_payload(raw_output, command="npm test")
        response = payload["tool_response"]
        assert isinstance(response, dict)
        response["nativeMetadata"] = {"requestId": "recover-me"}
        policy = {
            "mode": "safe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 8192,
            "minSavingsBytes": 1,
            "minSavingsRatio": 0.01,
            "recovery": {
                "ttlMinutes": 60,
                "maxSessionBytes": 8192,
            },
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            policy_path = temporary_path / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            temporary_home = temporary_path / "home"
            repo_key = "-" + str(REPOSITORY_ROOT).replace("/", "-").lstrip("-")
            base_directory = (
                temporary_home
                / ".softspark"
                / "ai-toolkit"
                / "sessions"
                / repo_key
            )
            base_directory.mkdir(parents=True, mode=0o700)
            base_directory.chmod(0o700)
            environment = {
                **os.environ,
                "HOME": str(temporary_home),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            hook_result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "hook",
                    "--policy",
                    str(policy_path),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env=environment,
                check=False,
            )
            updated = json.loads(hook_result.stdout)
            marker_output = updated["hookSpecificOutput"]["updatedToolOutput"]["stdout"]
            handle_match = re.search(r"recovery=([0-9a-f]{32})", marker_output)
            assert handle_match is not None
            handle = handle_match.group(1)

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "recover",
                    handle,
                ],
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env=environment,
                check=False,
            )

        self.assertEqual(0, result.returncode)
        self.assertEqual(response, json.loads(result.stdout))
        self.assertEqual("", result.stderr)

    def test_clean_removes_owned_session_recovery_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="clean-session",
            ) as recovery:
                first_handle = recovery.save({"stdout": "first"})
                second_handle = recovery.save({"stdout": "second"})

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "clean",
                    "--base-directory",
                    str(base_directory),
                ],
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="clean-session",
            ) as recovery:
                self.assertIsNone(recovery.load(first_handle))
                self.assertIsNone(recovery.load(second_handle))

        self.assertEqual(0, result.returncode)
        self.assertEqual({"removed": 2, "scope": "all"}, json.loads(result.stdout))
        self.assertEqual("", result.stderr)

    def test_clean_session_removes_empty_owned_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="clean-one-session",
            ) as recovery:
                handle = recovery.save({"stdout": "remove"})
                artifact = next(base_directory.rglob(f"{handle}.json"))
                session_directory = artifact.parent
                output_directory = session_directory.parent

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "clean",
                    "--base-directory",
                    str(base_directory),
                    "--session-id",
                    "clean-one-session",
                ],
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
            )

            self.assertFalse(session_directory.exists())
            self.assertFalse(output_directory.exists())

        self.assertEqual(0, result.returncode)
        self.assertEqual(
            {"removed": 1, "scope": "all"},
            json.loads(result.stdout),
        )
        self.assertEqual("", result.stderr)

    def test_hook_invalid_policy_fails_open_without_replacement(self) -> None:
        result = self.run_hook(
            {
                "mode": "safe",
                "profiles": ["repeat-lines"],
                "maxInputBytes": 1024,
                "minSavingsBytes": -1,
                "minSavingsRatio": -1.0,
                "recovery": {
                    "ttlMinutes": 60,
                    "maxSessionBytes": 4096,
                },
            },
            claude_payload("same\n" * 100, command="npm test"),
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_rejects_oversized_json_before_creating_runtime_state(
        self,
    ) -> None:
        policy = {
            "mode": "safe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 64,
            "minSavingsBytes": 1,
            "minSavingsRatio": 0.01,
            "recovery": {
                "ttlMinutes": 60,
                "maxSessionBytes": 8192,
            },
        }
        payload = claude_payload("same\n" * 20_000, command="npm test")
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            policy_path = temporary_path / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            temporary_home = temporary_path / "home"
            repo_key = "-" + str(REPOSITORY_ROOT).replace("/", "-").lstrip("-")
            session_root = (
                temporary_home
                / ".softspark"
                / "ai-toolkit"
                / "sessions"
                / repo_key
            )
            session_root.mkdir(parents=True, mode=0o700)
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "hook",
                    "--policy",
                    str(policy_path),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env={
                    **os.environ,
                    "HOME": str(temporary_home),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                check=False,
            )
            runtime_directory = session_root / "output-filter"

            self.assertFalse(runtime_directory.exists())

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_persists_circuit_failures_across_processes(self) -> None:
        policy = {
            "mode": "safe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 8192,
            "minSavingsBytes": 1,
            "minSavingsRatio": 0.01,
            "recovery": {
                "ttlMinutes": 60,
                "maxSessionBytes": 1,
            },
        }
        payload = claude_payload("same\n" * 500, command="npm test")
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            policy_path = temporary_path / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            temporary_home = temporary_path / "home"
            cwd = str(payload["cwd"])
            repo_key = "-" + cwd.replace("/", "-").lstrip("-")
            session_root = (
                temporary_home
                / ".softspark"
                / "ai-toolkit"
                / "sessions"
                / repo_key
            )
            session_root.mkdir(parents=True, mode=0o700)
            session_root.chmod(0o700)
            environment = {
                **os.environ,
                "HOME": str(temporary_home),
                "PYTHONDONTWRITEBYTECODE": "1",
            }

            for _ in range(3):
                subprocess.run(
                    [
                        sys.executable,
                        str(CLI_PATH),
                        "hook",
                        "--policy",
                        str(policy_path),
                    ],
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    cwd=REPOSITORY_ROOT,
                    env=environment,
                    check=False,
                )

            state_file = next(session_root.rglob(".circuit-state.json"))
            state = json.loads(state_file.read_text(encoding="utf-8"))
            fourth = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "hook",
                    "--policy",
                    str(policy_path),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env=environment,
                check=False,
            )
            fifth = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "hook",
                    "--policy",
                    str(policy_path),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env=environment,
                check=False,
            )

        self.assertEqual(3, state["consecutiveFailures"])
        warning = json.loads(fourth.stdout)
        self.assertIn("output filtering disabled", warning["systemMessage"])
        self.assertLessEqual(len(warning["systemMessage"]), 160)
        self.assertEqual("", fourth.stderr)
        self.assertEqual("", fifth.stdout)
        self.assertEqual("", fifth.stderr)

    def test_observe_hook_persists_metadata_only_jsonl(self) -> None:
        secret = "SECRET-CANARY-TELEMETRY"
        policy = {
            "mode": "observe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 8192,
            "minSavingsBytes": 1,
            "minSavingsRatio": 0.01,
            "recovery": {
                "ttlMinutes": 60,
                "maxSessionBytes": 4096,
            },
        }
        payload = claude_payload(
            f"{secret}\n" * 100,
            command="npm test",
        )
        payload["cwd"] = str(REPOSITORY_ROOT / "scripts")
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            policy_path = temporary_path / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            temporary_home = temporary_path / "home"
            repo_key = "-" + str(REPOSITORY_ROOT).replace("/", "-").lstrip("-")
            session_root = (
                temporary_home
                / ".softspark"
                / "ai-toolkit"
                / "sessions"
                / repo_key
            )
            session_root.mkdir(parents=True, mode=0o700)
            session_root.chmod(0o700)

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI_PATH),
                    "hook",
                    "--policy",
                    str(policy_path),
                ],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                cwd=REPOSITORY_ROOT,
                env={
                    **os.environ,
                    "HOME": str(temporary_home),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                check=False,
            )

            telemetry_file = next(session_root.rglob(".telemetry.jsonl"))
            telemetry_text = telemetry_file.read_text(encoding="utf-8")
            event = json.loads(telemetry_text)

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertNotIn(secret, telemetry_text)
        self.assertNotIn(str(REPOSITORY_ROOT), telemetry_text)
        self.assertNotIn("native-session-id", telemetry_text)
        self.assertEqual(
            {
                "profileId",
                "profileVersion",
                "inputBytes",
                "outputBytes",
                "inputLines",
                "outputLines",
                "durationMs",
                "outcome",
                "fallbackReason",
            },
            set(event),
        )
        self.assertEqual("observed", event["outcome"])

    def test_hook_rejects_deployment_script_command_shape(self) -> None:
        result = self.run_hook(
            {
                "mode": "safe",
                "profiles": ["repeat-lines"],
                "maxInputBytes": 8192,
                "minSavingsBytes": 1,
                "minSavingsRatio": 0.01,
                "recovery": {
                    "ttlMinutes": 60,
                    "maxSessionBytes": 8192,
                },
            },
            claude_payload(
                "deployment progress\n" * 100,
                command="python3 scripts/deploy.py",
            ),
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_rejects_composer_command_with_unsafe_prefix(self) -> None:
        result = self.run_hook(
            {
                "mode": "safe",
                "profiles": ["repeat-lines"],
                "maxInputBytes": 8192,
                "minSavingsBytes": 1,
                "minSavingsRatio": 0.01,
                "recovery": {
                    "ttlMinutes": 60,
                    "maxSessionBytes": 8192,
                },
            },
            claude_payload(
                "dependency output\n" * 100,
                command="composer install test",
            ),
        )

        self.assertEqual(0, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)

    def test_hook_requires_safe_task_token_boundaries(self) -> None:
        policy = {
            "mode": "safe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 8192,
            "minSavingsBytes": 1,
            "minSavingsRatio": 0.01,
            "recovery": {
                "ttlMinutes": 60,
                "maxSessionBytes": 8192,
            },
        }

        for command in ("npm run contest", "make latest", "composer run protest"):
            with self.subTest(command=command):
                result = self.run_hook(
                    policy,
                    claude_payload("ordinary output\n" * 100, command=command),
                )

                self.assertEqual(0, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual("", result.stderr)

    def test_hook_rejects_unsafe_or_unbounded_session_identifiers(self) -> None:
        policy = {
            "mode": "safe",
            "profiles": ["repeat-lines"],
            "maxInputBytes": 8192,
            "minSavingsBytes": 1,
            "minSavingsRatio": 0.01,
            "recovery": {
                "ttlMinutes": 60,
                "maxSessionBytes": 8192,
            },
        }

        for session_identifier in ("conversation/unsafe", "x" * 161):
            with self.subTest(session_identifier=session_identifier):
                payload = claude_payload("ordinary output\n" * 100)
                payload["session_id"] = session_identifier

                result = self.run_hook(policy, payload)

                self.assertEqual(0, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual("", result.stderr)


if __name__ == "__main__":
    unittest.main()
