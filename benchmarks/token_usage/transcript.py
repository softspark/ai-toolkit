# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Parse Claude Code session transcripts into requests, tool results and compactions.

A transcript is not a list of API requests. Claude Code writes one JSONL line per
content block, and every line of a request repeats that request's usage block, so
summing usage per line counts a multi-block request once per block. On a real
corpus that is 9901 assistant lines for 5214 requests. This module groups lines
by ``requestId`` (falling back to ``message.id``) and reads each request once:

- input and cache fields are identical across a request's lines;
- ``output_tokens`` is partial on earlier lines, so the maximum is taken;
- ``<synthetic>`` records are API-error placeholders with zero usage and are
  skipped;
- a record written twice under the same ``uuid`` is read once.

Tool results are measured from ``tool_result.content`` — what the model saw —
not from ``toolUseResult``, which can hold the full output of a result the model
only received as a persisted preview. A preview is recognised by its
``<persisted-output>`` marker, not only by ``persistedOutputPath``. Subagents live in separate files under
``<session>/subagents/`` and are attached through their ``meta.toolUseId``.

Stdlib only. Nothing here writes a file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNTHETIC_MODEL = "<synthetic>"
# A result too large to inline reaches the model as a preview wrapped in this
# marker. Only some of those records also carry toolUseResult.persistedOutputPath
# (3 of 12 on the September corpus), so the marker is the reliable signal.
PERSISTED_MARKER = "<persisted-output>"


@dataclass(frozen=True, slots=True)
class Request:
    request_id: str
    order: int
    model: str
    timestamp: str
    input_tokens: int
    cache_creation_tokens: int
    cache_creation_1h_tokens: int
    cache_read_tokens: int
    output_tokens: int
    iterations: int

    @property
    def context_tokens(self) -> int:
        """Input-side size of the request: the formula behind ``context_window.used_percentage``."""
        return self.input_tokens + self.cache_creation_tokens + self.cache_read_tokens


@dataclass(frozen=True, slots=True)
class ToolUse:
    tool_use_id: str
    name: str
    request_id: str
    order: int
    command: str | None


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_use_id: str
    tool_name: str
    request_id: str
    order: int
    text_bytes: int
    image_count: int
    image_bytes: int
    tool_reference_count: int
    is_error: bool
    persisted: bool


@dataclass(frozen=True, slots=True)
class Compaction:
    order: int
    trigger: str
    pre_tokens: int
    post_tokens: int


@dataclass(frozen=True, slots=True)
class Attachment:
    order: int
    type: str


@dataclass(frozen=True, slots=True)
class Prompt:
    """A user-authored message: not a tool result, not meta, not a compaction summary."""

    order: int
    text_bytes: int


@dataclass(frozen=True, slots=True)
class ParseStats:
    lines: int
    malformed: int
    duplicate_uuids: int
    assistant_lines: int
    synthetic: int
    multi_iteration: int


@dataclass(frozen=True, slots=True)
class Transcript:
    path: Path
    agent_id: str | None
    parent_tool_use_id: str | None
    requests: tuple[Request, ...]
    tool_uses: dict[str, ToolUse]
    tool_results: tuple[ToolResult, ...]
    compactions: tuple[Compaction, ...]
    attachments: tuple[Attachment, ...]
    prompts: tuple[Prompt, ...]
    # isMeta user records: skill bodies, expanded slash commands. Their text is
    # stored and enters context like a prompt, though no human typed it.
    meta_messages: tuple[Prompt, ...]
    stats: ParseStats

    @property
    def model_switches(self) -> int:
        return sum(1 for prev, cur in zip(self.requests, self.requests[1:]) if prev.model != cur.model)


@dataclass(frozen=True, slots=True)
class Session:
    main: Transcript
    subagents: tuple[Transcript, ...] = field(default_factory=tuple)


@dataclass(slots=True)
class _RequestDraft:
    request_id: str
    order: int
    model: str
    timestamp: str
    usage: dict[str, Any]
    output_tokens: int
    iterations: int


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _measure_result_content(content: Any) -> tuple[int, int, int, int, bool]:
    """Return (text_bytes, image_count, image_bytes, tool_reference_count, persisted_marker)."""
    if isinstance(content, str):
        return len(content.encode("utf-8")), 0, 0, 0, PERSISTED_MARKER in content
    text_bytes = image_count = image_bytes = references = 0
    marker = False
    if isinstance(content, list):
        for item in content:
            block = _dict(item)
            kind = block.get("type")
            if kind == "text":
                text = block.get("text")
                if isinstance(text, str):
                    text_bytes += len(text.encode("utf-8"))
                    marker = marker or PERSISTED_MARKER in text
            elif kind == "image":
                image_count += 1
                data = _dict(block.get("source")).get("data")
                image_bytes += len(data) if isinstance(data, str) else 0
            elif kind == "tool_reference":
                references += 1
    return text_bytes, image_count, image_bytes, references, marker


def parse_transcript(path: Path, *, agent_id: str | None = None,
                     parent_tool_use_id: str | None = None) -> Transcript:
    drafts: dict[str, _RequestDraft] = {}
    tool_uses: dict[str, ToolUse] = {}
    raw_results: list[tuple[int, dict[str, Any], bool]] = []
    compactions: list[Compaction] = []
    attachments: list[Attachment] = []
    prompts: list[Prompt] = []
    meta_messages: list[Prompt] = []
    seen_uuids: set[str] = set()
    lines = malformed = duplicates = assistant_lines = synthetic = 0

    with path.open(encoding="utf-8") as handle:
        for order, text in enumerate(handle):
            if not text.strip():
                continue
            lines += 1
            try:
                record = json.loads(text)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if not isinstance(record, dict):
                malformed += 1
                continue
            uuid = record.get("uuid")
            if isinstance(uuid, str):
                if uuid in seen_uuids:
                    duplicates += 1
                    continue
                seen_uuids.add(uuid)

            kind = record.get("type")
            if kind == "assistant":
                assistant_lines += 1
                message = _dict(record.get("message"))
                model = message.get("model")
                if model == SYNTHETIC_MODEL:
                    synthetic += 1
                    continue
                key = record.get("requestId") or message.get("id")
                if not isinstance(key, str):
                    malformed += 1
                    continue
                use = _dict(message.get("usage"))
                iterations = use.get("iterations")
                draft = drafts.get(key)
                if draft is None:
                    draft = _RequestDraft(
                        request_id=key, order=order, model=model if isinstance(model, str) else "",
                        timestamp=str(record.get("timestamp", "")), usage=use,
                        output_tokens=0, iterations=0,
                    )
                    drafts[key] = draft
                draft.output_tokens = max(draft.output_tokens, _int(use.get("output_tokens")))
                draft.iterations = max(draft.iterations, len(iterations) if isinstance(iterations, list) else 0)
                content = message.get("content")
                for block in content if isinstance(content, list) else []:
                    item = _dict(block)
                    if item.get("type") != "tool_use" or not isinstance(item.get("id"), str):
                        continue
                    command = _dict(item.get("input")).get("command")
                    tool_uses[item["id"]] = ToolUse(
                        tool_use_id=item["id"], name=str(item.get("name", "")), request_id=key,
                        order=order, command=command if isinstance(command, str) else None,
                    )
            elif kind == "user":
                content = _dict(record.get("message")).get("content")
                persisted = "persistedOutputPath" in _dict(record.get("toolUseResult"))
                has_result = False
                for block in content if isinstance(content, list) else []:
                    item = _dict(block)
                    if item.get("type") == "tool_result":
                        raw_results.append((order, item, persisted))
                        has_result = True
                if not has_result and not record.get("isCompactSummary"):
                    prompt_bytes, _, _, _, _ = _measure_result_content(content)
                    if prompt_bytes:
                        target = meta_messages if record.get("isMeta") else prompts
                        target.append(Prompt(order=order, text_bytes=prompt_bytes))
            elif kind == "system" and record.get("subtype") == "compact_boundary":
                meta = _dict(record.get("compactMetadata"))
                compactions.append(Compaction(
                    order=order, trigger=str(meta.get("trigger", "")),
                    pre_tokens=_int(meta.get("preTokens")), post_tokens=_int(meta.get("postTokens")),
                ))
            elif kind == "attachment":
                attachments.append(Attachment(order=order, type=str(_dict(record.get("attachment")).get("type", ""))))

    requests = tuple(
        Request(
            request_id=d.request_id, order=d.order, model=d.model, timestamp=d.timestamp,
            input_tokens=_int(d.usage.get("input_tokens")),
            cache_creation_tokens=_int(d.usage.get("cache_creation_input_tokens")),
            cache_creation_1h_tokens=_int(_dict(d.usage.get("cache_creation")).get("ephemeral_1h_input_tokens")),
            cache_read_tokens=_int(d.usage.get("cache_read_input_tokens")),
            output_tokens=d.output_tokens, iterations=d.iterations,
        )
        for d in sorted(drafts.values(), key=lambda d: d.order)
    )

    results: list[ToolResult] = []
    for order, item, persisted in raw_results:
        tool_use_id = item.get("tool_use_id")
        use_record = tool_uses.get(tool_use_id) if isinstance(tool_use_id, str) else None
        text_bytes, image_count, image_bytes, references, marker = _measure_result_content(item.get("content"))
        results.append(ToolResult(
            tool_use_id=str(tool_use_id), tool_name=use_record.name if use_record else "",
            request_id=use_record.request_id if use_record else "", order=order,
            text_bytes=text_bytes, image_count=image_count, image_bytes=image_bytes,
            tool_reference_count=references, is_error=item.get("is_error") is True,
            persisted=persisted or marker,
        ))

    return Transcript(
        path=path, agent_id=agent_id, parent_tool_use_id=parent_tool_use_id, requests=requests,
        tool_uses=tool_uses, tool_results=tuple(results), compactions=tuple(compactions),
        attachments=tuple(attachments), prompts=tuple(prompts), meta_messages=tuple(meta_messages),
        stats=ParseStats(
            lines=lines, malformed=malformed, duplicate_uuids=duplicates, assistant_lines=assistant_lines,
            synthetic=synthetic, multi_iteration=sum(1 for r in requests if r.iterations > 1),
        ),
    )


def load_session(main_path: Path) -> Session:
    """Parse a main transcript and every subagent transcript written under it."""
    subagents: list[Transcript] = []
    subagent_dir = main_path.parent / main_path.stem / "subagents"
    if subagent_dir.is_dir():
        for path in sorted(subagent_dir.glob("agent-*.jsonl")):
            agent_id = path.stem.removeprefix("agent-")
            meta_path = path.with_name(f"{path.stem}.meta.json")
            parent: str | None = None
            if meta_path.is_file():
                try:
                    tool_use_id = _dict(json.loads(meta_path.read_text(encoding="utf-8"))).get("toolUseId")
                except json.JSONDecodeError:
                    tool_use_id = None
                parent = tool_use_id if isinstance(tool_use_id, str) else None
            subagents.append(parse_transcript(path, agent_id=agent_id, parent_tool_use_id=parent))
    return Session(main=parse_transcript(main_path), subagents=tuple(subagents))


def discover_sessions(projects_root: Path) -> list[Path]:
    """Main transcripts only: ``<project>/<session>.jsonl``, never the subagent files beneath."""
    return sorted(
        path
        for project in projects_root.iterdir() if project.is_dir()
        for path in project.glob("*.jsonl")
    )


def refuse_repo_path(path: Path) -> Path:
    """Reject an output path inside this repository: ``benchmarks/`` and ``kb/`` ship to npm."""
    resolved = path.expanduser().resolve()
    if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
        raise ValueError(f"refusing to write measurement output inside the repository: {resolved}")
    return path
