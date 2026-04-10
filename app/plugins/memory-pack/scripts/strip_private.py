#!/usr/bin/env python3
"""Remove <private>...</private> blocks from stdin.

Used by observation-capture.sh to sanitize content before storage.
Handles multi-line private blocks and nested angle brackets.

Usage: echo "text <private>secret</private> more" | python3 strip_private.py
"""
from __future__ import annotations

import re
import sys


def main() -> None:
    content = sys.stdin.read()
    cleaned = re.sub(r"<private>.*?</private>", "", content, flags=re.DOTALL)
    sys.stdout.write(cleaned)


if __name__ == "__main__":
    main()
