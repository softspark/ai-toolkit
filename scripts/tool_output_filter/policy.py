"""Strict materialized policy contract."""

from __future__ import annotations

import json
import os

from .contracts import (
    DEFAULT_MAX_INPUT_BYTES,
    DEFAULT_MIN_SAVINGS_BYTES,
    DEFAULT_MIN_SAVINGS_RATIO,
    FilterMode,
)
from .recovery import DEFAULT_MAX_SESSION_BYTES, DEFAULT_TTL_MINUTES

_KNOWN_PROFILES = frozenset({"repeat-lines", "tap-success"})
_TOP_LEVEL_KEYS = frozenset(
    {
        "mode",
        "profiles",
        "maxInputBytes",
        "minSavingsBytes",
        "minSavingsRatio",
        "recovery",
    }
)
_RECOVERY_KEYS = frozenset({"mode", "ttlMinutes", "maxSessionBytes"})


class OutputFilterPolicy:
    __slots__ = (
        "max_input_bytes",
        "max_session_bytes",
        "min_savings_bytes",
        "min_savings_ratio",
        "mode",
        "profiles",
        "ttl_minutes",
    )

    def __init__(
        self,
        mode: FilterMode,
        profiles: tuple[str, ...],
        max_input_bytes: int = DEFAULT_MAX_INPUT_BYTES,
        min_savings_bytes: int = DEFAULT_MIN_SAVINGS_BYTES,
        min_savings_ratio: float = DEFAULT_MIN_SAVINGS_RATIO,
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
        max_session_bytes: int = DEFAULT_MAX_SESSION_BYTES,
    ) -> None:
        self.mode = mode
        self.profiles = profiles
        self.max_input_bytes = max_input_bytes
        self.min_savings_bytes = min_savings_bytes
        self.min_savings_ratio = min_savings_ratio
        self.ttl_minutes = ttl_minutes
        self.max_session_bytes = max_session_bytes


def _integer(data: dict[str, object], key: str, default: int) -> int:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _number(data: dict[str, object], key: str, default: float) -> float:
    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _validate_ranges(
    max_input_bytes: int,
    min_savings_bytes: int,
    min_savings_ratio: float,
    ttl_minutes: int,
    max_session_bytes: int,
) -> None:
    if not 1 <= max_input_bytes <= DEFAULT_MAX_INPUT_BYTES:
        raise ValueError("maxInputBytes is outside the safe range")
    if not 0 <= min_savings_bytes <= max_input_bytes:
        raise ValueError("minSavingsBytes is outside the safe range")
    if not 0.0 <= min_savings_ratio <= 1.0:
        raise ValueError("minSavingsRatio is outside the safe range")
    if ttl_minutes <= 0 or max_session_bytes <= 0:
        raise ValueError("recovery limits must be positive")


def load_policy(path: str | os.PathLike[str]) -> OutputFilterPolicy:
    """Load an unwrapped, materialized policy object."""

    with open(path, encoding="utf-8") as policy_file:
        data = json.load(policy_file)
    if not isinstance(data, dict):
        raise ValueError("output-filter policy must be an object")
    if set(data) - _TOP_LEVEL_KEYS:
        raise ValueError("output-filter policy contains unknown keys")
    mode = FilterMode(data["mode"])
    raw_profiles = data.get("profiles", [])
    if not isinstance(raw_profiles, list) or not all(
        isinstance(profile, str) for profile in raw_profiles
    ):
        raise ValueError("profiles must be a string array")
    if len(set(raw_profiles)) != len(raw_profiles):
        raise ValueError("profiles must not contain duplicates")
    if any(profile not in _KNOWN_PROFILES for profile in raw_profiles):
        raise ValueError("profiles contains an unknown profile")
    recovery = data.get("recovery", {})
    if not isinstance(recovery, dict):
        raise ValueError("recovery must be an object")
    if set(recovery) - _RECOVERY_KEYS:
        raise ValueError("recovery contains unknown keys")
    if recovery.get("mode", "ephemeral") != "ephemeral":
        raise ValueError("only ephemeral recovery is supported")
    max_input_bytes = _integer(
        data,
        "maxInputBytes",
        DEFAULT_MAX_INPUT_BYTES,
    )
    min_savings_bytes = _integer(
        data,
        "minSavingsBytes",
        DEFAULT_MIN_SAVINGS_BYTES,
    )
    min_savings_ratio = _number(
        data,
        "minSavingsRatio",
        DEFAULT_MIN_SAVINGS_RATIO,
    )
    ttl_minutes = _integer(recovery, "ttlMinutes", DEFAULT_TTL_MINUTES)
    max_session_bytes = _integer(
        recovery,
        "maxSessionBytes",
        DEFAULT_MAX_SESSION_BYTES,
    )
    _validate_ranges(
        max_input_bytes,
        min_savings_bytes,
        min_savings_ratio,
        ttl_minutes,
        max_session_bytes,
    )
    return OutputFilterPolicy(
        mode=mode,
        profiles=tuple(raw_profiles),
        max_input_bytes=max_input_bytes,
        min_savings_bytes=min_savings_bytes,
        min_savings_ratio=min_savings_ratio,
        ttl_minutes=ttl_minutes,
        max_session_bytes=max_session_bytes,
    )
