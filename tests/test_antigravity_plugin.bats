#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export AG_PLUGIN_TMP
    AG_PLUGIN_TMP="$(mktemp -d)"
}

teardown() {
    rm -rf "$AG_PLUGIN_TMP"
}

@test "antigravity plugin: deterministic self-contained export verifies offline" {
    first="$AG_PLUGIN_TMP/first.zip"
    second="$AG_PLUGIN_TMP/second.zip"
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" export --output "$first"
    [ "$status" -eq 0 ]
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" export --output "$second"
    [ "$status" -eq 0 ]
    [ "$(shasum "$first" | awk '{print $1}')" = "$(shasum "$second" | awk '{print $1}')" ]
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$first"
    [ "$status" -eq 0 ]
}

@test "antigravity plugin: archive has exact manifest and required resources" {
    archive="$AG_PLUGIN_TMP/plugin.zip"
    python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" export --output "$archive" >/dev/null
    run python3 - "$archive" <<'PY'
import json, subprocess, sys, tempfile, zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[1]) as zf:
    names = set(zf.namelist())
    manifest = json.loads(zf.read("ai-toolkit/plugin.json"))
    assert set(manifest) == {"$schema", "name", "description"}
    assert manifest["$schema"] == "https://antigravity.google/schemas/v1/plugin.json"
    assert manifest["name"] == "ai-toolkit"
    assert "ai-toolkit/hooks.json" in names
    assert "ai-toolkit/runtime/ai-toolkit-antigravity-hook.py" in names
    assert "ai-toolkit/LICENSE" in names
    assert any(name.startswith("ai-toolkit/rules/") for name in names)
    assert any(name.startswith("ai-toolkit/skills/") for name in names)
    assert any(name.startswith("ai-toolkit/agents/") for name in names)
    assert "ai-toolkit/resources/personas/backend-lead.md" in names
    assert "ai-toolkit/skills/briefing/scripts/session_token_stats.py" in names
    assert "ai-toolkit/scripts/audit_skills.py" in names
    hooks = zf.read("ai-toolkit/hooks.json").decode()
    assert "${extensionPath}/runtime/ai-toolkit-antigravity-hook.py" in hooks
    assert "/Users/" not in hooks and str(sys.argv[1]) not in hooks
    skill_docs = [name for name in names if name.endswith("/SKILL.md")]
    assert skill_docs
    assert all("${CLAUDE_SKILL_DIR}" not in zf.read(name).decode() for name in skill_docs)
    audit_skill = zf.read("ai-toolkit/skills/skill-audit/SKILL.md").decode()
    security_agent = zf.read(
        "ai-toolkit/agents/ai-toolkit-security-auditor/agent.md"
    ).decode()
    assert "${extensionPath}/scripts/audit_skills.py" in audit_skill
    assert "python3 scripts/audit_skills.py" not in audit_skill
    assert "${extensionPath}/skills/cve-scan/scripts/cve_scan.py" in security_agent
    assert "app/skills/cve-scan/scripts/cve_scan.py" not in security_agent

    with tempfile.TemporaryDirectory() as temporary:
        zf.extractall(temporary)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(temporary) / "ai-toolkit/scripts/audit_skills.py"),
                "--json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads(result.stdout)
        assert report["summary"]["total"] >= 0
PY
    [ "$status" -eq 0 ]
}

@test "antigravity plugin: verify rejects tampered hooks and path traversal" {
    archive="$AG_PLUGIN_TMP/plugin.zip"
    expanded="$AG_PLUGIN_TMP/expanded"
    runtime_expanded="$AG_PLUGIN_TMP/runtime-expanded"
    extra_expanded="$AG_PLUGIN_TMP/extra-expanded"
    missing_expanded="$AG_PLUGIN_TMP/missing-expanded"
    member_expanded="$AG_PLUGIN_TMP/member-expanded"
    python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" export --output "$archive" >/dev/null
    mkdir "$expanded"
    (cd "$expanded" && unzip -q "$archive")
    python3 - "$expanded/ai-toolkit/hooks.json" <<'PY'
import json, sys
p=sys.argv[1]
d=json.load(open(p)); d["ai-toolkit"]["Stop"][0]["command"]="python3 /tmp/evil.py Stop"
json.dump(d, open(p,"w"))
PY
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$expanded/ai-toolkit"
    [ "$status" -ne 0 ]

    mkdir "$runtime_expanded" "$extra_expanded" "$missing_expanded" "$member_expanded"
    (cd "$runtime_expanded" && unzip -q "$archive")
    printf '\n# tampered runtime\n' >> "$runtime_expanded/ai-toolkit/runtime/ai-toolkit-antigravity-hook.py"
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$runtime_expanded/ai-toolkit"
    [ "$status" -ne 0 ]

    (cd "$extra_expanded" && unzip -q "$archive")
    mkdir "$extra_expanded/ai-toolkit/unexpected-dir"
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$extra_expanded/ai-toolkit"
    [ "$status" -ne 0 ]

    (cd "$missing_expanded" && unzip -q "$archive")
    mv "$missing_expanded/ai-toolkit/LICENSE" "$AG_PLUGIN_TMP/LICENSE.missing"
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$missing_expanded/ai-toolkit"
    [ "$status" -ne 0 ]

    (cd "$member_expanded" && unzip -q "$archive")
    printf '\nmodified\n' >> "$member_expanded/ai-toolkit/LICENSE"
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$member_expanded/ai-toolkit"
    [ "$status" -ne 0 ]

    run python3 - "$TOOLKIT_DIR" "$AG_PLUGIN_TMP/traversal.zip" <<'PY'
import sys, zipfile
with zipfile.ZipFile(sys.argv[2], "w") as zf:
    zf.writestr("../escape", "x")
sys.path.insert(0, sys.argv[1] + "/scripts")
from antigravity_plugin import verify
verify(sys.argv[2])
PY
    [ "$status" -ne 0 ]
}

@test "antigravity plugin: refuses symlink source and preserves destination on failed export" {
    run python3 - "$TOOLKIT_DIR" "$AG_PLUGIN_TMP" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/scripts")
import antigravity_plugin
root=Path(sys.argv[2]); source=root/"source"; source.mkdir(); (source/"real").write_text("x")
(source/"link").symlink_to(source/"real")
try:
    antigravity_plugin._collect_tree(source, "rules")
except RuntimeError:
    pass
else:
    raise AssertionError("symlink source must be rejected")
PY
    [ "$status" -eq 0 ]

    archive_path="$AG_PLUGIN_TMP/existing.zip"
    printf '%s' original > "$archive_path"
    run env AI_TOOLKIT_ANTIGRAVITY_PLUGIN_INJECT_FAILURE=1 \
        python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" export --output "$archive_path"
    [ "$status" -ne 0 ]
    [ "$(cat "$archive_path")" = original ]
}

@test "antigravity plugin: verify rejects unsafe file mode" {
    plugin="$AG_PLUGIN_TMP/plugin-dir"
    python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" export --output "$AG_PLUGIN_TMP/plugin.zip" >/dev/null
    mkdir "$plugin"
    (cd "$plugin" && unzip -q "$AG_PLUGIN_TMP/plugin.zip")
    chmod 744 "$plugin/ai-toolkit/hooks.json"
    run python3 "$TOOLKIT_DIR/scripts/antigravity_plugin.py" verify "$plugin/ai-toolkit"
    [ "$status" -ne 0 ]
}
