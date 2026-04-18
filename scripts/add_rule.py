#!/usr/bin/env python3
"""add-rule -- Register a rule file or URL in ~/.softspark/ai-toolkit/rules/.

Registered rules are automatically injected into all AI tool configs
on next 'ai-toolkit install' or 'ai-toolkit update'.
URL-sourced rules are auto-refreshed on every update.

  Global: Claude, Cursor, Windsurf, Gemini, Augment
  Local (--local): all of the above + Copilot, Cline, Roo, Aider, Antigravity

Usage:
  add_rule.py <rule-file-or-url> [rule-name]

Arguments:
  rule-file-or-url  Path to .md file or HTTPS URL to register globally
  rule-name         Override the rule name (default: filename without .md)
"""
from __future__ import annotations

import re
import shutil
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _name_from_url(url: str) -> str:
    """Derive a rule name from a URL's last path segment."""
    parsed = urllib.parse.urlparse(url)
    filename = parsed.path.rstrip("/").split("/")[-1]
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return re.sub(r"[^a-zA-Z0-9_-]", "", stem)


def main() -> None:
    """Register a rule file or URL in the global rules directory."""
    if len(sys.argv) < 2:
        print("Usage: add_rule.py <rule-file-or-url> [rule-name]", file=sys.stderr)
        sys.exit(1)

    source = sys.argv[1]
    is_url = source.startswith("https://") or source.startswith("http://")

    if is_url and source.startswith("http://"):
        print("Error: only HTTPS URLs are supported. Use https:// for security.", file=sys.stderr)
        sys.exit(1)

    from paths import RULES_DIR
    rules_dir = RULES_DIR
    rules_dir.mkdir(parents=True, exist_ok=True)

    if is_url:
        from rule_sources import fetch_url, register_url_source

        rule_name = sys.argv[2] if len(sys.argv) > 2 else _name_from_url(source)
        rule_name = re.sub(r"[^a-zA-Z0-9_-]", "", rule_name)
        if not rule_name:
            print("Error: could not derive rule name from URL. Provide one explicitly.", file=sys.stderr)
            sys.exit(1)

        try:
            data = fetch_url(source)
        except Exception as exc:
            print(f"Error fetching URL: {exc}", file=sys.stderr)
            sys.exit(1)

        dest = rules_dir / f"{rule_name}.md"
        dest.write_bytes(data)
        register_url_source(rules_dir, rule_name, source, content=data)

        print(f"Registered: '{rule_name}' -> {dest}")
        print(f"Source URL: {source} (auto-refreshed on update)")
    else:
        rule_file = Path(source)
        if not rule_file.is_file():
            print(f"Rule file not found: {rule_file}", file=sys.stderr)
            sys.exit(1)

        rule_name = sys.argv[2] if len(sys.argv) > 2 else rule_file.stem
        rule_name = re.sub(r"[^a-zA-Z0-9_-]", "", rule_name)
        if not rule_name:
            print("Error: rule name is empty after sanitization", file=sys.stderr)
            sys.exit(1)

        dest = rules_dir / f"{rule_name}.md"
        shutil.copy2(rule_file, dest)

        print(f"Registered: '{rule_name}' -> {dest}")

    print()
    print("Apply now:")
    print("  ai-toolkit update            # global (Claude, Cursor, Windsurf, Gemini, Augment)")
    print("  ai-toolkit update --local    # project-local (all editors)")


if __name__ == "__main__":
    main()
