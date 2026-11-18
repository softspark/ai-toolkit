# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""GitHub issue publication tests use synthetic issues and a local fake transport."""

import argparse
import importlib.util
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "app/skills/prd-to-issues/scripts/publish_slice.py"
spec = importlib.util.spec_from_file_location("publish_slice", SCRIPT)
publisher = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = publisher
spec.loader.exec_module(publisher)
ISSUES = "repos/owner/project/issues"
BASE = "https://github.com/owner/project/issues"


def issue(number, **fields):
    return {"number": number, "id": 1000 + number, "html_url": f"{BASE}/{number}",
            "user": {"id": 7}, "title": "", "body": "", **fields}


class FakeGitHub:
    host = "github.com"

    def __init__(self):
        self.issues = {10: issue(10), 18: issue(18)}
        self.edges = []
        self.posts = []
        self.create_error = None
        self.link_error = None
        self.list_edges_error = None
        self.save_issue = True
        self.save_edge = True

    def request(self, endpoint, *, payload=None, pages=False):
        if payload is not None:
            self.posts.append((endpoint, payload))
        if endpoint == "user":
            return {"id": 7}
        if endpoint == f"{ISSUES}?state=all&per_page=100":
            assert pages
            return list(self.issues.values())
        if endpoint == ISSUES:
            number = max(self.issues) + 1
            created = issue(number, **payload)
            if self.save_issue:
                self.issues[number] = created
            if self.create_error:
                raise self.create_error
            return created
        if endpoint == f"{ISSUES}/19/dependencies/blocked_by?per_page=100":
            assert pages
            if self.list_edges_error:
                raise self.list_edges_error
            return self.edges
        if endpoint == f"{ISSUES}/19/dependencies/blocked_by":
            assert payload == {"issue_id": 1018}
            if self.save_edge:
                self.edges.append(self.issues[18])
            if self.link_error:
                raise self.link_error
            return self.issues[18]
        assert payload is None, f"Unexpected mutation: {endpoint}"
        return self.issues[int(endpoint.removeprefix(ISSUES + "/"))]


@pytest.fixture
def publication(tmp_path):
    body = tmp_path / "slice.md"
    body.write_text("**Type:** AFK\n\nBuild an export.", encoding="utf-8")
    args = argparse.Namespace(repo="owner/project", parent=10, key="export", title="Export",
                              body_file=body, blocked_by=[18], release_unapplied=None)
    api = FakeGitHub()
    with sqlite3.connect(tmp_path / "receipts.sqlite") as db:
        yield args, api, db
    db.close()


def test_normal_cli_sends_issue_id_on_child_and_checks_remote_state(monkeypatch, tmp_path, publication, capsys):
    args, api, _ = publication
    calls = []

    def fake_run(command, **kwargs):
        assert command[:4] == ["gh", "api", "--hostname", "github.com"]
        assert kwargs["timeout"] > 0
        endpoint = command[4]
        flags = command[5:]
        data = kwargs["input"]
        if data is not None:
            assert flags == ["--method", "POST", "--input", "-"]
        calls.append((endpoint, flags))
        value = api.request(endpoint, payload=json.loads(data) if data else None, pages="--paginate" in flags)
        # Simulate gh --paginate --slurp, including a result on a subsequent page.
        response = [[], value] if "--paginate" in flags else value
        return subprocess.CompletedProcess(command, 0, json.dumps(response), "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--repo", args.repo, "--parent", "10", "--key", "export",
                                     "--title", args.title, "--body-file", str(args.body_file), "--blocked-by", "18",
                                     "--receipts", str(tmp_path / "cli.sqlite"), "--host", "github.com"])
    assert publisher.main() == 0
    assert json.loads(capsys.readouterr().out)["dependencies"] == {"18": "native"}
    assert [endpoint for endpoint, _ in api.posts] == [ISSUES, f"{ISSUES}/19/dependencies/blocked_by"]
    assert api.posts[-1][1] == {"issue_id": 1018}
    assert calls[-1] == (f"{ISSUES}/19/dependencies/blocked_by?per_page=100", ["--paginate", "--slurp"])
    assert "Blocked by #18" in api.issues[19]["body"]
    assert api.issues[10] == issue(10)
    assert publisher.main() == 0
    assert len(api.posts) == 2


@pytest.mark.parametrize("status", [403, 404, 405, 410, 501])
def test_unavailable_dependency_api_preserves_verified_text(publication, status):
    args, api, db = publication
    api.list_edges_error = publisher.ApiError("Access unavailable", status)
    result = publisher.publish(args, api, db)
    assert result["dependencies"] == {18: "text-only"}
    assert "Blocked by #18" in api.issues[19]["body"]
    assert len(api.posts) == 1


def test_forbidden_edge_post_uses_prose_and_can_later_recover(publication):
    args, api, db = publication
    api.link_error = publisher.ApiError("Forbidden", 403)
    api.save_edge = False
    assert publisher.publish(args, api, db)["dependencies"] == {18: "text-only"}
    api.link_error, api.save_edge = None, True
    assert publisher.publish(args, api, db)["dependencies"] == {18: "native"}
    assert len([p for p, _ in api.posts if p == ISSUES]) == 1


def test_uncertain_posts_that_landed_are_reconciled_from_github(publication):
    args, api, db = publication
    api.create_error = api.link_error = publisher.ApiError("Timed out")
    assert publisher.publish(args, api, db)["dependencies"] == {18: "native"}
    assert len(api.posts) == 2


def test_uncertain_unconfirmed_issue_is_never_blindly_reposted(publication):
    args, api, db = publication
    api.create_error, api.save_issue = publisher.ApiError("Connection reset"), False
    with pytest.raises(publisher.ApiError):
        publisher.publish(args, api, db)
    with pytest.raises(RuntimeError, match="pending"):
        publisher.publish(args, api, db)
    assert len(api.posts) == 1


def test_overlapping_publishers_share_the_pending_create_claim(publication, tmp_path):
    args, api, db = publication
    original_request = api.request

    def interleaved_request(endpoint, **kwargs):
        if endpoint == ISSUES and kwargs.get("payload") is not None:
            with sqlite3.connect(tmp_path / "receipts.sqlite") as other:
                with pytest.raises(RuntimeError, match="pending"):
                    publisher.publish(args, api, other)
        return original_request(endpoint, **kwargs)

    api.request = interleaved_request
    assert publisher.publish(args, api, db)["number"] == 19
    assert len(api.posts) == 2


def test_authoritative_rate_rejection_can_be_retried_after_limit_lifts(publication):
    args, api, db = publication
    api.create_error, api.save_issue = publisher.ApiError("Too many requests", 429), False
    with pytest.raises(publisher.ApiError):
        publisher.publish(args, api, db)
    api.create_error, api.save_issue = None, True
    assert publisher.publish(args, api, db)["number"] == 19


def test_unconfirmed_edge_cannot_be_reported_or_reissued(publication):
    args, api, db = publication
    api.save_edge = False
    api.edges = [issue(18, id=2018)]
    with pytest.raises(RuntimeError, match="did not confirm"):
        publisher.publish(args, api, db)
    with pytest.raises(RuntimeError, match="Unconfirmed dependency"):
        publisher.publish(args, api, db)
    assert len(api.posts) == 2


@pytest.mark.parametrize(("status", "message"), [
    (403, "API rate limit exceeded"), (403, "secondary rate limit"), (429, "Too many requests"),
])
def test_rate_limit_is_an_error_not_text_fallback(publication, status, message):
    args, api, db = publication
    api.list_edges_error = publisher.ApiError(message, status)
    with pytest.raises(publisher.ApiError, match=message):
        publisher.publish(args, api, db)


def test_gh_rest_error_body_preserves_secondary_rate_limit_classification(monkeypatch):
    result = subprocess.CompletedProcess([], 1, '{"message":"Secondary rate limit exceeded"}', "gh: Forbidden (HTTP 403)")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: result)
    with pytest.raises(publisher.ApiError, match="Secondary rate limit") as error:
        publisher.GitHub("github.com").request("user")
    assert error.value.status == 403 and not error.value.unavailable()


@pytest.mark.parametrize("conflict", ["foreign", "duplicate", "different-plan", "removed-prose", "edited-title", "edited-body"])
def test_conflicting_existing_slice_is_never_mutated(publication, conflict):
    args, api, db = publication
    publisher.publish(args, api, db)
    child = api.issues[19]
    if conflict == "foreign":
        child["user"] = {"id": 99}
    elif conflict == "duplicate":
        api.issues[22] = issue(22, body=child["body"])
    elif conflict == "different-plan":
        args.title = "Different change with the same key"
    elif conflict == "edited-title":
        child["title"] = "Human title"
    elif conflict == "edited-body":
        child["body"] = child["body"].replace("Build an export.", "New requirement")
    else:
        child["body"] = child["body"].replace("Blocked by #18", "Pending")
    with sqlite3.connect(":memory:") as fresh_db:
        with pytest.raises(ValueError):
            publisher.publish(args, api, fresh_db)
    assert len(api.posts) == 2


def test_parent_and_pr_blockers_are_rejected_before_issue_creation(publication):
    args, api, db = publication
    args.blocked_by = [args.parent]
    with pytest.raises(ValueError):
        publisher.publish(args, api, db)
    args.blocked_by = [18]
    api.issues[18]["pull_request"] = {"url": BASE}
    with pytest.raises(ValueError):
        publisher.publish(args, api, db)
    assert not api.posts


def test_appended_human_notes_survive_reuse(publication):
    args, api, db = publication
    publisher.publish(args, api, db)
    api.issues[19]["body"] += "\n\nMaintainer note"
    assert publisher.publish(args, api, db)["number"] == 19
    assert api.issues[19]["body"].endswith("Maintainer note")
    assert len(api.posts) == 2


def test_removed_confirmed_dependency_requires_intent_review(publication):
    args, api, db = publication
    publisher.publish(args, api, db)
    api.edges = []
    with pytest.raises(RuntimeError, match="was removed"):
        publisher.publish(args, api, db)
    args.release_unapplied = "18"
    with pytest.raises(ValueError, match="Confirmed receipts are retained"):
        publisher.publish(args, api, db)
    assert len(api.posts) == 2


@pytest.mark.parametrize("target", ["issue", "18"])
def test_explicit_release_of_proven_unapplied_attempt_only_changes_local_receipt(publication, target):
    args, api, db = publication
    if target == "issue":
        api.save_issue = False
        api.create_error = publisher.ApiError("timeout")
    else:
        api.save_edge = False
        api.link_error = publisher.ApiError("timeout")
    with pytest.raises(publisher.ApiError, match="timeout"):
        publisher.publish(args, api, db)
    old_posts = len(api.posts)
    args.release_unapplied = target
    assert publisher.publish(args, api, db) == {"released_unapplied": target}
    assert len(api.posts) == old_posts
    api.create_error = api.link_error = None
    api.save_issue = api.save_edge = True
    args.release_unapplied = None
    assert publisher.publish(args, api, db)["dependencies"] == {18: "native"}
