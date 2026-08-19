#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Native Codex plugin export contract.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    TEST_TMP="$(cd "$TEST_TMP" && pwd -P)"
    export HOME="$TEST_TMP/home"
    mkdir -p "$HOME"
}

teardown() {
    rm -rf "$TEST_TMP"
}

@test "codex-plugin: export contains a native manifest, skills, hooks, and license" {
    archive="$TEST_TMP/ai-toolkit-codex-plugin.zip"

    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive"
    [ "$status" -eq 0 ]
    [ -f "$archive" ]

    run python3 - "$archive" "$TOOLKIT_DIR/package.json" <<'PY'
import json
import sys
import zipfile
from pathlib import Path

archive = Path(sys.argv[1])
package = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
with zipfile.ZipFile(archive) as plugin:
    names = set(plugin.namelist())
    assert ".codex-plugin/plugin.json" in names
    assert "skills/debug/SKILL.md" in names
    assert "hooks/hooks.json" in names
    assert "hooks/guard-destructive.sh" in names
    assert "LICENSE" in names

    manifest = json.loads(plugin.read(".codex-plugin/plugin.json"))
    assert manifest["name"] == "ai-toolkit"
    assert manifest["version"] == package["version"]
    assert manifest["skills"] == "./skills/"
    assert "hooks" not in manifest
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: export bundles skill runtime resources with plugin-local references" {
    archive="$TEST_TMP/runtime-resources.zip"

    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive" >/dev/null

    run python3 - "$archive" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as plugin:
    names = set(plugin.namelist())
    persona_resources = {
        "skills/persona/personas/backend-lead.md",
        "skills/persona/personas/devops-eng.md",
        "skills/persona/personas/frontend-lead.md",
        "skills/persona/personas/junior-dev.md",
    }
    assert persona_resources <= names
    assert "skills/briefing/scripts/session_token_stats.py" in names

    persona = plugin.read("skills/persona/SKILL.md").decode()
    briefing = plugin.read("skills/briefing/SKILL.md").decode()
    assert "./personas/" in persona
    assert "app/personas/" not in persona
    assert "~/.claude/skills/persona" not in persona
    assert "relative to toolkit root" not in persona
    assert "globally installed" not in persona
    assert "./scripts/session_token_stats.py" in briefing
    assert "python3 scripts/session_token_stats.py" not in briefing
    assert "app/hooks/ai-toolkit-statusline.sh" not in briefing
    helper = plugin.getinfo("skills/briefing/scripts/session_token_stats.py")
    assert (helper.external_attr >> 16) & 0o111
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: skill audit uses a self-contained staged helper" {
    archive="$TEST_TMP/skill-audit.zip"
    extracted="$TEST_TMP/plugin"

    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive" >/dev/null

    run python3 - "$archive" "$extracted" <<'PY'
import json
import subprocess
import sys
import zipfile
from pathlib import Path

archive = Path(sys.argv[1])
extracted = Path(sys.argv[2])
with zipfile.ZipFile(archive) as plugin:
    names = set(plugin.namelist())
    required_helpers = {
        "scripts/audit_skills.py",
        "scripts/_common.py",
        "scripts/frontmatter.py",
        "scripts/injection.py",
        "scripts/emission.py",
        "scripts/instruction_core.py",
    }
    assert required_helpers <= names
    skill = plugin.read("skills/skill-audit/SKILL.md").decode()
    assert "../../scripts/audit_skills.py" in skill
    assert "python3 scripts/audit_skills.py" not in skill
    plugin.extractall(extracted)

result = subprocess.run(
    [sys.executable, str(extracted / "scripts/audit_skills.py"), "--json"],
    check=True,
    text=True,
    capture_output=True,
)
report = json.loads(result.stdout)
assert report["summary"]["total"] >= 0
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: every explicit plugin-local skill dependency resolves" {
    archive="$TEST_TMP/dependency-audit.zip"

    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive" >/dev/null

    run python3 - "$archive" <<'PY'
import posixpath
import re
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as plugin:
    names = set(plugin.namelist())
    docs = plugin.read("skills/docs/SKILL.md").decode()
    assert "../documentation-standards/SKILL.md" in docs
    assert "app/skills/documentation-standards/SKILL.md" not in docs

    for skill_name in sorted(name for name in names if name.endswith("/SKILL.md")):
        text = plugin.read(skill_name).decode()
        references = re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", text)
        references += re.findall(
            r"(?:python3|python|node|bash)\s+(\./[^\s`]+)",
            text,
        )
        for reference in references:
            plugin_local = reference.startswith(
                (
                    "./scripts/",
                    "./reference/",
                    "./templates/",
                    "./personas/",
                    "./modes/",
                    "../",
                    "reference/",
                    "templates/",
                )
            )
            if not plugin_local:
                continue
            resolved = posixpath.normpath(
                posixpath.join(posixpath.dirname(skill_name), reference)
            )
            assert resolved in names, (skill_name, reference, resolved)
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: verify validates a clean stage without mutating home" {
    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" verify
    [ "$status" -eq 0 ]
    [[ "$output" == *"Codex plugin validation passed"* ]]
    [ -z "$(find "$HOME" -mindepth 1 -print -quit)" ]
}

@test "codex-plugin: CLI dispatches export and documents the command" {
    archive="$TEST_TMP/cli.zip"

    run $CLI codex-plugin export --output "$archive"
    [ "$status" -eq 0 ]
    [ -f "$archive" ]
    [[ "$output" == *"Codex IDE does not support plugins"* ]]

    run $CLI help
    [ "$status" -eq 0 ]
    [[ "$output" == *"codex-plugin"* ]]
    [[ "$output" == *"export [--output FILE]"* ]]
    [[ "$output" == *"verify"* ]]
}

@test "codex-plugin: hooks use the exact command schema and PLUGIN_ROOT assets" {
    archive="$TEST_TMP/hooks.zip"
    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive" >/dev/null

    run python3 - "$archive" <<'PY'
import json
import re
import sys
import zipfile

expected_events = {
    "SessionStart", "PreToolUse", "PostToolUse", "PermissionRequest",
    "UserPromptSubmit", "SubagentStart", "SubagentStop", "PreCompact",
    "SessionEnd", "Stop",
}
with zipfile.ZipFile(sys.argv[1]) as plugin:
    hooks = json.loads(plugin.read("hooks/hooks.json"))["hooks"]
    assert set(hooks) == expected_events
    for event, groups in hooks.items():
        for group in groups:
            assert set(group) in ({"hooks"}, {"matcher", "hooks"})
            for handler in group["hooks"]:
                expected_keys = (
                    {"type", "command", "timeout"}
                    if event == "SessionEnd"
                    else {"type", "command"}
                )
                assert set(handler) == expected_keys, (event, handler)
                assert handler["type"] == "command"
                command = handler["command"]
                assert "${PLUGIN_ROOT}/hooks/" in command
                assert "git rev-parse" not in command
                assert "CODEX_HOME" not in command
                assert ".softspark/ai-toolkit/hooks" not in command
                asset_name = re.search(r"\$\{PLUGIN_ROOT\}/hooks/([A-Za-z0-9._-]+)", command).group(1)
                info = plugin.getinfo(f"hooks/{asset_name}")
                assert (info.external_attr >> 16) & 0o111

    session_end = hooks["SessionEnd"][0]["hooks"][0]
    assert session_end["timeout"] == 3
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: archives are deterministic with fixed metadata and modes" {
    first="$TEST_TMP/first.zip"
    second="$TEST_TMP/second.zip"
    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$first" >/dev/null
    python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$second" >/dev/null
    [ "$(shasum "$first" | awk '{print $1}')" = "$(shasum "$second" | awk '{print $1}')" ]

    run python3 - "$first" <<'PY'
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1]) as plugin:
    infos = plugin.infolist()
    assert [info.filename for info in infos] == sorted(info.filename for info in infos)
    assert all(info.date_time == (2026, 1, 1, 0, 0, 0) for info in infos)
    assert (plugin.getinfo("hooks/guard-destructive.sh").external_attr >> 16) & 0o111
    assert (plugin.getinfo(".codex-plugin/plugin.json").external_attr >> 16) & 0o777 == 0o644
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: structural validation reports schema, mode, and symlink failures" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import json
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
temporary = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import codex_plugin

plugin = temporary / "invalid-plugin"
codex_plugin.stage_plugin(plugin)

manifest_path = plugin / ".codex-plugin" / "plugin.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
manifest["hooks"] = "../outside.json"
manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

guard = plugin / "hooks" / "guard-destructive.sh"
os.chmod(guard, 0o644)
hooks_path = plugin / "hooks" / "hooks.json"
hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"] += "; echo unexpected"
hooks_path.write_text(json.dumps(hooks), encoding="utf-8")
(plugin / "escaped-link").symlink_to(temporary / "outside")

errors = codex_plugin.validate_staged_plugin(plugin)
assert any("default hooks/hooks.json" in error for error in errors), errors
assert any("not executable" in error for error in errors), errors
assert any("contains a symlink" in error for error in errors), errors
assert any("differ from the canonical" in error for error in errors), errors
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: validation rejects missing and source-root skill dependencies" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
temporary = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import codex_plugin

plugin = temporary / "invalid-runtime-resources"
codex_plugin.stage_plugin(plugin)
(plugin / "skills/persona/personas/backend-lead.md").unlink()
(plugin / "skills/briefing/scripts/session_token_stats.py").unlink()
persona_skill = plugin / "skills/persona/SKILL.md"
persona_skill.write_text(
    persona_skill.read_text(encoding="utf-8")
    + "\nRead app/personas/backend-lead.md at runtime.\n",
    encoding="utf-8",
)

errors = codex_plugin.validate_staged_plugin(plugin)
assert any("persona runtime resource is missing" in error for error in errors), errors
assert any("briefing runtime resource is missing" in error for error in errors), errors
assert any("source-root runtime reference" in error for error in errors), errors
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: validation rejects an unclassified bare script reference" {
    run python3 - "$TOOLKIT_DIR" "$TEST_TMP" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
temporary = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import codex_plugin

plugin = temporary / "unclassified-script-reference"
codex_plugin.stage_plugin(plugin)
skill = plugin / "skills/skill-audit/SKILL.md"
skill.write_text(
    skill.read_text(encoding="utf-8")
    + "\nRun `python3 scripts/missed_plugin_helper.py` from this skill.\n",
    encoding="utf-8",
)
(plugin / "scripts/missed_plugin_helper.py").write_text(
    "print('sentinel')\n",
    encoding="utf-8",
)

errors = codex_plugin.validate_staged_plugin(plugin)
assert any("unclassified bare script reference" in error for error in errors), errors
PY
    [ "$status" -eq 0 ]
}

@test "codex-plugin: source and output symlinks are rejected without overwrite" {
    source="$TEST_TMP/source"
    destination="$TEST_TMP/destination"
    outside="$TEST_TMP/outside.txt"
    mkdir -p "$source"
    printf 'outside sentinel\n' > "$outside"
    ln -s "$outside" "$source/linked.txt"

    run python3 - "$TOOLKIT_DIR" "$source" "$destination" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
import codex_plugin

try:
    codex_plugin._copy_tree_strict(Path(sys.argv[2]), Path(sys.argv[3]))
except ValueError as error:
    assert "source symlink is not allowed" in str(error)
else:
    raise AssertionError("source symlink was accepted")
PY
    [ "$status" -eq 0 ]

    archive="$TEST_TMP/unsafe.zip"
    ln -s "$outside" "$archive"
    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" export --output "$archive"
    [ "$status" -ne 0 ]
    grep -q '^outside sentinel$' "$outside"
}

@test "codex-plugin: symlinked output ancestors cannot redirect archive writes" {
    outside="$TEST_TMP/outside-parent"
    linked_parent="$TEST_TMP/linked-parent"
    mkdir -p "$outside"
    printf 'outside archive sentinel\n' > "$outside/plugin.zip"
    ln -s "$outside" "$linked_parent"

    run python3 "$TOOLKIT_DIR/scripts/codex_plugin.py" \
        export --output "$linked_parent/plugin.zip"

    [ "$status" -ne 0 ]
    [[ "$output" == *"symlinked output ancestor"* ]]
    grep -q '^outside archive sentinel$' "$outside/plugin.zip"
}
