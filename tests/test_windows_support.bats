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
