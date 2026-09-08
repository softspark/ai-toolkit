# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""End-to-end QA checker tests using temporary Git repos and loopback HTTP."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[3] / "app/skills/prepare-test-env/scripts/env-check.py"


class EnvCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="toolkit-qa-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.worktree = self.root / "project"
        self.worktree.mkdir()
        self.run_dir = self.root / "run"
        self.run_dir.mkdir()
        self.descriptor = self.run_dir / "test-env.json"
        self.git("init", "-q")
        self.git("config", "user.name", "QA Fixture")
        self.git("config", "user.email", "qa@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.root / "no-hooks"))
        (self.worktree / "app.txt").write_text("first revision\n")
        self.git("add", ".")
        self.git("commit", "-qm", "test: initial fixture")
        result, source = self.cli("snapshot", "--worktree", str(self.worktree))
        self.assertEqual(result.returncode, 0, source)
        source.pop("ok")
        self.source = source
        self.requests = []
        self.response_status = 200
        self.response_delay = 0
        self.on_request = None
        self.runtime = dict(source)
        self.server = self.start_server()
        self.data = {
            "version": 1, "runId": "fixture-run", **source,
            "baseUrl": self.url, "healthUrl": self.url + "/ready",
            "browser": {"provider": "native-browser"},
            "ownership": {"startedByRun": False, "resources": []},
            "commands": {"start": None, "stop": None}, "credentials": {},
            "artifactsDir": str(self.run_dir / "artifacts"),
        }

    def start_server(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                fixture.requests.append(self.path)
                if fixture.on_request:
                    fixture.on_request()
                if fixture.response_delay:
                    time.sleep(fixture.response_delay)
                self.send_response(fixture.response_status)
                if fixture.response_status == 302:
                    self.send_header("Location", "http://192.0.2.1/leak")
                self.end_headers()
                if self.path == "/identity":
                    self.wfile.write(json.dumps(fixture.runtime).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.url = f"http://127.0.0.1:{server.server_port}"
        self.addCleanup(thread.join, 1)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.worktree), *args], text=True,
                                capture_output=True, check=True, timeout=10)
        return result.stdout.strip()

    def cli(self, *args, env=None):
        result = subprocess.run(["python3", str(SCRIPT), *args], text=True,
                                capture_output=True, check=False, timeout=20, env=env)
        self.assertNotIn("Traceback", result.stderr)
        return result, json.loads(result.stdout)

    def check(self, *extra, worktree=None, env=None):
        self.descriptor.write_text(json.dumps(self.data))
        return self.cli("check", "--descriptor", str(self.descriptor), "--worktree",
                        str(worktree or self.worktree), "--run-dir", str(self.run_dir), *extra, env=env)

    def assert_refused_without_http(self, *extra):
        result, report = self.check(*extra)
        self.assertEqual(result.returncode, 1, report)
        self.assertFalse(report["ok"])
        self.assertEqual(self.requests, [])
        return report

    def test_clean_source_and_ready_http_report_unverified_runtime(self):
        result, report = self.check()
        self.assertEqual(result.returncode, 0, report)
        self.assertTrue(report["httpReady"])
        self.assertEqual(report["runtimeIdentity"], "unverified")
        self.assertEqual(report["headSha"], self.git("rev-parse", "HEAD"))
        self.assertEqual(self.requests, ["/ready"])

    def test_matching_runtime_identity_is_verified(self):
        self.data["readiness"] = {"identityUrl": self.url + "/identity"}
        result, report = self.check()
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual(report["runtimeIdentity"], "verified")
        self.assertEqual(self.requests, ["/ready", "/identity"])

    def test_stale_running_application_is_rejected(self):
        self.data["readiness"] = {"identityUrl": self.url + "/identity"}
        self.runtime["headSha"] = "0" * 40
        result, report = self.check()
        self.assertEqual(result.returncode, 1, report)
        self.assertIn("running application", report["error"])

    def test_new_commit_invalidates_descriptor_before_http(self):
        (self.worktree / "app.txt").write_text("new revision\n")
        self.git("commit", "-am", "test: new revision", "-q")
        self.assertIn("stale", self.assert_refused_without_http()["error"])

    def test_source_changing_during_http_probe_is_rejected(self):
        self.on_request = lambda: (self.worktree / "app.txt").write_text("new source\n")
        result, report = self.check()
        self.assertEqual(result.returncode, 1, report)
        self.assertIn("dirty", report["error"])
        self.assertEqual(self.requests, ["/ready"])

    def test_malformed_json_missing_fields_and_nonobjects_are_rejected(self):
        for data in ([], None, {"version": 1}):
            with self.subTest(data=data):
                self.data = data
                self.assert_refused_without_http()
        for content in ("{broken-json", "[" * 2000 + "]" * 2000):
            with self.subTest(content=content[:20]):
                self.descriptor.write_text(content)
                result, report = self.cli("check", "--descriptor", str(self.descriptor),
                                          "--worktree", str(self.worktree), "--run-dir", str(self.run_dir))
                self.assertEqual(result.returncode, 1, report)
                self.assertEqual(self.requests, [])

    def test_dirty_and_untracked_source_cannot_be_final_qa(self):
        for filename in ("app.txt", "new-source.txt"):
            with self.subTest(filename=filename):
                target = self.worktree / filename
                target.write_text("changed source\n")
                self.assertIn("dirty", self.assert_refused_without_http()["error"])
                if filename == "app.txt":
                    target.write_text("first revision\n")

    def test_git_index_flags_cannot_hide_changed_source(self):
        for flag in ("assume-unchanged", "skip-worktree"):
            with self.subTest(flag=flag):
                self.git("update-index", "--" + flag, "app.txt")
                (self.worktree / "app.txt").write_text("hidden changed source\n")
                self.assertEqual(self.git("status", "--porcelain"), "")
                self.assertIn("source cannot be verified", self.assert_refused_without_http()["error"])
                (self.worktree / "app.txt").write_text("first revision\n")
                self.git("update-index", "--no-" + flag, "app.txt")

    def add_submodule(self):
        module_source = self.root / "module-source"
        module_source.mkdir()
        original = self.worktree
        self.worktree = module_source
        self.git("init", "-q")
        self.git("config", "user.name", "QA Fixture")
        self.git("config", "user.email", "qa@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", str(self.root / "no-hooks"))
        (module_source / "module.txt").write_text("module source\n")
        self.git("add", ".")
        self.git("commit", "-qm", "test: module source")
        self.worktree = original
        self.git("-c", "protocol.file.allow=always", "submodule", "add", "-q", str(module_source), "module")
        self.git("commit", "-qam", "test: add module")
        result, source = self.cli("snapshot", "--worktree", str(self.worktree))
        self.assertEqual(result.returncode, 0, source)
        source.pop("ok")
        self.data.update(source)
        return self.worktree / "module"

    def test_submodule_hidden_flags_and_ignored_dirtiness_are_rejected(self):
        module = self.add_submodule()
        self.git("config", "submodule.module.ignore", "all")
        self.git("-C", str(module), "update-index", "--assume-unchanged", "module.txt")
        (module / "module.txt").write_text("hidden submodule source\n")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("source cannot be verified", self.assert_refused_without_http()["error"])
        self.git("-C", str(module), "update-index", "--no-assume-unchanged", "module.txt")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertIn("dirty", self.assert_refused_without_http()["error"])

    def test_uninitialized_submodule_cannot_be_certified_as_clean(self):
        self.add_submodule()
        (self.worktree / "module").rename(self.root / "saved-initialized-module")
        (self.worktree / "module").mkdir()
        self.assertEqual(self.git("status", "--porcelain", "--ignore-submodules=none"), "")
        self.assertIn("uninitialized", self.assert_refused_without_http()["error"])

    def test_same_commit_in_another_worktree_is_rejected(self):
        other = self.root / "other"
        self.git("worktree", "add", "--detach", str(other), "HEAD")
        result, report = self.check(worktree=other)
        self.assertEqual(result.returncode, 1, report)
        self.assertIn("another worktree", report["error"])
        self.assertEqual(self.requests, [])

    def test_invalid_descriptor_shapes_and_secret_literals_are_rejected(self):
        variants = [
            {"version": True}, {"unexpected": "do not leak this"},
            {"credentials": {"password": "plaintext-secret"}},
            {"ownership": {"startedByRun": "yes", "resources": []}},
            {"ownership": {"startedByRun": True, "resources": [{"kind": [], "id": "1", "identity": "x"}]}},
            {"ownership": {"startedByRun": True, "resources": []}},
            {"commands": {"start": None, "stop": "stop shared service"}},
            {"browser": {"provider": ""}}, {"readiness": {}},
        ]
        original = dict(self.data)
        for values in variants:
            with self.subTest(values=values):
                self.data = {**original, **values}
                report = self.assert_refused_without_http()
                self.assertNotIn("plaintext-secret", json.dumps(report))

    def test_descriptor_commands_are_never_executed_or_echoed(self):
        sentinel = self.root / "should-not-exist"
        self.git("config", "core.fsmonitor", f"touch {sentinel}")
        self.data["commands"] = {"start": f"touch {sentinel}", "stop": f"touch {sentinel}"}
        self.data["ownership"] = {"startedByRun": True, "resources": [
            {"kind": "process", "id": "1", "identity": "fixture-creation-token"}]}
        self.data["credentials"] = {"passwordEnv": "QA_PASSWORD"}
        result, report = self.check()
        self.assertEqual(result.returncode, 0, report)
        self.assertFalse(sentinel.exists())
        self.assertNotIn("touch", result.stdout)
        self.assertNotIn("QA_PASSWORD", result.stdout)

    def test_artifacts_and_descriptors_cannot_escape_run_directory(self):
        self.data["artifactsDir"] = str(self.worktree / "artifacts")
        self.assert_refused_without_http()
        self.data["artifactsDir"] = str(self.run_dir / "link")
        (self.run_dir / "link").symlink_to(self.worktree, target_is_directory=True)
        self.assert_refused_without_http()
        self.data["artifactsDir"] = str(self.run_dir / "artifacts")
        self.descriptor = self.root / "outside.json"
        self.assert_refused_without_http()

    def test_run_directory_inside_any_linked_worktree_is_rejected(self):
        other = self.root / "other"
        self.git("worktree", "add", "--detach", str(other), "HEAD")
        self.run_dir = other / "ignored-run"
        self.run_dir.mkdir()
        self.descriptor = self.run_dir / "test-env.json"
        self.data["artifactsDir"] = str(self.run_dir / "artifacts")
        self.assertIn("outside every", self.assert_refused_without_http()["error"])

    def test_unhealthy_and_redirected_endpoints_are_rejected(self):
        for status in (503, 302):
            with self.subTest(status=status):
                self.response_status = status
                result, report = self.check()
                self.assertEqual(result.returncode, 1, report)
                self.assertIn("non-2xx", report["error"])
        self.assertEqual(self.requests, ["/ready", "/ready"])

    def test_slow_endpoint_times_out(self):
        self.response_delay = 0.3
        started = time.monotonic()
        result, report = self.check("--timeout", "0.05")
        self.assertEqual(result.returncode, 1, report)
        self.assertLess(time.monotonic() - started, 2)

    def test_external_and_malformed_urls_are_refused_before_network(self):
        urls = ["https://example.invalid/ready", "http://192.0.2.1/ready",
                "http://user:secret@127.0.0.1/ready", "file:///etc/passwd",
                "http://127.0.0.1:bad/ready", "http://127.0.0.1/ready?token=secret",
                "http://127.0.0.1/ready#token", "http://127.0.0.1\\@192.0.2.1/ready"]
        for url in urls:
            with self.subTest(url=url):
                self.data["healthUrl"] = url
                self.assert_refused_without_http()

    def test_remote_origin_requires_exact_explicit_https_authorization(self):
        spec = importlib.util.spec_from_file_location("qa_env_check", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch("socket.getaddrinfo", side_effect=AssertionError("unexpected DNS request")):
            allowed = module.allow_origins(["https://preview.example.invalid"])
            endpoint = module.validate_url("https://preview.example.invalid/ready", allowed)
            self.assertEqual(endpoint.hostname, "preview.example.invalid")
            for url in ("http://preview.example.invalid/ready",
                        "https://other.example.invalid/ready", "https://preview.example.invalid:444/ready"):
                with self.subTest(url=url), self.assertRaises(module.CheckError):
                    module.validate_url(url, allowed)

    def test_proxy_environment_does_not_redirect_local_probe(self):
        env = {**os.environ, "HTTP_PROXY": "http://192.0.2.1:9",
               "HTTPS_PROXY": "http://192.0.2.1:9", "ALL_PROXY": "http://192.0.2.1:9"}
        result, report = self.check(env=env)
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual(self.requests, ["/ready"])


if __name__ == "__main__":
    unittest.main()
