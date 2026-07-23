from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.tool_output_filter import FilterMode, FilterRequest, filter_output
from scripts.tool_output_filter.input import (
    load_bounded_json,
    read_bounded_text,
)
from scripts.tool_output_filter.profiles import apply_profile


class ToolOutputFilterPropertyTests(unittest.TestCase):
    def test_oversized_json_is_rejected_before_decoder_runs(self) -> None:
        decoder = Mock(side_effect=AssertionError("decoder must not run"))

        result = load_bounded_json(
            io.BytesIO(b"x" * 17),
            max_bytes=16,
            decoder=decoder,
        )

        self.assertIsNone(result)
        decoder.assert_not_called()

    def test_bounded_text_stops_after_one_byte_beyond_limit(self) -> None:
        stream = Mock(wraps=io.BytesIO(b"x" * 32))

        result = read_bounded_text(stream, max_bytes=16)

        self.assertIsNone(result)
        requested = sum(
            call.args[0] for call in stream.read.call_args_list
        )
        self.assertEqual(17, requested)

    def test_bounded_text_reassembles_short_reads(self) -> None:
        class OneByteStream:
            def __init__(self, data: bytes) -> None:
                self._buffer = io.BytesIO(data)

            def read(self, size: int) -> bytes:
                return self._buffer.read(min(1, size))

        result = read_bounded_text(OneByteStream(b"hello"), max_bytes=16)

        self.assertEqual("hello", result)

    def test_profiles_are_deterministic_and_idempotent(self) -> None:
        repeat_input = ("same progress line\n" * 200) + "complete\n"
        tap_input = "".join(
            [
                "TAP version 13\n",
                "1..100\n",
                *[
                    f"ok {number} - property case {number}\n"
                    for number in range(1, 101)
                ],
                "# tests 100\n",
                "# pass 100\n",
                "# fail 0\n",
            ]
        )

        for profile_id, raw_output in (
            ("repeat-lines", repeat_input),
            ("tap-success", tap_input),
        ):
            with self.subTest(profile=profile_id):
                first = apply_profile(profile_id, raw_output)
                duplicate = apply_profile(profile_id, raw_output)
                second = apply_profile(profile_id, first.output)

                self.assertTrue(first.accepted)
                self.assertEqual(first, duplicate)
                self.assertEqual(first.output, second.output)

    def test_invalid_unicode_returns_exact_raw_output(self) -> None:
        raw_output = "\ud800same\n" * 100
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
        self.assertEqual("invalid-text", result.fallback_reason)

    def test_image_response_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            is_image=True,
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request)

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("unsupported-media", result.fallback_reason)

    def test_streaming_response_returns_exact_raw_output(self) -> None:
        raw_output = "same\n" * 500
        request = FilterRequest(
            output=raw_output,
            mode=FilterMode.SAFE,
            profile_id="repeat-lines",
            is_streaming=True,
            min_savings_bytes=1,
            min_savings_ratio=0.01,
        )

        result = filter_output(request)

        self.assertEqual(raw_output, result.output)
        self.assertFalse(result.changed)
        self.assertEqual("unsupported-stream", result.fallback_reason)

    def test_fixture_corpus_matches_profile_oracle_and_has_provenance(self) -> None:
        fixture_root = (
            Path(__file__).parent / "fixtures" / "output-filter"
        )
        case_paths = sorted(fixture_root.glob("*/case.json"))

        self.assertEqual(4, len(case_paths))
        for case_path in case_paths:
            with self.subTest(case=case_path.parent.name):
                case = json.loads(case_path.read_text(encoding="utf-8"))
                result = apply_profile(case["profile"], case["input"])
                assert result is not None
                self.assertEqual(case["accepted"], result.accepted)
                self.assertEqual(case["expected"], result.output)
                self.assertTrue(case["origin"])
                self.assertTrue(case["mandatoryFacts"])


if __name__ == "__main__":
    unittest.main()
