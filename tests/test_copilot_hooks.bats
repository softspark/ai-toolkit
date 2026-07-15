#!/usr/bin/env bats
# Native GitHub Copilot hooks generator and runtime contract tests.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_ROOT="$(mktemp -d)"
    export HOME="$TEST_ROOT/home"
    mkdir -p "$HOME"
}

teardown() {
    rm -rf "$TEST_ROOT"
}

@test "copilot-hooks: repository config uses native v1 schema and self-contained commands" {
    run python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project"
    [ "$status" -eq 0 ]
    config="$TEST_ROOT/project/.github/hooks/ai-toolkit.json"
    runtime="$TEST_ROOT/project/.github/hooks/ai-toolkit/copilot_hook.py"
    [ -f "$config" ]
    [ -x "$runtime" ]

    run python3 - "$config" <<'PY'
import json
import re
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert set(data) == {"version", "hooks"}
assert data["version"] == 1
assert set(data["hooks"]) == {
    "sessionStart", "preToolUse", "postToolUse", "postToolUseFailure",
    "subagentStart", "agentStop",
}
matcher_events = {"notification", "permissionRequest", "postToolUse", "preCompact", "preToolUse", "subagentStart"}
allowed = {"type", "bash", "powershell", "cwd", "env", "timeoutSec", "matcher"}
for event, entries in data["hooks"].items():
    assert entries
    for entry in entries:
        assert set(entry) <= allowed, (event, entry)
        assert entry["type"] == "command"
        assert entry["env"] == {"AI_TOOLKIT_HOOK_OWNER": "ai-toolkit"}
        assert ".github/hooks/ai-toolkit/copilot_hook.py" in entry["bash"]
        assert ".softspark/ai-toolkit" not in entry["bash"]
        assert entry["timeoutSec"] > 0
        if "matcher" in entry:
            assert event in matcher_events
            re.compile(entry["matcher"])
assert data["hooks"]["postToolUse"][0]["matcher"] == "create|edit"
assert "matcher" not in data["hooks"]["preToolUse"][0]
PY
    [ "$status" -eq 0 ]
    python3 -m py_compile "$runtime"
}

@test "copilot-hooks: user install honors COPILOT_HOME" {
    custom_home="$TEST_ROOT/custom-copilot"
    run env COPILOT_HOME="$custom_home" HOME="$HOME" \
        python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" --global "$HOME"
    [ "$status" -eq 0 ]
    config="$custom_home/hooks/ai-toolkit.json"
    runtime="$custom_home/hooks/ai-toolkit/copilot_hook.py"
    [ -f "$config" ]
    [ -x "$runtime" ]
    grep -Fq "$runtime" "$config"
    [ ! -e "$HOME/.copilot/hooks/ai-toolkit.json" ]
}

@test "copilot-hooks: preserves unrelated user files and is deterministic" {
    hooks="$TEST_ROOT/project/.github/hooks"
    mkdir -p "$hooks/user-assets"
    printf '%s\n' '{"version":1,"hooks":{"sessionEnd":[{"bash":"echo user"}]}}' \
        > "$hooks/user.json"
    printf '%s\n' 'user asset' > "$hooks/user-assets/custom.txt"

    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project" >/dev/null
    shasum "$hooks/user.json" "$hooks/user-assets/custom.txt" > "$TEST_ROOT/user.before"
    find "$hooks" -type f -exec shasum {} \; | sort > "$TEST_ROOT/all.before"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project" >/dev/null
    shasum "$hooks/user.json" "$hooks/user-assets/custom.txt" > "$TEST_ROOT/user.after"
    find "$hooks" -type f -exec shasum {} \; | sort > "$TEST_ROOT/all.after"
    cmp "$TEST_ROOT/user.before" "$TEST_ROOT/user.after"
    cmp "$TEST_ROOT/all.before" "$TEST_ROOT/all.after"
}

@test "copilot-hooks: profile cleanup preserves a user-modified reserved bundle" {
    project="$TEST_ROOT/project"
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$project" >/dev/null
    config="$project/.github/hooks/ai-toolkit.json"
    runtime="$project/.github/hooks/ai-toolkit/copilot_hook.py"
    python3 - "$config" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
data["hooks"]["sessionEnd"] = [{"type": "command", "bash": "echo user"}]
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY

    run python3 - "$TOOLKIT_DIR" "$project" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from generate_copilot_hooks import cleanup

cleanup(Path(sys.argv[2]))
PY
    [ "$status" -eq 0 ]
    [ -f "$config" ]
    [ -f "$runtime" ]
    grep -q 'echo user' "$config"
}

@test "copilot-hooks: refuses user-owned reserved files without overwriting" {
    hooks="$TEST_ROOT/project/.github/hooks"
    mkdir -p "$hooks"
    printf '%s\n' '{"version":1,"hooks":{"sessionEnd":[{"bash":"echo user"}]}}' \
        > "$hooks/ai-toolkit.json"
    cp "$hooks/ai-toolkit.json" "$TEST_ROOT/config.before"

    run python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project"
    [ "$status" -ne 0 ]
    cmp "$TEST_ROOT/config.before" "$hooks/ai-toolkit.json"
    [ ! -e "$hooks/ai-toolkit/copilot_hook.py" ]
}

@test "copilot-hooks: refuses symlinked roots and config files" {
    external="$TEST_ROOT/external"
    mkdir -p "$external"
    printf '%s\n' 'sentinel' > "$external/sentinel"
    shasum "$external/sentinel" > "$TEST_ROOT/external.before"

    mkdir -p "$TEST_ROOT/symlink-root"
    ln -s "$external" "$TEST_ROOT/symlink-root/.github"
    run python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/symlink-root"
    [ "$status" -ne 0 ]
    shasum "$external/sentinel" > "$TEST_ROOT/external.after"
    cmp "$TEST_ROOT/external.before" "$TEST_ROOT/external.after"

    mkdir -p "$TEST_ROOT/symlink-file/.github/hooks"
    ln -s "$external/sentinel" "$TEST_ROOT/symlink-file/.github/hooks/ai-toolkit.json"
    run python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/symlink-file"
    [ "$status" -ne 0 ]
    grep -q '^sentinel$' "$external/sentinel"
}

@test "copilot-hooks: failed late replacement rolls back prior artifacts" {
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project" >/dev/null

    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT/project" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
project = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_copilot_hooks as module

config = project / ".github" / "hooks" / "ai-toolkit.json"
runtime = project / ".github" / "hooks" / "ai-toolkit" / "copilot_hook.py"
before = {path: (path.read_bytes(), path.stat().st_mode & 0o777) for path in (config, runtime)}
real_replace = os.replace
calls = 0

def fail_second_replace(source, destination):
    global calls
    calls += 1
    if calls == 2:
        raise OSError("injected late replacement failure")
    return real_replace(source, destination)

try:
    with mock.patch("os.replace", side_effect=fail_second_replace):
        module.generate(project)
except OSError as error:
    assert "injected" in str(error)
else:
    raise AssertionError("generator unexpectedly succeeded")

for path, expected in before.items():
    assert (path.read_bytes(), path.stat().st_mode & 0o777) == expected, path
PY
    [ "$status" -eq 0 ]
}

@test "copilot-hooks: preToolUse emits native deny JSON and allows safe force variants" {
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project" >/dev/null
    runtime="$TEST_ROOT/project/.github/hooks/ai-toolkit/copilot_hook.py"

    run python3 - "$runtime" <<'PY'
import json
import subprocess
import sys

runtime = sys.argv[1]
dangerous = "r" + "m -r" + "f /tmp/example"
cases = [
    ({"toolName": "bash", "toolArgs": {"command": dangerous}}, "deny"),
    ({"toolName": "bash", "toolArgs": {"command": "git push --force-with-lease"}}, None),
    ({"toolName": "edit", "toolArgs": {"path": "/Users/not-the-active-user/file"}}, "deny"),
]
for payload, expected in cases:
    result = subprocess.run(
        [sys.executable, runtime, "pre-tool-use"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result
    if expected is None:
        assert result.stdout == "", result.stdout
    else:
        output = json.loads(result.stdout)
        assert output["permissionDecision"] == expected, output
        assert output["permissionDecisionReason"], output
PY
    [ "$status" -eq 0 ]
}

@test "copilot-hooks: context events and failure event follow native output contracts" {
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project" >/dev/null
    runtime="$TEST_ROOT/project/.github/hooks/ai-toolkit/copilot_hook.py"

    for event in session-start post-tool-use subagent-start; do
        run bash -c "printf '%s' '{}' | python3 '$runtime' '$event'"
        [ "$status" -eq 0 ]
        python3 -c 'import json,sys; assert json.loads(sys.argv[1])["additionalContext"]' "$output"
    done

    run bash -c "printf '%s' '{}' | python3 '$runtime' post-tool-use-failure"
    [ "$status" -eq 2 ]
    [[ "$output" == *"tool failed"* ]]
}

@test "copilot-hooks: agentStop quality gate blocks twice then opens its circuit" {
    python3 "$TOOLKIT_DIR/scripts/generate_copilot_hooks.py" "$TEST_ROOT/project" >/dev/null
    runtime="$TEST_ROOT/project/.github/hooks/ai-toolkit/copilot_hook.py"
    project="$TEST_ROOT/quality-project"
    fake_bin="$TEST_ROOT/bin"
    state="$TEST_ROOT/state"
    mkdir -p "$project" "$fake_bin"
    printf '%s\n' '[project]' 'name = "quality-fixture"' 'version = "0.0.0"' \
        > "$project/pyproject.toml"
    cat > "$fake_bin/ruff" <<'SH'
#!/usr/bin/env bash
echo 'fixture quality failure' >&2
exit 1
SH
    chmod +x "$fake_bin/ruff"

    run env PATH="$fake_bin:$PATH" AI_TOOLKIT_COPILOT_STATE_DIR="$state" \
        python3 - "$runtime" "$project" <<'PY'
import json
import os
import subprocess
import sys

runtime, project = sys.argv[1:]
payload = json.dumps({"sessionId": "quality-session", "cwd": project})
outputs = []
for _ in range(3):
    result = subprocess.run(
        [sys.executable, runtime, "agent-stop"],
        input=payload,
        text=True,
        capture_output=True,
        env=os.environ,
        check=False,
    )
    assert result.returncode == 0, result
    outputs.append(result.stdout)
for output in outputs[:2]:
    parsed = json.loads(output)
    assert parsed["decision"] == "block"
    assert "fixture quality failure" in parsed["reason"]
assert outputs[2] == ""
PY
    [ "$status" -eq 0 ]
}
