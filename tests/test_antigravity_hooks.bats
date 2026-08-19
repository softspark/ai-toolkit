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

@test "antigravity hooks: emits exact five-event namespaced schema" {
    generate_hooks
    run python3 - "$AG_HOOK_TMP/.agents/hooks.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
assert set(doc) == {"ai-toolkit"}
managed = doc["ai-toolkit"]
assert set(managed) == {
    "PreToolUse", "PostToolUse", "PreInvocation", "PostInvocation", "Stop"
}
for event in ("PreToolUse", "PostToolUse"):
    assert all(set(group) == {"matcher", "hooks"} for group in managed[event])
    assert all(set(hook) == {"command", "timeout"}
               for group in managed[event] for hook in group["hooks"])
for event in ("PreInvocation", "PostInvocation", "Stop"):
    assert all(set(hook) == {"command", "timeout"} for hook in managed[event])
PY
    [ "$status" -eq 0 ]
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
    grep -q '.agents/hooks/ai-toolkit-antigravity-hook.py' "$AG_HOOK_TMP/.agents/hooks.json"
}

@test "antigravity hooks: adapter maps run_command and denies destructive commands" {
    generate_hooks
    run bash -c "printf '%s' '{\"toolCall\":{\"name\":\"run_command\",\"args\":{\"CommandLine\":\"rm -rf /tmp/x\"}}}' | python3 '$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py' PreToolUse"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d == {"decision":"deny"}' "$output"
    [ "$status" -eq 0 ]
}

@test "antigravity hooks: adapter allows benign commands and PostToolUse is empty" {
    generate_hooks
    run bash -c "printf '%s' '{\"toolCall\":{\"name\":\"run_command\",\"args\":{\"CommandLine\":\"git status --short\"}}}' | python3 '$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py' PreToolUse"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"allow"}' ]
    run bash -c "printf '%s' '{}' | python3 '$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py' PostToolUse"
    [ "$status" -eq 0 ]
    [ "$output" = '{}' ]
}

@test "antigravity hooks: invocation and Stop outputs use native camelCase" {
    generate_hooks
    adapter="$AG_HOOK_TMP/.agents/hooks/ai-toolkit-antigravity-hook.py"
    run bash -c "printf '%s' '{}' | python3 '$adapter' PreInvocation"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["injectSteps"] and set(d["injectSteps"][0]) == {"ephemeralMessage"}' "$output"
    [ "$status" -eq 0 ]
    run bash -c "printf '%s' '{}' | python3 '$adapter' PostInvocation"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d == {"injectSteps":[],"terminationBehavior":""}' "$output"
    [ "$status" -eq 0 ]
    run bash -c "printf '%s' '{}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"stop"}' ]
    run bash -c "printf '%s' '{\"factualBlock\":true}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    run python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d["decision"] == "continue" and d["reason"]' "$output"
    [ "$status" -eq 0 ]
    run bash -c "printf '%s' '{\"factualBlock\":true,\"stopHookActive\":true}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"stop"}' ]
    run bash -c "printf '%s' '{\"factualBlock\":true,\"executionNum\":2}' | python3 '$adapter' Stop"
    [ "$status" -eq 0 ]
    [ "$output" = '{"decision":"stop"}' ]
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
