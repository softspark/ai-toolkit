"""Stateful safety invariants shared by runtime adapters."""

from __future__ import annotations

DEFAULT_FAILURE_LIMIT = 3

# "never-worse" (savings margin missed after the recovery marker) is a benign
# outcome, not a safety failure: nothing was emitted. Only genuine anomalies
# may open the breaker.
_CIRCUIT_FAILURES = frozenset(
    {
        "profile-failed",
        "recovery-failed",
        "recovery-verification-failed",
    }
)


class SessionCircuitBreaker:
    """Open a session-local bypass after consecutive safety failures."""

    __slots__ = ("failure_limit", "consecutive_failures")

    def __init__(
        self,
        failure_limit: int = DEFAULT_FAILURE_LIMIT,
        consecutive_failures: int = 0,
    ) -> None:
        self.failure_limit = failure_limit
        self.consecutive_failures = consecutive_failures

    @property
    def is_open(self) -> bool:
        return self.consecutive_failures >= self.failure_limit

    def record(self, fallback_reason: str | None) -> None:
        if fallback_reason in _CIRCUIT_FAILURES:
            self.consecutive_failures += 1
        else:
            self.consecutive_failures = 0
