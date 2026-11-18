# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Privacy boundary of the per-repository generated handoff."""

from pathlib import Path
from runpy import run_path
import stat

import pytest


HOOK = Path(__file__).resolve().parents[2] / "app/hooks/_session-handoff.py"
HANDOFF = run_path(str(HOOK))


def test_later_sensitive_value_withdraws_prior_field_and_code_fences_do_not_publish():
    lines = (
        "## Checkpoint test", "Decision: earlier choice", "Next action: Run smoke tests",
        "Decision: customer@example.test", "````markdown", "```",
        "Next action: private fenced instruction", "````", "Unrecognised: private prose",
        "Artifacts: kb/howto/setup.md", "Objective: " + "w" * 401,
    )
    assert list(HANDOFF["checkpoint_fields"](lines)) == [
        "\n## Checkpoint", "- Next action: Run smoke tests", "- Artifacts: kb/howto/setup.md",
    ]


def test_only_recent_checkpoints_are_kept():
    count = HANDOFF["MAX_CHECKPOINTS"]
    lines = [line for i in range(count + 2)
             for line in ("## Checkpoint", f"Next action: review fixture {i}")]
    fields = list(HANDOFF["checkpoint_fields"](lines))
    assert fields.count("\n## Checkpoint") == count
    assert "- Next action: review fixture 0" not in fields
    assert f"- Next action: review fixture {count + 1}" in fields


@pytest.mark.parametrize("prefix", ["npm_", "glpat-"])
def test_unlabelled_package_and_tracker_credentials_omit_entire_field(prefix):
    value = prefix + "x" * 32
    lines = ["## Checkpoint", "Decision: use " + value, "Next action: run checks"]
    assert list(HANDOFF["checkpoint_fields"](lines)) == ["\n## Checkpoint", "- Next action: run checks"]


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_nonregular_checkpoint_is_omitted_and_previous_raw_summary_replaced(tmp_path, kind):
    checkpoints = tmp_path / "session-context.md.checkpoints"
    if kind == "directory":
        checkpoints.mkdir()
    else:
        other = tmp_path / "unrelated.md"
        other.write_text("## Checkpoint\nDecision: Should stay private")
        checkpoints.symlink_to(other)
    summary = tmp_path / "session-context.md"
    summary.write_text("# Session Context\n## Last Assistant Message\nPrivate reply")
    HANDOFF["write_summary"](tmp_path, "example-session", "7ac834d", "2")
    saved = summary.read_text()
    assert "Private reply" not in saved and "Should stay private" not in saved
    assert "example-session" not in saved
    assert "Commit: 7ac834d" in saved and "Uncommitted paths: 2" in saved
    assert stat.S_IMODE(summary.stat().st_mode) == 0o600
