# SPDX-License-Identifier: Apache-2.0
"""Offline baseline of the actual prompt hook; never echo prompt contents."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "app/hooks/user-prompt-submit.sh"
DEFAULT_DATASET = ROOT / "benchmarks/prompt-routing/diagnostic.json"
CATEGORIES = ("architecture", "debug", "plan", "review", "none")
MAX_CASES = 1000
MAX_BYTES = 10_000_000
MAX_PROMPT_LENGTH = 100_000
HOOK_TIMEOUT_SECONDS = 2


def load_dataset(path: Path) -> tuple[dict[str, Any], str]:
    """Require explicit provenance; labels are assertions, not verified truth."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("dataset exceeds byte limit")
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("dataset requires schema_version 1")
    if data.get("origin") not in ("synthetic", "natural"):
        raise ValueError("origin must be synthetic or natural")
    if data.get("labels") not in ("developer", "independent"):
        raise ValueError("labels must be developer or independent")
    cases = data.get("cases")
    if not isinstance(cases, list) or not 1 <= len(cases) <= MAX_CASES:
        raise ValueError("dataset requires 1..1000 cases")
    for index, case in enumerate(cases):
        validate_case(case, index)
    return data, hashlib.sha256(raw).hexdigest()


def validate_case(case: Any, index: int) -> None:
    if not isinstance(case, dict):
        raise TypeError(f"case {index}: expected object")
    prompt = case.get("prompt")
    if not isinstance(prompt, str) or len(prompt) > MAX_PROMPT_LENGTH or "\x00" in prompt:
        raise ValueError(f"case {index}: invalid prompt")
    if case.get("expected_category") not in CATEGORIES:
        raise ValueError(f"case {index}: invalid category")
    if case.get("language") not in ("pl", "en", "mixed", "neutral"):
        raise ValueError(f"case {index}: invalid language")
    if "expected_skill" not in case or not (
        case["expected_skill"] is None or isinstance(case["expected_skill"], str)
    ):
        raise ValueError(f"case {index}: expected_skill must be a string or null")


def parse_category(output: str, profile: str) -> str:
    if profile == "minimal":
        if output.strip():
            raise ValueError("minimal hook must be silent")
        return "none"
    payload = json.loads(output)
    context = payload["hookSpecificOutput"]["additionalContext"]
    markers = {
        "architecture": "UserPromptSubmit: task looks architectural or multi-step.",
        "debug": "UserPromptSubmit: debugging request detected.",
        "none": "UserPromptSubmit: apply KB-first research,",
    }
    matches = [category for category, marker in markers.items() if marker in context]
    if len(matches) != 1:
        raise ValueError("unrecognized hook context; update the output adapter explicitly")
    return matches[0]


def run_case(prompt: str, *, profile: str, directory: str) -> tuple[str, float]:
    # Fresh environment prevents user hooks, BASH_ENV, search-provider detection,
    # and real session state from affecting this controlled measurement.
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": directory,
        "TMPDIR": directory,
        "LC_ALL": "C",
        "TOOLKIT_HOOK_PROFILE": profile,
        "AI_TOOLKIT_HOOK_FORMAT": "json",
        "AI_TOOLKIT_SEARCH_FIRST": "off",
    }
    started = time.perf_counter_ns()
    result = subprocess.run(
        ["bash", str(HOOK)], input=json.dumps({"prompt": prompt, "session_id": "benchmark"}),
        text=True, capture_output=True, cwd=directory, env=environment,
        timeout=HOOK_TIMEOUT_SECONDS, check=False,
    )
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    if result.returncode != 0 or result.stderr:
        # Neither stdout nor stderr is safe to include in an error report.
        raise ValueError("hook failed or emitted diagnostics")
    return parse_category(result.stdout, profile), elapsed_ms


def percentile(values: list[float], fraction: float) -> float:
    """Nearest-rank percentile, including process startup and JSON I/O."""
    return round(sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)], 3)


def accuracy_interval(correct: int, total: int) -> list[float]:
    """Wilson 95% interval; synthetic observations remain non-representative."""
    proportion = correct / total
    z = 1.959963984540054
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total**2)) / denominator
    return [round(center - radius, 6), round(center + radius, 6)]


def summarize(cases: list[dict[str, Any]], predictions: list[str]) -> dict[str, Any]:
    matrix = {expected: dict.fromkeys(CATEGORIES, 0) for expected in CATEGORIES}
    for case, predicted in zip(cases, predictions, strict=True):
        matrix[case["expected_category"]][predicted] += 1
    correct = sum(matrix[category][category] for category in CATEGORIES)
    return {
        "case_count": len(cases), "correct": correct, "accuracy": correct / len(cases),
        "accuracy_wilson_95": accuracy_interval(correct, len(cases)),
        "confusion_expected_rows_predicted_columns": matrix,
        "false_positives": {
            category: sum(matrix[expected][category] for expected in CATEGORIES if expected != category)
            for category in ("architecture", "debug")
        },
        "mismatched_case_indices": [
            index for index, (case, prediction) in enumerate(zip(cases, predictions, strict=True))
            if case["expected_category"] != prediction
        ],
    }


def benchmark(data: dict[str, Any], *, repeats: int, profile: str) -> dict[str, Any]:
    if not 1 <= repeats <= 5 or profile not in ("standard", "minimal"):
        raise ValueError("invalid run options")
    cases = data["cases"]
    predictions: list[str] = []
    timings: list[float] = []
    with tempfile.TemporaryDirectory(prefix="prompt-routing-") as directory:
        for case in cases:
            observed = []
            for _ in range(repeats):
                prediction, elapsed = run_case(case["prompt"], profile=profile, directory=directory)
                observed.append(prediction)
                timings.append(elapsed)
            if len(set(observed)) != 1:
                raise ValueError("non-deterministic hook output")
            predictions.append(observed[0])
    return {
        "category_metrics": summarize(cases, predictions) if profile == "standard" else None,
        "minimal_all_silent": all(value == "none" for value in predictions) if profile == "minimal" else None,
        "latency_ms": {"p50": percentile(timings, 0.5), "p95": percentile(timings, 0.95)},
        "timing_samples": len(timings),
        "timing_scope": "whole bash subprocess; sequential fresh processes; no cold/warm inference distinction",
        "language_counts": dict(Counter(case["language"] for case in cases)),
        "no_expected_skill_count": sum(case["expected_skill"] is None for case in cases),
        "skill_suggestion_accuracy": None,
        "actual_model_skill_accuracy": None,
        "decision": "Inconclusive",
        "limitations": [
            "Baseline only; no candidate comparison or G-ROUTE decision.",
            "Provenance is declared by the dataset author, not independently verified by this runner.",
            "Current hook emits no skill suggestion; no model invocation or Skill telemetry is observed.",
            "Search-first off isolates category context; configured production search-provider detection is not timed.",
            "Synthetic fixture accuracy and Wilson intervals do not estimate natural-prompt performance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--repeats", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--profile", choices=("standard", "minimal"), default="standard")
    args = parser.parse_args()
    try:
        if not shutil.which("bash") or not shutil.which("jq"):
            raise ValueError("bash and jq are required")
        data, digest = load_dataset(args.dataset)
        report = benchmark(data, repeats=args.repeats, profile=args.profile)
        report.update({
            "schema_version": 1, "dataset_sha256": digest,
            "origin": data["origin"], "labels": data["labels"], "profile": args.profile,
            "hook_sha256": hashlib.sha256(HOOK.read_bytes()).hexdigest(),
            "hook_dependency_sha256": {
                name: hashlib.sha256((HOOK.parent / name).read_bytes()).hexdigest()
                for name in ("_profile-check.sh", "_hook-io.sh", "_search-capability.sh", "_prompt-intent.py")
            },
            "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
            "python": platform.python_version(),
        })
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
        print("Prompt-routing benchmark failed: check dataset schema, dependencies and hook output. No prompt logged.", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
