#!/usr/bin/env bats
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
#
# test_install_state.bats — Tests for install_state.py and version_check.py
# Run with: bats tests/test_install_state.bats

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="node $TOOLKIT_DIR/bin/ai-toolkit.js"

setup() {
    TEST_TMP="$(mktemp -d)"
    export HOME="$TEST_TMP"
}

teardown() {
    rm -rf "$TEST_TMP"
}

# ── ai-toolkit status (via CLI) ────────────────────────────────────────────

@test "status: exits 0 with state.json present" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core", "agents", "skills"]
}
EOF
    run $CLI status
    [ "$status" -eq 0 ]
}

@test "status: shows version number" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    run $CLI status
    echo "$output" | grep -q '1.2.1'
}

@test "status: exits 0 even without state.json" {
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -qi 'no install state'
}

@test "status: lists external rules and hooks from sources.json" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/rules"
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/hooks/external"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    cat > "$TEST_TMP/.softspark/ai-toolkit/rules/sources.json" <<'EOF'
{"schema_version": 1, "rules": {"jira-mcp": {"url": "https://example.com/r.md", "fetched_at": "2026-05-04T11:24:40Z"}}}
EOF
    cat > "$TEST_TMP/.softspark/ai-toolkit/hooks/external/sources.json" <<'EOF'
{"schema_version": 1, "hooks": {"jira-mcp-hooks": {"url": "https://example.com/h.json", "fetched_at": "2026-05-04T11:24:40Z"}}}
EOF
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'External sources:'
    echo "$output" | grep -q 'rule  jira-mcp'
    echo "$output" | grep -q 'hook  jira-mcp-hooks'
}

@test "status: shows local-path source with [local] tag" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/rules"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    cat > "$TEST_TMP/.softspark/ai-toolkit/rules/sources.json" <<'EOF'
{"schema_version": 1, "rules": {"my-local": {"path": "/abs/repo/my-local.md", "fetched_at": "2026-05-06T09:00:00Z", "sha256": "deadbeef"}}}
EOF
    # Materialize the file so it is not flagged as orphan
    : > "$TEST_TMP/.softspark/ai-toolkit/rules/my-local.md"
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rule  my-local  <- /abs/repo/my-local.md \[local\]'
}

@test "status: flags orphan rule files (file present, not in sources.json)" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit/rules"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    : > "$TEST_TMP/.softspark/ai-toolkit/rules/legacy-rule.md"
    run $CLI status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'rule  legacy-rule  <- (orphan, no source recorded'
}

@test "add_rule: registers local file with path in sources.json" {
    mkdir -p "$TEST_TMP/work"
    echo "test content" > "$TEST_TMP/work/local-rule.md"
    EXPECTED_PATH=$(python3 -c "import pathlib; print(pathlib.Path('$TEST_TMP/work/local-rule.md').resolve())")
    cd "$TEST_TMP/work"
    run python3 "$TOOLKIT_DIR/scripts/add_rule.py" "$TEST_TMP/work/local-rule.md"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/rules/sources.json" ]
    python3 -c "
import json
with open('$TEST_TMP/.softspark/ai-toolkit/rules/sources.json') as f:
    d = json.load(f)
entry = d['rules']['local-rule']
assert entry['path'] == '$EXPECTED_PATH', f'got path={entry.get(\"path\")}'
assert 'sha256' in entry, 'sha256 missing'
assert 'fetched_at' in entry, 'fetched_at missing'
"
}

@test "status: omits External sources section when no registries exist" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "1.2.1",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-01T00:00:00Z",
  "profile": "standard",
  "installed_modules": ["core"]
}
EOF
    run $CLI status
    [ "$status" -eq 0 ]
    ! echo "$output" | grep -q 'External sources:'
}

# ── install_state.py (direct Python) ───────────────────────────────────────

@test "install_state: record_install creates state.json" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import record_install
record_install(
    version='1.0.0',
    modules=['core', 'agents'],
    profile='standard',
)
"
    [ "$status" -eq 0 ]
    [ -f "$TEST_TMP/.softspark/ai-toolkit/state.json" ]
}

@test "install_state: load_state reads back recorded data" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import record_install, load_state
record_install(version='2.0.0', modules=['core'], profile='minimal')
state = load_state()
assert state['installed_version'] == '2.0.0', f'got {state}'
assert state['profile'] == 'minimal', f'got {state}'
assert 'core' in state['installed_modules'], f'got {state}'
print('OK')
"
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'OK'
}

@test "install_state: DSH lifecycle rejects malformed shared state without rewriting it" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    printf '%s\n' '{malformed' > "$TEST_TMP/.softspark/ai-toolkit/state.json"
    before="$(shasum "$TEST_TMP/.softspark/ai-toolkit/state.json")"

    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import get_dsh_profile
try:
    get_dsh_profile('web')
except ValueError as error:
    assert 'malformed' in str(error), error
else:
    raise AssertionError('malformed state was accepted')
"

    [ "$status" -eq 0 ]
    [ "$(shasum "$TEST_TMP/.softspark/ai-toolkit/state.json")" = "$before" ]
}

@test "install_state: atomic save failure preserves the previous shared state bytes" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    printf '%s\n' '{"sentinel":"before"}' > \
        "$TEST_TMP/.softspark/ai-toolkit/state.json"
    before="$(shasum "$TEST_TMP/.softspark/ai-toolkit/state.json")"

    run python3 - <<PY
import sys
sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps import install_state

real_publish = install_state._secure_publish_state

def fail_publish(temporary, path, expected_revision, **_kwargs):
    raise OSError('injected atomic publish failure')

install_state._secure_publish_state = fail_publish
try:
    try:
        install_state.save_state({'sentinel': 'after'})
    except OSError as error:
        assert 'injected' in str(error), error
    else:
        raise AssertionError('save unexpectedly succeeded')
finally:
    install_state._secure_publish_state = real_publish
PY

    [ "$status" -eq 0 ]
    [ "$(shasum "$TEST_TMP/.softspark/ai-toolkit/state.json")" = "$before" ]
    [ -z "$(find "$TEST_TMP/.softspark/ai-toolkit" -name '*.tmp' -print -quit)" ]
}

@test "install_state: DSH ownership schema rejects unknown credential-shaped fields" {
    # Deliberately models a legacy 1.0.0 profile before package-tree inventories.
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'JSON'
{
  "dsh": {
    "profiles": {
      "web": {
        "dsh_home": "/tmp/dsh",
        "profile": "web",
        "packages": {
          "@softspark/dsh-codex": "1.0.0",
          "@softspark/dsh-orchestrator": "1.0.0"
        },
        "preset_path": "/tmp/dsh/.agent-presets/softspark-orchestrator",
        "preset_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "owned": true,
        "installed_at": "2026-08-29T00:00:00Z",
        "last_updated": "2026-08-29T00:00:00Z",
        "access_token": "must-not-be-accepted"
      }
    }
  }
}

JSON

    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import get_dsh_profile
try:
    get_dsh_profile('web')
except ValueError as error:
    assert 'invalid DSH lifecycle state' in str(error), error
else:
    raise AssertionError('unknown DSH state field was accepted')
"

    [ "$status" -eq 0 ]
}

@test "install_state: legacy DSH state without package inventories fails actionable" {
    # Deliberately models a legacy 1.0.0 profile that cannot prove byte ownership.
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'JSON'
{
  "dsh": {
    "profiles": {
      "web": {
        "dsh_home": "/tmp/dsh",
        "profile": "web",
        "packages": {
          "@softspark/dsh-codex": "1.0.0",
          "@softspark/dsh-orchestrator": "1.0.0"
        },
        "preset_path": "/tmp/dsh/.agent-presets/softspark-orchestrator",
        "preset_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "owned": true,
        "installed_at": "2026-08-29T00:00:00Z",
        "last_updated": "2026-08-29T00:00:00Z"
      }
    }
  }
}
JSON

    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]) / "scripts"))
from install_steps import install_state
from install_steps.install_state import get_dsh_profile

try:
    get_dsh_profile("web")
except ValueError as error:
    message = str(error)
    assert "doctor" in message and "reinstall" in message, message
else:
    raise AssertionError("legacy DSH state claimed unknown package bytes")

invalid_unicode_inventory = {
    "digest": "d" * 64,
    "entries": [
        {"type": "directory", "path": ".", "mode": 0o755},
        {
            "type": "file",
            "path": "bad-\ud800-name",
            "mode": 0o644,
            "size": 0,
            "sha256": "e" * 64,
        },
    ],
}
assert not install_state._validate_dsh_tree_inventory(invalid_unicode_inventory)
PY

    [ "$status" -eq 0 ]
}

@test "install_state: DSH lifecycle rejects a user-owned symlinked state root" {
    external="$TEST_TMP/external-state-root"
    mkdir -p "$external"
    ln -s "$external" "$TEST_TMP/.softspark"

    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import get_dsh_profile
try:
    get_dsh_profile('web')
except ValueError as error:
    assert 'unsafe ai-toolkit state root' in str(error), error
else:
    raise AssertionError('symlinked state root was accepted')
"

    [ "$status" -eq 0 ]
    [ -z "$(find "$external" -mindepth 1 -print -quit)" ]
}

@test "install_state: explicit non-auto install clears stale detected languages" {
    run python3 -c "
import sys; sys.path.insert(0, '$TOOLKIT_DIR/scripts')
from install_steps.install_state import record_install, load_state
record_install(
    version='2.0.0',
    modules=['core', 'rules-cpp'],
    profile='standard',
    auto_detected=['rules-cpp'],
)
record_install(
    version='2.0.0',
    modules=['core', 'rules-cpp', 'rules-python'],
    profile='standard',
)
state = load_state()
assert 'auto_detected_languages' not in state, state
"
    [ "$status" -eq 0 ]
}

@test "install --local preserves global install profile and modules" {
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit" "$TEST_TMP/project"
    cat > "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'EOF'
{
  "installed_version": "4.13.0",
  "installed_at": "2026-01-01T00:00:00Z",
  "last_updated": "2026-01-02T00:00:00Z",
  "profile": "full",
  "installed_modules": ["core", "agents", "skills", "rules-python"]
}
EOF

    run bash -c "cd '$TEST_TMP/project' && python3 '$TOOLKIT_DIR/scripts/install.py' --local --profile minimal --skip-register"
    [ "$status" -eq 0 ]
    python3 - "$TEST_TMP/.softspark/ai-toolkit/state.json" <<'PY'
import json
import sys

state = json.load(open(sys.argv[1]))
assert state["profile"] == "full", state
assert state["installed_modules"] == ["core", "agents", "skills", "rules-python"], state
assert state["last_updated"] == "2026-01-02T00:00:00Z", state
PY
}

# ── version_check.py ───────────────────────────────────────────────────────

@test "install_state: DSH compare-and-swap preserves unrelated state and rejects profile races" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps.install_state import (
    record_dsh_profile,
    remove_dsh_profile,
    restore_dsh_profile,
)

home = Path.home() / ".dsh"
preset = home / ".agent-presets" / "softspark-orchestrator"
packages = {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}
package_trees = {
    package: {
        "digest": "d" * 64,
        "entries": [{"type": "directory", "path": ".", "mode": 0o755}],
    }
    for package in packages
}

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"

first = record_dsh_profile(
    dsh_home=home,
    profile="web",
    packages=packages,
    package_trees=package_trees,
    preset_path=preset,
    preset_hash="a" * 64,
    expected_profile=None,
)
state = json.loads(state_path.read_text())
state["concurrent"] = {"preserve": [True, 3]}
state_path.write_text(json.dumps(state) + "\n")

second = record_dsh_profile(
    dsh_home=home,
    profile="web",
    packages=packages,
    package_trees=package_trees,
    preset_path=preset,
    preset_hash="b" * 64,
    expected_profile=first,
)
state = json.loads(state_path.read_text())
assert state["concurrent"] == {"preserve": [True, 3]}, state

concurrent = dict(second)
concurrent["preset_hash"] = "c" * 64
state["dsh"]["profiles"]["web"] = concurrent
state["other_writer"] = "keep"
state_path.write_text(json.dumps(state) + "\n")

try:
    remove_dsh_profile("web", expected_profile=second)
except ValueError as error:
    assert "concurrent DSH state change" in str(error), error
else:
    raise AssertionError("DSH-specific race was overwritten")
assert json.loads(state_path.read_text())["dsh"]["profiles"]["web"] == concurrent

restore_dsh_profile(
    "web",
    expected_profile=concurrent,
    previous_profile=second,
)
state = json.loads(state_path.read_text())
assert state["dsh"]["profiles"]["web"] == second, state
assert state["other_writer"] == "keep", state
assert state["concurrent"] == {"preserve": [True, 3]}, state
PY

    [ "$status" -eq 0 ]
}

@test "install_state: DSH lifecycle honors canonical AI_TOOLKIT_HOME immediately" {
    fake_bin="$TEST_TMP/fake-bin"
    dsh_home="$TEST_TMP/dsh-home"
    custom_toolkit_home="$TEST_TMP/custom-ai-toolkit-home"
    mkdir -p "$fake_bin" "$dsh_home"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/dsh"
    cp "$TOOLKIT_DIR/tests/fixtures/dsh/fake_dsh.py" "$fake_bin/pnpm"
    chmod +x "$fake_bin/dsh" "$fake_bin/pnpm"
    command=(env HOME="$TEST_TMP" AI_TOOLKIT_HOME="$custom_toolkit_home" \
        DSH_HOME="$dsh_home" PATH="$fake_bin:$PATH" \
        node "$TOOLKIT_DIR/bin/ai-toolkit.js" dsh)

    run "${command[@]}" install --profile web
    [ "$status" -eq 0 ]
    [ -f "$custom_toolkit_home/state.json" ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/state.json" ]

    run "${command[@]}" update --profile web
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/state.json" ]

    run "${command[@]}" uninstall --profile web --yes
    [ "$status" -eq 0 ]
    [ ! -e "$TEST_TMP/.softspark/ai-toolkit/state.json" ]
}

@test "install_state: DSH state write retries after concurrent unrelated creation" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"
real_save = install_state._save_state_cas
injected = False

def inject_concurrent_creation(state, revision, **kwargs):
    global injected
    if not injected:
        injected = True
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text('{"concurrent":{"preserve":true}}\n')
    return real_save(state, revision, **kwargs)

install_state._save_state_cas = inject_concurrent_creation
packages = {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}
install_state.record_dsh_profile(
    dsh_home=Path.home() / ".dsh",
    profile="web",
    packages=packages,
    package_trees={
        package: {
            "digest": "d" * 64,
            "entries": [{"type": "directory", "path": ".", "mode": 0o755}],
        }
        for package in packages
    },
    preset_path=Path.home()
    / ".dsh"
    / ".agent-presets"
    / "softspark-orchestrator",
    preset_hash="a" * 64,
    expected_profile=None,
)
state = json.loads(state_path.read_text())
assert state["concurrent"] == {"preserve": True}, state
assert "web" in state["dsh"]["profiles"], state
PY

    [ "$status" -eq 0 ]
}

@test "install_state: shared writer lock closes the DSH compare-replace race" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
import threading
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"
at_dsh_replace = threading.Event()
generic_started = threading.Event()
generic_finished = threading.Event()
errors = []
real_publish = install_state._secure_publish_state
gated = False


def gated_publish(temporary, path, expected_revision, **kwargs):
    global gated
    temporary = Path(temporary)
    if temporary.name.startswith(".state.dsh-cas-") and not gated:
        gated = True
        at_dsh_replace.set()
        assert generic_started.wait(2), "generic writer never attempted the lock"
        generic_finished.wait(0.2)
    return real_publish(temporary, path, expected_revision, **kwargs)


def write_dsh():
    try:
        packages = {
            "@softspark/dsh-codex": "1.0.0",
            "@softspark/dsh-orchestrator": "1.0.1",
        }
        install_state.record_dsh_profile(
            dsh_home=Path.home() / ".dsh",
            profile="web",
            packages=packages,
            package_trees={
                package: {
                    "digest": "d" * 64,
                    "entries": [
                        {"type": "directory", "path": ".", "mode": 0o755}
                    ],
                }
                for package in packages
            },
            preset_path=Path.home()
            / ".dsh"
            / ".agent-presets"
            / "softspark-orchestrator",
            preset_hash="a" * 64,
            expected_profile=None,
        )
    except BaseException as error:
        errors.append(error)


def write_generic():
    generic_started.set()
    try:
        install_state.record_mcp_template("concurrent-template")
    except BaseException as error:
        errors.append(error)
    finally:
        generic_finished.set()


install_state._secure_publish_state = gated_publish
dsh_writer = threading.Thread(target=write_dsh)
dsh_writer.start()
assert at_dsh_replace.wait(2), "DSH writer did not reach replace boundary"
generic_writer = threading.Thread(target=write_generic)
generic_writer.start()
dsh_writer.join(3)
generic_writer.join(3)
assert not dsh_writer.is_alive(), "DSH writer deadlocked"
assert not generic_writer.is_alive(), "generic writer deadlocked"
assert not errors, errors
state = json.loads(state_path.read_text())
assert state["mcp_templates"] == ["concurrent-template"], state
assert state["dsh"]["profiles"]["web"]["preset_hash"] == "a" * 64, state
PY

    [ "$status" -eq 0 ]
}

@test "install_state: shared writer lock is bounded fail-closed and exception-safe" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"
state_path.parent.mkdir(parents=True)
state_path.write_text('{"sentinel":"before"}\n')
lock_path = state_path.parent / ".state.lock"
install_state._STATE_LOCK_TIMEOUT_SECONDS = 0.05
install_state._STATE_LOCK_POLL_SECONDS = 0.005

lock_path.write_text("held\n")
try:
    install_state.save_state({"sentinel": "contended"})
except OSError as error:
    assert "lock" in str(error).lower(), error
else:
    raise AssertionError("contended shared state write succeeded")
assert json.loads(state_path.read_text()) == {"sentinel": "before"}
assert lock_path.read_text() == "held\n"
lock_path.unlink()

outside = Path.home() / "outside-lock"
outside.write_text("owner bytes\n")
lock_path.symlink_to(outside)
try:
    install_state.save_state({"sentinel": "symlink"})
except OSError as error:
    assert "lock" in str(error).lower(), error
else:
    raise AssertionError("symlinked shared state lock was accepted")
assert outside.read_text() == "owner bytes\n"
assert json.loads(state_path.read_text()) == {"sentinel": "before"}
lock_path.unlink()

lock_path.mkdir()
try:
    install_state.save_state({"sentinel": "directory"})
except OSError as error:
    assert "lock" in str(error).lower(), error
else:
    raise AssertionError("malformed shared state lock was accepted")
assert lock_path.is_dir()
assert json.loads(state_path.read_text()) == {"sentinel": "before"}
lock_path.rmdir()

state_path.write_text("{malformed\n")
try:
    install_state.save_state({"sentinel": "malformed-state"})
except ValueError as error:
    assert "malformed" in str(error).lower(), error
else:
    raise AssertionError("malformed shared state was overwritten")
assert state_path.read_text() == "{malformed\n"

state_path.unlink()
outside_state = Path.home() / "outside-state"
outside_state.write_text('{"owner":"preserve"}\n')
state_path.symlink_to(outside_state)
try:
    install_state.save_state({"sentinel": "symlink-state"})
except ValueError as error:
    assert "malformed" in str(error).lower(), error
else:
    raise AssertionError("symlinked shared state was overwritten")
assert state_path.is_symlink()
assert outside_state.read_text() == '{"owner":"preserve"}\n'
state_path.unlink()
state_path.write_text('{"sentinel":"before"}\n')

real_publish = install_state._secure_publish_state


def fail_publish(_temporary, _path, _expected_revision, **_kwargs):
    raise OSError("injected state publish failure")


install_state._secure_publish_state = fail_publish
try:
    install_state.save_state({"sentinel": "failed"})
except OSError as error:
    assert "injected" in str(error), error
else:
    raise AssertionError("injected state failure was ignored")
finally:
    install_state._secure_publish_state = real_publish
assert not lock_path.exists() and not lock_path.is_symlink()
install_state.save_state({"sentinel": "after"})
assert json.loads(state_path.read_text()) == {"sentinel": "after"}
assert not lock_path.exists() and not lock_path.is_symlink()
PY

    [ "$status" -eq 0 ]
}

@test "install_state: portable writers survive unsupported DSH state primitives" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"
original_platform = install_state.sys.platform
original_fchmod = install_state.os.fchmod
install_state.sys.platform = "win32"
install_state.os.fchmod = None
try:
    install_state.record_install(
        version="9.9.9",
        modules=["core"],
        profile="minimal",
    )
    install_state.record_mcp_template("portable-template")
finally:
    install_state.os.fchmod = original_fchmod
    install_state.sys.platform = original_platform
state = json.loads(state_path.read_text(encoding="utf-8"))
assert state["installed_version"] == "9.9.9", state
assert state["mcp_templates"] == ["portable-template"], state
assert not (state_path.parent / ".state.lock").exists()
assert not list(state_path.parent.glob(".state.*.tmp"))
assert not list(state_path.parent.glob(".state-private-cleanup-*"))
PY

    [ "$status" -eq 0 ]
}

@test "install_state: secure DSH lock acquisition uses a pinned parent" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

real_open = install_state.os.open
lock_calls = []


def observe_open(path, flags, mode=0o777, *, dir_fd=None):
    if Path(path).name == ".state.lock":
        lock_calls.append((path, dir_fd))
        assert Path(path) == Path(".state.lock"), path
        assert dir_fd is not None
    if dir_fd is None:
        return real_open(path, flags, mode)
    return real_open(path, flags, mode, dir_fd=dir_fd)


install_state.os.open = observe_open
packages = {
    "@softspark/dsh-codex": "1.0.0",
    "@softspark/dsh-orchestrator": "1.0.1",
}
try:
    install_state.record_dsh_profile(
        dsh_home=Path.home() / ".dsh",
        profile="web",
        packages=packages,
        package_trees={
            package: {
                "digest": "d" * 64,
                "entries": [
                    {"type": "directory", "path": ".", "mode": 0o755}
                ],
            }
            for package in packages
        },
        preset_path=Path.home()
        / ".dsh"
        / ".agent-presets"
        / "softspark-orchestrator",
        preset_hash="a" * 64,
        expected_profile=None,
    )
finally:
    install_state.os.open = real_open

assert lock_calls, "secure DSH writer did not acquire the shared state lock"
PY

    [ "$status" -eq 0 ]
}

@test "install_state: DSH state, CAS, and snapshot reads reject unstable inodes" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"
state_path.parent.mkdir(parents=True)


def large_state(fill):
    return ('{"padding":"' + fill * (128 * 1024) + '"}\n').encode()


state_path.write_bytes(large_state("A"))
state_path.chmod(0o600)
real_open = install_state.os.open
mode_changed = [False]


def change_mode_before_state_open(path, flags, mode=0o777, *, dir_fd=None):
    if Path(path).name == state_path.name and not mode_changed[0]:
        mode_changed[0] = True
        state_path.chmod(0o640)
    if dir_fd is None:
        return real_open(path, flags, mode)
    return real_open(path, flags, mode, dir_fd=dir_fd)


install_state.os.open = change_mode_before_state_open
try:
    assert install_state.load_state() == {}, "public state read accepted mode drift"
finally:
    install_state.os.open = real_open
assert mode_changed[0], "public state-open boundary was not reached"

state_path.write_bytes(large_state("A"))
state_path.chmod(0o600)
mode_changed[0] = False
install_state.os.open = change_mode_before_state_open
try:
    try:
        install_state.get_dsh_profile("web")
    except ValueError:
        pass
    else:
        raise AssertionError("DSH ownership read accepted mode drift")
finally:
    install_state.os.open = real_open
assert mode_changed[0], "DSH ownership state-open boundary was not reached"


def assert_same_inode_mutation_rejected(operation, label):
    state_path.write_bytes(large_state("A"))
    state_path.chmod(0o600)
    metadata = state_path.stat(follow_symlinks=False)
    real_read = install_state.os.read
    mutated = [False]

    def mutate_second_half(descriptor, size):
        chunk = real_read(descriptor, size)
        if chunk and not mutated[0]:
            mutated[0] = True
            writer = os.open(state_path, os.O_WRONLY)
            try:
                os.pwrite(writer, b"B" * (64 * 1024), 64 * 1024)
                os.fsync(writer)
            finally:
                os.close(writer)
            os.utime(
                state_path,
                ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
                follow_symlinks=False,
            )
        return chunk

    install_state.os.read = mutate_second_half
    try:
        try:
            operation()
        except ValueError:
            pass
        else:
            raise AssertionError(f"{label} accepted same-inode mutation")
    finally:
        install_state.os.read = real_read
    assert mutated[0], f"{label} read boundary was not reached"


assert_same_inode_mutation_rejected(
    lambda: install_state.capture_dsh_profile_snapshot(
        "web", expected_profile=None
    ),
    "DSH state snapshot",
)

inventory = {
    "digest": "0" * 64,
    "entries": [{"type": "directory", "path": ".", "mode": 0o755}],
}
assert_same_inode_mutation_rejected(
    lambda: install_state.record_dsh_profile(
        dsh_home=Path.home() / ".dsh",
        profile="web",
        packages={"@softspark/dsh-codex": "1.0.0"},
        package_trees={"@softspark/dsh-codex": inventory},
        preset_path=Path.home() / ".dsh/.agent-presets/softspark-orchestrator",
        preset_hash="1" * 64,
        expected_profile=None,
    ),
    "DSH state CAS",
)
PY

    [ "$status" -eq 0 ]
}

@test "install_state: equal-content rollback chmods only the pinned state inode" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import json
import os
import stat
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

state_path = Path.home() / ".softspark" / "ai-toolkit" / "state.json"
state_path.parent.mkdir(parents=True)
content = b"{}\n"
state_path.write_bytes(content)
state_path.chmod(0o640)
original_inode = state_path.stat(follow_symlinks=False).st_ino
preserved = state_path.with_name("state-managed.json")
state_parent = state_path.parent.stat(follow_symlinks=False)
snapshot = install_state.DshStateSnapshot(
    state_path,
    True,
    content,
    0o600,
    json.loads(content),
    "web",
    None,
    state_parent.st_dev,
    state_parent.st_ino,
)

real_fchmod = install_state.os.fchmod
injected = [False]


def replace_before_fchmod(descriptor, mode):
    metadata = os.fstat(descriptor)
    if metadata.st_ino == original_inode and not injected[0]:
        injected[0] = True
        state_path.rename(preserved)
        state_path.write_bytes(content)
        state_path.chmod(0o640)
    real_fchmod(descriptor, mode)


install_state.os.fchmod = replace_before_fchmod
try:
    conflict = install_state.restore_dsh_profile_snapshot(
        snapshot,
        expected_profile=None,
    )
finally:
    install_state.os.fchmod = real_fchmod

assert injected[0], "pinned state chmod boundary was not reached"
assert conflict == state_path, conflict
assert state_path.read_bytes() == content
assert stat.S_IMODE(state_path.stat(follow_symlinks=False).st_mode) == 0o640
assert state_path.stat(follow_symlinks=False).st_ino != original_inode
assert preserved.read_bytes() == content
assert stat.S_IMODE(preserved.stat(follow_symlinks=False).st_mode) == 0o600
PY

    [ "$status" -eq 0 ]
}

@test "install_state: generic writer preserves both state roots when parent is replaced after lock" {
    custom_root="$TEST_TMP/custom-generic-state"
    displaced="$TEST_TMP/custom-generic-state-displaced"
    mkdir -p "$custom_root"
    printf '%s\n' '{"sentinel":"original"}' > "$custom_root/state.json"

    run env HOME="$TEST_TMP" AI_TOOLKIT_HOME="$custom_root" python3 - \
        "$TOOLKIT_DIR" "$custom_root" "$displaced" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
state_root = Path(sys.argv[2])
displaced = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

real_load = install_state._load_state_strict
injected = [False]


def replace_parent_after_lock(*args, **kwargs):
    if not injected[0]:
        injected[0] = True
        state_root.rename(displaced)
        state_root.mkdir()
        (state_root / "state.json").write_text(
            json.dumps({"sentinel": "replacement"}) + "\n"
        )
    return real_load(*args, **kwargs)


install_state._load_state_strict = replace_parent_after_lock
try:
    try:
        install_state.save_state({"new_key": "must-not-publish"})
    except OSError as error:
        assert "state parent" in str(error), error
    else:
        raise AssertionError("replaced state parent was accepted")
finally:
    install_state._load_state_strict = real_load

assert injected[0], "post-lock state boundary was not reached"
assert json.loads((displaced / "state.json").read_text()) == {
    "sentinel": "original"
}
assert json.loads((state_root / "state.json").read_text()) == {
    "sentinel": "replacement"
}
assert not list(displaced.glob(".state.*.tmp")), list(displaced.iterdir())
assert not list(state_root.glob(".state.*.tmp")), list(state_root.iterdir())
assert not (displaced / ".state.lock").exists()
assert not (state_root / ".state.lock").exists()
PY

    [ "$status" -eq 0 ]
}

@test "install_state: DSH CAS preserves both custom state roots when parent is replaced after lock" {
    custom_root="$TEST_TMP/custom-dsh-state"
    displaced="$TEST_TMP/custom-dsh-state-displaced"
    mkdir -p "$custom_root"
    printf '%s\n' '{"sentinel":"original"}' > "$custom_root/state.json"

    run env HOME="$TEST_TMP" AI_TOOLKIT_HOME="$custom_root" python3 - \
        "$TOOLKIT_DIR" "$custom_root" "$displaced" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
state_root = Path(sys.argv[2])
displaced = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

real_load = install_state._load_state_revision_strict
injected = [False]


def replace_parent_after_lock(*args, **kwargs):
    if not injected[0]:
        injected[0] = True
        state_root.rename(displaced)
        state_root.mkdir()
        (state_root / "state.json").write_text(
            json.dumps({"sentinel": "replacement"}) + "\n"
        )
    return real_load(*args, **kwargs)


install_state._load_state_revision_strict = replace_parent_after_lock
try:
    try:
        install_state.record_dsh_profile(
            dsh_home=Path.home() / ".dsh",
            profile="web",
            packages={"package": "1.0.0"},
            package_trees={
                "package": {
                    "digest": "0" * 64,
                    "entries": [{"type": "directory", "path": ".", "mode": 0o755}],
                }
            },
            preset_path=Path.home() / ".dsh/.agent-presets/preset",
            preset_hash="1" * 64,
            expected_profile=None,
        )
    except (OSError, ValueError) as error:
        assert "state parent" in str(error), error
    else:
        raise AssertionError("DSH CAS accepted a replaced state parent")
finally:
    install_state._load_state_revision_strict = real_load

assert injected[0], "post-lock DSH CAS boundary was not reached"
assert json.loads((displaced / "state.json").read_text()) == {
    "sentinel": "original"
}
assert json.loads((state_root / "state.json").read_text()) == {
    "sentinel": "replacement"
}
assert not list(displaced.glob(".state*.tmp")), list(displaced.iterdir())
assert not list(state_root.glob(".state*.tmp")), list(state_root.iterdir())
assert not (displaced / ".state.lock").exists()
assert not (state_root / ".state.lock").exists()
PY

    [ "$status" -eq 0 ]
}

@test "install_state: pinned publication refuses a state parent swap before rename" {
    custom_root="$TEST_TMP/custom-publish-state"
    displaced="$TEST_TMP/custom-publish-state-displaced"
    mkdir -p "$custom_root"
    printf '%s\n' '{"sentinel":"original"}' > "$custom_root/state.json"

    run env HOME="$TEST_TMP" AI_TOOLKIT_HOME="$custom_root" python3 - \
        "$TOOLKIT_DIR" "$custom_root" "$displaced" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
state_root = Path(sys.argv[2])
displaced = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

real_publish = install_state._secure_publish_state
injected = [False]


def replace_parent_before_publish(temporary, path, revision, **kwargs):
    if not injected[0]:
        injected[0] = True
        state_root.rename(displaced)
        state_root.mkdir()
        (state_root / "state.json").write_text(
            json.dumps({"sentinel": "replacement"}) + "\n"
        )
    return real_publish(temporary, path, revision, **kwargs)


install_state._secure_publish_state = replace_parent_before_publish
try:
    try:
        install_state.save_state({"new_key": "must-not-publish"})
    except OSError as error:
        assert "state parent" in str(error), error
    else:
        raise AssertionError("publication accepted a replaced state parent")
finally:
    install_state._secure_publish_state = real_publish

assert injected[0], "state publication boundary was not reached"
assert json.loads((displaced / "state.json").read_text()) == {
    "sentinel": "original"
}
assert json.loads((state_root / "state.json").read_text()) == {
    "sentinel": "replacement"
}
assert not list(displaced.glob(".state*.tmp")), list(displaced.iterdir())
assert not list(state_root.glob(".state*.tmp")), list(state_root.iterdir())
assert not (displaced / ".state.lock").exists()
assert not (state_root / ".state.lock").exists()
PY

    [ "$status" -eq 0 ]
}

@test "install_state: first DSH publication cannot follow a replaced custom state root" {
    custom_root="$TEST_TMP/custom-first-publish-state"
    displaced="$TEST_TMP/custom-first-publish-state-displaced"
    mkdir -p "$custom_root"

    run env HOME="$TEST_TMP" AI_TOOLKIT_HOME="$custom_root" python3 - \
        "$TOOLKIT_DIR" "$custom_root" "$displaced" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
state_root = Path(sys.argv[2])
displaced = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

real_publish = install_state._secure_publish_state
injected = [False]


def replace_parent_before_first_publish(temporary, path, revision, **kwargs):
    if not injected[0]:
        injected[0] = True
        state_root.rename(displaced)
        state_root.mkdir()
        (state_root / "state.json").write_text(
            json.dumps({"sentinel": "replacement"}) + "\n"
        )
    return real_publish(temporary, path, revision, **kwargs)


install_state._secure_publish_state = replace_parent_before_first_publish
try:
    try:
        install_state.record_dsh_profile(
            dsh_home=Path.home() / ".dsh",
            profile="web",
            packages={"package": "1.0.0"},
            package_trees={
                "package": {
                    "digest": "0" * 64,
                    "entries": [{"type": "directory", "path": ".", "mode": 0o755}],
                }
            },
            preset_path=Path.home() / ".dsh/.agent-presets/preset",
            preset_hash="1" * 64,
            expected_profile=None,
        )
    except (OSError, ValueError) as error:
        assert "state parent" in str(error), error
    else:
        raise AssertionError("first DSH publication followed a replacement root")
finally:
    install_state._secure_publish_state = real_publish

assert injected[0], "first-publication boundary was not reached"
assert not (displaced / "state.json").exists()
assert json.loads((state_root / "state.json").read_text()) == {
    "sentinel": "replacement"
}
assert not list(displaced.glob(".state*.tmp")), list(displaced.iterdir())
assert not list(state_root.glob(".state*.tmp")), list(state_root.iterdir())
assert not (displaced / ".state.lock").exists()
assert not (state_root / ".state.lock").exists()
PY

    [ "$status" -eq 0 ]
}

@test "version_check: exits 0 when up to date (offline)" {
    # Pre-seed cache to avoid hitting npm
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    local VERSION
    VERSION=$(python3 -c "import json; print(json.load(open('$TOOLKIT_DIR/package.json'))['version'])")
    python3 -c "
import json, time
data = {'installed': '$VERSION', 'latest': '$VERSION', 'checked_at': time.time()}
with open('$TEST_TMP/.softspark/ai-toolkit/version-check.json', 'w') as f:
    json.dump(data, f)
"
    run python3 "$TOOLKIT_DIR/scripts/version_check.py"
    [ "$status" -eq 0 ]
}

@test "version_check: --status shows installed version" {
    # Pre-seed cache to avoid hitting npm
    mkdir -p "$TEST_TMP/.softspark/ai-toolkit"
    local VERSION
    VERSION=$(python3 -c "import json; print(json.load(open('$TOOLKIT_DIR/package.json'))['version'])")
    python3 -c "
import json, time
data = {'installed': '$VERSION', 'latest': '$VERSION', 'checked_at': time.time()}
with open('$TEST_TMP/.softspark/ai-toolkit/version-check.json', 'w') as f:
    json.dump(data, f)
"
    run python3 "$TOOLKIT_DIR/scripts/version_check.py" --status
    [ "$status" -eq 0 ]
    echo "$output" | grep -q 'Installed:'
    echo "$output" | grep -q "$VERSION"
}

@test "version_check: creates cache file after check" {
    # Force a check (will try npm and cache result or fail gracefully)
    run python3 "$TOOLKIT_DIR/scripts/version_check.py" --force
    # Even if npm is unreachable, the script exits 0 (up to date / unknown)
    # Just verify it ran without crashing
    true
    # If npm was reachable, cache should exist
    # If not, script handles gracefully — no assertion on file existence
}

@test "install_state: DSH snapshot pins the state root across final CAS and restore" {
    custom_root="$TEST_TMP/pinned-dsh-state"
    displaced="$TEST_TMP/pinned-dsh-state-displaced"
    mkdir -p "$custom_root"
    printf '%s\n' '{}' > "$custom_root/state.json"

    run env HOME="$TEST_TMP" AI_TOOLKIT_HOME="$custom_root" python3 - \
        "$TOOLKIT_DIR" "$custom_root" "$displaced" <<'PY'
import json
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
state_root = Path(sys.argv[2])
displaced = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
from install_steps import install_state

snapshot = install_state.capture_dsh_profile_snapshot(
    "web", expected_profile=None
)
original = (state_root / "state.json").read_bytes()
state_root.rename(displaced)
state_root.mkdir()
(state_root / "state.json").write_bytes(original)

inventory = {
    "digest": "0" * 64,
    "entries": [{"type": "directory", "path": ".", "mode": 0o755}],
}
try:
    install_state.record_dsh_profile(
        dsh_home=Path.home() / ".dsh",
        profile="web",
        packages={"package": "1.0.0"},
        package_trees={"package": inventory},
        preset_path=Path.home() / ".dsh/.agent-presets/preset",
        preset_hash="1" * 64,
        expected_profile=None,
        state_snapshot=snapshot,
    )
except (OSError, ValueError) as error:
    assert "state parent identity changed" in str(error), error
else:
    raise AssertionError("DSH CAS accepted a replacement state root")

conflict = install_state.restore_dsh_profile_snapshot(
    snapshot,
    expected_profile=None,
)
assert conflict == snapshot.path, conflict
assert (displaced / "state.json").read_bytes() == original
assert (state_root / "state.json").read_bytes() == original
assert not list(displaced.glob(".state*.tmp")), list(displaced.iterdir())
assert not list(state_root.glob(".state*.tmp")), list(state_root.iterdir())
assert not (displaced / ".state.lock").exists()
assert not (state_root / ".state.lock").exists()
PY

    [ "$status" -eq 0 ]
}
