#!/usr/bin/env python3
"""ai-toolkit sync — Sync config to/from GitHub Gist.

Usage:
    sync.py --export              Export config snapshot as JSON to stdout
    sync.py --push                Push config to GitHub Gist (requires gh CLI)
    sync.py --pull [gist-id]      Pull config from Gist and apply
    sync.py --import <file|url>   Import config from local file or URL
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir

CONFIG_DIR = Path.home() / ".ai-toolkit"
RULES_DIR = CONFIG_DIR / "rules"
GIST_ID_FILE = CONFIG_DIR / ".gist-id"


def do_export() -> str:
    """Export config snapshot as JSON."""
    # Read toolkit version
    version = "unknown"
    pkg = toolkit_dir / "package.json"
    if pkg.is_file():
        with open(pkg) as f:
            version = json.load(f).get("version", "unknown")

    # Collect rules
    rules: dict[str, str] = {}
    if RULES_DIR.is_dir():
        for f in sorted(RULES_DIR.glob("*.md")):
            rules[f.stem] = f.read_text(encoding="utf-8")

    # Collect stats
    stats: dict = {}
    stats_file = CONFIG_DIR / "stats.json"
    if stats_file.is_file():
        try:
            with open(stats_file) as f:
                stats = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    snapshot = {
        "schema_version": 1,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "toolkit_version": version,
        "rules": rules,
        "stats": stats,
    }
    return json.dumps(snapshot, indent=2)


def do_import(source: str) -> None:
    """Import config from file or URL."""
    tmpfile: str | None = None

    if source.startswith("https://") or source.startswith("http://"):
        if not source.startswith("https://"):
            print("Error: HTTP imports are not supported. Use HTTPS for security.", file=sys.stderr)
            sys.exit(1)
        tmp_fd, tmpfile = tempfile.mkstemp(suffix=".json")
        os.close(tmp_fd)
        try:
            import ssl
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(source, timeout=30, context=ctx) as resp:
                data = resp.read(10 * 1024 * 1024)  # 10MB max
                with open(tmpfile, 'wb') as f:
                    f.write(data)
        except Exception:
            if os.path.exists(tmpfile):
                os.unlink(tmpfile)
            raise
        source = tmpfile

    source_path = Path(source)
    if not source_path.is_file():
        print(f"Error: file not found: {source}", file=sys.stderr)
        sys.exit(1)

    with open(source_path) as f:
        data = json.load(f)

    if data.get("schema_version") != 1:
        print("Error: unsupported schema version", file=sys.stderr)
        sys.exit(1)

    rules = data.get("rules", {})
    if rules:
        RULES_DIR.mkdir(parents=True, exist_ok=True)
        for name, content in rules.items():
            if "/" in name or "\\" in name or ".." in name:
                print(f"  SKIPPED: '{name}' — invalid rule name (path traversal)", file=sys.stderr)
                continue
            path = RULES_DIR / f"{name}.md"
            path.write_text(content, encoding="utf-8")
            print(f"  Applied rule: {name}")

    print(f"\nImported {len(rules)} rules from {source_path}")
    print(f"Toolkit version at export: {data.get('toolkit_version', 'unknown')}")

    if tmpfile:
        os.unlink(tmpfile)


def do_push() -> None:
    """Push config to GitHub Gist."""
    if not shutil.which("gh"):
        print("Error: gh CLI not found. Install: https://cli.github.com")
        sys.exit(1)

    result = subprocess.run(["gh", "auth", "status"], capture_output=True)
    if result.returncode != 0:
        print("Error: gh not authenticated. Run: gh auth login")
        sys.exit(1)

    tmp_fd, tmpfile = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)
    Path(tmpfile).write_text(do_export(), encoding="utf-8")

    if GIST_ID_FILE.is_file():
        gist_id = GIST_ID_FILE.read_text().strip()
        subprocess.run(
            ["gh", "gist", "edit", gist_id, "-f", "ai-toolkit-config.json", tmpfile],
            check=True,
        )
        print(f"Updated gist: {gist_id}")
    else:
        result = subprocess.run(
            ["gh", "gist", "create", "--filename", "ai-toolkit-config.json",
             "--desc", "ai-toolkit config sync", tmpfile],
            capture_output=True, text=True,
        )
        gist_url = result.stdout.strip()
        import re
        match = re.search(r"[a-f0-9]{20,}", gist_url)
        gist_id = match.group(0) if match else gist_url
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        GIST_ID_FILE.write_text(gist_id, encoding="utf-8")
        print(f"Created gist: {gist_url}")
        print(f"Gist ID saved to: {GIST_ID_FILE}")

    os.unlink(tmpfile)


def do_pull(gist_id: str = "") -> None:
    """Pull config from GitHub Gist."""
    if not shutil.which("gh"):
        print("Error: gh CLI not found. Install: https://cli.github.com")
        sys.exit(1)

    if not gist_id and GIST_ID_FILE.is_file():
        gist_id = GIST_ID_FILE.read_text().strip()
    if not gist_id:
        print("Error: no gist ID provided and no saved gist ID found")
        print("Usage: ai-toolkit sync --pull <gist-id>")
        sys.exit(1)

    tmp_fd, tmpfile = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)
    with open(tmpfile, "w") as f:
        subprocess.run(
            ["gh", "gist", "view", gist_id, "-f", "ai-toolkit-config.json"],
            stdout=f,
            check=True,
        )
    do_import(tmpfile)
    os.unlink(tmpfile)

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    GIST_ID_FILE.write_text(gist_id, encoding="utf-8")


def main() -> None:
    action = ""
    arg = ""
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--export":
            action = "export"
        elif a == "--push":
            action = "push"
        elif a == "--pull":
            action = "pull"
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                i += 1
                arg = args[i]
        elif a == "--import":
            action = "import"
            if i + 1 < len(args):
                i += 1
                arg = args[i]
        elif a.startswith("-"):
            print(f"Unknown option: {a}")
            sys.exit(1)
        else:
            arg = a
        i += 1

    if not action:
        print("Usage: ai-toolkit sync [--export|--push|--pull <gist-id>|--import <file>]")
        sys.exit(1)

    if action == "export":
        print(do_export())
    elif action == "import":
        if not arg:
            print("Error: --import requires a file path or URL")
            sys.exit(1)
        do_import(arg)
    elif action == "push":
        do_push()
    elif action == "pull":
        do_pull(arg)


if __name__ == "__main__":
    main()
