from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.tool_output_filter import (
    FilterMode,
    FilterRequest,
    RecoveryStore,
    SessionCircuitBreaker,
    TelemetrySink,
    filter_output,
)


def raw_response_for(output: str) -> dict[str, object]:
    return {
        "stdout": output,
        "stderr": "",
        "interrupted": False,
        "isImage": False,
    }


class MemoryRecoveryStore(RecoveryStore):
    def __init__(self) -> None:
        self.values: dict[str, object] = {}

    def save(self, output: object) -> str:
        handle = "fixed-handle"
        self.values[handle] = output
        return handle

    def load(self, handle: str) -> object | None:
        return self.values.get(handle)

    def delete(self, handle: str) -> None:
        self.values.pop(handle, None)


class FailingRecoveryStore(RecoveryStore):
    def __init__(self) -> None:
        self.save_calls = 0

    def save(self, output: object) -> str:
        self.save_calls += 1
        raise OSError("disk unavailable")

    def load(self, handle: str) -> object | None:
        raise AssertionError("load must not run after save failed")

    def delete(self, handle: str) -> None:
        raise AssertionError("delete must not run without a handle")


class LongHandleRecoveryStore(MemoryRecoveryStore):
    def __init__(self) -> None:
        super().__init__()
        self.deleted: list[str] = []

    def save(self, output: object) -> str:
        handle = "h" * 512
        self.values[handle] = output
        return handle

    def delete(self, handle: str) -> None:
        super().delete(handle)
        self.deleted.append(handle)


class RecordingTelemetrySink(TelemetrySink):
    def __init__(self) -> None:
        self.events = []

    def record(self, event) -> None:
        self.events.append(event)


class ToolOutputFilterTests(unittest.TestCase):
    def test_off_mode_returns_exact_raw_output(self) -> None:
        raw_output = "żółć\x1b[31m\nsame line\nsame line\n\n"
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.OFF,
            profile_id="repeat-lines",
        )

        result = filter_output(request)

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("disabled", result.outcome)

    def test_observe_mode_reports_candidate_without_changing_output(self) -> None:
        raw_output = ("downloaded dependency\n" * 80) + "complete\n"
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.OBSERVE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request)

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("observed", result.outcome)
        self.assertEqual("repeat-lines", result.telemetry.profile_id)
        self.assertLess(result.telemetry.output_bytes, result.telemetry.input_bytes)

    def test_safe_mode_replaces_output_only_after_exact_recovery(self) -> None:
        raw_output = ("downloaded dependency\n" * 80) + "complete\n"
        recovery = MemoryRecoveryStore()
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=recovery)

        self.assertTrue(result.changed)
        self.assertEqual("replaced", result.outcome)
        self.assertEqual(
            raw_response_for(raw_output),
            recovery.load("fixed-handle"),
        )
        self.assertIn("recovery=fixed-handle", result.output)
        self.assertLess(
            len(result.output.encode("utf-8")),
            len(raw_output.encode("utf-8")),
        )

    def test_safe_mode_without_recovery_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request)

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("recovery-unavailable", result.fallback_reason)

    def test_failed_execution_returns_exact_raw_output(self) -> None:
        raw_output = "fatal: same\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            successful=False,
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("execution-failed", result.fallback_reason)

    def test_non_empty_stderr_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            stderr="warning from tool\n",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("stderr-present", result.fallback_reason)

    def test_interrupted_execution_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            interrupted=True,
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("execution-interrupted", result.fallback_reason)

    def test_output_over_hard_input_cap_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 10
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            max_input_bytes=8,
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("input-too-large", result.fallback_reason)

    def test_terminal_and_binary_controls_return_exact_raw_output(
        self,
    ) -> None:
        controls = (
            "\x00binary",
            "\x07bell",
            "\x1b[31mansi\x1b[0m",
            "\x1b]0;osc-title\x07",
            "\x7fdelete",
            "\x9bc1-csi",
            "progress\rreplacement",
        )
        for control in controls:
            with self.subTest(control=repr(control)):
                raw_output = ("same\n" * 500) + control + "\n"
                recovery = MemoryRecoveryStore()
                request = FilterRequest(
                    output=raw_output,
                    raw_response=raw_response_for(raw_output),
                    mode=FilterMode.SAFE,
                    profile_id="repeat-lines",
                    min_savings_bytes=1,
                    min_savings_ratio=0.01,
                )

                result = filter_output(request, recovery=recovery)

                self.assertEqual(raw_output, result.output)
                self.assertFalse(result.changed)
                self.assertEqual(
                    "unsupported-control-sequence",
                    result.fallback_reason,
                )
                self.assertEqual({}, recovery.values)

    def test_crlf_and_tab_are_eligible_text_controls(self) -> None:
        raw_output = ("same\tvalue\r\n" * 500) + "complete\r\n"
        recovery = MemoryRecoveryStore()
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=recovery)

        self.assertTrue(result.changed)
        self.assertEqual("replaced", result.outcome)

    def test_unknown_profile_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="unknown",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("unknown-profile", result.fallback_reason)

    def test_repeat_lines_does_not_collapse_diagnostics(self) -> None:
        raw_output = "ERROR: database unavailable\n" * 100
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("insufficient-savings", result.fallback_reason)

    def test_repeat_lines_treats_existing_filter_markers_as_immutable(self) -> None:
        marker = (
            "[ai-toolkit-output-filter repeat-lines/v1: "
            "9 adjacent copies omitted]\n"
        )
        raw_output = marker * 100
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("insufficient-savings", result.fallback_reason)

    def test_recovery_exception_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=FailingRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("recovery-failed", result.fallback_reason)

    def test_observe_reports_metadata_without_output_content(self) -> None:
        secret = "SECRET-CANARY-DO-NOT-RECORD"
        raw_output = (f"{secret}\n" * 200) + "complete\n"
        telemetry = RecordingTelemetrySink()
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.OBSERVE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, telemetry=telemetry)

        self.assertEqual(raw_output, result.output)
        self.assertEqual(1, len(telemetry.events))
        serialized_event = repr(telemetry.events[0].as_dict())
        self.assertNotIn(secret, serialized_event)
        self.assertEqual("observed", telemetry.events[0].outcome)

    def test_never_worse_gate_discards_recovery_and_returns_raw(self) -> None:
        raw_output = "x\n" * 100
        recovery = LongHandleRecoveryStore()
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=recovery)

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("never-worse", result.fallback_reason)
        self.assertEqual(1, len(recovery.deleted))

    def test_never_worse_gate_does_not_count_as_safety_failure(self) -> None:
        raw_output = "x\n" * 100
        recovery = LongHandleRecoveryStore()
        circuit_breaker = SessionCircuitBreaker()
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(
            request,
            recovery=recovery,
            circuit_breaker=circuit_breaker,
        )

        self.assertEqual("never-worse", result.fallback_reason)
        self.assertEqual(0, circuit_breaker.consecutive_failures)

    def test_unicode_line_separator_is_rejected_as_control(self) -> None:
        raw_output = ("A " * 500) + "\u2028suffix"
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.OBSERVE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request)

        self.assertEqual(raw_output, result.output)
        self.assertEqual(
            "unsupported-control-sequence",
            result.fallback_reason,
        )

    def test_safe_mode_without_raw_response_returns_exact_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("raw-response-unavailable", result.fallback_reason)

    def test_safe_mode_round_trips_entire_raw_response_object(self) -> None:
        raw_output = "same\n" * 500
        raw_response = {
            "stdout": raw_output,
            "stderr": "",
            "interrupted": False,
            "isImage": False,
            "nativeMetadata": {"requestId": "local-only"},
        }
        recovery = MemoryRecoveryStore()
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=recovery)

        self.assertTrue(result.changed)
        self.assertEqual(raw_response, recovery.load("fixed-handle"))

    def test_three_runtime_failures_open_session_circuit_breaker(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )
        recovery = FailingRecoveryStore()
        circuit_breaker = SessionCircuitBreaker()

        for _ in range(3):
            filter_output(
                request,
                recovery=recovery,
                circuit_breaker=circuit_breaker,
            )
        result = filter_output(
            request,
            recovery=recovery,
            circuit_breaker=circuit_breaker,
        )

        self.assertEqual(raw_output, result.output)
        self.assertEqual("circuit-open", result.fallback_reason)
        self.assertEqual(3, recovery.save_calls)

    def test_profile_exception_returns_exact_raw_output_and_counts_failure(
        self,
    ) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.OBSERVE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )
        circuit_breaker = SessionCircuitBreaker()

        with patch(
            "scripts.tool_output_filter.engine.apply_profile",
            side_effect=RuntimeError("synthetic profile failure"),
        ):
            result = filter_output(
                request,
                circuit_breaker=circuit_breaker,
            )

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("profile-failed", result.fallback_reason)
        self.assertEqual(1, circuit_breaker.consecutive_failures)

    def test_tap_success_compacts_ok_lines_and_preserves_metadata(self) -> None:
        ordinary_results = [
            f"ok {number} - synthetic case {number}\n"
            for number in range(1, 200)
        ]
        raw_output = "".join(
            [
                "TAP version 13\n",
                "1..200\n",
                *ordinary_results,
                "ok 200 - optional case # SKIP unavailable locally\n",
                "# tests 200\n",
                "# pass 200\n",
                "# duration_ms 42.5\n",
            ]
        )
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="tap-success",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertTrue(result.changed)
        self.assertIn("TAP version 13", result.output)
        self.assertIn("1..200", result.output)
        self.assertIn("# SKIP unavailable locally", result.output)
        self.assertIn("# tests 200", result.output)
        self.assertIn("# duration_ms 42.5", result.output)
        self.assertNotIn("synthetic case 100", result.output)
        self.assertIn("tap-success/v1", result.output)

    def test_tap_diagnostic_comment_returns_exact_raw_output(self) -> None:
        raw_output = "".join(
            [
                "TAP version 13\n",
                "1..3\n",
                "ok 1 - first\n",
                "# error: flaky cleanup detected\n",
                "ok 2 - second\n",
                "ok 3 - third\n",
            ]
        )
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="tap-success",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("profile-rejected", result.fallback_reason)

    def test_tap_nonzero_failure_summary_returns_exact_raw_output(self) -> None:
        result_lines = [
            f"ok {number} - synthetic case {number}\n"
            for number in range(1, 101)
        ]
        raw_output = "".join(
            [
                "TAP version 13\n",
                "1..100\n",
                *result_lines,
                "# tests 100\n",
                "# pass 99\n",
                "# fail 1\n",
            ]
        )
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="tap-success",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("profile-rejected", result.fallback_reason)

    def test_tap_inconsistent_pass_summary_returns_exact_raw_output(
        self,
    ) -> None:
        result_lines = [
            f"ok {number} - synthetic case {number}\n"
            for number in range(1, 101)
        ]
        raw_output = "".join(
            [
                "TAP version 13\n",
                "1..100\n",
                *result_lines,
                "# tests 100\n",
                "# pass 99\n",
                "# fail 0\n",
            ]
        )
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="tap-success",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("profile-rejected", result.fallback_reason)

    def test_repeat_lines_preserves_blank_layout_lines(self) -> None:
        raw_output = "\n" * 500
        request = FilterRequest(
            output=raw_output,
            raw_response=raw_response_for(raw_output),
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request, recovery=MemoryRecoveryStore())

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("insufficient-savings", result.fallback_reason)


if __name__ == "__main__":
    unittest.main()
