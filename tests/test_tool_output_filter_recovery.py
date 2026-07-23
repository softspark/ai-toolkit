from __future__ import annotations

import stat
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from scripts.tool_output_filter.contracts import FilterTelemetry
from scripts.tool_output_filter.recovery import (
    EphemeralRecoveryStore,
    RecoveryUnavailableError,
    clean_owned_recovery_tree,
    clean_session,
    count_owned_recovery_artifacts,
)


class EphemeralRecoveryStoreTests(unittest.TestCase):
    def test_round_trip_is_exact_and_artifacts_are_private(self) -> None:
        response = {
            "stdout": "sekret\n",
            "stderr": "",
            "interrupted": False,
            "isImage": False,
            "metadata": {"attempt": 2},
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)

            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="native-session-id",
            ) as recovery:
                handle = recovery.save(response)
                restored = recovery.load(handle)

            self.assertEqual(response, restored)
            self.assertNotIn("native-session-id", handle)
            artifacts = list(base_directory.rglob("*"))
            directories = [path for path in artifacts if path.is_dir()]
            files = [path for path in artifacts if path.is_file()]
            self.assertEqual(2, len(directories))
            self.assertEqual(1, len(files))
            for directory in directories:
                self.assertEqual(
                    0o700,
                    stat.S_IMODE(directory.stat().st_mode),
                )
            self.assertEqual(0o600, stat.S_IMODE(files[0].stat().st_mode))

    def test_save_refuses_to_exceed_session_quota(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="quota-session",
                max_session_bytes=64,
            ) as recovery:
                with self.assertRaises(RecoveryUnavailableError):
                    recovery.save({"stdout": "x" * 100})

            files = [
                path
                for path in base_directory.rglob("*")
                if path.is_file()
            ]
            self.assertEqual([], files)

    def test_clean_expired_removes_only_owned_stale_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="ttl-session",
                ttl_minutes=1,
                clock=lambda: 61.0,
            ) as recovery:
                handle = recovery.save({"stdout": "recover me"})
                artifact = next(base_directory.rglob(f"{handle}.json"))
                os.utime(artifact, (0, 0))

                removed = recovery.clean_expired()

                self.assertEqual(1, removed)
                self.assertIsNone(recovery.load(handle))

    def test_clean_all_preserves_unowned_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="cleanup-session",
            ) as recovery:
                first_handle = recovery.save({"stdout": "first"})
                second_handle = recovery.save({"stdout": "second"})
                session_directory = next(
                    path
                    for path in base_directory.rglob("*")
                    if path.is_dir() and path.name != "output-filter"
                )
                unowned_file = session_directory / "keep.txt"
                unowned_file.write_text("keep", encoding="utf-8")

                removed = recovery.clean_all()

                self.assertEqual(2, removed)
                self.assertIsNone(recovery.load(first_handle))
                self.assertIsNone(recovery.load(second_handle))
                self.assertEqual("keep", unowned_file.read_text(encoding="utf-8"))

    def test_clean_all_preflights_every_owned_name_before_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            base_directory = temporary_path / "repo-session"
            base_directory.mkdir(mode=0o700)
            outside_file = temporary_path / "outside.json"
            outside_file.write_text("outside", encoding="utf-8")
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="preflight-session",
            ) as recovery:
                handle = recovery.save({"stdout": "must survive"})
                artifact = next(base_directory.rglob(f"{handle}.json"))
                malicious_name = artifact.parent / ("f" * 32 + ".json")
                malicious_name.symlink_to(outside_file)

                with patch(
                    "scripts.tool_output_filter.recovery.os.listdir",
                    return_value=[artifact.name, malicious_name.name],
                ):
                    with self.assertRaises(RecoveryUnavailableError):
                        recovery.clean_all()

                self.assertEqual(
                    {"stdout": "must survive"},
                    recovery.load(handle),
                )
                self.assertEqual(
                    "outside",
                    outside_file.read_text(encoding="utf-8"),
                )

    def test_circuit_failure_count_survives_store_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="circuit-session",
            ) as recovery:
                recovery.save_failure_count(3)

            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="circuit-session",
            ) as recovery:
                self.assertEqual(3, recovery.load_failure_count())

            state_file = next(
                base_directory.rglob(".circuit-state.json")
            )
            self.assertEqual(0o600, stat.S_IMODE(state_file.stat().st_mode))

    def test_default_zero_circuit_count_uses_implicit_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="zero-circuit-session",
            ) as recovery:
                recovery.save_failure_count(0)

            self.assertEqual(
                [],
                list(base_directory.rglob(".circuit-state.json")),
            )

    def test_clean_session_removes_recovery_and_preserves_unowned_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            base_directory = Path(temporary_directory) / "repo-session"
            base_directory.mkdir(mode=0o700)
            with EphemeralRecoveryStore(
                base_directory,
                session_identifier="owned-session",
            ) as recovery:
                handle = recovery.save({"stdout": "remove"})
                recovery.save_failure_count(2)
                recovery.record(
                    FilterTelemetry(
                        profile_id="repeat-lines",
                        profile_version=1,
                        input_bytes=100,
                        output_bytes=20,
                        input_lines=10,
                        output_lines=2,
                        outcome="observed",
                    )
                )
                artifact = next(base_directory.rglob(f"{handle}.json"))
                circuit_state = next(
                    base_directory.rglob(".circuit-state.json")
                )
                telemetry = next(base_directory.rglob(".telemetry.jsonl"))
                unowned_file = artifact.parent / "keep.txt"
                unowned_file.write_text("keep", encoding="utf-8")
                pending_file = artifact.parent / (
                    ".pending-" + ("a" * 32)
                )
                pending_file.write_text("interrupted write", encoding="utf-8")
                pending_file.chmod(0o600)

            removed = clean_session(base_directory, "owned-session")

            self.assertEqual(4, removed)
            self.assertFalse(artifact.exists())
            self.assertFalse(circuit_state.exists())
            self.assertFalse(telemetry.exists())
            self.assertFalse(pending_file.exists())
            self.assertEqual("keep", unowned_file.read_text(encoding="utf-8"))

    def test_tree_cleanup_rejects_owned_name_symlink_before_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            sessions_root = temporary_path / "sessions"
            repo_directory = sessions_root / "repo"
            repo_directory.mkdir(parents=True, mode=0o700)
            with EphemeralRecoveryStore(
                repo_directory,
                session_identifier="tree-session",
            ) as recovery:
                handle = recovery.save({"stdout": "must survive preflight"})
                recovery.save_failure_count(2)
                recovery.record(
                    FilterTelemetry(
                        profile_id="repeat-lines",
                        profile_version=1,
                        input_bytes=100,
                        output_bytes=20,
                        input_lines=10,
                        output_lines=2,
                        outcome="observed",
                    )
                )
                artifact = next(repo_directory.rglob(f"{handle}.json"))
                circuit_state = next(
                    repo_directory.rglob(".circuit-state.json")
                )
                telemetry = next(repo_directory.rglob(".telemetry.jsonl"))
            outside_file = temporary_path / "outside.json"
            outside_file.write_text("outside", encoding="utf-8")
            malicious_name = artifact.parent / ("f" * 32 + ".json")
            malicious_name.symlink_to(outside_file)

            with self.assertRaises(RecoveryUnavailableError):
                clean_owned_recovery_tree(sessions_root)

            self.assertTrue(artifact.exists())
            self.assertTrue(circuit_state.exists())
            self.assertTrue(telemetry.exists())
            self.assertEqual("outside", outside_file.read_text(encoding="utf-8"))

    def test_owned_artifact_count_uses_secure_preflight_and_ignores_foreign(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            sessions_root = temporary_path / "sessions"
            repo_directory = sessions_root / "repo"
            repo_directory.mkdir(parents=True, mode=0o700)
            with EphemeralRecoveryStore(
                repo_directory,
                session_identifier="count-session",
            ) as recovery:
                recovery.save({"stdout": "count"})
                recovery.save_failure_count(2)
                recovery.record(
                    FilterTelemetry(
                        profile_id="repeat-lines",
                        profile_version=1,
                        input_bytes=100,
                        output_bytes=20,
                        input_lines=10,
                        output_lines=2,
                        outcome="observed",
                    )
                )
                session_directory = next(
                    path
                    for path in repo_directory.rglob("*")
                    if path.is_dir() and path.name != "output-filter"
                )
                (session_directory / "keep.txt").write_text(
                    "foreign",
                    encoding="utf-8",
                )

            self.assertEqual(
                3,
                count_owned_recovery_artifacts(sessions_root),
            )

            clean_owned_recovery_tree(sessions_root)

            self.assertEqual(
                0,
                count_owned_recovery_artifacts(sessions_root),
            )

    def test_owned_artifact_count_rejects_unsafe_owned_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            sessions_root = temporary_path / "sessions"
            repo_directory = sessions_root / "repo"
            repo_directory.mkdir(parents=True, mode=0o700)
            with EphemeralRecoveryStore(
                repo_directory,
                session_identifier="unsafe-count-session",
            ) as recovery:
                handle = recovery.save({"stdout": "count"})
                artifact = next(repo_directory.rglob(f"{handle}.json"))
            outside_file = temporary_path / "outside.json"
            outside_file.write_text("outside", encoding="utf-8")
            (artifact.parent / ("f" * 32 + ".json")).symlink_to(outside_file)

            with self.assertRaises(RecoveryUnavailableError):
                count_owned_recovery_artifacts(sessions_root)

if __name__ == "__main__":
    unittest.main()
