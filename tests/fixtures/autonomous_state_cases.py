#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Real Git/SQLite fixtures; stdlib runner also works inside the Bats suite."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "app/skills/autonomous-dev/scripts/run-state.py"
SPEC = importlib.util.spec_from_file_location("autonomous_run_state", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
STATE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STATE
SPEC.loader.exec_module(STATE)


class JournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="autonomous-state-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.environment = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.hooksPath", os.devnull)
        self.git("config", "commit.gpgsign", "false")
        (self.repo / "source.txt").write_text("first revision\n")
        self.git("add", "source.txt")
        self.git("commit", "-m", "test: initialize fixture")
        self.git("switch", "-c", "feature")
        self.now = 1000.0
        self.store = self.base / "journal"
        self.plan = self.base / "plan.md"
        self.plan.write_text("Implement fixture source and verify validation, review, QA and CI.\n")
        self.journal = STATE.Journal(self.repo, self.store, clock=lambda: self.now)
        self.initial = self.journal.initialize(
            self.arguments(
                "init",
                "--subject",
                "issue:7",
                "--objective",
                "Implement a fixture",
                "--source-kind",
                "issue",
                "--source",
                "issue:7",
                "--plan",
                str(self.plan),
            )
        )
        self.run_id = self.initial["run"]["run_id"]
        self.owner = self.initial["owner_token"]

    def git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo), *args], env=self.environment, check=True, capture_output=True, text=True
        ).stdout.strip()

    def arguments(self, *args: str) -> Any:
        return STATE.parser().parse_args(["--repo", str(self.repo), "--store", str(self.store), *args])

    def mutate(self, verb: str, *args: str, owner: str | None = None) -> dict[str, Any]:
        return self.journal.mutate(self.arguments(verb, "--run", self.run_id, "--owner", owner or self.owner, *args))

    def record(self, kind: str, result: str = "pass") -> dict[str, Any]:
        report = self.base / f"{kind}.md"
        report.write_text(f"{kind}: {result}. Verified fixture evidence.\n")
        return self.mutate(
            "record",
            "--kind",
            kind,
            "--result",
            result,
            "--report",
            str(report),
            "--summary",
            f"{kind} {result}: fixture checked",
        )

    def ready(self) -> None:
        self.mutate("checkpoint", "--stage", "ci", "--pr-url", "https://github.com/example/project/pull/7")
        for kind in STATE.KINDS:
            self.record(kind)

    def cli(self, *args: str, repo: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(repo or self.repo), "--store", str(self.store), *args],
            capture_output=True,
            text=True,
            env=self.environment,
            check=False,
        )

    def test_init_preserves_subject_and_returns_external_artifact_directory(self) -> None:
        self.assertTrue(Path(self.initial["artifact_dir"]).is_dir())
        self.assertFalse(Path(self.initial["artifact_dir"]).is_relative_to(self.repo))
        self.assertEqual(self.initial["run"]["target_branch"], "main")
        self.assertEqual(self.initial["run"]["fingerprint"]["branch"], "feature")
        with self.assertRaisesRegex(STATE.StateError, "already has run"):
            self.journal.initialize(
                self.arguments(
                    "init",
                    "--subject",
                    "issue:7",
                    "--objective",
                    "replacement",
                    "--source-kind",
                    "pr",
                    "--source",
                    "pr:9",
                )
            )
        self.assertEqual(self.journal.status(self.run_id)["run"]["objective"], "Implement a fixture")

    def test_generated_owner_is_cli_safe_even_when_random_bytes_encode_a_leading_dash(self) -> None:
        with patch.object(STATE.secrets, "token_urlsafe", return_value="-leading-dash-fixture"):
            initialized = self.journal.initialize(self.arguments(
                "init", "--subject", "brief:token", "--objective", "Exercise CLI owner token",
                "--source-kind", "brief", "--source", "fixture", "--plan", str(self.plan),
            ))
        result = self.cli(
            "checkpoint", "--run", initialized["run"]["run_id"],
            "--owner", initialized["owner_token"], "--stage", "plan",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_list_discovers_subject_without_mutation_or_owner_credentials(self) -> None:
        database = self.store / "runs.sqlite3"
        before = database.read_bytes()
        result = self.cli("list", "--subject", "issue:7")
        self.assertEqual(result.returncode, 0, result.stdout)
        runs = json.loads(result.stdout)["runs"]
        self.assertEqual([run["run_id"] for run in runs], [self.run_id])
        self.assertNotIn(self.owner, result.stdout)
        self.assertNotIn("owner_digest", result.stdout)
        self.assertEqual(json.loads(self.cli("list", "--subject", "unknown").stdout)["runs"], [])
        self.assertEqual(database.read_bytes(), before)

    def test_list_filters_repository_and_does_not_create_missing_store(self) -> None:
        empty_store = self.base / "absent"
        empty = STATE.Journal(self.repo, empty_store)
        self.assertEqual(empty.list_runs(), {"ok": True, "runs": []})
        self.assertFalse(empty_store.exists())
        other = self.base / "other"
        subprocess.run(["git", "init", "-q", str(other)], check=True, env=self.environment)
        self.assertEqual(STATE.Journal(other, self.store).list_runs()["runs"], [])
        self.assertEqual(len(self.journal.list_runs()["runs"]), 1)

    def test_status_is_read_only_and_does_not_expose_owner_token(self) -> None:
        database = self.store / "runs.sqlite3"
        previous = database.stat().st_mtime_ns
        status = self.journal.status(self.run_id)
        self.assertEqual(database.stat().st_mtime_ns, previous)
        self.assertNotIn(self.owner, json.dumps(status))
        self.assertNotIn("owner_digest", status["run"])
        self.assertIn("attempt start", status["next_step"])
        missing = STATE.Journal(self.repo, self.base / "missing")
        with self.assertRaisesRegex(STATE.StateError, "No run journal"):
            missing.status(self.run_id)
        self.assertFalse(missing.store.exists())

    def test_every_mutation_refuses_wrong_owner_without_history_changes(self) -> None:
        cases = [
            ("checkpoint", "--stage", "plan"),
            ("record", "--kind", "review", "--result", "pass", "--report", "missing", "--summary", "fake"),
            ("attempt", "--action", "start"),
            ("release", "--reason", "handoff"),
            ("complete",),
        ]
        for case in cases:
            with self.subTest(verb=case[0]), self.assertRaisesRegex(STATE.StateError, "not owned"):
                self.mutate(*case, owner="other-session-token")
        self.assertEqual(len(self.journal.status(self.run_id)["history"]), 1)

    def test_takeover_requires_previous_owner_and_reason_and_invalidates_old_token(self) -> None:
        previous = self.initial["run"]["owner_id"]
        with self.assertRaisesRegex(STATE.StateError, "takeover requires"):
            self.mutate("claim", owner="new-session-token")
        with self.assertRaisesRegex(STATE.StateError, "takeover requires"):
            self.mutate("claim", "--previous-owner", "wrong", "--reason", "session exited", owner="new-session-token")
        changed = self.mutate(
            "claim", "--previous-owner", previous, "--reason", "session exited", owner="new-session-token"
        )
        self.assertNotEqual(changed["run"]["owner_id"], previous)
        with self.assertRaisesRegex(STATE.StateError, "not owned"):
            self.mutate("checkpoint", "--stage", "plan")

    def test_concurrent_sessions_cannot_claim_the_same_released_run(self) -> None:
        self.mutate("release", "--reason", "handoff")
        owners = ["concurrent-session-one", "concurrent-session-two"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda owner: self.cli("claim", "--run", self.run_id, "--owner", owner), owners))
        self.assertEqual(sorted(item.returncode for item in outcomes), [0, 1])
        for item in outcomes:
            self.assertEqual(json.loads(item.stdout)["ok"], item.returncode == 0)
            self.assertEqual(item.stderr, "")

    def test_same_common_repository_and_default_store_across_linked_worktrees(self) -> None:
        linked = self.base / "linked"
        self.git("worktree", "add", "-b", "other-feature", str(linked))
        self.assertEqual(STATE.default_store(self.repo), STATE.default_store(linked))
        linked_journal = STATE.Journal(linked, self.store)
        status = linked_journal.status(self.run_id)
        self.assertEqual(status["current_git"]["repository"], self.initial["current_git"]["repository"])
        self.assertTrue(status["next_step"].startswith("claim --rebind-worktree:"))
        with self.assertRaisesRegex(STATE.StateError, "already has run"):
            linked_journal.initialize(
                self.arguments(
                    "init",
                    "--subject",
                    "issue:7",
                    "--objective",
                    "duplicate",
                    "--source-kind",
                    "issue",
                    "--source",
                    "issue:7",
                )
            )
        with self.assertRaisesRegex(STATE.StateError, "Wrong working tree"):
            linked_journal.mutate(
                self.arguments("checkpoint", "--run", self.run_id, "--owner", self.owner, "--stage", "plan")
            )

    def test_explicit_worktree_rebinding_preserves_subject_and_invalidates_old_evidence(self) -> None:
        self.record("validation")
        linked = self.base / "linked"
        self.git("worktree", "add", "--force", str(linked), "feature")
        linked_journal = STATE.Journal(linked, self.store)
        args = self.arguments("claim", "--run", self.run_id, "--owner", self.owner, "--rebind-worktree")
        moved = linked_journal.mutate(args)
        self.assertEqual(moved["run"]["subject"], "issue:7")
        self.assertEqual(moved["run"]["fingerprint"]["worktree"], str(linked))
        self.assertIn("validation: stale Git fingerprint", moved["blockers"])

    def test_dirty_worktree_contents_branch_and_commits_invalidate_evidence(self) -> None:
        self.ready()
        (self.repo / "source.txt").write_text("second revision\n")
        status = self.journal.status(self.run_id)
        self.assertFalse(status["current_git"]["clean"])
        self.assertIn("review: stale Git fingerprint", status["blockers"])
        first_dirty = status["current_git"]["digest"]
        (self.repo / "source.txt").write_text("third revision\n")
        self.assertNotEqual(self.journal.status(self.run_id)["current_git"]["digest"], first_dirty)
        self.git("add", "source.txt")
        self.git("commit", "-m", "test: change revision")
        self.mutate("checkpoint", "--stage", "validate")
        with self.assertRaisesRegex(STATE.StateError, "stale Git fingerprint"):
            self.mutate("complete")
        self.ready()
        self.git("switch", "-c", "another-feature")
        self.assertIn("ci: stale Git fingerprint", self.journal.status(self.run_id)["blockers"])

    def test_untracked_contents_index_and_symlinks_affect_fingerprint(self) -> None:
        original = STATE.fingerprint(self.repo)
        extra = self.repo / "new.txt"
        extra.write_text("one")
        first = STATE.fingerprint(self.repo)
        extra.write_text("two")
        second = STATE.fingerprint(self.repo)
        self.assertNotEqual(first.digest, second.digest)
        self.git("add", "new.txt")
        self.assertNotEqual(second.digest, STATE.fingerprint(self.repo).digest)
        (self.repo / "link").symlink_to("new.txt")
        self.assertNotEqual(original.digest, STATE.fingerprint(self.repo).digest)

    def test_reports_must_exist_be_nonempty_and_remain_unchanged(self) -> None:
        empty = self.base / "empty"
        empty.touch()
        for report in (empty, self.base / "absent", self.base):
            with self.subTest(report=report), self.assertRaisesRegex(STATE.StateError, "existing nonempty"):
                self.mutate(
                    "record",
                    "--kind",
                    "validation",
                    "--result",
                    "pass",
                    "--report",
                    str(report),
                    "--summary",
                    "checked",
                )
        self.ready()
        (self.base / "review.md").write_text("changed after recording")
        self.assertIn("review: report contents changed", self.journal.status(self.run_id)["blockers"])
        with self.assertRaisesRegex(STATE.StateError, "report contents changed"):
            self.mutate("complete")

    def test_completion_requires_all_gates_and_pending_ci_never_passes(self) -> None:
        with self.assertRaisesRegex(STATE.StateError, "evidence missing"):
            self.mutate("complete")
        self.ready()
        self.record("ci", "pending")
        with self.assertRaisesRegex(STATE.StateError, "ci: pending"):
            self.mutate("complete")
        self.record("ci", "fail")
        with self.assertRaisesRegex(STATE.StateError, "ci: fail"):
            self.mutate("complete")

    def test_existing_failed_ci_cannot_be_ignored_when_closing_an_attempt(self) -> None:
        self.mutate("attempt", "--action", "start")
        self.ready()
        self.record("ci", "fail")
        with self.assertRaisesRegex(STATE.StateError, "ci: fail"):
            self.mutate("attempt", "--action", "pass", "--summary", "Local checks passed")
        self.record("ci")
        self.mutate("attempt", "--action", "pass", "--summary", "All checks passed")
        self.mutate("checkpoint", "--stage", "blocked")
        with self.assertRaisesRegex(STATE.StateError, "Run is blocked"):
            self.mutate("complete")

    def test_not_applicable_requires_initial_opt_out_and_nonempty_reason_and_report(self) -> None:
        with self.assertRaisesRegex(STATE.StateError, "Only QA or CI"):
            self.record("qa", "not-applicable")
        optional = self.journal.initialize(
            self.arguments(
                "init",
                "--subject",
                "brief:optional",
                "--objective",
                "Documentation",
                "--source-kind",
                "brief",
                "--source",
                "brief.md",
                "--qa-optional",
                "--ci-optional",
                "--plan",
                str(self.plan),
            )
        )
        self.run_id, self.owner = optional["run"]["run_id"], optional["owner_token"]
        self.mutate("attempt", "--action", "start")
        self.mutate("checkpoint", "--stage", "ci", "--pr-url", "https://github.com/example/project/pull/8")
        self.record("validation")
        self.record("review")
        self.record("qa", "not-applicable")
        self.record("ci", "not-applicable")
        self.mutate("attempt", "--action", "pass", "--summary", "Required gates passed; QA and CI inapplicable")
        self.assertEqual(self.mutate("complete")["run"]["status"], "complete")

    def test_complete_requires_successfully_closed_latest_attempt(self) -> None:
        self.ready()
        with self.assertRaisesRegex(STATE.StateError, "successfully closed latest attempt"):
            self.mutate("complete")
        self.mutate("attempt", "--action", "start")
        self.mutate("attempt", "--action", "fail", "--summary", "Failed cycle")
        self.ready()
        with self.assertRaisesRegex(STATE.StateError, "successfully closed latest attempt"):
            self.mutate("complete")

    def test_changed_source_cannot_reuse_a_previous_successful_attempt(self) -> None:
        self.mutate("attempt", "--action", "start")
        self.ready()
        self.mutate("attempt", "--action", "pass", "--summary", "Initial source verified")
        (self.repo / "source.txt").write_text("changed source")
        self.git("add", "source.txt")
        self.git("commit", "-m", "test: new source after successful cycle")
        self.ready()
        with self.assertRaisesRegex(STATE.StateError, "successfully closed latest attempt"):
            self.mutate("complete")

    def test_plan_must_exist_and_remain_unchanged_and_revisions_invalidate_evidence(self) -> None:
        for path in (self.base / "absent", self.base / "empty"):
            if path.name == "empty":
                path.touch()
            with self.assertRaisesRegex(STATE.StateError, "existing nonempty local file"):
                self.mutate("checkpoint", "--stage", "plan", "--plan", str(path))
        self.mutate("attempt", "--action", "start")
        self.ready()
        self.mutate("attempt", "--action", "pass", "--summary", "Current plan verified")
        self.plan.write_text("Add an additional validation command to this plan.\n")
        self.assertIn("Plan contents changed", " ".join(self.journal.status(self.run_id)["blockers"]))
        with self.assertRaisesRegex(STATE.StateError, "Plan contents changed"):
            self.mutate("complete")
        with self.assertRaisesRegex(STATE.StateError, "Plan contents changed"):
            self.record("validation")
        revised = self.mutate("checkpoint", "--stage", "plan", "--plan", str(self.plan))
        self.assertEqual(revised["run"]["evidence"], {})
        self.assertIsNone(revised["run"]["last_attempt_result"])
        self.assertTrue(any(event["action"] == "record" for event in revised["history"]))
        self.plan.rename(self.base / "retained-plan-backup.md")
        self.assertIn("Plan file is missing or empty", self.journal.status(self.run_id)["blockers"])

    def test_next_step_follows_plan_cycle_local_gates_publication_ci_and_done(self) -> None:
        fresh = self.journal.initialize(
            self.arguments(
                "init",
                "--subject",
                "brief:fresh",
                "--objective",
                "New task",
                "--source-kind",
                "brief",
                "--source",
                "task text",
            )
        )
        self.run_id, self.owner = fresh["run"]["run_id"], fresh["owner_token"]
        self.assertTrue(fresh["next_step"].startswith("plan:"))
        planned = self.mutate("checkpoint", "--stage", "plan", "--plan", str(self.plan))
        self.assertTrue(planned["next_step"].startswith("attempt start:"))
        active = self.mutate("attempt", "--action", "start")
        self.assertTrue(active["next_step"].startswith("implement:"))
        checking = self.mutate("checkpoint", "--stage", "validate")
        self.assertTrue(checking["next_step"].startswith("validation:"))
        for kind in ("validation", "review", "qa"):
            self.record(kind)
        self.assertTrue(self.journal.status(self.run_id)["next_step"].startswith("publish:"))
        published = self.mutate("checkpoint", "--stage", "ci", "--pr-url", "https://github.com/example/project/pull/20")
        self.assertTrue(published["next_step"].startswith("ci:"))
        checks = self.record("ci")
        self.assertTrue(checks["next_step"].startswith("attempt pass:"))
        passed = self.mutate("attempt", "--action", "pass", "--summary", "All gates passed")
        self.assertTrue(passed["next_step"].startswith("complete:"))
        done = self.mutate("complete")
        self.assertTrue(done["next_step"].startswith("done:"))

    def test_assume_unchanged_and_skip_worktree_never_certify_clean_head(self) -> None:
        for flag in ("--assume-unchanged", "--skip-worktree"):
            with self.subTest(flag=flag):
                self.git("update-index", flag, "source.txt")
                (self.repo / "source.txt").write_text("Hidden modified contents")
                current = STATE.fingerprint(self.repo)
                self.assertFalse(current.clean)
                self.assertIn("cannot be fully verified", current.verification_problem)
                self.assertTrue(self.journal.status(self.run_id)["next_step"].startswith("blocked:"))
                self.ready()
                with self.assertRaisesRegex(STATE.StateError, "cannot be fully verified"):
                    self.mutate("complete")
                self.git("update-index", "--no-assume-unchanged", "--no-skip-worktree", "source.txt")

    def test_submodule_ignore_config_cannot_hide_dirty_source(self) -> None:
        child = self.base / "child-source"
        child.mkdir()
        subprocess.run(
            ["git", "clone", "--local", str(self.repo), str(child)],
            capture_output=True,
            env=self.environment,
            check=True,
        )
        self.git("-c", "protocol.file.allow=always", "submodule", "add", str(child), "nested")
        self.git("commit", "-m", "test: add local submodule")
        uninitialized = self.base / "uninitialized-clone"
        subprocess.run(
            ["git", "clone", "--local", str(self.repo), str(uninitialized)],
            capture_output=True,
            env=self.environment,
            check=True,
        )
        missing_nested = STATE.fingerprint(uninitialized)
        self.assertFalse(missing_nested.clean)
        self.assertIn("Uninitialized submodule", missing_nested.verification_problem)
        self.git("config", "submodule.nested.ignore", "all")
        (self.repo / "nested/source.txt").write_text("Dirty nested source")
        current = STATE.fingerprint(self.repo)
        self.assertFalse(current.clean)
        self.assertIn("Submodule", current.verification_problem)
        self.ready()
        with self.assertRaisesRegex(STATE.StateError, "Submodule"):
            self.mutate("complete")

    def test_happy_run_has_auditable_attempt_and_immutable_completion(self) -> None:
        self.mutate("attempt", "--action", "start")
        self.ready()
        self.mutate("attempt", "--action", "pass", "--summary", "All local checks passed")
        done = self.mutate("complete")
        self.assertEqual(done["run"]["stage"], "ready-pr")
        self.assertEqual(done["run"]["status"], "complete")
        self.assertEqual(done["blockers"], [])
        self.assertEqual(done["history"][-1]["action"], "complete")
        with self.assertRaisesRegex(STATE.StateError, "immutable"):
            self.mutate("checkpoint", "--stage", "implement")

    def test_interruption_and_resume_preserve_attempt_and_failure_history(self) -> None:
        self.mutate("attempt", "--action", "start")
        self.record("review", "fail")
        self.record("validation", "fail")
        self.mutate("attempt", "--action", "fail", "--summary", "Both gates failed in one cycle")
        self.journal = STATE.Journal(self.repo, self.store, clock=lambda: self.now)
        self.mutate("claim")
        self.record("validation")
        self.assertEqual(self.journal.status(self.run_id)["run"]["consecutive_failures"], 1)
        self.now += 60
        self.mutate("attempt", "--action", "start")
        with self.assertRaisesRegex(STATE.StateError, "review: fail"):
            self.mutate("attempt", "--action", "pass", "--summary", "Validation alone passed")
        self.mutate("release", "--reason", "Interrupted host")
        resumed = self.mutate("claim", owner="replacement-session")
        self.assertTrue(resumed["run"]["attempt_active"])
        self.assertEqual(resumed["run"]["attempts"], 2)

    def test_retry_floor_and_three_failed_cycles_cannot_reset_on_resume(self) -> None:
        for index in range(3):
            self.mutate("attempt", "--action", "start")
            self.mutate("attempt", "--action", "fail", "--summary", f"cycle {index + 1} failed")
            if index == 0:
                with self.assertRaisesRegex(STATE.StateError, "60 seconds"):
                    self.mutate("attempt", "--action", "start")
            self.now += 60
        self.mutate("claim")
        with self.assertRaisesRegex(STATE.StateError, "circuit breaker"):
            self.mutate("attempt", "--action", "start")
        self.ready()
        with self.assertRaisesRegex(STATE.StateError, "Circuit breaker"):
            self.mutate("complete")

    def test_five_attempt_limit_persists_even_when_each_attempt_passes(self) -> None:
        self.ready()
        for _ in range(5):
            self.mutate("attempt", "--action", "start")
            self.mutate("attempt", "--action", "pass", "--summary", "Local gates passed")
            self.now += 60
        self.mutate("claim")
        with self.assertRaisesRegex(STATE.StateError, "attempt limit"):
            self.mutate("attempt", "--action", "start")
        self.assertEqual(self.journal.status(self.run_id)["run"]["attempts"], 5)
        (self.repo / "source.txt").write_text("Source changed after the fifth passed attempt")
        self.assertTrue(self.journal.status(self.run_id)["next_step"].startswith("halt:"))

    def test_pr_identity_cannot_be_silently_replaced(self) -> None:
        self.mutate("checkpoint", "--stage", "publish", "--pr-url", "https://github.com/example/project/pull/7")
        with self.assertRaisesRegex(STATE.StateError, "different PR"):
            self.mutate("checkpoint", "--stage", "publish", "--pr-url", "https://github.com/example/project/pull/8")
        with self.assertRaisesRegex(STATE.StateError, "HTTPS"):
            self.mutate("checkpoint", "--stage", "publish", "--pr-url", "http://example.invalid/pr/1")

    def test_cli_returns_json_errors_nonzero_and_help_without_tracebacks(self) -> None:
        for args in [
            ("record",),
            ("status", "--run", "absent"),
            ("complete", "--run", self.run_id, "--owner", "bad-session-token"),
        ]:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stdout)["ok"])
                self.assertEqual(result.stderr, "")
        help_result = self.cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("checkpoint", help_result.stdout)
        self.assertNotIn("Traceback", help_result.stderr)


if __name__ == "__main__":
    unittest.main()
