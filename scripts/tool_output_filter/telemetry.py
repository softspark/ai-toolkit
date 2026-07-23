"""Metadata-only telemetry boundary."""

from __future__ import annotations

from .contracts import FilterTelemetry


class TelemetrySink:
    """Receives content-free filter decision events."""

    def record(self, event: FilterTelemetry) -> None:
        """Record one event without raising into the filter path."""
        raise NotImplementedError
