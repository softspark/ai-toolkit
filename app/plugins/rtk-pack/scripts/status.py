#!/usr/bin/env python3
"""Report rtk-pack health: binary, digest, and hook wiring.

Invoked by `ai-toolkit plugin status` and `ai-toolkit doctor` through the
generic scripts/status.py hook in scripts/plugin.py.

The point of this script is to distinguish "installed" from "working". The pack
can be recorded as installed, have its hook wired, and still do nothing at all
because the binary never downloaded. That is the failure mode this project has
already shipped once, so it gets its own line rather than being inferred.

Stdlib only. Never raises; exit code is always 0.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PACK_NAME = "rtk-pack"
TOOLKIT_DATA_DIR = Path(
    os.environ.get("AI_TOOLKIT_DATA_DIR", Path.home() / ".softspark" / "ai-toolkit")
)
PACK_STATE_DIR = TOOLKIT_DATA_DIR / "plugin-scripts" / PACK_NAME
VERSION_FILE = PACK_STATE_DIR / "version.json"
HOOK_FILE = TOOLKIT_DATA_DIR / "hooks" / f"plugin-{PACK_NAME}-rewrite.sh"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"


def find_binary() -> Path | None:
    for candidate in (PACK_STATE_DIR / "bin" / "rtk", PACK_STATE_DIR / "bin" / "rtk.exe"):
        if candidate.is_file():
            return candidate
    return None


def digest_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def hook_registered() -> bool:
    """True when settings.json still points at this pack's hook."""
    try:
        settings = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return f"plugin-{PACK_NAME}-rewrite.sh" in json.dumps(settings.get("hooks", {}))


def main() -> int:
    binary = find_binary()
    if binary is None:
        print("rtk binary: MISSING — the hook is inert and every command runs unchanged")
        print("  fix: ai-toolkit plugin install rtk-pack")
        return 0

    record: dict = {}
    try:
        record = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass

    upstream = record.get("upstream_version", "unknown")
    print(f"rtk binary: {binary} (upstream {upstream})")

    # The recorded digest is of the archive, not the extracted binary, so it
    # cannot be recomputed here. Report the binary's own digest and whether the
    # install record still exists, and say which is which rather than implying
    # a verification that is not happening.
    if record:
        print(f"  install record: {record.get('asset', '?')} sha256 {record.get('sha256', '?')[:16]}…")
    else:
        print("  install record: MISSING — reinstall to restore provenance")
    print(f"  binary sha256: {digest_of(binary)[:16]}…")

    if not os.access(binary, os.X_OK):
        print("  executable: NO — the hook cannot run it")

    try:
        proc = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=15)
        reported = (proc.stdout.strip() or proc.stderr.strip()).splitlines()[0] if proc.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError, IndexError):
        reported = ""
    if reported:
        print(f"  runs: {reported}")
        expected = str(upstream).lstrip("v")
        if expected and expected not in reported:
            print(f"  WARNING: binary reports {reported}, manifest pins {upstream}")
    else:
        print("  runs: NO — binary present but will not start")

    print(f"  hook script: {'present' if HOOK_FILE.is_file() else 'MISSING'}")
    print(f"  hook registered in settings.json: {'yes' if hook_registered() else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
