# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Run the installed Devin file hooks with the same stdin and matchers as the CLI."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from generate_devin_hooks import generate  # noqa: E402


@pytest.fixture
def invoke(tmp_path: Path):
    destination = tmp_path / ".softspark/ai-toolkit/hooks"
    destination.parent.mkdir(parents=True)
    destination.symlink_to(Path(__file__).resolve().parents[2] / "app/hooks")
    events = json.loads(generate(tmp_path).read_text())
    env = dict(os.environ, HOME=str(tmp_path), AI_TOOLKIT_DISABLED_HOOKS="",
               TOOLKIT_HOOK_PROFILE="standard", AI_TOOLKIT_HOOK_FORMAT="")

    def run(tool, arguments, event="PreToolUse", script=None, **fields):
        payload = dict(tool_name=tool, tool_input=arguments, hook_event_name=event,
                       session_id="devin-fixture", cwd=str(tmp_path), **fields)
        commands = [handler["command"] for group in events[event]
                    if re.search(group["matcher"], tool) for handler in group["hooks"]
                    if script is None or script in handler["command"]]
        assert commands, (event, tool)
        results = [subprocess.run(["bash", "-c", command], input=json.dumps(payload),
                                  text=True, capture_output=True, env=env, cwd=tmp_path,
                                  timeout=10) for command in commands]
        assert all(result.returncode in (0, 2) for result in results), results
        return results

    return run


@pytest.mark.parametrize("tool,key", [
    ("read", "file_path"), ("edit", "file_path"), ("write", "file_path"),
    ("notebook_read", "notebook_path"), ("notebook_edit", "notebook_path"),
    ("grep", "path"), ("glob", "path"),
])
def test_devin_home_guard_recognizes_native_paths(invoke, tool, key) -> None:
    results = invoke(tool, {key: "/home/other-fixture-user/notes.ipynb"})
    assert any(r.returncode == 2 and "wrong username" in r.stderr for r in results)


def test_devin_mutations_block_protected_config_while_reads_remain_available(invoke) -> None:
    for tool in ("edit", "write"):
        results = invoke(tool, {"file_path": "eslint.config.js", "content": "fixture"})
        assert any(r.returncode == 2 and "protected" in r.stderr for r in results)
    assert all(r.returncode == 0 for r in invoke("read", {"file_path": "eslint.config.js"}))
    assert all(r.returncode == 0 for r in invoke("grep", {"pattern": "fixture"}))
    results = invoke("glob", {"pattern": "/home/other-fixture-user/*.ipynb"})
    assert any(r.returncode == 2 and "wrong username" in r.stderr for r in results)


@pytest.mark.parametrize("body,reason", [
    ("*** Add File: docs/notes.md\n+fixture\n*** Add File: ruff.toml\n+test", "protected"),
    ("*** Delete File: eslint.config.js", "protected"),
    ("*** Update File: docs/notes.md\n*** Move to: tsconfig.json", "protected"),
    ("*** Update File: /home/other-fixture-user/notes.md\n*** Move to: notes.md", "wrong username"),
    ("*** Update File: notes.md\n*** Move to: /home/other-fixture-user/moved.md", "wrong username"),
    ("*** Update File: pyproject.toml\n@@\n-[tool.ruff]\n+[tool.black]", "protected"),
])
def test_devin_patch_checks_each_file_and_move_destination(invoke, body, reason) -> None:
    patch = f"*** Begin Patch\n{body}\n*** End Patch"
    results = invoke("apply_patch", {"input": patch})
    assert any(r.returncode == 2 and reason in r.stderr for r in results)


def test_devin_patch_uses_headers_and_keeps_content_scoped_to_its_file(invoke) -> None:
    patch = ("*** Begin Patch\n*** Add File: docs/notes.md\n+[tool.ruff]\n"
             "+*** Delete File: ruff.toml\n*** Update File: pyproject.toml\n"
             "@@\n-version=1\n+version=2\n*** End Patch")
    assert all(r.returncode == 0 for r in invoke("apply_patch", patch))
    results = invoke("apply_patch", patch, "PostToolUse", "post-tool-use.sh")
    context = json.loads(results[0].stdout)["hookSpecificOutput"]
    assert context["hookEventName"] == "PostToolUse"
    assert "docs/notes.md" in context["additionalContext"]
    assert "pyproject.toml" in context["additionalContext"]
    assert "[tool.ruff]" not in context["additionalContext"]


def test_devin_failed_write_skips_post_edit_notifications_and_audit(invoke, tmp_path) -> None:
    results = invoke("write", {"file_path": ".env", "content": "private fixture"}, "PostToolUse",
                     tool_response={"success": False, "output": "", "error": "write failed"})
    assert all(r.returncode == 0 and not r.stdout and not r.stderr for r in results)
    assert not (tmp_path / ".softspark/ai-toolkit/governance.log").exists()


def test_devin_malformed_patch_blocks_before_an_edit(invoke) -> None:
    results = invoke("apply_patch", {"input": "unknown patch format"})
    assert any(r.returncode == 2 for r in results)
    observations = invoke("apply_patch", {"input": "private malformed text"}, "PostToolUse")
    assert all(r.returncode == 0 and "private" not in r.stderr for r in observations)


def test_doctor_restores_missing_devin_file_adapter(tmp_path, monkeypatch) -> None:
    import doctor

    monkeypatch.setattr(doctor, "HOOKS_DIR", tmp_path)
    doctor.check_hook_scripts(doctor.DiagResult(), fix_mode=True)
    expected = Path(__file__).resolve().parents[2] / "app/hooks/_devin-file-hook.py"
    assert (tmp_path / expected.name).read_bytes() == expected.read_bytes()


@pytest.mark.parametrize("previous", [b"[]", b"{unfinished", b"\xff"])
def test_devin_regeneration_preserves_unreadable_configuration(tmp_path, previous) -> None:
    target = tmp_path / ".devin/hooks.v1.json"
    target.parent.mkdir()
    target.write_bytes(previous)
    with pytest.raises(ValueError):
        generate(tmp_path)
    assert target.read_bytes() == previous


def test_devin_regeneration_refuses_symlinked_hooks_directory(tmp_path) -> None:
    outside = tmp_path / "external"
    outside.mkdir()
    (tmp_path / ".devin").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinked"):
        generate(tmp_path)
    assert list(outside.iterdir()) == []


def test_devin_regeneration_preserves_original_when_replace_fails(tmp_path, monkeypatch) -> None:
    target = tmp_path / ".devin/hooks.v1.json"
    target.parent.mkdir()
    previous = b'{"Stop":[{"hooks":[]}]}'
    target.write_bytes(previous)

    def fail_replace(*args):
        raise OSError("unavailable")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="unavailable"):
        generate(tmp_path)
    assert target.read_bytes() == previous
    assert list(target.parent.iterdir()) == [target]
