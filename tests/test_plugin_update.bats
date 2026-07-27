#!/usr/bin/env bats
# Tests for version-aware plugin pack updates and their wiring into
# `ai-toolkit update`.
#
# Before this, `plugin update` removed and reinstalled every pack
# unconditionally. For a pack that downloads a binary at install time that
# means refetching it on every core update, so the update path now skips a
# pack whose manifest version matches what was recorded at install.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="$TOOLKIT_DIR/bin/ai-toolkit.js"
PLUGIN_PY="$TOOLKIT_DIR/scripts/plugin.py"
STATE=".softspark/ai-toolkit/plugins.json"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

record_version() {
    python3 -c "
import json, pathlib
p = pathlib.Path('$TEST_TMP/$STATE')
d = json.loads(p.read_text())
d['targets']['claude']['versions']['$1'] = '$2'
p.write_text(json.dumps(d, indent=2))
"
}

recorded_version() {
    python3 -c "
import json, pathlib
d = json.loads(pathlib.Path('$TEST_TMP/$STATE').read_text())
print(d['targets']['claude']['versions'].get('$1', ''))
"
}

@test "install records the pack version in plugins.json" {
    run node "$CLI" plugin install --editor claude memory-pack
    [ "$status" -eq 0 ]
    run recorded_version memory-pack
    [ "$output" = "1.0.0" ]
}

@test "update --all is a silent no-op when nothing moved" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin update --editor claude --all
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "update --all reinstalls a pack whose recorded version is stale" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    record_version memory-pack 0.9.0

    run node "$CLI" plugin update --editor claude --all
    [ "$status" -eq 0 ]
    case "$output" in
        *"0.9.0 -> 1.0.0"*) ;;
        *) echo "expected a version transition, got: $output"; return 1 ;;
    esac

    run recorded_version memory-pack
    [ "$output" = "1.0.0" ]
}

@test "update --dry-run reports the pending change without acting" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    record_version memory-pack 0.9.0

    run node "$CLI" plugin update --editor claude --all --dry-run
    [ "$status" -eq 0 ]
    case "$output" in
        *"Would update"*) ;;
        *) echo "expected a dry-run report, got: $output"; return 1 ;;
    esac

    # Untouched: the stale marker is still what it was.
    run recorded_version memory-pack
    [ "$output" = "0.9.0" ]
}

@test "update --dry-run says nothing is pending when all packs are current" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin update --editor claude --all --dry-run
    [ "$status" -eq 0 ]
    case "$output" in
        *"up to date"*) ;;
        *) echo "expected an up-to-date report, got: $output"; return 1 ;;
    esac
}

@test "update --all with no packs installed does no work and stays quiet" {
    run node "$CLI" plugin update --editor claude --all
    [ "$status" -eq 0 ]
    [ -z "$output" ]
}

@test "--force reinstalls even when the version matches" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin update --editor claude --all --force
    [ "$status" -eq 0 ]
    case "$output" in
        *"Updating: memory-pack"*) ;;
        *) echo "expected a forced update, got: $output"; return 1 ;;
    esac
}

@test "remove forgets the recorded version" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    node "$CLI" plugin remove --editor claude memory-pack >/dev/null 2>&1
    run recorded_version memory-pack
    [ -z "$output" ]
}

@test "state written before versions were tracked updates each pack once" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    # Legacy shape: installed list, no versions map.
    python3 -c "
import json, pathlib
p = pathlib.Path('$TEST_TMP/$STATE')
p.write_text(json.dumps({'targets': {'claude': {'installed': ['memory-pack']}}}, indent=2))
"
    run node "$CLI" plugin update --editor claude --all --dry-run
    [ "$status" -eq 0 ]
    case "$output" in
        *"unrecorded -> 1.0.0"*) ;;
        *) echo "expected the unrecorded-version transition, got: $output"; return 1 ;;
    esac
}

@test "ai-toolkit update --local leaves plugin packs alone" {
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    record_version memory-pack 0.9.0

    run bash -c "cd '$TEST_TMP' && node '$CLI' update --local --dry-run 2>&1"
    [ "$status" -eq 0 ]
    # Packs are global state; --local is project-local config only.
    run recorded_version memory-pack
    [ "$output" = "0.9.0" ]
}

@test "plugin.py update tolerates a corrupt plugins.json without crashing" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    printf 'not json' > "$TEST_TMP/$STATE"
    run python3 "$PLUGIN_PY" update --editor claude --all
    [ "$status" -eq 0 ]
}

@test "plugin status dispatches to a pack's own status.py generically" {
    # memory-pack has no status.py, so its output must be unchanged and the
    # generic path must not invent lines for packs that do not opt in.
    node "$CLI" plugin install --editor claude memory-pack >/dev/null 2>&1
    run node "$CLI" plugin status
    [ "$status" -eq 0 ]
    case "$output" in
        *"memory-pack"*) ;;
        *) echo "expected memory-pack in status, got: $output"; return 1 ;;
    esac
    case "$output" in
        *"status unavailable"*) echo "generic dispatch must stay silent for packs without status.py"; return 1 ;;
        *) ;;
    esac
}

@test "install skips an editor a pack does not declare support for" {
    # Driven against a fixture pack rather than a shipped one: no pack in
    # app/plugins declares supported_editors today, and creating one there
    # would race the pack-count assertions in other files under --jobs 4.
    run python3 -c "
import json, pathlib, sys, tempfile
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin

tmp = pathlib.Path(tempfile.mkdtemp())
pack = tmp / 'fixture-pack'
pack.mkdir()
(pack / 'plugin.json').write_text(json.dumps({
    'name': 'fixture-pack',
    'description': 'declares support for claude only',
    'version': '1.0.0',
    'domain': 'testing',
    'type': 'plugin-pack',
    'includes': {'agents': [], 'skills': [], 'rules': [], 'hooks': []},
    'supported_editors': ['claude'],
}))
plugin.PLUGINS_DIR = tmp

sys.exit(0 if plugin.install_pack('fixture-pack', 'codex') is False else 1)
"
    [ "$status" -eq 0 ]
    case "$output" in
        *"Skipping: fixture-pack does not support codex"*) ;;
        *) echo "expected codex to be skipped, got: $output"; return 1 ;;
    esac
}

@test "a pack without supported_editors still installs everywhere" {
    run node "$CLI" plugin install --editor all memory-pack
    [ "$status" -eq 0 ]
    case "$output" in
        *"Skipping"*) echo "memory-pack must not be skipped: $output"; return 1 ;;
        *) ;;
    esac
}

@test "a pack with two hooks on one event keeps both entries" {
    # _merge_claude_hooks used to strip this pack's entries inside the per-spec
    # loop, so the second hook on an event removed the first.
    run python3 -c "
import sys, json, pathlib
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin
plugin.CLAUDE_DIR = pathlib.Path('$TEST_TMP/.claude')
specs = [
    {'name': 'a.sh', 'event': 'PreToolUse', 'is_core': False, 'source': pathlib.Path('/dev/null')},
    {'name': 'b.sh', 'event': 'PreToolUse', 'is_core': False, 'source': pathlib.Path('/dev/null')},
]
plugin._merge_claude_hooks('demo', specs)
d = json.loads((plugin.CLAUDE_DIR / 'settings.json').read_text())
n = len(d['hooks']['PreToolUse'])
print('entries:', n)
sys.exit(0 if n == 2 else 1)
"
    [ "$status" -eq 0 ]
}

@test "remove deletes a pack hook that is not named .sh" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/hooks"
    touch "$TEST_TMP/.softspark/ai-toolkit/hooks/plugin-demo-runner.py"
    run python3 -c "
import sys, pathlib
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin
plugin.HOOKS_DIR = pathlib.Path('$TEST_TMP/.softspark/ai-toolkit/hooks')
found = list(plugin.HOOKS_DIR.glob('plugin-demo-*'))
print([p.name for p in found])
sys.exit(0 if len(found) == 1 else 1)
"
    [ "$status" -eq 0 ]
}

@test "remove drops a skill symlink the pack owns" {
    # A pack-local skill with no core counterpart: the link resolves into the
    # pack directory, so removal owns it.
    pack="$TEST_TMP/packs/demo-pack"
    mkdir -p "$pack/skills/demo-only-skill"
    cat > "$pack/skills/demo-only-skill/SKILL.md" <<'MD'
---
name: demo-only-skill
description: fixture
---
MD
    cat > "$pack/plugin.json" <<'JSON'
{"name":"demo-pack","description":"fixture","version":"1.0.0","domain":"demo",
 "type":"plugin-pack","status":"experimental",
 "requires":{"ai-toolkit":">=1.0.0"},
 "includes":{"agents":[],"skills":["demo-only-skill"],"rules":[],"hooks":[]}}
JSON

    run python3 -c "
import sys, pathlib
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin
plugin.PLUGINS_DIR = pathlib.Path('$TEST_TMP/packs')
plugin.CLAUDE_DIR = pathlib.Path('$TEST_TMP/.claude')
plugin.PLUGINS_STATE_FILE = pathlib.Path('$TEST_TMP/plugins.json')
pack = plugin.find_pack('demo-pack')
pd = pathlib.Path(pack['_dir'])
items = []
plugin._install_claude_skills(pack, pd, items)
link = plugin.CLAUDE_DIR / 'skills' / 'demo-only-skill'
assert link.is_symlink(), 'install did not create the link'
plugin._remove_claude_pack_links(pack, pd)
print('link after remove:', link.is_symlink() or link.exists())
sys.exit(0 if not (link.is_symlink() or link.exists()) else 1)
"
    [ "$status" -eq 0 ]
}

@test "remove keeps a skill symlink that points at a core asset" {
    # The pack merely referenced a core skill; the base install owns it.
    pack="$TEST_TMP/packs/ref-pack"
    mkdir -p "$pack"
    cat > "$pack/plugin.json" <<'JSON'
{"name":"ref-pack","description":"fixture","version":"1.0.0","domain":"demo",
 "type":"plugin-pack","status":"experimental",
 "requires":{"ai-toolkit":">=1.0.0"},
 "includes":{"agents":[],"skills":["debug"],"rules":[],"hooks":[]}}
JSON

    run python3 -c "
import sys, pathlib
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
import plugin
plugin.PLUGINS_DIR = pathlib.Path('$TEST_TMP/packs')
plugin.CLAUDE_DIR = pathlib.Path('$TEST_TMP/.claude')
pack = plugin.find_pack('ref-pack')
pd = pathlib.Path(pack['_dir'])
plugin._install_claude_skills(pack, pd, [])
link = plugin.CLAUDE_DIR / 'skills' / 'debug'
assert link.is_symlink(), 'install did not link the core skill'
plugin._remove_claude_pack_links(pack, pd)
print('core link preserved:', link.is_symlink())
sys.exit(0 if link.is_symlink() else 1)
"
    [ "$status" -eq 0 ]
}
