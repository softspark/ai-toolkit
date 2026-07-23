"""Bounded input helpers for fail-open runtime adapters."""

from __future__ import annotations

import json
from collections.abc import Callable

JSON_ENVELOPE_ALLOWANCE_BYTES = 64 * 1024


def read_bounded_text(
    stream: object,
    *,
    max_bytes: int,
) -> str | None:
    """Read UTF-8 text without retaining data beyond the byte limit."""

    if max_bytes < 0:
        raise ValueError("maximum input bytes must be non-negative")
    read = getattr(stream, "read", None)
    if not callable(read):
        raise TypeError("bounded text input must be readable")
    chunks: list[bytes] = []
    received = 0
    while received <= max_bytes:
        chunk = read(max_bytes + 1 - received)
        if not isinstance(chunk, bytes):
            raise TypeError("bounded text input must be binary")
        if not chunk:
            break
        chunks.append(chunk)
        received += len(chunk)
    if received > max_bytes:
        return None
    return b"".join(chunks).decode("utf-8")


def load_bounded_json(
    stream: object,
    *,
    max_bytes: int,
    decoder: Callable[[str], object] = json.loads,
) -> object | None:
    """Decode one JSON value only when its encoded form fits the hard cap."""

    text = read_bounded_text(stream, max_bytes=max_bytes)
    if text is None:
        return None
    return decoder(text)


__all__ = [
    "JSON_ENVELOPE_ALLOWANCE_BYTES",
    "load_bounded_json",
    "read_bounded_text",
]
