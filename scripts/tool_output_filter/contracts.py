"""Public data contracts for the tool-output filter."""

from __future__ import annotations

from enum import Enum

DEFAULT_MAX_INPUT_BYTES = 8 * 1024 * 1024
DEFAULT_MIN_SAVINGS_BYTES = 1024
DEFAULT_MIN_SAVINGS_RATIO = 0.15


class _ImmutableSlots:
    """Allow one assignment per declared slot."""

    __slots__ = ()

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, name):
            raise AttributeError(f"{type(self).__name__} is immutable")
        object.__setattr__(self, name, value)


class FilterMode(str, Enum):
    """Supported activation modes."""

    OFF = "off"
    OBSERVE = "observe"
    SAFE = "safe"


class FilterRequest(_ImmutableSlots):
    """Normalized successful textual tool output."""

    __slots__ = (
        "interrupted",
        "is_image",
        "is_streaming",
        "max_input_bytes",
        "min_savings_bytes",
        "min_savings_ratio",
        "mode",
        "output",
        "profile_id",
        "raw_response",
        "stderr",
        "successful",
    )

    def __init__(
        self,
        output: str,
        mode: FilterMode,
        profile_id: str,
        raw_response: object | None = None,
        successful: bool = True,
        stderr: str = "",
        interrupted: bool = False,
        is_image: bool = False,
        is_streaming: bool = False,
        max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
        min_savings_bytes: int = DEFAULT_MIN_SAVINGS_BYTES,
        min_savings_ratio: float = DEFAULT_MIN_SAVINGS_RATIO,
    ) -> None:
        self.output = output
        self.mode = mode
        self.profile_id = profile_id
        self.raw_response = raw_response
        self.successful = successful
        self.stderr = stderr
        self.interrupted = interrupted
        self.is_image = is_image
        self.is_streaming = is_streaming
        self.max_input_bytes = max_input_bytes
        self.min_savings_bytes = min_savings_bytes
        self.min_savings_ratio = min_savings_ratio


class FilterTelemetry(_ImmutableSlots):
    """Content-free measurements for one filter decision."""

    __slots__ = (
        "duration_ms",
        "fallback_reason",
        "input_bytes",
        "input_lines",
        "outcome",
        "output_bytes",
        "output_lines",
        "profile_id",
        "profile_version",
    )

    def __init__(
        self,
        profile_id: str,
        profile_version: int,
        input_bytes: int,
        output_bytes: int,
        input_lines: int,
        output_lines: int,
        duration_ms: float = 0.0,
        outcome: str = "",
        fallback_reason: str | None = None,
    ) -> None:
        self.profile_id = profile_id
        self.profile_version = profile_version
        self.input_bytes = input_bytes
        self.output_bytes = output_bytes
        self.input_lines = input_lines
        self.output_lines = output_lines
        self.duration_ms = duration_ms
        self.outcome = outcome
        self.fallback_reason = fallback_reason

    def with_runtime(
        self,
        *,
        duration_ms: float,
        outcome: str,
        fallback_reason: str | None,
    ) -> FilterTelemetry:
        return FilterTelemetry(
            self.profile_id,
            self.profile_version,
            self.input_bytes,
            self.output_bytes,
            self.input_lines,
            self.output_lines,
            duration_ms,
            outcome,
            fallback_reason,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            slot: getattr(self, slot)
            for slot in self.__slots__
        }


class FilterResult(_ImmutableSlots):
    """Observable result returned by the filtering engine."""

    __slots__ = (
        "changed",
        "fallback_reason",
        "outcome",
        "output",
        "telemetry",
    )

    def __init__(
        self,
        output: str,
        changed: bool,
        outcome: str,
        telemetry: FilterTelemetry | None = None,
        fallback_reason: str | None = None,
    ) -> None:
        self.output = output
        self.changed = changed
        self.outcome = outcome
        self.telemetry = telemetry
        self.fallback_reason = fallback_reason

    def with_telemetry(self, telemetry: FilterTelemetry) -> FilterResult:
        return FilterResult(
            self.output,
            self.changed,
            self.outcome,
            telemetry,
            self.fallback_reason,
        )
