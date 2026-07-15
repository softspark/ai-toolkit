#!/usr/bin/env bats
# Windows support contract tests.

TOOLKIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "detect_os recognizes Windows package managers" {
    run python3 - <<PY
import platform
import shutil
import sys

sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import _common

platform.system = lambda: "Windows"
shutil.which = lambda name: "C:/Windows/System32/winget.exe" if name == "winget" else None

info = _common.detect_os()
assert info["os"] == "Windows", info
assert info["pkg_manager"] == "winget", info
assert info["install_cmd"] == "winget install", info
print("ok")
PY
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "project_registry imports without fcntl (Windows compat)" {
    TMP_HOME="$(mktemp -d)"
    run env HOME="$TMP_HOME" python3 - <<PY
import sys

# Make ``import fcntl`` raise ImportError to simulate Windows.
class _BlockFcntl:
    def find_module(self, name, path=None):
        return self if name == "fcntl" else None
    def load_module(self, name):
        raise ImportError("simulated: fcntl unavailable on Windows")
sys.meta_path.insert(0, _BlockFcntl())
sys.modules.pop("fcntl", None)

sys.path.insert(0, "$TOOLKIT_DIR/scripts")

from install_steps import project_registry  # must not raise

# On POSIX the lock body normally uses fcntl. Force the Windows branch and
# stub msvcrt so we exercise the cross-platform code path end-to-end.
import os, types
project_registry.fcntl = None
msvcrt_stub = types.ModuleType("msvcrt")
msvcrt_stub.LK_NBLCK = 1
msvcrt_stub.LK_UNLCK = 4
msvcrt_stub.locking = lambda fd, mode, nbytes: None
project_registry.msvcrt = msvcrt_stub
_orig_name = os.name
os.name = "nt"
try:
    with project_registry._registry_lock():
        pass
finally:
    os.name = _orig_name
print("ok")
PY
    rm -rf "$TMP_HOME"
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "check_deps exposes Windows install hints" {
    run python3 - <<PY
import platform
import shutil
import sys

sys.path.insert(0, "$TOOLKIT_DIR/scripts")
import _common
import check_deps

check_deps.detect_os = lambda: {
    "os": "Windows",
    "distro": "test",
    "pkg_manager": "winget",
    "install_cmd": "winget install",
}
check_deps.shutil.which = lambda _name: None
check_deps.get_version = lambda _binary: ""

results = check_deps.check_deps(verbose=False)
cmds = "\\n".join(results["missing_cmds"])
assert "winget install Python.Python.3" in cmds, cmds
assert "winget install Git.Git" in cmds, cmds
assert "winget install OpenJS.NodeJS" in cmds, cmds
print("ok")
PY
    [ "$status" -eq 0 ]
    [ "$output" = "ok" ]
}

@test "inject-hook mutations fail closed without secure dir_fd primitives" {
    TMP_ROOT="$(mktemp -d)"
    mkdir -p "$TMP_ROOT/target/.claude" "$TMP_ROOT/target/.codex"
    cat > "$TMP_ROOT/target/hooks.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo test"}]}]}}
JSON
    printf '%s\n' '{"permissions":{"allow":["Read"]}}' \
        > "$TMP_ROOT/target/.claude/settings.json"
    printf '%s\n' '{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo user"}]}]}}' \
        > "$TMP_ROOT/target/.codex/hooks.json"

    run env HOME="$TMP_ROOT" SOFTSPARK_HOME="$TMP_ROOT/.softspark" \
        python3 - "$TOOLKIT_DIR" "$TMP_ROOT" <<'PY'
import os
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
target = root / "target"
sys.path.insert(0, str(toolkit / "scripts"))
import inject_hook_cli as module

def snapshot(path):
    return {
        item.relative_to(path).as_posix(): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }

before = snapshot(root)
module._SECURE_DIR_FD = False
for action in (
    lambda: module.inject(str(target / "hooks.json"), str(target)),
    lambda: module.remove("hooks", str(target)),
):
    try:
        action()
    except RuntimeError as error:
        assert "No files were changed" in str(error), str(error)
    else:
        raise AssertionError("unsafe mutation helper did not fail closed")

assert module._parse_args([])["source_file"] == ""
assert snapshot(root) == before
assert not list(root.rglob("*.tmp"))
PY
    rm -rf "$TMP_ROOT"
    [ "$status" -eq 0 ]
}

@test "Codex hook writers fail closed without secure dir_fd primitives" {
    TMP_ROOT="$(mktemp -d)"
    mkdir -p "$TMP_ROOT/target/.codex"
    printf '%s\n' '{"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo user"}]}]}}' \
        > "$TMP_ROOT/target/.codex/hooks.json"

    run python3 - "$TOOLKIT_DIR" "$TMP_ROOT" <<'PY'
import sys
from pathlib import Path

toolkit = Path(sys.argv[1])
root = Path(sys.argv[2])
target = root / "target"
sys.path.insert(0, str(toolkit / "scripts"))
import generate_codex_hooks as module

def snapshot(path):
    return {
        item.relative_to(path).as_posix(): item.read_bytes()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }

document = {
    "hooks": {
        "Stop": [{"hooks": [{"type": "command", "command": "echo safe"}]}]
    }
}
module.validate_hooks_document(document)
before = snapshot(root)
module._SECURE_DIR_FD = False
for action in (
    lambda: module.write_hooks_json(target / ".codex/hooks.json", document),
    lambda: module.generate(target),
):
    try:
        action()
    except RuntimeError as error:
        assert "No files were changed" in str(error), str(error)
    else:
        raise AssertionError("unsafe Codex writer did not fail closed")

assert snapshot(root) == before
assert not list(root.rglob("*.tmp"))
PY
    rm -rf "$TMP_ROOT"
    [ "$status" -eq 0 ]
}
