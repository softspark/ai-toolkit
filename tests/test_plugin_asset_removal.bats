#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# Plugin pack removal must leave no owned hook or script behind (v4.32.1).
# The Claude/Codex install path copied hooks into ~/.softspark/ai-toolkit/hooks
# and scripts into plugin-scripts/<pack>/ without recording ownership, so
# removal reported every file as "untracked" and preserved it. Found by the
# post-release SOP on v4.32.0 (Phase 5: "residue: 5"), identical on v4.31.0.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
    export SOFTSPARK_HOME="$TEST_TMP/.softspark"
    unset CODEX_HOME
    python3 "$TOOLKIT_DIR/scripts/install.py" >/dev/null 2>&1
}

teardown() {
    rm -rf "$TEST_TMP"
}

_residue() {
    find "$SOFTSPARK_HOME" -path '*memory-pack*' -type f | wc -l | tr -d ' '
}

_ownership() {
    python3 -c "
import json, os
d = json.load(open(os.environ['SOFTSPARK_HOME'] + '/ai-toolkit/plugins.json'))
o = d.get('shared_asset_ownership', {}).get('memory-pack')
print('none' if not o else ','.join(sorted(o.get('consumers', {}))))"
}

@test "plugin install (claude) records hook and script ownership" {
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack
    [ "$status" -eq 0 ]
    [ "$(_ownership)" = "claude" ]
    [ -f "$SOFTSPARK_HOME/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh" ]
    [ -f "$SOFTSPARK_HOME/ai-toolkit/plugin-scripts/memory-pack/init_db.py" ]
}

@test "plugin remove (claude) deletes every owned hook and script, zero residue" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack >/dev/null 2>&1
    [ "$(_residue)" -gt 0 ]
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove memory-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "Removed plugin asset: plugin-memory-pack-session-summary.sh"
    echo "$output" | grep -q "Removed plugin asset: init_db.py"
    ! echo "$output" | grep -q "WARN preserved"
    [ "$(_residue)" -eq 0 ]
    [ ! -d "$SOFTSPARK_HOME/ai-toolkit/plugin-scripts/memory-pack" ]
    [ "$(_ownership)" = "none" ]
    # settings.json no longer references the pack hooks
    python3 -c "
import json, os
d = json.load(open(os.environ['HOME'] + '/.claude/settings.json'))
assert 'memory-pack' not in json.dumps(d.get('hooks', {}))"
}

@test "plugin remove preserves a hook the user edited and names it" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack >/dev/null 2>&1
    printf '\n# user edit\n' >> "$SOFTSPARK_HOME/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh"
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove memory-pack
    [ "$status" -eq 0 ]
    echo "$output" | grep -q "WARN preserved changed plugin asset: .*plugin-memory-pack-session-summary.sh"
    [ -f "$SOFTSPARK_HOME/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh" ]
    [ ! -f "$SOFTSPARK_HOME/ai-toolkit/hooks/plugin-memory-pack-observation-capture.sh" ]
    [ ! -d "$SOFTSPARK_HOME/ai-toolkit/plugin-scripts/memory-pack" ]
}

@test "plugin remove keeps shared assets while another editor still consumes them" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack >/dev/null 2>&1
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack --editor codex >/dev/null 2>&1
    [ "$(_ownership)" = "claude,codex" ]
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove memory-pack --editor claude
    [ "$status" -eq 0 ]
    [ "$(_residue)" -eq 4 ]
    [ "$(_ownership)" = "codex" ]
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove memory-pack --editor codex
    [ "$status" -eq 0 ]
    [ "$(_residue)" -eq 0 ]
    [ "$(_ownership)" = "none" ]
}

@test "plugin remove then reinstall works and records ownership again" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack >/dev/null 2>&1
    python3 "$TOOLKIT_DIR/scripts/plugin.py" remove memory-pack >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" install memory-pack
    [ "$status" -eq 0 ]
    [ "$(_ownership)" = "claude" ]
    [ "$(_residue)" -eq 4 ]
}
