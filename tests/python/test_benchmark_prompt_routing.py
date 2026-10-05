# SPDX-License-Identifier: Apache-2.0
"""Verify offline measurement and privacy boundaries against the actual hook."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark_prompt_routing import (
    DEFAULT_DATASET,
    benchmark,
    load_dataset,
    parse_category,
    percentile,
    summarize,
)


def test_diagnostic_data_declares_non_independent_synthetic_origin() -> None:
    data, digest = load_dataset(DEFAULT_DATASET)
    assert (data["origin"], data["labels"]) == ("synthetic", "developer")
    assert len(data["cases"]) == 20
    assert len(digest) == 64


@pytest.mark.parametrize("mutation", [
    {"expected_category": "unknown"}, {"language": "unknown"}, {"prompt": None},
    {"expected_skill": 12}, {"prompt": "nul\x00prompt"},
])
def test_invalid_case_is_rejected_without_echoing_prompt(tmp_path: Path, mutation: dict) -> None:
    data, _ = load_dataset(DEFAULT_DATASET)
    data["cases"][0].update(mutation)
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="case 0:"):
        load_dataset(path)


def test_confusion_and_false_positive_counts_use_unique_cases() -> None:
    cases = [{"expected_category": "none"}, {"expected_category": "debug"}, {"expected_category": "review"}]
    result = summarize(cases, ["architecture", "debug", "debug"])
    assert result["correct"] == 1
    assert result["accuracy"] == pytest.approx(1 / 3)
    assert result["false_positives"] == {"architecture": 1, "debug": 1}
    assert result["mismatched_case_indices"] == [0, 2]
    assert result["accuracy_wilson_95"][0] < result["accuracy"] < result["accuracy_wilson_95"][1]
    assert percentile([1, 2, 3, 4, 100], .95) == 100


def test_unknown_context_cannot_silently_become_none() -> None:
    with pytest.raises(ValueError, match="unrecognized"):
        parse_category(json.dumps({"hookSpecificOutput": {"additionalContext": "new format"}}), "standard")


def test_minimal_output_is_rejected_even_if_it_contains_generic_category() -> None:
    with pytest.raises(ValueError, match="minimal hook must be silent"):
        parse_category('{"hookSpecificOutput":{"additionalContext":"UserPromptSubmit: apply KB-first research,"}}', "minimal")


def test_actual_hook_benchmark_is_isolated_and_never_reports_prompts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("BASH_ENV", str(tmp_path / "must-not-source"))
    monkeypatch.setenv("AI_TOOLKIT_DISABLED_HOOKS", "user-prompt-submit")
    data, _ = load_dataset(DEFAULT_DATASET)
    data["cases"] = data["cases"][:3]
    result = benchmark(data, repeats=2, profile="standard")
    assert result["category_metrics"]["correct"] == 3
    assert result["timing_samples"] == 6
    assert result["decision"] == "Inconclusive"
    assert result["skill_suggestion_accuracy"] is None
    assert result["actual_model_skill_accuracy"] is None
    assert all(case["prompt"] not in json.dumps(result) for case in data["cases"])
    assert not (tmp_path / ".softspark").exists()


def test_minimal_profile_is_silence_check_not_perfect_category_accuracy() -> None:
    data, _ = load_dataset(DEFAULT_DATASET)
    data["cases"] = data["cases"][:1]
    result = benchmark(data, repeats=1, profile="minimal")
    assert result["category_metrics"] is None
    assert result["minimal_all_silent"] is True


def test_cli_malformed_dataset_never_echoes_private_content(tmp_path: Path) -> None:
    path = tmp_path / "private.json"
    path.write_text('{"PRIVATE_PROMPT_MARKER": invalid}')
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/benchmark_prompt_routing.py"), "--dataset", str(path)],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 2
    assert "PRIVATE_PROMPT_MARKER" not in result.stdout + result.stderr
    assert str(path) not in result.stdout + result.stderr
