#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Offline fake for the DSH plugin-manager process boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


SUPPORTED_VERSION = "0.1.1-rc.2"
SUPPORTED_PNPM_VERSION = "11.24.0"


def _home() -> Path:
    return Path(os.environ["DSH_HOME"])


def _control() -> dict[str, object]:
    path = _home() / "fake-control.json"
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _matches_control(key: str, value: object) -> bool:
    return value == key or (isinstance(value, list) and key in value)


def _consume_control_match(field: str, key: str) -> bool:
    control = _control()
    value = control.get(field)
    if not _matches_control(key, value):
        return False
    if isinstance(value, list):
        remaining = [item for item in value if item != key]
        if remaining:
            control[field] = remaining
        else:
            control.pop(field, None)
    else:
        control.pop(field, None)
    (_home() / "fake-control.json").write_text(json.dumps(control), encoding="utf-8")
    return True


def _append_argv(argv: list[str]) -> None:
    home = _home()
    home.mkdir(parents=True, exist_ok=True)
    with (home / "fake-argv.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(argv) + "\n")
    (home / "fake-env-keys.json").write_text(
        json.dumps(sorted(os.environ)) + "\n",
        encoding="utf-8",
    )
    if _control().get("record_path"):
        with (home / "fake-path.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(os.environ.get("PATH", "")) + "\n")


def _spawn_delayed_descendant_tree(profile_root: Path) -> None:
    control = _control()
    delay = float(control.get("descendant_delay_seconds", 0.4))
    marker = _home() / "late-descendant-marker.txt"
    profile_marker = profile_root / "late-descendant-profile-write.txt"
    grandchild = """
import sys
import time
from pathlib import Path

time.sleep(float(sys.argv[1]))
marker = Path(sys.argv[2])
profile_marker = Path(sys.argv[3])
marker.write_text("late descendant survived\\n", encoding="utf-8")
profile_marker.parent.mkdir(parents=True, exist_ok=True)
profile_marker.write_text("late profile mutation\\n", encoding="utf-8")
"""
    child = """
import subprocess
import sys
import time

subprocess.Popen([
    sys.executable,
    "-c",
    sys.argv[1],
    sys.argv[2],
    sys.argv[3],
    sys.argv[4],
])
time.sleep(float(sys.argv[5]))
"""
    subprocess.Popen(
        [
            sys.executable,
            "-c",
            child,
            grandchild,
            str(delay),
            str(marker),
            str(profile_marker),
            str(control.get("descendant_parent_sleep_seconds", 5)),
        ]
    )


def _package_parts(specification: str) -> tuple[str, str]:
    package, version = specification.rsplit("@", 1)
    return package, version


def _package_root(profile_root: Path, package: str) -> Path:
    return profile_root / "node_modules" / Path(package)


def _write_profile_manifest(profile_root: Path, dependencies: dict[str, str]) -> None:
    profile_root.mkdir(parents=True, exist_ok=True)
    manifest = {"dependencies": dict(sorted(dependencies.items()))}
    (profile_root / "package.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def _create_preset_race(kind: object) -> None:
    destination = _home() / ".agent-presets" / "softspark-orchestrator"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if kind == "directory":
        destination.mkdir()
        (destination / "keep.txt").write_text(
            "concurrent user data\n", encoding="utf-8"
        )
    elif kind == "file":
        destination.write_text("concurrent user data\n", encoding="utf-8")
    elif kind == "symlink":
        target = _home() / "concurrent-user-preset"
        target.mkdir()
        (target / "keep.txt").write_text("concurrent user data\n", encoding="utf-8")
        destination.symlink_to(target, target_is_directory=True)


def _replace_package_with_user_data(profile_root: Path, package: str) -> None:
    """Simulate an unowned concurrent replacement without discarding old bytes."""
    package_root = _package_root(profile_root, package)
    preserved = package_root.with_name(f"{package_root.name}.pre-race")
    if package_root.exists() and not preserved.exists():
        package_root.rename(preserved)
    package_root.mkdir(parents=True, exist_ok=False)
    (package_root / "package.json").write_text(
        json.dumps({"name": package, "version": "9.9.9"}) + "\n",
        encoding="utf-8",
    )
    (package_root / "concurrent-user-data.txt").write_text(
        "preserve concurrent bytes\n", encoding="utf-8"
    )
    manifest_path = profile_root / "package.json"
    dependencies = json.loads(manifest_path.read_text(encoding="utf-8")).get(
        "dependencies", {}
    )
    dependencies[package] = "9.9.9"
    _write_profile_manifest(profile_root, dependencies)


def _add(profile_root: Path, specification: str) -> int:
    package, version = _package_parts(specification)
    manifest_path = profile_root / "package.json"
    dependencies = {}
    if manifest_path.is_file():
        dependencies = json.loads(manifest_path.read_text(encoding="utf-8")).get(
            "dependencies", {}
        )
    dependencies[package] = version
    package_root = _package_root(profile_root, package)
    package_root.mkdir(parents=True, exist_ok=True)
    (package_root / "package.json").write_text(
        json.dumps({"name": package, "version": version}) + "\n",
        encoding="utf-8",
    )
    if package == "@softspark/dsh-orchestrator":
        preset = package_root / "agent-presets" / "softspark-orchestrator"
        preset.mkdir(parents=True, exist_ok=True)
        control = _control()
        content = control.get(
            "preset_content_once",
            control.get("preset_content", "softspark orchestrator\n"),
        )
        (preset / "preset.md").write_text(str(content), encoding="utf-8")
        if "preset_content_once" in control:
            control.pop("preset_content_once")
            (_home() / "fake-control.json").write_text(
                json.dumps(control), encoding="utf-8"
            )
    _write_profile_manifest(profile_root, dependencies)
    return 0


def _remove(profile_root: Path, package: str) -> int:
    manifest_path = profile_root / "package.json"
    dependencies = {}
    if manifest_path.is_file():
        dependencies = json.loads(manifest_path.read_text(encoding="utf-8")).get(
            "dependencies", {}
        )
    dependencies.pop(package, None)
    package_root = _package_root(profile_root, package)
    if package_root.is_dir():
        for path in sorted(package_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        package_root.rmdir()
    _write_profile_manifest(profile_root, dependencies)
    return 0


def _pnpm_main(argv: list[str]) -> int:
    if argv != ["--version"]:
        print("unsupported fake pnpm invocation", file=sys.stderr)
        return 64
    control = _control()
    if sleep_seconds := control.get("pnpm_sleep_seconds"):
        time.sleep(float(sleep_seconds))
    if stdout := control.get("pnpm_stdout"):
        print(str(stdout))
    if stderr := control.get("pnpm_stderr"):
        print(str(stderr), file=sys.stderr)
    if failure_code := control.get("pnpm_fail_code"):
        return int(failure_code)
    if "pnpm_stdout" not in control:
        print(str(control.get("pnpm_version", SUPPORTED_PNPM_VERSION)))
    return 0


def main(argv: list[str]) -> int:
    if Path(sys.argv[0]).name == "pnpm":
        return _pnpm_main(argv)
    if argv == ["--version"]:
        print(f"dsh {_control().get('version', SUPPORTED_VERSION)}")
        return 0
    _append_argv(argv)
    if len(argv) < 5 or argv[:2] != ["plugin", "--profile"]:
        print("unsupported fake invocation", file=sys.stderr)
        return 64
    profile, operation, operand = argv[2:5]
    profile_root = _home() / "profiles" / profile
    package = _package_parts(operand)[0] if operation == "add" else operand
    failure_key = f"{operation}:{package}"
    if _matches_control(
        failure_key,
        _control().get("spawn_delayed_descendant_tree_before"),
    ):
        _spawn_delayed_descendant_tree(profile_root)
        time.sleep(float(_control().get("descendant_host_sleep_seconds", 5)))
    if _matches_control(failure_key, _control().get("sleep_before")):
        time.sleep(float(_control().get("sleep_seconds", 1)))
    if _consume_control_match("fail_before_once", failure_key) or _matches_control(
        failure_key, _control().get("fail_before")
    ):
        control = _control()
        if _matches_control(failure_key, control.get("replace_package_before_failure")):
            replacement = control.get("replacement_package", "@softspark/dsh-codex")
            _replace_package_with_user_data(profile_root, str(replacement))
        control = _control()
        if "failure_stdout" in control:
            print(str(control["failure_stdout"]))
        if "failure_stderr" in control:
            print(str(control["failure_stderr"]), file=sys.stderr)
        if "failure_stdout" not in control and "failure_stderr" not in control:
            message = control.get("failure_message", "simulated offline plugin failure")
            print(str(message), file=sys.stderr)
        return int(_control().get("fail_code", 70))
    if _consume_control_match("success_noop_once", failure_key) or _matches_control(
        failure_key, _control().get("success_noop")
    ):
        return 0
    if _consume_control_match("wrong_version_once", failure_key):
        if operation != "add":
            return 64
        operand = f"{package}@9.9.9"
    if operation == "add" and argv[5:] == ["--save-exact"]:
        result = _add(profile_root, operand)
        if package == "@softspark/dsh-orchestrator" and (
            race_kind := _control().get("preset_race_after_add")
        ):
            _create_preset_race(race_kind)
        if _consume_control_match("fail_after_once", failure_key) or _matches_control(
            failure_key, _control().get("fail_after")
        ):
            print("simulated late add failure", file=sys.stderr)
            return 71
        if _consume_control_match("mutate_unrelated_once", failure_key):
            manifest = json.loads(
                (profile_root / "package.json").read_text(encoding="utf-8")
            )
            manifest.setdefault("dependencies", {})["unrelated"] = "9.9.9"
            _write_profile_manifest(profile_root, manifest["dependencies"])
        return result
    if operation == "remove" and len(argv) == 5:
        result = _remove(profile_root, operand)
        if _consume_control_match("fail_after_once", failure_key) or _matches_control(
            failure_key, _control().get("fail_after")
        ):
            print("simulated late remove failure", file=sys.stderr)
            return 72
        if _consume_control_match("mutate_unrelated_once", failure_key):
            manifest = json.loads(
                (profile_root / "package.json").read_text(encoding="utf-8")
            )
            manifest.setdefault("dependencies", {})["unrelated"] = "9.9.9"
            _write_profile_manifest(profile_root, manifest["dependencies"])
        return result
    print("unsupported fake plugin invocation", file=sys.stderr)
    return 64


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
