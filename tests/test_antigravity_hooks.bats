#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export AG_HOOK_TMP
    AG_HOOK_TMP="$(mktemp -d)"
}

teardown() {
    rm -rf "$AG_HOOK_TMP"
}

generate_hooks() {
    (cd "$AG_HOOK_TMP" && python3 "$TOOLKIT_DIR/scripts/generate_antigravity_hooks.py" . >/dev/null)
}

# Run every managed handler the way Antigravity does: through `sh -c`, with
# the working directory set to the directory that holds hooks.json.
run_handlers_like_agy() {
    local hooks_json="$1" cwd="$2"
    python3 - "$hooks_json" "$cwd" <<'PY'
import json, subprocess, sys
hooks_json, cwd = sys.argv[1], sys.argv[2]
managed = json.load(open(hooks_json, encoding="utf-8"))["ai-toolkit"]
payloads = {
    "PreToolUse": {"toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf /"}}},
    "PreInvocation": {"invocationNum": 1, "workspacePaths": ["/w"]},
    "Stop": {"executionNum": 1, "fullyIdle": True},
}
for event, entries in managed.items():
    handlers = [h for g in entries for h in g["hooks"]] if event == "PreToolUse" else entries
    for handler in handlers:
        done = subprocess.run(["sh", "-c", handler["command"]], cwd=cwd,
                              input=json.dumps(payloads[event]), text=True,
                              capture_output=True, timeout=10)
        if done.returncode != 0:
            print(f"{event}: exit {done.returncode}: {done.stderr.strip()}")
            sys.exit(1)
        result = json.loads(done.stdout)
        print(f"{event} {json.dumps(result, sort_keys=True)}")
PY
}

@test "antigravity hooks: registers only events the adapter acts on" {
    generate_hooks
    run python3 - "$AG_HOOK_TMP/.agents/hooks.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert set(doc) == {"ai-toolkit"}
managed = doc["ai-toolkit"]
assert set(managed) == {"PreToolUse", "PreInvocation", "Stop"}, managed
# A hook that only inspects run_command must not gate file reads or writes.
assert [group["matcher"] for group in managed["PreToolUse"]] == ["run_command"]
assert all(set(group) == {"matcher", "hooks"} for group in managed["PreToolUse"])
assert all(set(hook) == {"command", "timeout"}
           for group in managed["PreToolUse"] for hook in group["hooks"])
for event in ("PreInvocation", "Stop"):
    assert all(set(hook) == {"command", "timeout"} for hook in managed[event])
PY
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
}

@test "antigravity hooks: every handler starts from the hooks.json directory like agy" {
    generate_hooks
    run run_handlers_like_agy "$AG_HOOK_TMP/.agents/hooks.json" "$AG_HOOK_TMP/.agents"
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
    [[ "$output" == *'PreToolUse {"decision": "deny"}'* ]]
    [[ "$output" == *'PreInvocation {"injectSteps"'* ]]
    [[ "$output" == *'Stop {"decision": "stop"}'* ]]
}

@test "antigravity hooks: commands are relative to hooks.json, not the workspace root" {
    # agy never starts a handler from the workspace root (agy 1.3.1 hook
    # reference and its logs); the command must not depend on it either way.
    generate_hooks
    run run_handlers_like_agy "$AG_HOOK_TMP/.agents/hooks.json" "$AG_HOOK_TMP"
    [ "$status" -ne 0 ]
    ! grep -q '\.agents/hooks/' "$AG_HOOK_TMP/.agents/hooks.json"
}

@test "antigravity hooks: global hooks start from ~/.gemini/config like agy" {
    home="$AG_HOOK_TMP/home"
    mkdir -p "$home"
    python3 - "$TOOLKIT_DIR/scripts" "$home" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from generate_antigravity_hooks import generate_global
generate_global(Path(sys.argv[2]))
PY
    run run_handlers_like_agy "$home/.gemini/config/hooks.json" "$home/.gemini/config"
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
    [[ "$output" == *'PreToolUse {"decision": "deny"}'* ]]
    ! grep -q 'HOME' "$home/.gemini/config/hooks.json"
}

@test "antigravity hooks: diagnose reports handlers that cannot start and stale namespaces" {
    mkdir -p "$AG_HOOK_TMP/.agents/hooks"
    cat > "$AG_HOOK_TMP/.agents/hooks.json" <<'JSON'
{"ai-toolkit":{"PreToolUse":[{"matcher":"run_command|view_file","hooks":[{"command":"python3 .agents/hooks/ai-toolkit-antigravity-hook.py PreToolUse","timeout":5}]}]}}
JSON
    run python3 - "$TOOLKIT_DIR/scripts" "$AG_HOOK_TMP/.agents/hooks.json" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from generate_antigravity_hooks import diagnose, generate, is_current
path = Path(sys.argv[2])
problems = diagnose(path)
assert len(problems) == 1 and ".agents/.agents/hooks" in problems[0], problems
assert not is_current(path)
generate(path.parent.parent)
assert diagnose(path) == [] and is_current(path)
PY
    [ "$status" -eq 0 ] || { echo "$output"; return 1; }
}

@test "antigravity hooks: merge preserves unrelated namespaces and replaces managed namespace" {
    mkdir -p "$AG_HOOK_TMP/.agents"
    cat > "$AG_HOOK_TMP/.agents/hooks.json" <<'JSON'
{"user-hooks":{"Stop":[{"command":"keep","timeout":9}]},"ai-toolkit":{"Bogus":[]}}
JSON
    generate_hooks
    run python3 - "$AG_HOOK_TMP/.agents/hooks.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert doc["user-hooks"]["Stop"][0]["command"] == "keep"
assert "Bogus" not in doc["ai-toolkit"]
PY
    [ "$status" -eq 0 ]
}

@test "antigravity hooks: generation is idempotent and runtime is adjacent" {
    generate_hooks
    first="$(shasum "$AG_HOOK_TMP/.agents/hooks.json" "$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py")"
    generate_hooks
    second="$(shasum "$AG_HOOK_TMP/.agents/hooks.json" "$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py")"
    [ "$first" = "$second" ]
    grep -q '"python3 hooks/ai-toolkit-antigravity-hook.py PreToolUse"' "$AG_HOOK_TMP/.agents/hooks.json"
}

@test "antigravity hooks: adapter maps run_command and denies destructive commands" {
    generate_hooks
    run bash -c "printf '%s' '{\"toolCall\":{\"name\":\"run_command\",\"args\":{\"CommandLine\":\"rm -rf /tmp/x\"}}}' | python3 '$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py' PreToolUse"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d == {"decision":"deny"}' "$output"
    [ "$status" -eq 0 ]
}

@test "antigravity hooks: adapter allows benign commands and rejects unregistered events" {
    generate_hooks
    run bash -c "printf '%s' '{\"toolCall\":{\"name\":\"run_command\",\"args\":{\"CommandLine\":\"git status --short\"}}}' | python3 '$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py' PreToolUse"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"allow"}' ]
    run bash -c "printf '%s' '{}' | python3 '$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py' PostToolUse"
    [ "$status" -eq 2 ]
}

@test "antigravity hooks: invocation and Stop outputs use native camelCase" {
    generate_hooks
    adapter="$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py"
    run bash -c "printf '%s' '{}' | python3 '$adapter' PreInvocation"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["injectSteps"] and set(d["injectSteps"][0]) == {"ephemeralMessage"}' "$output"
    [ "$status" -eq 0 ]
    run bash -c "printf '%s' '{}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"stop"}' ]
    run bash -c "printf '%s' '{\"executionNum\":1,\"terminationReason\":\"agent_stopped\",\"error\":\"pending validation\",\"fullyIdle\":false}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["decision"] == "continue" and d["reason"]' "$output"
    [ "$status" -eq 0 ]
    run bash -c "printf '%s' '{\"executionNum\":1,\"terminationReason\":\"completed\",\"fullyIdle\":true}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"stop"}' ]
    run bash -c "printf '%s' '{\"executionNum\":2,\"terminationReason\":\"agent_stopped\",\"fullyIdle\":false}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"stop"}' ]
    ! grep -qE 'factualBlock|stopHookActive' "$adapter"
}

@test "antigravity hooks: ai-toolkit doctor fails on the caller's broken project hooks" {
    project="$AG_HOOK_TMP/project"
    mkdir -p "$project/.agents/hooks" "$AG_HOOK_TMP/home"
    cat > "$project/.agents/hooks.json" <<'JSON'
{"ai-toolkit":{"Stop":[{"command":"python3 .agents/hooks/ai-toolkit-antigravity-hook.py Stop","timeout":5}]}}
JSON
    cd "$project"
    project="$(pwd -P)"  # macOS temp dirs resolve through /private
    run env HOME="$AG_HOOK_TMP/home" node "$TOOLKIT_DIR/bin/ai-toolkit.js" doctor
    [ "$status" -ne 0 ]
    [[ "$output" == *"Antigravity hook cannot start: $project/.agents/hooks.json: Stop"* ]]
    [[ "$output" == *"ai-toolkit install --local --editors antigravity"* ]]
}

@test "antigravity hooks: rejects symlinked config root without touching target" {
    external="$AG_HOOK_TMP/external"
    project="$AG_HOOK_TMP/project"
    mkdir -p "$external" "$project"
    ln -s "$external" "$project/.agents"
    run python3 "$TOOLKIT_DIR/scripts/generate_antigravity_hooks.py" "$project"
    [ "$status" -ne 0 ]
    [ ! -e "$external/hooks.json" ]
}
