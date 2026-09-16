#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Replay recorded Bash calls through rtk and judge the result against K1a, K1b and K2.

Usage (from benchmarks/):
    python3 -m token_usage.replay_rtk PROJECTS_ROOT --rtk BINARY --work DIR --out FILE [--reuse-results]

Steps, all local:

1. Extract every Bash command and the output the model saw into ``DIR/records.jsonl``
   (mode 600). ``DIR`` and ``FILE`` must lie outside this repository.
2. Refuse to run unless the binary's SHA-256 is the pinned one.
3. Run ``replay_rtk_runner.py`` in a container with no network, a read-only root,
   tmpfs for everything writable, telemetry and the recall store disabled, and
   the tee directory in tmpfs. The runner asks rtk's own Claude hook whether it
   would rewrite each command and, where the rewrite is one call with a stdin
   filter, pipes the recorded output through it.
4. Turn the measured byte reductions into token removals per tool result, simulate
   every session forward, and report the thresholds fixed before this ran:

   - **K1a** sessions without compaction: context-token reduction >= 2%, 90% CI
     lower bound > 0, still >= 2% with each of the three largest left out;
   - **K1b** sessions with compaction: no auto compaction moves earlier;
   - **K2** API-list-price-weighted usage reduction >= 2%;
   - the **retry break-even**: extra requests per 100 rewritten commands that
     would cancel the context-token saving.

Families rtk rewrites but ``rtk pipe`` cannot measure are bounded, never guessed:
lower bound 0, point estimate at the pooled measured effectiveness, upper bound
at the best measured family. ``rtk read`` counts as 0 at every level, because at
its default level it returns the file unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

from .attribute import Fit, Item, fit, in_holdout, windows
from .decompose import (
    SessionOutcome,
    Selector,
    bootstrap_interval,
    outcome,
    reduction,
    usage_categories,
    without_largest,
)
from .transcript import PERSISTED_MARKER, Session, discover_sessions, load_session, refuse_repo_path

RTK_VERSION = "0.49.0"
# rtk-aarch64-unknown-linux-gnu from the v0.49.0 release; the tarball matched the
# release's checksums.txt (c8ea4b65...1ba7) before this binary was extracted.
RTK_SHA256 = "4fa443857061b1226a21a8503112adba078a5c7ca3f7fd5919782afacf5566ca"
# python:3.12-slim-trixie. The binary needs glibc >= 2.39; bookworm ships 2.36 and
# every call fails before running, which would read as "rtk rewrites nothing".
IMAGE = "python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea"
RUNNER = Path(__file__).with_name("replay_rtk_runner.py")
ZERO_FAMILIES = frozenset({"read"})
MIN_FAMILY_SAMPLES = 20
MIN_EXTREME_SAMPLES = 5
THRESHOLD = 0.02
# lower: unmeasured rewrites save nothing. point: they save the pooled measured share.
# upper: the best family with enough samples, never below pooled. extreme: the best
# family with any usable sample count — the case least favourable to a "no".
LEVELS = ("lower", "point", "upper", "extreme")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def bash_records(path: Path) -> Iterator[dict[str, Any]]:
    """Bash command and the output the model saw, keyed by tool_use_id."""
    commands: dict[str, str] = {}
    seen: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for text in handle:
            try:
                record = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            uuid = record.get("uuid")
            if isinstance(uuid, str):
                if uuid in seen:
                    continue
                seen.add(uuid)
            content = _dict(record.get("message")).get("content")
            for block in content if isinstance(content, list) else []:
                item = _dict(block)
                if record.get("type") == "assistant" and item.get("type") == "tool_use" and item.get("name") == "Bash":
                    command = _dict(item.get("input")).get("command")
                    if isinstance(item.get("id"), str) and isinstance(command, str):
                        commands[item["id"]] = command
                elif record.get("type") == "user" and item.get("type") == "tool_result":
                    key = item.get("tool_use_id")
                    if not isinstance(key, str) or key not in commands:
                        continue
                    body = item.get("content")
                    if isinstance(body, list):
                        body = "".join(_dict(b).get("text", "") for b in body if _dict(b).get("type") == "text")
                    output = body if isinstance(body, str) else ""
                    yield {"key": key, "command": commands[key], "output": output,
                           "persisted": PERSISTED_MARKER in output}


def verify_binary(path: Path) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != RTK_SHA256:
        raise ValueError(f"rtk binary digest {digest} is not the pinned {RTK_VERSION} digest {RTK_SHA256}")


def write_records(sessions: Sequence[Session], out: Path) -> int:
    count = 0
    refuse_repo_path(out)
    with open(os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as sink:
        for session in sessions:
            for transcript in (session.main, *session.subagents):
                for record in bash_records(transcript.path):
                    sink.write(json.dumps(record) + "\n")
                    count += 1
    return count


def run_container(records: Path, work: Path, rtk_binary: Path) -> Path:
    results = work / "results.jsonl"
    command = [
        "docker", "run", "--rm", "--network", "none", "--read-only",
        "--tmpfs", "/tmp", "-e", "HOME=/tmp/h", "-e", "XDG_DATA_HOME=/tmp/xdg", "-e", "XDG_CONFIG_HOME=/tmp/xdgc",
        "-e", "RTK_TELEMETRY_DISABLED=1", "-e", "RTK_RECALL=0", "-e", "RTK_TEE_DIR=/tmp/tee",
        "-v", f"{rtk_binary.resolve()}:/opt/rtk/rtk:ro",
        "-v", f"{RUNNER.resolve()}:/opt/replay/runner.py:ro",
        "-v", f"{records.resolve()}:/in/records.jsonl:ro",
        "-v", f"{work.resolve()}:/out",
        IMAGE, "python3", "/opt/replay/runner.py", "/in/records.jsonl", "/out/results.jsonl",
    ]
    subprocess.run(command, check=True)
    return results


@dataclass(frozen=True, slots=True)
class FamilyEffect:
    samples: int
    raw_bytes: int
    removed_bytes: int
    removed_whitespace: int

    @property
    def effectiveness(self) -> float:
        return self.removed_bytes / self.raw_bytes if self.raw_bytes else 0.0


def family_effects(results: Sequence[dict[str, Any]]) -> dict[str, FamilyEffect]:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for r in results:
        if r.get("filtered_bytes") is None:
            continue
        raw, kept = int(r["raw_bytes"]), int(r["filtered_bytes"])
        removed = max(0, raw - kept)
        ws_removed = max(0, int(r["raw_whitespace"]) - int(r["filtered_whitespace"])) if removed else 0
        row = totals[str(r["filter"])]
        row[0] += 1
        row[1] += raw
        row[2] += removed
        row[3] += min(ws_removed, removed)
    return {name: FamilyEffect(*row) for name, row in totals.items()}


def removal_fractions(results: Sequence[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Share of each Bash result's tokens removed, at every level in ``LEVELS``."""
    effects = family_effects(results)
    measured_raw = sum(e.raw_bytes for e in effects.values())
    pooled = sum(e.removed_bytes for e in effects.values()) / measured_raw if measured_raw else 0.0
    best = max([pooled, *(e.effectiveness for e in effects.values() if e.samples >= MIN_FAMILY_SAMPLES)])
    extreme = max([best, *(e.effectiveness for e in effects.values() if e.samples >= MIN_EXTREME_SAMPLES)])
    fractions: dict[str, dict[str, float]] = {}
    for r in results:
        key = str(r.get("key"))
        if not r.get("rewritten") or not r.get("raw_bytes"):
            continue
        if r.get("filtered_bytes") is not None:
            share = max(0.0, 1.0 - int(r["filtered_bytes"]) / int(r["raw_bytes"]))
            fractions[key] = {level: share for level in LEVELS}
        elif set(r.get("families", [])) <= ZERO_FAMILIES:
            fractions[key] = {level: 0.0 for level in LEVELS}
        else:
            fractions[key] = {"lower": 0.0, "point": pooled, "upper": best, "extreme": extreme}
    return fractions


def bash_selector(fractions: dict[str, dict[str, float]], level: str) -> Selector:
    def select(item: Item) -> float:
        if item.kind != "tool_result" or item.category != "bash" or item.tool_use_id is None:
            return 0.0
        return fractions.get(item.tool_use_id, {}).get(level, 0.0)
    return select


def _k1(outcomes: Sequence[SessionOutcome]) -> dict[str, Any]:
    plain = [o for o in outcomes if not o.compactions_observed]
    compacting = [o for o in outcomes if o.compactions_observed]
    low, high = bootstrap_interval(plain) if plain else (0.0, 0.0)
    leave_out = without_largest(plain)
    k1a = reduction(plain)
    earliest = min((o.earliest_shift for o in compacting), default=0)
    return {
        "k1a": {
            "sessions": len(plain),
            "reduction": round(k1a, 5),
            "ci90": [round(low, 5), round(high, 5)],
            "without_each_top3": [round(v, 5) for v in leave_out],
            "pass": k1a >= THRESHOLD and low > 0 and all(v >= THRESHOLD for v in leave_out),
        },
        "k1b": {
            "sessions": len(compacting),
            "auto_compaction_delay_requests": sum(o.auto_delay_requests for o in compacting),
            "auto_compactions_avoided": sum(o.auto_avoided for o in compacting),
            "earliest_shift_requests": earliest,
            "context_token_change_reported_only": round(-reduction(compacting), 5),
            "pass": earliest >= 0,
        },
    }


def verdict(sessions: Sequence[Session], model: Fit, results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    fractions = removal_fractions(results)
    rewritten = sum(1 for r in results if r.get("rewritten"))
    report: dict[str, Any] = {}
    for level in LEVELS:
        select = bash_selector(fractions, level)
        per_bound: dict[str, Any] = {}
        for bound in ("lower", "upper"):
            outcomes = [outcome(s, model, select, bound) for s in sessions]
            saved = sum(o.observed - o.counterfactual for o in outcomes)
            per_request = sum(o.observed for o in outcomes) / max(1, sum(o.requests for o in outcomes))
            per_bound[bound] = {
                **_k1(outcomes),
                "retry_break_even_per_100_rewrites": round(100 * saved / per_request / rewritten, 3)
                if rewritten and per_request else 0.0,
            }
        usage = usage_categories(sessions, model, select)
        k2 = usage["api_price_weighted_reduction"]
        report[level] = {"threshold_bounds": per_bound, "k2": {"reduction": k2, "pass": k2 >= THRESHOLD}}
    return report


def coverage(results: Sequence[dict[str, Any]], model: Fit) -> dict[str, Any]:
    total_bytes = sum(int(r.get("raw_bytes", 0)) for r in results)
    rewritten = [r for r in results if r.get("rewritten")]
    by_family: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in rewritten:
        name = "+".join(r.get("families", [])) if r.get("rtk_calls", 0) == 1 else "multiple-rtk-calls"
        by_family[name][0] += 1
        by_family[name][1] += int(r.get("raw_bytes", 0))
    measured = sum(int(r["raw_bytes"]) for r in rewritten if r.get("filtered_bytes") is not None)
    rewritten_bytes = sum(int(r.get("raw_bytes", 0)) for r in rewritten)
    effects = family_effects(results)
    return {
        "bash_results": len(results),
        "rewritten": len(rewritten),
        "rewritten_byte_share": round(rewritten_bytes / total_bytes, 4) if total_bytes else 0.0,
        "measured_share_of_rewritten_bytes": round(measured / rewritten_bytes, 4) if rewritten_bytes else 0.0,
        "hook_failures": sum(1 for r in results if r.get("hook_rc") not in (0, None)),
        "pipe_failures": sum(1 for r in results if r.get("pipe_rc") not in (0, None)),
        "by_family": {
            k: {"count": v[0], "byte_share_of_rewritten": round(v[1] / rewritten_bytes, 4) if rewritten_bytes else 0.0}
            for k, v in sorted(by_family.items(), key=lambda kv: -kv[1][1])[:15]
        },
        "measured_effectiveness": {
            name: {"samples": e.samples, "removed_byte_share": round(e.effectiveness, 4),
                   "whitespace_share_of_removed": round(e.removed_whitespace / e.removed_bytes, 4)
                   if e.removed_bytes else 0.0}
            for name, e in sorted(effects.items(), key=lambda kv: -kv[1].raw_bytes)
        },
        "bash_tokens_per_byte": round(model.rate_for("bash"), 4),
    }


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Replay recorded Bash calls through rtk.")
    parser.add_argument("root")
    parser.add_argument("--rtk", required=True, help="the pinned linux aarch64 rtk binary")
    parser.add_argument("--work", required=True, help="private working directory outside the repository")
    parser.add_argument("--out", required=True, help="report path outside the repository")
    parser.add_argument("--reuse-results", action="store_true", help="aggregate an existing results.jsonl")
    args = parser.parse_args(argv)

    work = refuse_repo_path(Path(args.work).expanduser())
    out = refuse_repo_path(Path(args.out).expanduser())
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    sessions = [load_session(p) for p in discover_sessions(Path(args.root).expanduser())]
    results_path = work / "results.jsonl"
    if not args.reuse_results:
        verify_binary(Path(args.rtk))
        records = work / "records.jsonl"
        write_records(sessions, records)
        results_path = run_container(records, work, Path(args.rtk))
        os.chmod(results_path, 0o600)
    results = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    all_windows = [w for s in sessions for t in (s.main, *s.subagents) for w in windows(t)]
    model = fit([w for w in all_windows if not in_holdout(w)])
    report = {
        "label": "exploratory; n below any convergence target",
        "rtk_version": RTK_VERSION,
        "coverage": coverage(results, model),
        "verdict": verdict(sessions, model, results),
    }
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.chmod(out, 0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
