#!/usr/bin/env bats
# Native Codex hooks generator contract and safety tests.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    TEST_ROOT="$(mktemp -d)"
}

teardown() {
    rm -rf "$TEST_ROOT"
}

file_mode() {
    python3 - "$1" <<'PY'
import stat
import sys
from pathlib import Path

print(format(stat.S_IMODE(Path(sys.argv[1]).stat().st_mode), "o"))
PY
}

@test "codex-hooks-native: project hooks are self-contained and schema-valid" {
    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"/hooks"* ]]
    [[ "$output" == *"trust"* ]]
    [ -f "$TEST_ROOT/.codex/hooks.json" ]
    [ -x "$TEST_ROOT/.codex/hooks/guard-destructive.sh" ]
    [ -f "$TEST_ROOT/.codex/hooks/_hook-io.sh" ]

    run python3 - "$TEST_ROOT/.codex/hooks.json" <<'PY'
import json
import sys
from pathlib import Path

supported = {
    "PreToolUse", "PostToolUse", "PermissionRequest", "PreCompact",
    "PostCompact", "SessionStart", "UserPromptSubmit", "SubagentStart",
    "SubagentStop", "Stop",
}
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert set(data) == {"hooks"}
assert set(data["hooks"]) <= supported
assert "PostCompact" not in data["hooks"]
for event, groups in data["hooks"].items():
    for group in groups:
        assert set(group) in ({"hooks"}, {"matcher", "hooks"}), (event, group)
        if event in {"PreToolUse", "PostToolUse", "PermissionRequest"}:
            assert group.get("matcher") == "Bash", (event, group)
        if event in {"UserPromptSubmit", "Stop"}:
            assert "matcher" not in group, (event, group)
        for handler in group["hooks"]:
            assert set(handler) == {"type", "command"}, handler
            assert handler["type"] == "command"
            command = handler["command"]
            assert "AI_TOOLKIT_HOOK_OWNER=ai-toolkit" in command
            assert "$(git rev-parse --show-toplevel" in command
            assert "/.codex/hooks/" in command
            assert ".softspark/ai-toolkit/hooks" not in command
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: global hooks use stable Codex home assets" {
    run env HOME="$TEST_ROOT" python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from generate_codex_hooks import generate

generate(target, global_install=True)
PY
    [ "$status" -eq 0 ]
    [[ "$output" == *"/hooks"* ]]
    [ -x "$TEST_ROOT/.codex/ai-toolkit-hooks/guard-destructive.sh" ]
    [ ! -e "$TEST_ROOT/.codex/hooks/guard-destructive.sh" ]
    grep -q '\${CODEX_HOME:-\$HOME/.codex}/ai-toolkit-hooks/' \
        "$TEST_ROOT/.codex/hooks.json"
    ! grep -q 'git rev-parse' "$TEST_ROOT/.codex/hooks.json"
}

@test "codex-hooks-native: merge preserves user handlers and replaces managed legacy entries" {
    mkdir -p "$TEST_ROOT/.codex/hooks"
    cat > "$TEST_ROOT/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo user-pre"}]},
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "AI_TOOLKIT_HOOK_QUIET=1 \"$HOME/.softspark/ai-toolkit/hooks/guard-destructive.sh\""}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "echo user-stop"}]}
    ]
  }
}
JSON
    printf '%s\n' '#!/usr/bin/env bash' '# ai-toolkit-managed: codex-hook-script' \
        'exit 0' > "$TEST_ROOT/.codex/hooks/retired-managed.sh"
    printf '%s\n' '#!/usr/bin/env bash' 'echo user' \
        > "$TEST_ROOT/.codex/hooks/user-owned.sh"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT"
    [ "$status" -eq 0 ]
    grep -q 'echo user-pre' "$TEST_ROOT/.codex/hooks.json"
    grep -q 'echo user-stop' "$TEST_ROOT/.codex/hooks.json"
    ! grep -q '.softspark/ai-toolkit/hooks' "$TEST_ROOT/.codex/hooks.json"
    [ ! -e "$TEST_ROOT/.codex/hooks/retired-managed.sh" ]
    [ -f "$TEST_ROOT/.codex/hooks/user-owned.sh" ]

    find "$TEST_ROOT/.codex" -type f -exec shasum {} \; | sort > "$TEST_ROOT/first.sha"
    python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT" >/dev/null
    find "$TEST_ROOT/.codex" -type f ! -name 'first.sha' -exec shasum {} \; | sort \
        > "$TEST_ROOT/second.sha"
    cmp "$TEST_ROOT/first.sha" "$TEST_ROOT/second.sha"
}

@test "codex-hooks-native: user script collisions fail without overwrite" {
    mkdir -p "$TEST_ROOT/.codex/hooks"
    printf '%s\n' '#!/usr/bin/env bash' 'echo user guard' \
        > "$TEST_ROOT/.codex/hooks/guard-destructive.sh"
    cp "$TEST_ROOT/.codex/hooks/guard-destructive.sh" "$TEST_ROOT/user-guard.before"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT"
    [ "$status" -ne 0 ]
    cmp "$TEST_ROOT/user-guard.before" "$TEST_ROOT/.codex/hooks/guard-destructive.sh"
    [ ! -e "$TEST_ROOT/.codex/hooks.json" ]
}

@test "codex-hooks-native: symlinked roots and files never write externally" {
    external="$TEST_ROOT/external"
    mkdir -p "$external"
    printf '%s\n' 'external sentinel' > "$external/sentinel.txt"
    shasum "$external/sentinel.txt" > "$TEST_ROOT/external.before"

    target="$TEST_ROOT/target"
    mkdir -p "$target"
    ln -s "$external" "$target/.codex"
    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$target"
    [ "$status" -ne 0 ]
    shasum "$external/sentinel.txt" > "$TEST_ROOT/external.after"
    cmp "$TEST_ROOT/external.before" "$TEST_ROOT/external.after"
    [ ! -e "$external/hooks.json" ]

    file_target="$TEST_ROOT/file-target"
    mkdir -p "$file_target/.codex"
    ln -s "$external/sentinel.txt" "$file_target/.codex/hooks.json"
    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$file_target"
    [ "$status" -ne 0 ]
    grep -q 'external sentinel' "$external/sentinel.txt"
}

@test "codex-hooks-native: failed atomic replacement preserves prior artifacts" {
    python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT" >/dev/null

    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks as module

hooks_json = target / ".codex" / "hooks.json"
guard = target / ".codex" / "hooks" / "guard-destructive.sh"
before = {
    path.relative_to(target): path.read_bytes()
    for path in (target / ".codex").rglob("*")
    if path.is_file()
}
real_replace = os.replace
calls = 0

def fail_after_two_replacements(source, destination, **kwargs):
    global calls
    calls += 1
    if calls == 3:
        raise OSError("injected late hooks replace failure")
    return real_replace(source, destination, **kwargs)

with mock.patch("os.replace", side_effect=fail_after_two_replacements):
    try:
        module.generate(target)
    except OSError as error:
        assert "injected late hooks replace failure" in str(error)
    else:
        raise AssertionError("expected replacement failure")

after = {
    path.relative_to(target): path.read_bytes()
    for path in (target / ".codex").rglob("*")
    if path.is_file() and not path.name.endswith(".tmp")
}
assert after == before, (before.keys(), after.keys())
assert not list((target / ".codex").rglob("*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: public writer pins parent across ancestor swap and rollback" {
    local target="$TEST_ROOT/target"
    local external="$TEST_ROOT/external"
    mkdir -p "$target/.codex" "$external"
    cat > "$target/.codex/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo original"}]}]}}
JSON
    printf '%s\n' 'external hooks sentinel' > "$external/hooks.json"
    printf '%s\n' 'external sibling sentinel' > "$external/sibling.txt"

    run python3 - "$TOOLKIT_DIR" "$target" "$external" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
external = Path(sys.argv[3])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks as module

codex_dir = target / ".codex"
real_codex_dir = target / ".codex-real"
hooks_path = codex_dir / "hooks.json"
original = hooks_path.read_bytes()
external_before = {
    path.name: path.read_bytes() for path in external.iterdir() if path.is_file()
}
replacement = {
    "hooks": {
        "Stop": [
            {"hooks": [{"type": "command", "command": "echo replacement"}]}
        ]
    }
}
real_replace = os.replace
swapped = False

def swap_then_fail(source, destination, **kwargs):
    global swapped
    if not swapped:
        swapped = True
        real_replace(codex_dir, real_codex_dir)
        os.symlink(external, codex_dir)
        real_replace(source, destination, **kwargs)
        raise OSError("injected ancestor swap failure")
    return real_replace(source, destination, **kwargs)

with mock.patch("os.replace", side_effect=swap_then_fail):
    try:
        module.write_hooks_json(hooks_path, replacement)
    except OSError as error:
        assert "ancestor swap failure" in str(error)
    else:
        raise AssertionError("expected ancestor swap failure")

assert codex_dir.is_symlink()
assert (real_codex_dir / "hooks.json").read_bytes() == original
assert {
    path.name: path.read_bytes() for path in external.iterdir() if path.is_file()
} == external_before
assert not list(real_codex_dir.rglob("*.tmp"))
assert not list(external.rglob("*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: preserves existing mode and creates secure config with executable assets" {
    local existing="$TEST_ROOT/existing"
    local fresh="$TEST_ROOT/fresh"
    mkdir -p "$existing/.codex" "$fresh"
    cat > "$existing/.codex/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo user"}]}]}}
JSON
    chmod 0600 "$existing/.codex/hooks.json"

    run bash -c "umask 077; python3 '$TOOLKIT_DIR/scripts/generate_codex_hooks.py' '$existing' >/dev/null"
    [ "$status" -eq 0 ]
    [ "$(file_mode "$existing/.codex/hooks.json")" = "600" ]

    run bash -c "umask 077; python3 '$TOOLKIT_DIR/scripts/generate_codex_hooks.py' '$fresh' >/dev/null"
    [ "$status" -eq 0 ]
    [ "$(file_mode "$fresh/.codex/hooks.json")" = "600" ]
    [ "$(file_mode "$fresh/.codex/hooks/guard-destructive.sh")" = "755" ]
}

@test "codex-hooks-native: root traversal pins every intermediate ancestor" {
    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import json
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks as module

stable = root / "stable"
real_stable = root / "stable-real"
external = root / "external"
relative = Path("inner/project/.codex")
real_codex = stable / relative
external_codex = external / relative
real_codex.mkdir(parents=True)
external_codex.mkdir(parents=True)
hooks_path = real_codex / "hooks.json"
external_hooks = external_codex / "hooks.json"
hooks_path.write_text('{"hooks":{}}\n', encoding="utf-8")
external_hooks.write_text("external sentinel\n", encoding="utf-8")
external_before = external_hooks.read_bytes()
document = {
    "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "echo pinned"}]}]
    }
}
trusted_root = real_codex
real_open = os.open
swapped = False

def swap_during_root_traversal(path, flags, mode=0o777, *, dir_fd=None):
    global swapped
    raw = os.fspath(path)
    old_absolute_open = os.path.abspath(raw) == os.path.abspath(trusted_root)
    new_component_open = raw == "inner" and dir_fd is not None
    if not swapped and (old_absolute_open or new_component_open):
        swapped = True
        os.replace(stable, real_stable)
        os.symlink(external, stable)
    if dir_fd is None:
        return real_open(path, flags, mode)
    return real_open(path, flags, mode, dir_fd=dir_fd)

with mock.patch("os.open", side_effect=swap_during_root_traversal):
    module.write_hooks_json(
        hooks_path,
        document,
        trusted_root=trusted_root,
    )

assert stable.is_symlink()
updated = json.loads((real_stable / relative / "hooks.json").read_text())
assert updated == document
assert external_hooks.read_bytes() == external_before
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: one trusted-root pin is reused for every destination" {
    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from secure_fs import SecureDestination, SecureTransaction, run_secure_transaction

stable = root / "stable"
real_stable = root / "stable-real"
external = root / "external"
relative = Path("inner/project/.codex")
trusted_root = stable / relative
external_root = external / relative
trusted_root.mkdir(parents=True)
external_root.mkdir(parents=True)
(external_root / "first.json").write_text("external first\n", encoding="utf-8")
(external_root / "second.json").write_text("external second\n", encoding="utf-8")
external_before = {
    path.name: path.read_bytes() for path in external_root.iterdir()
}
first = SecureDestination(trusted_root / "first.json", trusted_root, "first")
second = SecureDestination(trusted_root / "second.json", trusted_root, "second")
real_prepare = SecureTransaction._prepare
prepared = 0

def swap_after_first_prepare(self, destination):
    global prepared
    result = real_prepare(self, destination)
    prepared += 1
    if prepared == 1:
        os.replace(stable, real_stable)
        os.symlink(external, stable)
    return result

def write_both(transaction):
    transaction.atomic_write(first, b"pinned first\n")
    transaction.atomic_write(second, b"pinned second\n")

with mock.patch.object(
    SecureTransaction,
    "_prepare",
    autospec=True,
    side_effect=swap_after_first_prepare,
):
    run_secure_transaction([first, second], write_both)

assert stable.is_symlink()
real_root = real_stable / relative
assert (real_root / "first.json").read_bytes() == b"pinned first\n"
assert (real_root / "second.json").read_bytes() == b"pinned second\n"
assert {
    path.name: path.read_bytes() for path in external_root.iterdir()
} == external_before
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: merges bytes changed immediately before transaction" {
    mkdir -p "$TEST_ROOT/.codex"
    printf '%s\n' '{"hooks":{}}' > "$TEST_ROOT/.codex/hooks.json"

    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import json
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks as module

hooks_path = target / ".codex/hooks.json"
concurrent = {
    "hooks": {
        "Stop": [
            {"hooks": [{"type": "command", "command": "echo concurrent-user"}]}
        ]
    }
}
real_run = module.run_secure_transaction
changed = False

def change_then_start(destinations, mutation):
    global changed
    if not changed:
        changed = True
        hooks_path.write_text(json.dumps(concurrent) + "\n", encoding="utf-8")
    return real_run(destinations, mutation)

with mock.patch.object(
    module,
    "run_secure_transaction",
    side_effect=change_then_start,
):
    module.generate(target)

data = json.loads(hooks_path.read_text(encoding="utf-8"))
commands = [
    handler["command"]
    for group in data["hooks"]["Stop"]
    for handler in group["hooks"]
]
assert "echo concurrent-user" in commands, commands
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: stale cleanup failure rolls back the whole upgrade" {
    mkdir -p "$TEST_ROOT/.codex/hooks"
    printf '%s\n' '{"hooks":{}}' > "$TEST_ROOT/.codex/hooks.json"
    printf '%s\n' '#!/usr/bin/env bash' '# ai-toolkit-managed: codex-hook-script' \
        'echo old expected' > "$TEST_ROOT/.codex/hooks/guard-destructive.sh"
    printf '%s\n' '#!/usr/bin/env bash' '# ai-toolkit-managed: codex-hook-script' \
        'echo retired' > "$TEST_ROOT/.codex/hooks/retired-managed.sh"

    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks as module
from secure_fs import SecureTransaction

before = {
    path.relative_to(target): path.read_bytes()
    for path in (target / ".codex").rglob("*")
    if path.is_file()
}
real_unlink = SecureTransaction.unlink

def fail_stale_cleanup(self, destination):
    if destination.path.name == "retired-managed.sh":
        raise OSError("injected stale cleanup failure")
    return real_unlink(self, destination)

with mock.patch.object(
    SecureTransaction,
    "unlink",
    autospec=True,
    side_effect=fail_stale_cleanup,
):
    try:
        module.generate(target)
    except OSError as error:
        assert "stale cleanup failure" in str(error)
    else:
        raise AssertionError("expected stale cleanup failure")

after = {
    path.relative_to(target): path.read_bytes()
    for path in (target / ".codex").rglob("*")
    if path.is_file()
}
assert after == before, (before.keys(), after.keys())
assert not list((target / ".codex").rglob("*.tmp"))
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: temporary cleanup never masks primary write failure" {
    mkdir -p "$TEST_ROOT/.codex"
    printf '%s\n' '{"hooks":{}}' > "$TEST_ROOT/.codex/hooks.json"

    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
target = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from secure_fs import SecureDestination, SecureTransaction

path = target / ".codex/hooks.json"
destination = SecureDestination(path, target, "test hooks")
transaction = SecureTransaction([destination])
transaction.materialize_parents()

def primary_failure(*_args, **_kwargs):
    raise OSError("primary replace failure")

def cleanup_failure(*_args, **_kwargs):
    raise OSError("secondary cleanup failure")

try:
    with mock.patch("os.replace", side_effect=primary_failure), mock.patch(
        "os.unlink", side_effect=cleanup_failure
    ):
        try:
            transaction.atomic_write(destination, b'{"hooks":{}}\n')
        except OSError as error:
            assert "primary replace failure" in str(error), error
        else:
            raise AssertionError("expected primary failure")
finally:
    transaction.close()
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: directory create and rollback removal fsync their parents" {
    run python3 - "$TOOLKIT_DIR" "$TEST_ROOT" <<'PY'
import os
import sys
from pathlib import Path
from unittest import mock

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
sys.path.insert(0, str(toolkit / "scripts"))
from secure_fs import SecureDestination, run_secure_transaction

destination = SecureDestination(root / "one/two/hooks.json", root, "test hooks")
real_mkdir = os.mkdir
real_rmdir = os.rmdir
real_fsync = os.fsync
events = []

def record_mkdir(path, mode=0o777, *, dir_fd=None):
    result = real_mkdir(path, mode=mode, dir_fd=dir_fd)
    events.append(("mkdir", dir_fd, os.fspath(path)))
    return result

def record_rmdir(path, *, dir_fd=None):
    result = real_rmdir(path, dir_fd=dir_fd)
    events.append(("rmdir", dir_fd, os.fspath(path)))
    return result

def record_fsync(fd):
    events.append(("fsync", fd, ""))
    return real_fsync(fd)

def fail_after_materialize(_transaction):
    raise OSError("force rollback")

with mock.patch("os.mkdir", side_effect=record_mkdir), mock.patch(
    "os.rmdir", side_effect=record_rmdir
), mock.patch("os.fsync", side_effect=record_fsync):
    try:
        run_secure_transaction([destination], fail_after_materialize)
    except OSError as error:
        assert "force rollback" in str(error)
    else:
        raise AssertionError("expected rollback")

for index, event in enumerate(events):
    if event[0] in {"mkdir", "rmdir"}:
        assert events[index + 1][:2] == ("fsync", event[1]), events
assert not (root / "one").exists()
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: context adapters reference Codex instruction surfaces" {
    python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT" >/dev/null

    session="$TEST_ROOT/.codex/hooks/codex-session-start.sh"
    compact="$TEST_ROOT/.codex/hooks/codex-pre-compact.sh"
    health="$TEST_ROOT/.codex/hooks/codex-mcp-health.sh"
    [ -x "$session" ]
    [ -x "$compact" ]
    [ -x "$health" ]
    grep -q 'AGENTS.md' "$session"
    grep -q 'AGENTS.md' "$compact"
    ! grep -q 'CLAUDE.md' "$session"
    ! grep -q 'CLAUDE.md' "$compact"
    grep -q 'mcp_servers' "$health"
    ! grep -q '\.claude/settings' "$health"
}

@test "codex-hooks-native: representative Codex payloads execute from nested cwd" {
    python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT" >/dev/null

    run python3 - "$TEST_ROOT" <<'PY'
import json
import subprocess
import sys
from pathlib import Path

project = Path(sys.argv[1])
subprocess.run(["git", "init", "-q", str(project)], check=True)
nested = project / "nested" / "cwd"
nested.mkdir(parents=True)
data = json.loads((project / ".codex" / "hooks.json").read_text())

def command(event, suffix):
    for group in data["hooks"][event]:
        for handler in group["hooks"]:
            if handler["command"].endswith(f'/{suffix}"'):
                return handler["command"]
    raise AssertionError((event, suffix))

dangerous = json.dumps({
    "session_id": "codex-test",
    "cwd": str(nested),
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "rm -rf /tmp/forbidden"},
})
blocked = subprocess.run(
    command("PreToolUse", "guard-destructive.sh"),
    shell=True,
    cwd=nested,
    input=dangerous,
    text=True,
    capture_output=True,
)
assert blocked.returncode == 2, blocked
assert "destructive" in blocked.stderr.lower(), blocked.stderr

quality = json.dumps({
    "session_id": "codex-test",
    "cwd": str(nested),
    "hook_event_name": "PreToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "git commit -m 'bad'"},
})
advisory = subprocess.run(
    command("PreToolUse", "commit-quality.sh"),
    shell=True,
    cwd=nested,
    input=quality,
    text=True,
    capture_output=True,
)
assert advisory.returncode == 0, advisory
assert "Commit quality advisory" in advisory.stdout, advisory.stdout

stop = subprocess.run(
    command("Stop", "quality-check.sh"),
    shell=True,
    cwd=nested,
    input=json.dumps({"hook_event_name": "Stop", "cwd": str(nested)}),
    text=True,
    capture_output=True,
)
assert stop.returncode == 0, stop
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: invalid existing handler schema is rejected unchanged" {
    mkdir -p "$TEST_ROOT/.codex"
    cat > "$TEST_ROOT/.codex/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo user","unknown":true}]}]}}
JSON
    cp "$TEST_ROOT/.codex/hooks.json" "$TEST_ROOT/hooks.before"

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT"
    [ "$status" -ne 0 ]
    cmp "$TEST_ROOT/hooks.before" "$TEST_ROOT/.codex/hooks.json"
    [ ! -e "$TEST_ROOT/.codex/hooks" ]
}

@test "codex-hooks-native: global CLI honors an existing custom CODEX_HOME" {
    custom_home="$TEST_ROOT/custom-codex-home"
    mkdir -p "$custom_home"

    run env HOME="$TEST_ROOT" CODEX_HOME="$custom_home" \
        python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT" --global
    [ "$status" -eq 0 ]
    [ -f "$custom_home/hooks.json" ]
    [ -x "$custom_home/ai-toolkit-hooks/guard-destructive.sh" ]
    [ ! -e "$TEST_ROOT/.codex/hooks.json" ]
    grep -q '\${CODEX_HOME:-\$HOME/.codex}/ai-toolkit-hooks/' \
        "$custom_home/hooks.json"
}

@test "codex-hooks-native: legacy plugin ownership migrates without losing its handler" {
    mkdir -p "$TEST_ROOT/.codex"
    cat > "$TEST_ROOT/.codex/hooks.json" <<'JSON'
{
  "hooks": {
    "Stop": [
      {
        "_source": "ai-toolkit-plugin-memory-pack",
        "hooks": [
          {
            "type": "command",
            "command": "\"$HOME/.softspark/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh\""
          }
        ]
      }
    ]
  }
}
JSON

    run python3 "$TOOLKIT_DIR/scripts/generate_codex_hooks.py" "$TEST_ROOT"
    [ "$status" -eq 0 ]

    run python3 - "$TEST_ROOT/.codex/hooks.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert "_source" not in json.dumps(data)
commands = [
    handler["command"]
    for groups in data["hooks"].values()
    for group in groups
    for handler in group["hooks"]
]
legacy = [
    command
    for command in commands
    if "AI_TOOLKIT_HOOK_OWNER=ai-toolkit-plugin-memory-pack" in command
]
assert len(legacy) == 1, commands
assert ".softspark/ai-toolkit/hooks/plugin-memory-pack-session-summary.sh" in legacy[0]
PY
    [ "$status" -eq 0 ]
}

@test "codex-hooks-native: validator rejects empty commands and invalid timeouts" {
    run python3 - "$TOOLKIT_DIR" <<'PY'
import copy
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
sys.path.insert(0, str(toolkit / "scripts"))
from generate_codex_hooks import validate_hooks_document

valid = {
    "hooks": {
        "Stop": [
            {
                "hooks": [
                    {"type": "command", "command": "echo valid", "timeout": 30}
                ]
            }
        ]
    }
}
validate_hooks_document(valid)

invalid_values = [
    ("command", ""),
    ("command", "   "),
    ("timeout", True),
    ("timeout", 1.5),
    ("timeout", 0),
    ("timeout", -1),
]
for field, value in invalid_values:
    document = copy.deepcopy(valid)
    document["hooks"]["Stop"][0]["hooks"][0][field] = value
    try:
        validate_hooks_document(document)
    except ValueError:
        pass
    else:
        raise AssertionError((field, value))
PY
    [ "$status" -eq 0 ]
}
