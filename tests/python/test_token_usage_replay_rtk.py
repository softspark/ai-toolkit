# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Tests for benchmarks/token_usage/replay_rtk.py and its container-side runner.

The runner is exercised against a fake ``rtk`` that rewrites ``git status`` and
strips spaces in ``pipe``, so the plumbing — hook parsing, filter choice, sizes,
and the absence of any command or output text in the results — is tested without
the real binary or a container.
"""
from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[2] / "benchmarks"
sys.path.insert(0, str(BENCH))

from token_usage import replay_rtk_runner as runner  # noqa: E402
from token_usage.attribute import Item  # noqa: E402
from token_usage.replay_rtk import (  # noqa: E402
    bash_records,
    bash_selector,
    family_effects,
    removal_fractions,
    verify_binary,
    write_records,
)

FAKE_RTK = """#!/bin/sh
if [ "$1" = "hook" ]; then
  input=$(cat)
  case "$input" in
    *'git status'*) printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{"command":"cd x && rtk git status"}}}' ;;
    *'"cat notes.txt"'*) printf '%s' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","updatedInput":{"command":"rtk read notes.txt"}}}' ;;
  esac
  exit 0
fi
if [ "$1" = "pipe" ]; then tr -d ' '; exit 0; fi
exit 1
"""


@pytest.fixture()
def fake_rtk(tmp_path: Path) -> str:
    path = tmp_path / "rtk"
    path.write_text(FAKE_RTK)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def test_invocations_families_and_filters() -> None:
    calls = runner.invocations("cd /x && rtk git status -s && rtk grep -rn foo . | head")
    assert calls == [("git", "status"), ("grep", None)]
    assert [runner.family(*c) for c in calls] == ["git status", "grep"]
    assert [runner.pipe_filter(*c) for c in calls] == ["git-status", "grep"]
    assert runner.pipe_filter("gh", "pr") is None
    assert runner.invocations("echo rtkfoo && myrtk ls") == []


def test_hook_output_parsing() -> None:
    assert runner.rewritten_command("") is None
    assert runner.rewritten_command("not json") is None
    assert runner.rewritten_command('{"hookSpecificOutput":{"updatedInput":{"command":"rtk ls"}}}') == "rtk ls"


def test_replay_reports_sizes_and_families_only(fake_rtk: str) -> None:
    secret_command = "cd /private/secret-repo && git status --porcelain"
    secret_output = "On branch  secret-branch  now"
    result = runner.replay({"key": "t1", "command": secret_command, "output": secret_output}, rtk=fake_rtk)
    assert result["rewritten"] and result["families"] == ["git status"] and result["filter"] == "git-status"
    assert result["raw_bytes"] == len(secret_output)
    assert result["filtered_bytes"] == len(secret_output.replace(" ", ""))
    rendered = json.dumps(result)
    assert "secret" not in rendered
    assert "private" not in rendered and "porcelain" not in rendered

    untouched = runner.replay({"key": "t2", "command": "make build", "output": "ok"}, rtk=fake_rtk)
    assert not untouched["rewritten"] and untouched["filtered_bytes"] is None


def test_fractions_bound_unmeasured_families_and_zero_rtk_read() -> None:
    results = [
        {"key": f"m{i}", "rewritten": True, "rtk_calls": 1, "families": ["git status"], "filter": "git-status",
         "raw_bytes": 1000, "raw_whitespace": 300, "filtered_bytes": 700, "filtered_whitespace": 50}
        for i in range(25)
    ] + [
        {"key": "g1", "rewritten": True, "rtk_calls": 1, "families": ["grep"], "filter": "grep",
         "raw_bytes": 1000, "raw_whitespace": 0, "filtered_bytes": 900, "filtered_whitespace": 0},
        {"key": "u1", "rewritten": True, "rtk_calls": 1, "families": ["gh pr"], "filter": None,
         "raw_bytes": 500, "raw_whitespace": 0, "filtered_bytes": None, "filtered_whitespace": None},
        {"key": "r1", "rewritten": True, "rtk_calls": 1, "families": ["read"], "filter": None,
         "raw_bytes": 5000, "raw_whitespace": 0, "filtered_bytes": None, "filtered_whitespace": None},
        {"key": "n1", "rewritten": False, "rtk_calls": 0, "families": [], "filter": None,
         "raw_bytes": 800, "raw_whitespace": 0, "filtered_bytes": None, "filtered_whitespace": None},
    ]
    effects = family_effects(results)
    assert effects["git-status"].effectiveness == pytest.approx(0.3)
    assert effects["git-status"].removed_whitespace == 25 * 250
    fractions = removal_fractions(results)
    assert fractions["m0"] == pytest.approx({"lower": 0.3, "point": 0.3, "upper": 0.3, "extreme": 0.3})
    pooled = (25 * 300 + 100) / (25 * 1000 + 1000)
    # grep has 1 sample, below both minimums, so git-status is the best family at every level.
    assert fractions["u1"] == pytest.approx({"lower": 0.0, "point": pooled, "upper": 0.3, "extreme": 0.3})
    assert fractions["r1"] == {"lower": 0.0, "point": 0.0, "upper": 0.0, "extreme": 0.0}
    assert "n1" not in fractions

    select = bash_selector(fractions, "upper")
    assert select(Item(kind="tool_result", category="bash", text_bytes=500, tool_use_id="u1")) == pytest.approx(0.3)
    assert select(Item(kind="tool_result", category="rag-mcp", text_bytes=500, tool_use_id="u1")) == 0.0


def test_upper_never_falls_below_pooled_and_extreme_reaches_small_families() -> None:
    def row(key: str, name: str, raw: int, kept: int) -> dict[str, object]:
        return {"key": key, "rewritten": True, "rtk_calls": 1, "families": [name], "filter": name,
                "raw_bytes": raw, "raw_whitespace": 0, "filtered_bytes": kept, "filtered_whitespace": 0}

    results = [row(f"g{i}", "grep", 1000, 850) for i in range(30)]  # 15%, enough samples
    results += [row(f"l{i}", "git-log", 10000, 2500) for i in range(6)]  # 75%, few samples, many bytes
    results.append({"key": "u", "rewritten": True, "rtk_calls": 2, "families": ["git status", "git diff"],
                    "filter": None, "raw_bytes": 900, "raw_whitespace": 0, "filtered_bytes": None,
                    "filtered_whitespace": None})
    unmeasured = removal_fractions(results)["u"]
    pooled = (30 * 150 + 6 * 7500) / (30 * 1000 + 6 * 10000)
    assert unmeasured["point"] == pytest.approx(pooled)
    assert unmeasured["upper"] == pytest.approx(pooled)  # the eligible best (15%) is below pooled
    assert unmeasured["extreme"] == pytest.approx(0.75)
    assert unmeasured["lower"] <= unmeasured["point"] <= unmeasured["upper"] <= unmeasured["extreme"]


def test_bash_records_link_commands_and_skip_duplicates(tmp_path: Path) -> None:
    lines = [
        {"type": "assistant", "uuid": "a1", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "git status"}},
            {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "x"}}]}},
        {"type": "user", "uuid": "u1", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": "clean"}]}]}},
        {"type": "user", "uuid": "u1", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "clean"}]}},
        {"type": "user", "uuid": "u2", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t2", "content": "file body"}]}},
    ]
    path = tmp_path / "s.jsonl"
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")
    assert list(bash_records(path)) == [{"key": "t1", "command": "git status", "output": "clean", "persisted": False}]


def test_binary_and_output_guards(tmp_path: Path) -> None:
    fake = tmp_path / "rtk"
    fake.write_bytes(b"not rtk")
    with pytest.raises(ValueError):
        verify_binary(fake)
    with pytest.raises(ValueError):
        write_records([], BENCH / "token_usage" / "records.jsonl")
    assert not (BENCH / "token_usage" / "records.jsonl").exists()
