# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""`ai-toolkit adopt-agents-md` moves project instructions into AGENTS.md.

Each case runs in a subprocess with HOME and AI_TOOLKIT_HOME pointed at a
temporary directory and AI_TOOLKIT_USER_CWD removed, so backups stay in the
sandbox and an inherited directory handoff can never redirect the edits.

Run: npm run test:py (pytest, config in pytest.ini).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "agents_md.py"

CLAUDE_MD = """\
# Project

Run make test.

<!-- TOOLKIT:custom-rule START -->
Managed rule.
<!-- TOOLKIT:custom-rule END -->

## Deploy

Use make deploy.

## Project Constitution
@.claude/constitution.md
"""


def _adopt(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "AI_TOOLKIT_USER_CWD"}
    env.update(HOME=str(project.parent / "home"),
               AI_TOOLKIT_HOME=str(project.parent / "home" / "toolkit-data"))
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=project, env=env,
                          capture_output=True, text=True, timeout=60, check=False)


def test_interleaved_toolkit_sections_stay_in_claude_md(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")

    done = _adopt(project)

    assert done.returncode == 0, done.stderr
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == (
        "# Project\n\nRun make test.\n\n## Deploy\n\nUse make deploy.\n"
    )
    claude = (project / "CLAUDE.md").read_text(encoding="utf-8")
    assert claude.splitlines()[2] == "@AGENTS.md"
    assert "Managed rule." in claude and "@.claude/constitution.md" in claude
    assert "Run make test." not in claude and "Use make deploy." not in claude
    assert list((tmp_path / "home" / "toolkit-data" / "backups").glob("*CLAUDE.md.*.bak"))


def test_dry_run_changes_nothing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")

    done = _adopt(project, "--dry-run")

    assert done.returncode == 0, done.stderr
    assert "Would change: AGENTS.md" in done.stdout
    assert (project / "CLAUDE.md").read_text(encoding="utf-8") == CLAUDE_MD
    assert not (project / "AGENTS.md").exists()


def test_existing_agents_md_content_is_kept_after_claude_instructions(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "CLAUDE.md").write_text("# Claude part\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("# Shared part\n", encoding="utf-8")

    assert _adopt(project).returncode == 0
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == "# Claude part\n\n# Shared part\n"


def test_symlinked_claude_md_is_refused(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    real = tmp_path / "elsewhere.md"
    real.write_text("# Elsewhere\n", encoding="utf-8")
    (project / "CLAUDE.md").symlink_to(real)

    done = _adopt(project)

    assert done.returncode == 1
    assert "Refusing to edit symlinked" in done.stderr
    assert real.read_text(encoding="utf-8") == "# Elsewhere\n"
