# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Uninstall removal of every installed plugin pack via the regular remove path.

``scripts/plugin.py`` binds HOME and the data dir at import time, so each
step runs in a subprocess with a temp HOME, like tests/test_plugin.bats.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
PACKS = ("memory-pack", "enterprise-pack")
PLUGIN_MARKERS = tuple(f"plugin-{pack}" for pack in PACKS) + ("ai-toolkit-plugin-",)
USER_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "mine.sh"}]}

REMOVE_TWICE = """
import json, sys
sys.path.insert(0, sys.argv[1])
import plugin
data_dir = plugin.TOOLKIT_DATA_DIR
result = [plugin.discover_installed(data_dir), plugin.remove_all_installed(data_dir),
          plugin.discover_installed(data_dir), plugin.remove_all_installed(data_dir)]
print("RESULT " + json.dumps(result))
"""


def _run(home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        key: value for key, value in os.environ.items()
        if key not in {"CODEX_HOME", "AI_TOOLKIT_HOME", "SOFTSPARK_HOME", "COPILOT_HOME"}
    }
    env["HOME"] = str(home)
    result = subprocess.run(
        [sys.executable, *args], env=env, capture_output=True, text=True, timeout=300
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _text_files(root: Path) -> list[Path]:
    files = []
    for directory, dirnames, filenames in os.walk(root):  # does not follow symlinks
        for filename in filenames:
            path = Path(directory) / filename
            if not path.is_symlink() and path.suffix != ".db":
                files.append(path)
    return files


@pytest.fixture
def home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    _run(home, str(SCRIPTS / "plugin.py"), "install", "--editor", "all", *PACKS)
    settings = home / ".claude" / "settings.json"
    data = json.loads(settings.read_text())
    data.setdefault("hooks", {}).setdefault("PreToolUse", []).append(USER_HOOK)
    settings.write_text(json.dumps(data))
    return home


def test_remove_all_installed_leaves_no_plugin_surface(home: Path) -> None:
    data_dir = home / ".softspark" / "ai-toolkit"
    assert (data_dir / "plugin-scripts" / "memory-pack").is_dir()
    assert any(
        marker in path.read_text(errors="ignore")
        for path in _text_files(home) for marker in PLUGIN_MARKERS
    )

    output = _run(home, "-c", REMOVE_TWICE, str(SCRIPTS)).stdout
    counts = json.loads(output.split("RESULT ", 1)[1])
    pairs = len(PACKS) * 4  # claude, codex, cursor, gemini
    assert counts == [pairs, pairs, 0, 0]

    leftovers = [
        str(path.relative_to(home)) for path in _text_files(home)
        if any(marker in path.read_text(errors="ignore") for marker in PLUGIN_MARKERS)
        or any(marker in path.name for marker in PLUGIN_MARKERS)
    ]
    assert leftovers == []
    assert not (data_dir / "plugin-scripts" / "memory-pack").exists()
    state = json.loads((data_dir / "plugins.json").read_text())
    assert all(not target["installed"] for target in state["targets"].values())
    settings = json.loads((home / ".claude" / "settings.json").read_text())
    assert USER_HOOK in settings["hooks"]["PreToolUse"]


def test_mismatched_data_dir_refused(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    script = (
        "import sys; sys.path.insert(0, sys.argv[1]); import plugin; from pathlib import Path\n"
        "try:\n    plugin.remove_all_installed(Path(sys.argv[2]))\n"
        "except ValueError:\n    print('REFUSED')\n"
    )
    output = _run(home, "-c", script, str(SCRIPTS), str(tmp_path / "other")).stdout
    assert "REFUSED" in output
