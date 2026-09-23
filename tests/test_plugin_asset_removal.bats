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

@test "plugin remove all prunes the script directory after the last runtime" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install --editor all memory-pack >/dev/null 2>&1
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove --editor all memory-pack
    [ "$status" -eq 0 ]
    [ "$(_ownership)" = "none" ]
    [ "$(_residue)" -eq 0 ]
    [ ! -e "$SOFTSPARK_HOME/ai-toolkit/plugin-scripts/memory-pack" ]
}

@test "plugin Cursor and Gemini removal prune their final owned script directory" {
    for editor in cursor gemini; do
        python3 "$TOOLKIT_DIR/scripts/plugin.py" install --editor "$editor" memory-pack >/dev/null 2>&1
        run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove --editor "$editor" memory-pack
        [ "$status" -eq 0 ]
        [ ! -e "$SOFTSPARK_HOME/ai-toolkit/plugin-scripts/memory-pack" ]
    done
}

@test "plugin JSON runtime removal retains user files and generated caches" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install --editor cursor memory-pack >/dev/null 2>&1
    local scripts="$SOFTSPARK_HOME/ai-toolkit/plugin-scripts/memory-pack"
    mkdir -p "$scripts/__pycache__"
    printf 'user content\n' > "$scripts/notes.txt"
    printf 'cache content\n' > "$scripts/__pycache__/example.pyc"
    run python3 "$TOOLKIT_DIR/scripts/plugin.py" remove --editor cursor memory-pack
    [ "$status" -eq 0 ]
    [ ! -e "$scripts/init_db.py" ]
    [ "$(cat "$scripts/notes.txt")" = "user content" ]
    [ "$(cat "$scripts/__pycache__/example.pyc")" = "cache content" ]
}

@test "plugin JSON update failure preserves directory identity for outer rollback" {
    python3 "$TOOLKIT_DIR/scripts/plugin.py" install --editor cursor memory-pack >/dev/null 2>&1
    run python3 - "$TOOLKIT_DIR/scripts" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import plugin

scripts = plugin.TOOLKIT_DATA_DIR / 'plugin-scripts/memory-pack'
before = {path.name: path.read_bytes() for path in scripts.iterdir()}
identity = scripts.stat().st_ino
state = plugin.PLUGINS_STATE_FILE.read_bytes()

def fail_install(*args, **kwargs):
    raise RuntimeError('injected install failure')

plugin._install_pack_locked = fail_install
try:
    plugin.update_pack('memory-pack', 'cursor', force=True)
except RuntimeError as error:
    assert str(error) == 'injected install failure', error
else:
    raise AssertionError('update should fail')
assert scripts.stat().st_ino == identity
assert {path.name: path.read_bytes() for path in scripts.iterdir()} == before
assert plugin.PLUGINS_STATE_FILE.read_bytes() == state
PY
    [ "$status" -eq 0 ]
}

@test "plugin postcommit pruning preserves a swapped script directory and symlink" {
    run python3 - "$TOOLKIT_DIR/scripts" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import plugin

prune = plugin._prune_removed_script_directory
for editor, symlink in (('cursor', False), ('gemini', True)):
    assert plugin.install_pack('memory-pack', editor)
    root = plugin.TOOLKIT_DATA_DIR / 'plugin-scripts/memory-pack'
    saved = root.with_name('saved-' + editor)
    target = root.with_name('user-' + editor)

    def replace_before_pruning(transaction, plan, name):
        root.rename(saved)
        if symlink:
            target.mkdir()
            root.symlink_to(target, target_is_directory=True)
        else:
            root.mkdir()
        prune(transaction, plan, name)

    plugin._prune_removed_script_directory = replace_before_pruning
    assert plugin.remove_pack('memory-pack', editor)
    assert root.is_dir() and saved.is_dir()
    assert root.is_symlink() == symlink
    assert 'memory-pack' not in plugin._installed_for(plugin.load_state(), editor)
    # Move the preserved replacement aside before the next independent case.
    root.rename(root.with_name('preserved-' + editor))
PY
    [ "$status" -eq 0 ]
    [[ "$output" == *"WARN preserved plugin script directory"* ]]
}
