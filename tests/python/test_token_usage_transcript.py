# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Tests for benchmarks/token_usage/transcript.py.

Every fixture is synthetic. Where a test asserts a deduplicated figure, it also
asserts that the naive per-line figure differs, so the fixture provably
exercises the defect the parser exists to avoid: a test that would pass against
the naive parser proves nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

BENCH = Path(__file__).resolve().parents[2] / "benchmarks"
sys.path.insert(0, str(BENCH))

from token_usage.transcript import (  # noqa: E402
    discover_sessions,
    load_session,
    parse_transcript,
    refuse_repo_path,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def usage(inp: int, cache_create: int, cache_read: int, out: int, **extra: Any) -> dict[str, Any]:
    return {
        "input_tokens": inp,
        "cache_creation_input_tokens": cache_create,
        "cache_read_input_tokens": cache_read,
        "output_tokens": out,
        "cache_creation": {"ephemeral_5m_input_tokens": 0, "ephemeral_1h_input_tokens": cache_create},
        **extra,
    }


def assistant(uuid: str, request_id: str | None, model: str, content: list[dict[str, Any]],
              use: dict[str, Any], **extra: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "type": "assistant",
        "uuid": uuid,
        "timestamp": "2026-09-16T10:00:00Z",
        "message": {"id": f"msg-{request_id}", "model": model, "content": content, "usage": use},
        **extra,
    }
    if request_id is not None:
        record["requestId"] = request_id
    return record


MAIN_LINES: list[Any] = [
    {"type": "user", "uuid": "u1", "message": {"role": "user", "content": "hi"}},
    # One request written as two block lines; the earlier line carries a partial output count.
    assistant("a1", "r1", "claude-opus-5", [{"type": "thinking", "thinking": ""}], usage(5, 1000, 0, 3)),
    assistant("a2", "r1", "claude-opus-5",
              [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "git status"}}],
              usage(5, 1000, 0, 40)),
    {"type": "user", "uuid": "u2",
     "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "On branch main\n"}]},
     "toolUseResult": {"stdout": "On branch main\n"}},
    # The same record written twice.
    {"type": "user", "uuid": "u2",
     "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "On branch main\n"}]},
     "toolUseResult": {"stdout": "On branch main\n"}},
    {"type": "attachment", "uuid": "x1", "attachment": {"type": "output_style"}},
    # A skill body: stored as an isMeta user record, enters context, typed by nobody.
    {"type": "user", "uuid": "u6", "isMeta": True, "message": {"content": [{"type": "text", "text": "# Skill body"}]}},
    assistant("a3", "r2", "claude-opus-5",
              [{"type": "tool_use", "id": "t3", "name": "Bash", "input": {"command": "cat big.log"}}],
              usage(2, 200, 1000, 50)),
    # A persisted preview that carries the marker but no toolUseResult.persistedOutputPath.
    {"type": "user", "uuid": "u5",
     "message": {"content": [{"type": "tool_result", "tool_use_id": "t3",
                              "content": "<persisted-output>\nOutput too large. Preview:\n..."}]}},
    # An API error placeholder: no requestId, zero usage.
    assistant("a4", None, "<synthetic>", [{"type": "text", "text": "err"}], usage(0, 0, 0, 0)),
    {"type": "system", "subtype": "compact_boundary", "uuid": "s1",
     "compactMetadata": {"trigger": "auto", "preTokens": 1250, "postTokens": 100}},
    {"type": "user", "uuid": "u3", "isCompactSummary": True, "message": {"content": "summary"}},
    assistant("a5", "r3", "claude-fable-5-1",
              [{"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "x"}}],
              usage(1, 120, 0, 10)),
    {"type": "user", "uuid": "u4",
     "message": {"content": [{"type": "tool_result", "tool_use_id": "t2", "is_error": True, "content": [
         {"type": "text", "text": "abc"},
         {"type": "image", "source": {"type": "base64", "data": "AAAA"}},
     ]}]},
     "toolUseResult": {"persistedOutputPath": "tool-results/x.txt", "persistedOutputSize": 90000}},
    assistant("a6", "r4", "claude-fable-5-1", [{"type": "text", "text": "done"}],
              usage(1, 10, 120, 5, iterations=[{"type": "fallback_message"}, {"type": "message"}])),
    "not json at all",
]

SUB_LINES: list[Any] = [
    assistant("b1", "r9", "claude-opus-5", [{"type": "text", "text": "sub"}], usage(3, 500, 0, 7),
              isSidechain=True, agentId="x"),
]


def write_jsonl(path: Path, lines: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(line if isinstance(line, str) else json.dumps(line) for line in lines) + "\n")


@pytest.fixture()
def corpus(tmp_path: Path) -> Path:
    project = tmp_path / "projects" / "-proj"
    write_jsonl(project / "sess-1.jsonl", MAIN_LINES)
    write_jsonl(project / "sess-1" / "subagents" / "agent-x.jsonl", SUB_LINES)
    (project / "sess-1" / "subagents" / "agent-x.meta.json").write_text(
        json.dumps({"agentType": "Explore", "toolUseId": "t1"}))
    return tmp_path / "projects"


def naive_output_sum(lines: list[Any]) -> int:
    total = 0
    for line in lines:
        if isinstance(line, dict) and line.get("type") == "assistant":
            total += line["message"]["usage"]["output_tokens"]
    return total


def test_requests_are_counted_once_per_request_id(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    assert [r.request_id for r in transcript.requests] == ["r1", "r2", "r3", "r4"]
    assert transcript.stats.assistant_lines == 6
    assert transcript.stats.synthetic == 1


def test_output_takes_the_final_block_count_not_the_sum(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    r1 = transcript.requests[0]
    assert (r1.input_tokens, r1.cache_creation_tokens, r1.cache_read_tokens, r1.output_tokens) == (5, 1000, 0, 40)
    assert r1.context_tokens == 1005
    parsed = sum(r.output_tokens for r in transcript.requests)
    assert parsed == 105
    assert naive_output_sum(MAIN_LINES) != parsed


def test_repeated_uuid_is_read_once(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    assert transcript.stats.duplicate_uuids == 1
    assert [t.tool_use_id for t in transcript.tool_results] == ["t1", "t3", "t2"]


def test_tool_results_are_linked_and_measured(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    bash, preview, read = transcript.tool_results
    assert (bash.tool_name, bash.request_id, bash.text_bytes, bash.image_count) == ("Bash", "r1", 15, 0)
    assert transcript.tool_uses["t1"].command == "git status"
    assert (read.tool_name, read.text_bytes, read.image_count, read.image_bytes) == ("Read", 3, 1, 4)
    assert read.is_error and read.persisted and not bash.persisted


def test_persisted_preview_is_recognised_by_its_marker_alone(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    preview = transcript.tool_results[1]
    assert (preview.tool_use_id, preview.tool_name, preview.request_id) == ("t3", "Bash", "r2")
    assert preview.persisted


def test_compaction_attachments_models_and_malformed_lines(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    (compaction,) = transcript.compactions
    assert (compaction.trigger, compaction.pre_tokens, compaction.post_tokens) == ("auto", 1250, 100)
    assert compaction.order < transcript.requests[2].order
    assert [a.type for a in transcript.attachments] == ["output_style"]
    assert transcript.model_switches == 1
    assert transcript.stats.multi_iteration == 1
    assert transcript.stats.malformed == 1


def test_prompts_exclude_meta_results_and_compaction_summaries(corpus: Path) -> None:
    transcript = parse_transcript(corpus / "-proj" / "sess-1.jsonl")
    assert [(p.order, p.text_bytes) for p in transcript.prompts] == [(0, 2)]
    assert [p.text_bytes for p in transcript.meta_messages] == [len("# Skill body")]


def test_subagents_attach_to_their_parent_tool_use(corpus: Path) -> None:
    session = load_session(corpus / "-proj" / "sess-1.jsonl")
    (sub,) = session.subagents
    assert (sub.agent_id, sub.parent_tool_use_id) == ("x", "t1")
    assert [r.request_id for r in sub.requests] == ["r9"]
    assert session.main.agent_id is None


def test_discovery_does_not_mistake_subagents_for_sessions(corpus: Path) -> None:
    assert [p.name for p in discover_sessions(corpus)] == ["sess-1.jsonl"]


def test_survey_reports_aggregates_without_identities(corpus: Path) -> None:
    from token_usage.survey import survey

    report = survey(corpus)
    assert report["requests"]["distinct_requests"] == 5
    assert report["requests"]["lines_per_request"] == round(6 / 5, 3)
    assert report["context"]["top1_share"] == 1.0
    assert report["compactions"]["by_trigger"] == {"auto": 1}
    rendered = json.dumps(report)
    for private in ("sess-1", "git status", "cat big.log", "On branch main", "-proj", "agent-x"):
        assert private not in rendered


def test_output_paths_inside_the_repository_are_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        refuse_repo_path(REPO_ROOT / "benchmarks" / "results.json")
    assert refuse_repo_path(tmp_path / "out.json") == tmp_path / "out.json"
