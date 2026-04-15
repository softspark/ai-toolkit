#!/usr/bin/env python3
"""Shared URL fetch utility for ai-toolkit.

HTTPS-only, timeout-capped, size-limited fetcher used by both
rule_sources and hook_sources.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import ssl
import urllib.error
import urllib.request

_FETCH_TIMEOUT = 30  # seconds
_FETCH_MAX_BYTES = 10 * 1024 * 1024  # 10MB


def fetch_url(url: str) -> bytes:
    """Fetch URL content. HTTPS only, 30s timeout, 10MB cap.

    Args:
        url: The HTTPS URL to fetch.

    Returns:
        Raw bytes of the response body.

    Raises:
        ValueError: if URL is not HTTPS or returns binary content.
        urllib.error.URLError: on network failure.
    """
    if not url.startswith("https://"):
        raise ValueError(
            f"Only HTTPS URLs are supported (got: {url.split('://')[0]}://)"
        )

    ctx = ssl.create_default_context()
    with urllib.request.urlopen(url, timeout=_FETCH_TIMEOUT, context=ctx) as resp:
        data = resp.read(_FETCH_MAX_BYTES)
        # Detect truncation — if there's more data, the response exceeds the limit
        if resp.read(1):
            raise ValueError(
                f"Response exceeds {_FETCH_MAX_BYTES} byte limit: {url}"
            )

    # Basic binary detection — reject if null bytes present
    if b"\x00" in data:
        raise ValueError(f"URL returned binary content: {url}")

    return data
