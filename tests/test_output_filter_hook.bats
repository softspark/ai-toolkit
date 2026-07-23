#!/usr/bin/env bats
# Contract tests for the Claude PostToolUse output-filter adapter.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
HOOK="$TOOLKIT_DIR/app/hooks/filter-tool-output.sh"

setup() {
    TEST_DIR="$(mktemp -d)"
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME/.softspark/ai-toolkit/hooks" \
        "$HOME/.softspark/ai-toolkit/scripts" "$TEST_DIR/bin"
    # The hook refuses to run a missing or symlinked runtime path.
    : > "$HOME/.softspark/ai-toolkit/scripts/output_filter_hook.py"

    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
echo "python must not run in off mode" >&2
exit 91
EOF
    chmod +x "$TEST_DIR/bin/python3"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "output filter hook exits silently without Python when policy mode is off" {
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"off"}
EOF

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "output filter hook transports observe payload and policy to the Python runtime" {
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"observe"}
EOF
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CAPTURE_ARGS"
IFS= read -r payload || true
printf '%s' "$payload" > "$CAPTURE_STDIN"
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export CAPTURE_ARGS="$TEST_DIR/args"
    export CAPTURE_STDIN="$TEST_DIR/stdin"
    payload='{"hook_event_name":"PostToolUse","tool_name":"Bash","tool_response":{"stdout":"ok","stderr":"","interrupted":false,"isImage":false}}'

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" bash "$HOOK" <<< "$payload"

    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ "$(sed -n '1p' "$CAPTURE_ARGS")" = "-S" ]
    [ "$(sed -n '2p' "$CAPTURE_ARGS")" = "$HOME/.softspark/ai-toolkit/scripts/output_filter_hook.py" ]
    [ "$(sed -n '3p' "$CAPTURE_ARGS")" = "hook" ]
    [ "$(sed -n '4p' "$CAPTURE_ARGS")" = "--policy" ]
    [ "$(sed -n '5p' "$CAPTURE_ARGS")" = "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" ]
    [ "$(cat "$CAPTURE_STDIN")" = "$payload" ]
}

@test "output filter hook respects the minimal hook profile" {
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"observe"}
EOF
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
touch "$PYTHON_RAN"
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export PYTHON_RAN="$TEST_DIR/minimal-python-ran"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        TOOLKIT_HOOK_PROFILE=minimal \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$PYTHON_RAN" ]
}

@test "output filter hook fails open when the Python runtime fails" {
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"safe"}
EOF
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
echo "runtime failure" >&2
exit 70
EOF
    chmod +x "$TEST_DIR/bin/python3"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "output filter hook is the last Claude PostToolUse Bash matcher" {
    run python3 - "$TOOLKIT_DIR/app/hooks.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    hooks = json.load(handle)["hooks"]["PostToolUse"]

last = hooks[-1]
assert last["matcher"] == "Bash"
assert last["_source"] == "ai-toolkit"
assert last["hooks"] == [{
    "type": "command",
    "command": "\"$HOME/.softspark/ai-toolkit/hooks/filter-tool-output.sh\"",
}]
PY

    [ "$status" -eq 0 ]
}

@test "ai-toolkit CLI exposes the native output-filter command" {
    run node "$TOOLKIT_DIR/bin/ai-toolkit.js" help

    [ "$status" -eq 0 ]
    [[ "$output" == *"output-filter"* ]]
}

@test "output filter hook prefers the trusted current project policy" {
    project="$TEST_DIR/project-one"
    mkdir -p "$project/.claude"
    printf '{"projects":[{"path":"%s"}]}\n' "$project" \
        > "$HOME/.softspark/ai-toolkit/projects.json"
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"off"}
EOF
    cat > "$project/.claude/ai-toolkit-output-filter.json" <<'EOF'
{"mode":"observe"}
EOF
    printf 'ai-toolkit-output-filter-policy-v1\n' \
        > "$project/.claude/.ai-toolkit-output-filter.owner"
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$@" > "$CAPTURE_ARGS"
cat >/dev/null
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export CAPTURE_ARGS="$TEST_DIR/project-args"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        CLAUDE_PROJECT_DIR="$project" \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ "$(sed -n '5p' "$CAPTURE_ARGS")" = \
        "$project/.claude/ai-toolkit-output-filter.json" ]
}

@test "output filter hook rejects an invalid policy before invoking Python" {
    invalid_policy="$TEST_DIR/invalid-policy.json"
    printf '{"mode":"lossy"}\n' > "$invalid_policy"
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
touch "$PYTHON_RAN"
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export PYTHON_RAN="$TEST_DIR/python-ran"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        AI_TOOLKIT_OUTPUT_FILTER_POLICY="$invalid_policy" \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$PYTHON_RAN" ]
}

@test "output filter hook source is executable" {
    [ -x "$HOOK" ]
}

@test "output filter hook ignores a project policy from an unregistered checkout" {
    project="$TEST_DIR/cloned-repo"
    mkdir -p "$project/.claude"
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"off"}
EOF
    cat > "$project/.claude/ai-toolkit-output-filter.json" <<'EOF'
{"mode":"safe"}
EOF
    printf 'ai-toolkit-output-filter-policy-v1\n' \
        > "$project/.claude/.ai-toolkit-output-filter.owner"
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
touch "$PYTHON_RAN"
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export PYTHON_RAN="$TEST_DIR/unregistered-python-ran"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        CLAUDE_PROJECT_DIR="$project" \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$PYTHON_RAN" ]
}

@test "output filter hook refuses a missing or symlinked runtime override" {
    cat > "$HOME/.softspark/ai-toolkit/hooks/output-filter-policy.json" <<'EOF'
{"mode":"observe"}
EOF
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
touch "$PYTHON_RAN"
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export PYTHON_RAN="$TEST_DIR/override-python-ran"
    : > "$TEST_DIR/real-runtime.py"
    ln -s "$TEST_DIR/real-runtime.py" "$TEST_DIR/runtime-link.py"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        AI_TOOLKIT_OUTPUT_FILTER_HOOK_RUNTIME="$TEST_DIR/missing.py" \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'
    [ "$status" -eq 0 ]
    [ ! -e "$PYTHON_RAN" ]

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        AI_TOOLKIT_OUTPUT_FILTER_HOOK_RUNTIME="$TEST_DIR/runtime-link.py" \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'
    [ "$status" -eq 0 ]
    [ ! -e "$PYTHON_RAN" ]
}

@test "output filter hook rejects a symlinked project policy directory" {
    project="$TEST_DIR/symlink-project"
    external="$TEST_DIR/external-claude"
    mkdir -p "$project" "$external"
    cat > "$external/ai-toolkit-output-filter.json" <<'EOF'
{"mode":"safe"}
EOF
    printf 'ai-toolkit-output-filter-policy-v1\n' \
        > "$external/.ai-toolkit-output-filter.owner"
    ln -s "$external" "$project/.claude"
    cat > "$TEST_DIR/bin/python3" <<'EOF'
#!/usr/bin/env bash
touch "$PYTHON_RAN"
EOF
    chmod +x "$TEST_DIR/bin/python3"
    export PYTHON_RAN="$TEST_DIR/symlink-python-ran"

    run env PATH="$TEST_DIR/bin:/usr/bin:/bin" \
        CLAUDE_PROJECT_DIR="$project" \
        bash "$HOOK" <<< '{"tool_name":"Bash"}'

    [ "$status" -eq 0 ]
    [ -z "$output" ]
    [ ! -e "$PYTHON_RAN" ]
}
