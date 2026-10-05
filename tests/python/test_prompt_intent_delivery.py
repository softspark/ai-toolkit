# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Exercise prompt classification from installed assets, with a temporary HOME."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INSTALL = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
target = Path(sys.argv[2])
kind = sys.argv[3]
if kind == "global":
    from install_steps.hooks import install_hooks
    claude = target / ".claude"
    hooks = target / ".softspark/ai-toolkit/hooks"
    claude.mkdir(parents=True)
    hooks.mkdir(parents=True)
    install_hooks(claude, hooks, "hooks", "", False)
elif kind == "plugin-core":
    from plugin import _ensure_core_hook_scripts
    _ensure_core_hook_scripts()
elif kind.startswith("codex"):
    from generate_codex_hooks import generate
    generate(target, global_install=kind == "codex-global")
elif kind == "claude-app":
    from claude_app import stage_plugin
    stage_plugin(target / "plugin", include_custom_rules=False)
"""


@pytest.mark.parametrize(("kind", "relative_hooks"), [
    ("global", ".softspark/ai-toolkit/hooks"),
    ("plugin-core", ".softspark/ai-toolkit/hooks"),
    ("codex-project", ".codex/hooks"),
    ("codex-global", ".codex/ai-toolkit-hooks"),
    ("claude-app", "plugin/hooks"),
])
def test_delivered_hook_classifies_with_its_adjacent_helper(
    tmp_path: Path, kind: str, relative_hooks: str,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "HOME": str(home), "PATH": os.environ["PATH"],
        "PYTHONDONTWRITEBYTECODE": "1", "TOOLKIT_HOOK_PROFILE": "standard",
        "AI_TOOLKIT_HOOK_FORMAT": "json", "AI_TOOLKIT_HOOK_QUIET": "1",
        "AI_TOOLKIT_SEARCH_FIRST": "off",
    }
    installed = subprocess.run(
        [sys.executable, "-c", INSTALL, str(ROOT / "scripts"), str(home), kind],
        env=env, cwd=home, text=True, capture_output=True, timeout=30,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    hook_dir = home / relative_hooks
    assert (hook_dir / "_prompt-intent.py").is_file()

    for prompt, expected in (
        ("Napraw błąd logowania", "debugging request detected"),
        ('Opisz obraz: "designer ladybug"', "apply KB-first research"),
    ):
        result = subprocess.run(
            ["bash", str(hook_dir / "user-prompt-submit.sh")],
            input=json.dumps({"prompt": prompt, "session_id": "delivery-test"}),
            env=env, cwd=home, text=True, capture_output=True, timeout=10,
        )
        assert result.returncode == 0, result.stderr
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        assert expected in context
