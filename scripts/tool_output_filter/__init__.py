"""Dependency-free post-execution tool-output filtering."""

from .contracts import FilterMode, FilterRequest, FilterResult
from .engine import filter_output
from .invariants import SessionCircuitBreaker
from .recovery import (
    EphemeralRecoveryStore,
    RecoveryStore,
    RecoveryUnavailableError,
    clean_owned_recovery_tree,
    clean_owned_repo_recovery,
    clean_session,
    count_owned_recovery_artifacts,
    recover_by_handle,
)
from .telemetry import TelemetrySink

__all__ = [
    "EphemeralRecoveryStore",
    "FilterMode",
    "FilterRequest",
    "FilterResult",
    "RecoveryStore",
    "RecoveryUnavailableError",
    "SessionCircuitBreaker",
    "TelemetrySink",
    "clean_owned_recovery_tree",
    "clean_owned_repo_recovery",
    "clean_session",
    "count_owned_recovery_artifacts",
    "filter_output",
    "recover_by_handle",
]
