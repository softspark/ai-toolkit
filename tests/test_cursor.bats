#!/usr/bin/env bats
# Cursor-specific tests for generate_cursor_mdc.py and generate_cursor_rules.py.
# The bulk of Cursor coverage lives in test_generators.bats; this file adds
# activation-mode and frontmatter contract tests that the 2026-04 docs sweep
# surfaced.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup_file() {
    export CR_TMP; CR_TMP="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$CR_TMP" >/dev/null
}

teardown_file() {
    rm -rf "$CR_TMP"
}

# ── Frontmatter contract ──────────────────────────────────────────────────

@test "cursor: every .mdc begins with a YAML frontmatter fence" {
    for f in "$CR_TMP"/.cursor/rules/ai-toolkit-*.mdc; do
        head -1 "$f" | grep -q '^---$' || {
            echo "missing frontmatter fence: $f" >&2
            return 1
        }
    done
}

@test "cursor: every .mdc declares alwaysApply (the Cursor required key)" {
    for f in "$CR_TMP"/.cursor/rules/ai-toolkit-*.mdc; do
        head -10 "$f" | grep -q '^alwaysApply: ' || {
            echo "missing alwaysApply: $f" >&2
            return 1
        }
    done
}

@test "cursor: alwaysApply is only ever true or false" {
    for f in "$CR_TMP"/.cursor/rules/ai-toolkit-*.mdc; do
        val=$(head -10 "$f" | grep -m1 '^alwaysApply: ' | awk '{print $2}')
        case "$val" in
          true|false) ;;
          *) echo "bad alwaysApply '$val' in $f" >&2; return 1 ;;
        esac
    done
}

# ── Rule type mapping ─────────────────────────────────────────────────────

@test "cursor: agents-and-skills.mdc is Always Apply" {
    grep -q '^alwaysApply: true$' \
      "$CR_TMP/.cursor/rules/ai-toolkit-agents-and-skills.mdc"
}

@test "cursor: security.mdc is Always Apply" {
    grep -q '^alwaysApply: true$' \
      "$CR_TMP/.cursor/rules/ai-toolkit-security.mdc"
}

@test "cursor: testing.mdc is Apply to Specific Files (has globs)" {
    f="$CR_TMP/.cursor/rules/ai-toolkit-testing.mdc"
    grep -q '^globs: ' "$f"
    grep -q '^alwaysApply: false$' "$f"
}

@test "cursor: testing.mdc globs target test patterns" {
    f="$CR_TMP/.cursor/rules/ai-toolkit-testing.mdc"
    grep '^globs: ' "$f" | grep -q '\*\*/\*\.test\.\*'
    grep '^globs: ' "$f" | grep -q '\*\*/tests/\*\*'
}

@test "cursor: code-style.mdc is Apply Intelligently (description, no always/globs)" {
    f="$CR_TMP/.cursor/rules/ai-toolkit-code-style.mdc"
    grep -q '^description: ' "$f"
    grep -q '^alwaysApply: false$' "$f"
    ! grep -q '^globs: ' "$f"
}

# ── Legacy .cursorrules generator ─────────────────────────────────────────

@test "cursor: generate_cursor_rules.py still produces non-empty output" {
    out="$(mktemp)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_rules.py" > "$out" 2>/dev/null
    [ "$(wc -c < "$out" | xargs)" -gt 200 ]
    rm -f "$out"
}

@test "cursor: .mdc regeneration is idempotent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$tmp" >/dev/null
    snap1=$(find "$tmp" -type f | sort | xargs shasum | shasum | awk '{print $1}')
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_mdc.py" "$tmp" >/dev/null
    snap2=$(find "$tmp" -type f | sort | xargs shasum | shasum | awk '{print $1}')
    [ "$snap1" = "$snap2" ]
    rm -rf "$tmp"
}

# ── Native hook contract ─────────────────────────────────────────────────────────────────

@test "cursor hooks: emits every documented Cursor 3.11 event" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    python3 - "$tmp/.cursor/hooks.json" <<'PY'
import json
import sys

expected = {
    "sessionStart", "sessionEnd", "preToolUse", "postToolUse",
    "postToolUseFailure", "subagentStart", "subagentStop",
    "beforeShellExecution", "afterShellExecution", "beforeMCPExecution",
    "afterMCPExecution", "beforeReadFile", "afterFileEdit",
    "beforeSubmitPrompt", "preCompact", "stop", "afterAgentResponse",
    "afterAgentThought", "beforeTabFileRead", "afterTabFileEdit",
    "workspaceOpen",
}
data = json.load(open(sys.argv[1], encoding="utf-8"))
missing = expected - set(data["hooks"])
assert not missing, f"missing documented Cursor hook events: {sorted(missing)}"
PY
    rm -rf "$tmp"
}

@test "cursor hooks: stop requests one bounded retry when quality check fails" {
    tmp="$(mktemp -d)"
    fake_bin="$tmp/fake-bin"
    mkdir -p "$fake_bin"
    touch "$tmp/pyproject.toml"
    printf '#!/bin/sh\necho cursor-quality-failed >&2\nexit 1\n' > "$fake_bin/ruff"
    chmod +x "$fake_bin/ruff"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null

    run env PATH="$fake_bin:$PATH" CURSOR_PROJECT_DIR="$tmp" \
        python3 "$tmp/.cursor/hooks/ai-toolkit/cursor_hook.py" stop <<'JSON'
{"status":"completed","loop_count":0}
JSON
    [ "$status" -eq 0 ]
    python3 - "$output" <<'PY'
import json
import sys

response = json.loads(sys.argv[1])
assert "cursor-quality-failed" in response["followup_message"]
PY
    rm -rf "$tmp"
}

@test "cursor hooks: follow-up events declare the constitutional loop limit" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    python3 - "$tmp/.cursor/hooks.json" <<'PY'
import json
import sys

hooks = json.load(open(sys.argv[1], encoding="utf-8"))["hooks"]
for event in ("stop", "subagentStop"):
    entries = [
        entry for entry in hooks[event]
        if "cursor_hook.py" in entry.get("command", "")
    ]
    assert entries and entries[0].get("loop_limit") == 5, (event, entries)
PY
    rm -rf "$tmp"
}

@test "cursor hooks: project manifest uses an executable repo-vendored runtime" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    runtime="$tmp/.cursor/hooks/ai-toolkit/cursor_hook.py"
    [ -x "$runtime" ]
    ! grep -q '\$HOME/.softspark' "$tmp/.cursor/hooks.json"
    ! grep -qE '/Users/|/home/' "$tmp/.cursor/hooks.json"
    grep -q '\.cursor/hooks/ai-toolkit/cursor_hook.py' "$tmp/.cursor/hooks.json"
    ! grep -q '\$HOME/.softspark' "$runtime"
    rm -rf "$tmp"
}

@test "cursor hooks: managed command entries contain only documented schema keys" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    python3 - "$tmp/.cursor/hooks.json" <<'PY'
import json
import sys

allowed = {"command", "matcher", "timeout", "failClosed", "loop_limit"}
hooks = json.load(open(sys.argv[1], encoding="utf-8"))["hooks"]
managed = [
    entry
    for entries in hooks.values()
    for entry in entries
    if "cursor_hook.py" in entry.get("command", "")
]
assert managed
for entry in managed:
    assert not set(entry) - allowed, entry
PY
    rm -rf "$tmp"
}

@test "cursor hooks: preserves user config and migrates legacy managed entries" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.cursor"
    cat > "$tmp/.cursor/hooks.json" <<'JSON'
{
  "version": 1,
  "customSetting": "keep-me",
  "hooks": {
    "afterAgentResponse": [
      {"command": "python3 user-audit.py", "timeout": 7}
    ],
    "sessionStart": [
      {"_source": "ai-toolkit", "command": "legacy-managed-command"}
    ]
  }
}
JSON
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    python3 - "$tmp/.cursor/hooks.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
assert data["customSetting"] == "keep-me"
responses = data["hooks"]["afterAgentResponse"]
assert any(entry.get("command") == "python3 user-audit.py" for entry in responses)
assert not any(entry.get("command") == "legacy-managed-command" for entry in data["hooks"]["sessionStart"])
for entries in data["hooks"].values():
    assert sum("cursor_hook.py" in entry.get("command", "") for entry in entries) == 1
PY
    rm -rf "$tmp"
}

@test "cursor hooks: config and vendored runtime are byte-idempotent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    first="$(shasum "$tmp/.cursor/hooks.json" "$tmp/.cursor/hooks/ai-toolkit/cursor_hook.py")"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    second="$(shasum "$tmp/.cursor/hooks.json" "$tmp/.cursor/hooks/ai-toolkit/cursor_hook.py")"
    [ "$first" = "$second" ]
    rm -rf "$tmp"
}

@test "cursor hooks: refuses a symlinked config without changing its target" {
    tmp="$(mktemp -d)"
    mkdir -p "$tmp/.cursor"
    target="$tmp/user-hooks.json"
    printf '{"version":1,"hooks":{},"owner":"user"}\n' > "$target"
    before="$(shasum "$target")"
    ln -s "$target" "$tmp/.cursor/hooks.json"
    run python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp"
    [ "$status" -ne 0 ]
    [ "$before" = "$(shasum "$target")" ]
    rm -rf "$tmp"
}

@test "cursor hooks: destructive shell command is denied with Cursor JSON" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    runtime="$tmp/.cursor/hooks/ai-toolkit/cursor_hook.py"
    run python3 "$runtime" before-shell <<'JSON'
{"command":"rm -rf /tmp/unsafe-cursor-test","cwd":"/tmp","sandbox":true}
JSON
    [ "$status" -eq 2 ]
    python3 - "$output" <<'PY'
import json
import sys

response = json.loads(sys.argv[1])
assert response["permission"] == "deny"
assert "destructive" in response["user_message"].lower()
PY
    rm -rf "$tmp"
}

@test "cursor hooks: observational conversation events are fail-open and silent" {
    tmp="$(mktemp -d)"
    python3 "$TOOLKIT_DIR/scripts/generate_cursor_hooks.py" "$tmp" >/dev/null
    runtime="$tmp/.cursor/hooks/ai-toolkit/cursor_hook.py"
    run python3 "$runtime" observe <<'JSON'
{"text":"assistant response","duration_ms":12}
JSON
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    rm -rf "$tmp"
}
