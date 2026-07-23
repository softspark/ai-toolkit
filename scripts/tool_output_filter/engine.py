"""Pure orchestration for post-execution output filtering."""

from __future__ import annotations

import re
import time
from collections.abc import Callable

from .contracts import FilterMode, FilterRequest, FilterResult, FilterTelemetry
from .invariants import SessionCircuitBreaker
from .profiles import ProfileTransform, apply_profile
from .recovery import RecoveryStore
from .telemetry import TelemetrySink

_UNSAFE_CONTROL_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029]|\r(?!\n)"
)


def _meets_savings_gate(
    raw_output: str,
    candidate: str,
    request: FilterRequest,
) -> bool:
    input_bytes = len(raw_output.encode("utf-8"))
    output_bytes = len(candidate.encode("utf-8"))
    bytes_saved = input_bytes - output_bytes
    savings_ratio = bytes_saved / input_bytes if input_bytes else 0.0
    return (
        bytes_saved >= request.min_savings_bytes
        and savings_ratio >= request.min_savings_ratio
    )


def _telemetry(
    request: FilterRequest,
    output: str,
    profile_id: str,
    profile_version: int,
) -> FilterTelemetry:
    return FilterTelemetry(
        profile_id=profile_id,
        profile_version=profile_version,
        input_bytes=len(request.output.encode("utf-8")),
        output_bytes=len(output.encode("utf-8")),
        input_lines=len(request.output.splitlines()),
        output_lines=len(output.splitlines()),
    )


def _with_recovery_marker(
    candidate: str,
    request: FilterRequest,
    handle: str,
    profile_id: str,
    profile_version: int,
) -> str:
    separator = "" if candidate.endswith("\n") else "\n"
    emitted_lines = len(candidate.splitlines()) + 1
    return (
        f"{candidate}{separator}"
        f"[ai-toolkit-output-filter {profile_id}/v{profile_version}; "
        f"original_lines={len(request.output.splitlines())}; "
        f"emitted_lines={emitted_lines}; recovery={handle}]\n"
    )


def _discard_recovery(recovery: RecoveryStore, handle: str) -> None:
    try:
        recovery.delete(handle)
    except Exception:
        pass


def _passthrough(
    request: FilterRequest,
    reason: str,
    telemetry: FilterTelemetry | None = None,
) -> FilterResult:
    return FilterResult(
        output=request.output,
        changed=False,
        outcome="passthrough",
        telemetry=telemetry,
        fallback_reason=reason,
    )


def _eligibility_failure(request: FilterRequest) -> str | None:
    if not request.successful:
        return "execution-failed"
    if request.stderr:
        return "stderr-present"
    if request.interrupted:
        return "execution-interrupted"
    if request.is_image:
        return "unsupported-media"
    if request.is_streaming:
        return "unsupported-stream"
    if _UNSAFE_CONTROL_PATTERN.search(request.output) is not None:
        return "unsupported-control-sequence"
    try:
        input_bytes = len(request.output.encode("utf-8"))
    except UnicodeEncodeError:
        return "invalid-text"
    if input_bytes > request.max_input_bytes:
        return "input-too-large"
    return None


def _apply_profile_safely(
    request: FilterRequest,
) -> tuple[ProfileTransform | None, str | None]:
    try:
        profile = apply_profile(request.profile_id, request.output)
    except Exception:
        return None, "profile-failed"
    if profile is None:
        return None, "unknown-profile"
    if not profile.accepted:
        return None, "profile-rejected"
    return profile, None


def _save_verified_recovery(
    response: object,
    recovery: RecoveryStore,
) -> tuple[str | None, str | None]:
    handle: str | None = None
    try:
        handle = recovery.save(response)
        recovered = recovery.load(handle)
    except Exception:
        if handle is not None:
            _discard_recovery(recovery, handle)
        return None, "recovery-failed"
    if recovered != response:
        _discard_recovery(recovery, handle)
        return None, "recovery-verification-failed"
    return handle, None


def _safe_result(
    request: FilterRequest,
    profile: ProfileTransform,
    telemetry: FilterTelemetry,
    recovery: RecoveryStore | None,
) -> FilterResult:
    if request.raw_response is None:
        return _passthrough(request, "raw-response-unavailable", telemetry)
    if recovery is None:
        return _passthrough(request, "recovery-unavailable", telemetry)
    handle, failure = _save_verified_recovery(
        request.raw_response,
        recovery,
    )
    if failure is not None or handle is None:
        return _passthrough(request, failure or "recovery-failed", telemetry)
    replacement = _with_recovery_marker(
        profile.output,
        request,
        handle,
        request.profile_id,
        profile.profile_version,
    )
    if not _meets_savings_gate(request.output, replacement, request):
        _discard_recovery(recovery, handle)
        return _passthrough(request, "never-worse", telemetry)
    return FilterResult(
        output=replacement,
        changed=True,
        outcome="replaced",
        telemetry=_telemetry(
            request,
            replacement,
            request.profile_id,
            profile.profile_version,
        ),
    )


def _filter_output(
    request: FilterRequest,
    *,
    recovery: RecoveryStore | None = None,
) -> FilterResult:
    """Return an exact passthrough unless every safety gate succeeds."""

    if request.mode is FilterMode.OFF:
        return FilterResult(request.output, False, "disabled")
    eligibility_failure = _eligibility_failure(request)
    if eligibility_failure is not None:
        return _passthrough(request, eligibility_failure)
    profile, profile_failure = _apply_profile_safely(request)
    if profile_failure is not None or profile is None:
        return _passthrough(
            request,
            profile_failure or "profile-failed",
        )
    if not _meets_savings_gate(request.output, profile.output, request):
        return _passthrough(request, "insufficient-savings")
    candidate_telemetry = _telemetry(
        request,
        profile.output,
        request.profile_id,
        profile.profile_version,
    )
    if request.mode is FilterMode.OBSERVE:
        return FilterResult(
            request.output,
            False,
            "observed",
            candidate_telemetry,
        )
    return _safe_result(
        request,
        profile,
        candidate_telemetry,
        recovery,
    )


def filter_output(
    request: FilterRequest,
    *,
    recovery: RecoveryStore | None = None,
    telemetry: TelemetrySink | None = None,
    circuit_breaker: SessionCircuitBreaker | None = None,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> FilterResult:
    """Apply one profile without mutating execution state or raw input."""

    if circuit_breaker is not None and circuit_breaker.is_open:
        return FilterResult(
            output=request.output,
            changed=False,
            outcome="passthrough",
            fallback_reason="circuit-open",
        )

    started_ns = clock_ns()
    result = _filter_output(request, recovery=recovery)
    finished_ns = clock_ns()
    if circuit_breaker is not None:
        circuit_breaker.record(result.fallback_reason)
    if result.telemetry is None:
        return result

    event = result.telemetry.with_runtime(
        duration_ms=max(0, finished_ns - started_ns) / 1_000_000,
        outcome=result.outcome,
        fallback_reason=result.fallback_reason,
    )
    result = result.with_telemetry(event)
    if telemetry is not None:
        try:
            telemetry.record(event)
        except Exception:
            pass
    return result
