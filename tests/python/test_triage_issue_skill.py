# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Verify the published triage instructions and CLI examples across native exports."""

from pathlib import Path
import shlex
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from codex_skill_adapter import build_codex_skill_text, build_opencode_skill_text  # noqa: E402
from generate_copilot import _render_skill_markdown  # noqa: E402


@pytest.fixture(params=["claude", "codex", "opencode", "copilot"])
def skill(request):
    source = ROOT / "app/skills/triage-issue/SKILL.md"
    if request.param == "copilot":
        return _render_skill_markdown(source.parent)[1]
    if request.param == "codex":
        return build_codex_skill_text(source)
    if request.param == "opencode":
        return build_opencode_skill_text(source)
    return source.read_text(encoding="utf-8")


def gh_commands(text):
    return [shlex.split(line) for line in text.splitlines() if line.startswith("gh ")]


def test_existing_issue_route_preserves_input_forms_and_read_only_commands(skill):
    usage, body = skill.split("## Existing issue\n", 1)
    existing, _ = body.split("## New bug report\n", 1)
    for argument in ("#42", "42", "https://github.com/owner/repo/issues/42"):
        assert f"/triage-issue {argument}\n" in usage

    view, paginate = gh_commands(existing)
    assert view[:5] == ["gh", "issue", "view", "$issue_ref", "--json"]
    assert {"url", "number", "title", "body", "author", "comments", "state", "stateReason"} <= set(view[5].split(","))
    assert paginate == ["gh", "api", "--hostname", "$host", "--paginate",
                        "repos/$repo/issues/$number/comments?per_page=100"]
    assert "read-only by default" in existing
    assert "reporter's latest follow-up" in existing
    assert "support, design or scope decision" in existing


def test_new_report_checks_existing_issues_before_filing_in_the_same_repository(skill):
    _, new_report = skill.split("## New bug report\n", 1)
    search, create = gh_commands(new_report)
    assert search[:3] == ["gh", "issue", "list"]
    assert search[search.index("--state") + 1] == "all"
    assert search[search.index("--search") + 1] == "$search_terms"
    assert create[:3] == ["gh", "issue", "create"]
    assert search[search.index("--repo") + 1] == create[create.index("--repo") + 1] == "$repo"
    assert "--title" in create and "--body-file" in create
    assert "existing-issue branch" in new_report
    assert "## TDD Fix Plan" in new_report
