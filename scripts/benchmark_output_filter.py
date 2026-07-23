#!/usr/bin/env python3
"""Deterministic offline benchmarks for native output profiles."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from tool_output_filter.profiles import apply_profile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = (
    REPOSITORY_ROOT / "benchmarks" / "output-filter" / "scenarios.json"
)
MEMORY_ALLOWANCE_BYTES = 16 * 1024 * 1024
COLD_HOOK_INPUT_BYTES = 4 * 1024
COLD_HOOK_MAX_P95_MS = 75.0
DEFAULT_ITERATIONS = 100
HOOK_RUNTIME = REPOSITORY_ROOT / "scripts" / "output_filter_hook.py"
HOOK_SCRIPT = REPOSITORY_ROOT / "app" / "hooks" / "filter-tool-output.sh"


def _repeat_output(target_bytes: int, line_width: int) -> str:
    prefix = "synthetic progress "
    line = prefix + ("x" * max(1, line_width - len(prefix) - 1)) + "\n"
    count = math.ceil(target_bytes / len(line.encode("utf-8")))
    return line * count


def _tap_output(test_count: int) -> str:
    result_lines = [
        f"ok {number} - synthetic benchmark case {number}\n"
        for number in range(1, test_count + 1)
    ]
    return "".join(
        [
            "TAP version 13\n",
            f"1..{test_count}\n",
            *result_lines,
            f"# tests {test_count}\n",
            f"# pass {test_count}\n",
            "# fail 0\n",
            "# duration_ms 1\n",
        ]
    )


def _integer_field(scenario: dict[str, object], key: str) -> int:
    value = scenario.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"benchmark field {key} must be an integer")
    return value


def _number_field(scenario: dict[str, object], key: str) -> float:
    value = scenario.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"benchmark field {key} must be numeric")
    return float(value)


def _string_field(scenario: dict[str, object], key: str) -> str:
    value = scenario.get(key)
    if not isinstance(value, str):
        raise ValueError(f"benchmark field {key} must be text")
    return value


def _scenario_input(scenario: dict[str, object]) -> str:
    kind = _string_field(scenario, "kind")
    if kind == "repeat":
        return _repeat_output(
            _integer_field(scenario, "targetBytes"),
            _integer_field(scenario, "lineWidth"),
        )
    if kind == "tap":
        return _tap_output(_integer_field(scenario, "testCount"))
    raise ValueError(f"unknown benchmark kind: {kind}")


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _measure_scenario(
    scenario: dict[str, object],
    iterations: int,
) -> dict[str, object]:
    raw_output = _scenario_input(scenario)
    profile_id = _string_field(scenario, "profile")
    scenario_name = _string_field(scenario, "name")
    durations: list[float] = []
    candidate = apply_profile(profile_id, raw_output)
    if candidate is None or not candidate.accepted:
        raise RuntimeError(f"profile rejected benchmark {scenario_name}")

    for _ in range(iterations):
        started = time.perf_counter_ns()
        measured = apply_profile(profile_id, raw_output)
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
        if measured != candidate:
            raise RuntimeError(
                f"non-deterministic benchmark {scenario_name}"
            )

    tracemalloc.start()
    apply_profile(profile_id, raw_output)
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    input_bytes = len(raw_output.encode("utf-8"))
    candidate_bytes = len(candidate.output.encode("utf-8"))
    savings_ratio = (input_bytes - candidate_bytes) / input_bytes
    p95_ms = _p95(durations)
    memory_limit = input_bytes * 3 + MEMORY_ALLOWANCE_BYTES
    passed = (
        candidate_bytes < input_bytes
        and savings_ratio >= 0.3
        and p95_ms <= _number_field(scenario, "maxP95Ms")
        and peak_bytes <= memory_limit
    )
    return {
        "name": scenario_name,
        "profile": profile_id,
        "inputBytes": input_bytes,
        "candidateBytes": candidate_bytes,
        "savingsRatio": round(savings_ratio, 4),
        "p95Ms": round(p95_ms, 3),
        "peakBytes": peak_bytes,
        "memoryLimitBytes": memory_limit,
        "passed": passed,
    }


def _hook_policy(mode: str) -> dict[str, object]:
    return {
        "mode": mode,
        "profiles": ["repeat-lines"],
        "maxInputBytes": 8 * 1024 * 1024,
        "minSavingsBytes": 1024,
        "minSavingsRatio": 0.15,
        "recovery": {
            "mode": "ephemeral",
            "ttlMinutes": 60,
            "maxSessionBytes": 32 * 1024 * 1024,
        },
    }


def _hook_payload(raw_output: str, session_id: str) -> str:
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "session_id": session_id,
        "cwd": str(REPOSITORY_ROOT),
        "tool_input": {"command": "npm test"},
        "tool_response": {
            "stdout": raw_output,
            "stderr": "",
            "interrupted": False,
            "isImage": False,
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _hook_session_root(temporary_home: Path) -> Path:
    repo_key = "-" + str(REPOSITORY_ROOT).replace("/", "-").lstrip("-")
    return (
        temporary_home
        / ".softspark"
        / "ai-toolkit"
        / "sessions"
        / repo_key
    )


def _run_cold_hook(
    payload: str,
    environment: dict[str, str],
) -> tuple[float, int]:
    started = time.perf_counter_ns()
    result = subprocess.run(
        ["bash", str(HOOK_SCRIPT)],
        input=payload,
        text=True,
        capture_output=True,
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
    )
    duration_ms = (time.perf_counter_ns() - started) / 1_000_000
    if result.returncode != 0 or result.stderr:
        raise RuntimeError("cold hook invocation failed")
    if result.stdout:
        raise RuntimeError("observe hook unexpectedly changed output")
    return duration_ms, len(result.stdout.encode("utf-8"))


def _measure_cold_hook(
    iterations: int,
    mode: str = "observe",
) -> dict[str, object]:
    raw_output = _repeat_output(COLD_HOOK_INPUT_BYTES, 96)
    input_bytes = len(raw_output.encode("utf-8"))
    durations: list[float] = []
    emitted_sizes: list[int] = []
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        policy_path = temporary_path / "policy.json"
        policy_path.write_text(
            json.dumps(_hook_policy(mode), separators=(",", ":")),
            encoding="utf-8",
        )
        temporary_home = temporary_path / "home"
        session_root = _hook_session_root(temporary_home)
        session_root.mkdir(parents=True, mode=0o700)
        session_root.chmod(0o700)
        environment = {
            **os.environ,
            "HOME": str(temporary_home),
            "PYTHONPYCACHEPREFIX": str(temporary_path / "pycache"),
            "AI_TOOLKIT_DISABLED_HOOKS": "",
            "AI_TOOLKIT_OUTPUT_FILTER_HOOK_RUNTIME": str(HOOK_RUNTIME),
            "AI_TOOLKIT_OUTPUT_FILTER_DISABLE": "0",
            "AI_TOOLKIT_OUTPUT_FILTER_POLICY": str(policy_path),
            "TOOLKIT_HOOK_PROFILE": "standard",
        }
        environment.pop("PYTHONDONTWRITEBYTECODE", None)
        session_id = "benchmark-session"
        for iteration in range(iterations):
            duration_ms, emitted_bytes = _run_cold_hook(
                _hook_payload(raw_output, session_id),
                environment,
            )
            durations.append(duration_ms)
            emitted_sizes.append(emitted_bytes)
        if mode == "observe":
            telemetry_files = list(session_root.rglob(".telemetry.jsonl"))
            if len(telemetry_files) != 1:
                raise RuntimeError(
                    "cold hook did not complete observe telemetry"
                )
            telemetry_lines = telemetry_files[0].read_text(
                encoding="ascii",
            ).splitlines()
            if len(telemetry_lines) != iterations:
                raise RuntimeError(
                    "cold hook telemetry event count is incomplete"
                )
    p95_ms = _p95(durations)
    emitted_bytes = max(emitted_sizes)
    return {
        "name": "claude-hook-cold-4k",
        "mode": mode,
        "adapter": "bash-wrapper",
        "sessionReused": True,
        "iterations": iterations,
        "inputBytes": input_bytes,
        "emittedBytes": emitted_bytes,
        "p95Ms": round(p95_ms, 3),
        "maxP95Ms": COLD_HOOK_MAX_P95_MS,
        "passed": (
            emitted_bytes < input_bytes
            and p95_ms <= COLD_HOOK_MAX_P95_MS
        ),
    }


def _load_corpus(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as corpus_file:
        data = json.load(corpus_file)
    if not isinstance(data, list):
        raise ValueError("benchmark corpus must be an array")
    return data


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--max-input-bytes", type=int)
    parser.add_argument("--report-cold-hook-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.iterations <= 0:
        return 2
    scenarios = []
    for definition in _load_corpus(args.corpus):
        raw_size = len(_scenario_input(definition).encode("utf-8"))
        if args.max_input_bytes is not None and raw_size > args.max_input_bytes:
            continue
        scenarios.append(_measure_scenario(definition, args.iterations))
    cold_hook = _measure_cold_hook(args.iterations)
    profile_gates_passed = bool(scenarios) and all(
        scenario["passed"] for scenario in scenarios
    )
    cold_hook_enforced = not args.report_cold_hook_only
    report = {
        "passed": (
            profile_gates_passed
            and (
                cold_hook["passed"]
                or not cold_hook_enforced
            )
        ),
        "scenarios": scenarios,
        "coldHook": cold_hook,
        "coldHookEnforced": cold_hook_enforced,
    }
    if args.json:
        print(json.dumps(report, separators=(",", ":")))
    else:
        for scenario in scenarios:
            print(
                f"{scenario['name']}: p95={scenario['p95Ms']}ms "
                f"savings={scenario['savingsRatio']} "
                f"peak={scenario['peakBytes']} passed={scenario['passed']}"
            )
        print(
            f"{cold_hook['name']}: p95={cold_hook['p95Ms']}ms "
            f"emitted={cold_hook['emittedBytes']} "
            f"passed={cold_hook['passed']}"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
