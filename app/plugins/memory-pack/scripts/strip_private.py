#!/usr/bin/env python3
"""Sanitize stdin before it is stored in the session memory database.

Two passes:
1. Remove ``<private>...</private>`` blocks (explicit user opt-out).
2. Redact high-confidence secrets (API keys, tokens, private keys) so a token
   that scrolls through a tool output never lands in the SQLite memory store.

Used by observation-capture.sh and session-summary.sh.

Usage: echo "text <private>secret</private> sk-..." | python3 strip_private.py
"""
from __future__ import annotations

import re
import sys

# High-confidence, structural secret patterns only. These match a specific
# token shape (not "password = ..." prose) so false positives stay near zero —
# important because over-redaction silently corrupts stored observations.
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws-key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}"), "api-key"),
    (re.compile(r"\bgh[posru]_[A-Za-z0-9]{36,}"), "github-token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "slack-token"),
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}"), "google-key"),
    (re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
        r"[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
    ), "private-key"),
]


def scrub_secrets(text: str) -> str:
    """Replace recognised secret tokens with a labelled redaction marker."""
    for pattern, label in _SECRET_PATTERNS:
        text = pattern.sub(f"[REDACTED:{label}]", text)
    return text


def main() -> None:
    content = sys.stdin.read()
    cleaned = re.sub(r"<private>.*?</private>", "", content, flags=re.DOTALL)
    cleaned = scrub_secrets(cleaned)
    sys.stdout.write(cleaned)


if __name__ == "__main__":
    main()
