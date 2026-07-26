#!/usr/bin/env python3
"""Verify a cross-built rtk binary is silent, and fingerprint it for drift.

Phase 1 of kb/history/completed/rtk-pack-integration-20260726.md. "No telemetry symbols in
the binary" is NOT a usable acceptance test: the guard is a runtime branch on a
const (`telemetry.rs:23-26`), not a `#[cfg]`, and `Cargo.toml:51` sets
`strip = true`, so a symbol check passes for the wrong reason. This script
asserts what is actually checkable instead:

  build-gate   RTK_TELEMETRY_URL / RTK_TELEMETRY_TOKEN unset at build time
  runs         the binary starts and reports its version
  no-state     a sandboxed run creates no telemetry state on disk
  offline      a run with no network route behaves identically (Linux only)
  fingerprint  size, digest and TLS-marker scan, recorded for drift detection

Stdlib only. Emits JSON to stdout; exits non-zero if any assertion fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Compile-time telemetry inputs. Upstream injects these in its own release
# workflow (release.yml:85-86); our builds must leave both undefined.
TELEMETRY_BUILD_VARS = ("RTK_TELEMETRY_URL", "RTK_TELEMETRY_TOKEN")

# Telemetry state rtk would create if it ever ran the ping path. Names come from
# src/core/telemetry.rs (salt file) and the tracking DB under the data dir.
TELEMETRY_STATE_GLOBS = ("**/rtk/*salt*", "**/rtk/telemetry*", "**/rtk/*consent*")

# webpki-roots embeds CA subjects as readable DER. Their presence means rustls
# survived LTO, which is advisory rather than a failure: it says the HTTP stack
# was linked in, not that anything is sent. Recorded so drift is visible.
TLS_MARKERS = (b"ISRG Root X1", b"DigiCert", b"Baltimore CyberTrust", b"GlobalSign")

RUNNABLE_HERE = {
    ("Darwin", "arm64"): {"aarch64-apple-darwin"},
    ("Darwin", "x86_64"): {"x86_64-apple-darwin"},
    ("Linux", "x86_64"): {"x86_64-unknown-linux-gnu", "x86_64-unknown-linux-musl"},
    ("Linux", "aarch64"): {"aarch64-unknown-linux-gnu", "aarch64-unknown-linux-musl"},
    ("Windows", "AMD64"): {"x86_64-pc-windows-msvc"},
}

# qemu-user turns the one genuinely cross-built target into a verifiable one.
# Without it every assertion below reports "skipped" and the artifact ships
# having been started exactly zero times.
QEMU_FOR = {
    "aarch64-unknown-linux-gnu": ("qemu-aarch64-static", "qemu-aarch64"),
    "aarch64-unknown-linux-musl": ("qemu-aarch64-static", "qemu-aarch64"),
}

# Rosetta 2 does the same job on Apple silicon, which is what lets us verify an
# x86_64 artifact built on an arm64 runner. Probed, never assumed: the image can
# ship without it.
ROSETTA_FOR = {"x86_64-apple-darwin": ("Darwin", "arm64")}


class Failure(Exception):
    pass


def can_run_natively(target: str) -> bool:
    return target in RUNNABLE_HERE.get((platform.system(), platform.machine()), set())


def emulator_for(target: str) -> list | None:
    """qemu invocation for this target, with the sysroot passed as a flag.

    The prefix goes through `-L` rather than QEMU_LD_PREFIX because the offline
    check runs under sudo, and sudo's env_reset strips the variable. A gnu
    target is dynamically linked, so losing it means qemu cannot find
    ld-linux-aarch64.so.1 and the process dies with 255 before main.
    """
    if can_run_natively(target) or platform.system() != "Linux":
        return None
    for candidate in QEMU_FOR.get(target, ()):
        found = shutil.which(candidate)
        if not found:
            continue
        prefix = os.environ.get("QEMU_LD_PREFIX", "")
        return [found, "-L", prefix] if prefix else [found]
    return None


def rosetta_for(target: str) -> list | None:
    if ROSETTA_FOR.get(target) != (platform.system(), platform.machine()):
        return None
    if shutil.which("arch") is None:
        return None
    try:
        probe = subprocess.run(
            ["arch", "-x86_64", "/usr/bin/true"], capture_output=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return ["arch", "-x86_64"] if probe.returncode == 0 else None


def launcher(target: str):
    """(wrapper, how) for running this target here, or (None, reason)."""
    if can_run_natively(target):
        return [], "native"
    emu = emulator_for(target)
    if emu:
        return emu, f"emulated via {Path(emu[0]).name}"
    rosetta = rosetta_for(target)
    if rosetta:
        return rosetta, "translated via Rosetta 2"
    return None, f"{target} is not runnable on {platform.system()}/{platform.machine()} and no emulator is installed"


def sandbox_env(root: Path) -> dict:
    """An environment whose config/data/cache all resolve inside root."""
    env = dict(os.environ)
    for var in TELEMETRY_BUILD_VARS:
        env.pop(var, None)
    env["HOME"] = str(root)
    env["USERPROFILE"] = str(root)
    env["XDG_CONFIG_HOME"] = str(root / "config")
    env["XDG_DATA_HOME"] = str(root / "data")
    env["XDG_CACHE_HOME"] = str(root / "cache")
    env["APPDATA"] = str(root / "AppData" / "Roaming")
    env["LOCALAPPDATA"] = str(root / "AppData" / "Local")
    return env


def run(binary: Path, args: list, env: dict, wrapper: list | None = None):
    cmd = (wrapper or []) + [str(binary)] + args
    proc = subprocess.run(cmd, env=env, capture_output=True, timeout=120)
    return proc.returncode, proc.stdout.decode("utf-8", "replace"), proc.stderr.decode("utf-8", "replace")


def check_build_gate() -> dict:
    """The variables must be undefined in this environment too.

    The workflow asserts this before `cargo build`; re-asserting here catches a
    verification job that was handed a binary from a contaminated build.
    """
    leaked = [v for v in TELEMETRY_BUILD_VARS if os.environ.get(v)]
    if leaked:
        raise Failure(f"telemetry build variables are set: {', '.join(leaked)}")
    return {"pass": True, "checked": list(TELEMETRY_BUILD_VARS)}


def check_runs(binary: Path, target: str, upstream_tag: str) -> dict:
    """Starts, identifies itself as rtk, and reports the version we asked for.

    Without the identity assertion this check passes for any binary that exits
    0 on an unknown flag, `/bin/echo` included.
    """
    wrapper, how = launcher(target)
    if wrapper is None:
        return {"pass": None, "skipped": how}
    with tempfile.TemporaryDirectory() as tmp:
        code, out, err = run(binary, ["--version"], sandbox_env(Path(tmp)), wrapper=wrapper)
    if code != 0:
        raise Failure(f"`rtk --version` exited {code}: {err.strip()[:200]}")
    version = (out.strip() or err.strip())
    if "rtk" not in version.lower():
        raise Failure(f"`--version` output does not identify rtk: {version[:120]!r}")
    expected = upstream_tag.lstrip("v")
    if expected and expected not in version:
        raise Failure(f"version {version[:120]!r} does not match upstream tag {upstream_tag}")
    return {"pass": True, "version": version, "how": how}


def check_no_state(binary: Path, target: str) -> dict:
    """A real command must not leave telemetry state behind."""
    wrapper, how = launcher(target)
    if wrapper is None:
        return {"pass": None, "skipped": how}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        env = sandbox_env(root)
        for args in (["--version"], ["--help"], ["git", "status"]):
            run(binary, args, env, wrapper=wrapper)
        found = sorted(
            str(p.relative_to(root))
            for pattern in TELEMETRY_STATE_GLOBS
            for p in root.glob(pattern)
            if p.is_file()
        )
    if found:
        raise Failure(f"telemetry state created: {found}")
    return {"pass": True, "sandbox_clean": True}


def check_offline(binary: Path, target: str) -> dict:
    """Run with no network route and assert identical behaviour.

    `unshare -rn` gives a network namespace with only a down loopback, so any
    outbound connection fails immediately. There is no equivalent that works
    unprivileged on macOS or Windows runners, so this assertion is Linux-only
    and reports itself skipped elsewhere rather than pretending to pass.
    """
    wrapper, how = launcher(target)
    if wrapper is None:
        return {"pass": None, "skipped": how}
    if platform.system() != "Linux" or shutil.which("unshare") is None:
        return {"pass": None, "skipped": "unshare(1) network namespaces are Linux-only"}

    # Ubuntu 24.04 sets kernel.apparmor_restrict_unprivileged_userns=1, so the
    # unprivileged form is refused on GitHub runners and this assertion silently
    # became a skip. Fall back to passwordless sudo, which runners have.
    #
    # Each entry is (baseline, isolated): identical except for the network
    # namespace. Comparing against a plain run instead would confound the
    # network with sudo's env_reset, and the difference would be read as
    # evidence about the binary when it is evidence about the harness.
    isolators = [
        (["unshare", "-r"], ["unshare", "-rn"]),
        (["sudo", "-n", "unshare", "-r"], ["sudo", "-n", "unshare", "-rn"]),
    ]
    baseline = isolated = None
    for base, iso in isolators:
        if subprocess.run(iso + ["true"], capture_output=True, timeout=30).returncode == 0:
            baseline, isolated = base, iso
            break
    if isolated is None:
        return {"pass": None, "skipped": "no usable network namespace: unprivileged userns refused and sudo unavailable"}

    with tempfile.TemporaryDirectory() as tmp:
        env = sandbox_env(Path(tmp))
        online_code, _, online_err = run(binary, ["--version"], env, wrapper=baseline + wrapper)
        offline_code, _, offline_err = run(binary, ["--version"], env, wrapper=isolated + wrapper)
    if online_code != 0:
        # The baseline could not start inside the namespace, so the comparison
        # says nothing about the binary. That is a harness limitation, not a
        # defect in the artifact, and reporting it as a failure would blame the
        # thing being measured for the measurement not working. Skip instead,
        # and carry the reason so it is visible rather than silent.
        return {
            "pass": None,
            "skipped": (
                f"baseline run under {' '.join(baseline)} exited {online_code}, "
                f"so the network comparison proves nothing"
            ),
            "detail": online_err.strip()[:200],
        }
    if offline_code != online_code:
        raise Failure(
            f"behaviour differs without a network route: online exit {online_code}, offline exit {offline_code}"
        )
    return {
        "pass": True,
        "exit_code": offline_code,
        "stderr_empty": not offline_err.strip(),
        "isolator": " ".join(isolated),
    }


def fingerprint(binary: Path) -> dict:
    data = binary.read_bytes()
    markers = sorted(m.decode() for m in TLS_MARKERS if m in data)
    printable = re.findall(rb"[\x20-\x7e]{8,}", data)
    return {
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "tls_markers_present": markers,
        "printable_string_count": len(printable),
        "strings_digest": hashlib.sha256(b"\n".join(sorted(set(printable)))).hexdigest(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--binary", required=True, type=Path)
    ap.add_argument("--target", required=True)
    ap.add_argument("--upstream-tag", default="", help="recorded in the manifest for traceability")
    ap.add_argument("--out", type=Path, help="write the manifest here as well as stdout")
    args = ap.parse_args()

    if not args.binary.is_file():
        print(json.dumps({"error": f"no such binary: {args.binary}"}), file=sys.stderr)
        return 2

    checks = {}
    failures = []
    for name, fn in (
        ("build_gate", lambda: check_build_gate()),
        ("runs", lambda: check_runs(args.binary, args.target, args.upstream_tag)),
        ("no_state", lambda: check_no_state(args.binary, args.target)),
        ("offline", lambda: check_offline(args.binary, args.target)),
    ):
        try:
            checks[name] = fn()
        except Failure as exc:
            checks[name] = {"pass": False, "reason": str(exc)}
            failures.append(f"{name}: {exc}")
        except (OSError, subprocess.SubprocessError) as exc:
            checks[name] = {"pass": False, "reason": f"{type(exc).__name__}: {exc}"}
            failures.append(f"{name}: {exc}")

    # A target nobody could start here must not report "pass". Every runtime
    # assertion would have been skipped, and a green tick on an artifact that
    # was never executed is the same silent-pass trap this plan keeps finding.
    ran_anything = checks.get("runs", {}).get("pass") is True
    if failures:
        verdict = "fail"
    elif ran_anything:
        verdict = "pass"
    else:
        verdict = "inconclusive"

    manifest = {
        "target": args.target,
        "upstream_tag": args.upstream_tag,
        "host": f"{platform.system()}/{platform.machine()}",
        # Recorded because the emulated path only works when the workflow
        # supplies the cross sysroot; a manifest that does not say so cannot be
        # audited later.
        "qemu_ld_prefix": os.environ.get("QEMU_LD_PREFIX", ""),
        "checks": checks,
        "fingerprint": fingerprint(args.binary),
        "verdict": verdict,
        "failures": failures,
    }
    text = json.dumps(manifest, indent=2, sort_keys=True)
    print(text)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
