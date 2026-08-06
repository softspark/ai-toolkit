#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Public surface manifest — the enforceable half of BACKWARD_COMPATIBILITY.md.

`BACKWARD_COMPATIBILITY.md` names the surfaces users depend on. Prose stops
nothing: rename a skill and every gate stays green. This turns the list into a
committed snapshot and a test.

The check is deliberately one-directional:

    entry in the manifest, missing from the tree  -> FAIL   (a removal)
    entry in the tree, missing from the manifest  -> pass   (an addition)

Additions are free because a surface nobody has installed yet has no users to
break. Removals fail because someone out there pinned the version that had it.

The manifest is NOT regenerated automatically. If it were, deleting a skill would
delete its manifest entry in the same breath and the check would detect nothing.
`--update` is a deliberate act: run it, read the diff, and any line that
disappeared is a breaking change owing an entry in DECISIONS.md.

Stdlib-only.

Usage:
    python3 scripts/surface_manifest.py            # check, human-readable
    python3 scripts/surface_manifest.py --json     # check, machine-readable
    python3 scripts/surface_manifest.py --update   # rewrite app/surface.json
    python3 scripts/surface_manifest.py --toolkit-dir /path

Exit codes:
    0  no protected surface was removed
    1  a removal detected (or the manifest is missing on a check run)
    2  usage error
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir as default_toolkit_dir

MANIFEST_RELPATH = Path("app") / "surface.json"

FM_FIELD_RE = re.compile(r"^([a-z][a-z0-9-]*):")
CLI_COMMAND_RE = re.compile(r"^\s+'?([a-z][a-z0-9-]*)'?\s*:")


def _frontmatter_fields(path: Path) -> set[str]:
    parts = path.read_text(encoding="utf-8").split("---")
    if len(parts) < 3:
        return set()
    return {
        m.group(1)
        for line in parts[1].splitlines()
        if (m := FM_FIELD_RE.match(line))
    }


def collect_surface(tk_dir: Path) -> dict:
    """Read the current public surface out of the tree."""
    skills_dir = tk_dir / "app" / "skills"
    agents_dir = tk_dir / "app" / "agents"

    skills: list[str] = []
    skill_fields: set[str] = set()
    for d in sorted(skills_dir.iterdir()) if skills_dir.is_dir() else []:
        if not d.is_dir() or d.name.startswith("_") or not (d / "SKILL.md").is_file():
            continue
        skills.append(d.name)
        skill_fields |= _frontmatter_fields(d / "SKILL.md")

    agents: list[str] = []
    agent_fields: set[str] = set()
    for f in sorted(agents_dir.glob("*.md")) if agents_dir.is_dir() else []:
        agents.append(f.stem)
        agent_fields |= _frontmatter_fields(f)

    hooks_dir = tk_dir / "app" / "hooks"
    hook_scripts = sorted(
        f.name for f in hooks_dir.glob("*.sh") if not f.name.startswith("_")
    ) if hooks_dir.is_dir() else []

    hook_events: list[str] = []
    hooks_json = tk_dir / "app" / "hooks.json"
    if hooks_json.is_file():
        try:
            hook_events = sorted(json.loads(hooks_json.read_text(encoding="utf-8")).get("hooks", {}))
        except (json.JSONDecodeError, OSError):
            hook_events = []

    plugins_dir = tk_dir / "app" / "plugins"
    packs = sorted(
        d.name for d in plugins_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ) if plugins_dir.is_dir() else []

    kb_categories: list[str] = []
    validate_py = tk_dir / "scripts" / "validate.py"
    if validate_py.is_file():
        text = validate_py.read_text(encoding="utf-8")
        block = re.search(r"VALID_KB_CATEGORIES\s*=\s*frozenset\(\{(.*?)\}\)", text, re.S)
        if block:
            kb_categories = sorted(re.findall(r'"([a-z-]+)"', block.group(1)))

    cli_commands: list[str] = []
    cli = tk_dir / "bin" / "ai-toolkit.js"
    if not cli.is_file():
        candidates = sorted((tk_dir / "bin").glob("*.js")) if (tk_dir / "bin").is_dir() else []
        cli = candidates[0] if candidates else cli
    if cli.is_file():
        # The COMMANDS map is what `--help` prints, so it is the published surface.
        # An undocumented internal branch is not a promise and is not captured here.
        block = re.search(r"const COMMANDS\s*=\s*\{(.*?)\n\};", cli.read_text(encoding="utf-8"), re.S)
        if block:
            cli_commands = sorted({
                m.group(1) for line in block.group(1).splitlines()
                if (m := CLI_COMMAND_RE.match(line))
            })

    return {
        "skills": skills,
        "agents": agents,
        "skill_frontmatter_fields": sorted(skill_fields),
        "agent_frontmatter_fields": sorted(agent_fields),
        "hook_scripts": hook_scripts,
        "hook_events": hook_events,
        "plugin_packs": packs,
        "kb_categories": kb_categories,
        "cli_commands": cli_commands,
    }


def compare(manifest: dict, current: dict) -> dict:
    """Removals fail, additions pass. See the module docstring for why."""
    removed: dict[str, list[str]] = {}
    added: dict[str, list[str]] = {}
    for key, entries in manifest.items():
        if key.startswith("_"):
            continue
        have = set(current.get(key, []))
        gone = [e for e in entries if e not in have]
        if gone:
            removed[key] = gone
        new = [e for e in current.get(key, []) if e not in set(entries)]
        if new:
            added[key] = new
    return {"removed": removed, "added": added, "ok": not removed}


def _write_manifest(path: Path, current: dict) -> None:
    payload = {
        "_comment": (
            "Public surface snapshot. Removing an entry is a breaking change: see "
            "BACKWARD_COMPATIBILITY.md, and record it in DECISIONS.md. Regenerate "
            "deliberately with `python3 scripts/surface_manifest.py --update` and "
            "read the diff — never as a reflex to green a red build."
        ),
        **current,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    update = False
    as_json = False
    tk_dir = default_toolkit_dir

    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--update":
            update = True
        elif arg == "--json":
            as_json = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        elif arg == "--toolkit-dir":
            idx += 1
            if idx >= len(argv):
                print("ERROR: --toolkit-dir requires a value", file=sys.stderr)
                return 2
            tk_dir = Path(argv[idx])
        elif arg.startswith("-"):
            print(f"ERROR: unknown option: {arg}", file=sys.stderr)
            return 2
        else:
            tk_dir = Path(arg)
        idx += 1

    tk_dir = tk_dir.resolve()
    manifest_path = tk_dir / MANIFEST_RELPATH
    current = collect_surface(tk_dir)

    if update:
        _write_manifest(manifest_path, current)
        total = sum(len(v) for v in current.values())
        print(f"Wrote {manifest_path.relative_to(tk_dir)} — {total} protected entries")
        print("Read the diff. Every line removed is a breaking change.")
        return 0

    if not manifest_path.is_file():
        print(f"ERROR: {MANIFEST_RELPATH} not found — run with --update to create it",
              file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = compare(manifest, current)

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["ok"] else 1

    print("## Public Surface")
    if result["removed"]:
        for key, entries in sorted(result["removed"].items()):
            for entry in entries:
                print(f"  ERROR: {key}: '{entry}' was removed from the public surface")
        print()
        print("A removal is a breaking change. Either restore it, or take the")
        print("deprecation path in BACKWARD_COMPATIBILITY.md, record it in")
        print("DECISIONS.md, and re-run with --update.")
        print()
        print("SURFACE CHECK FAILED")
        return 1

    protected = sum(len(v) for k, v in manifest.items() if not k.startswith("_"))
    print(f"  OK: {protected} protected entries intact")
    if result["added"]:
        new_total = sum(len(v) for v in result["added"].values())
        detail = ", ".join(f"{k} +{len(v)}" for k, v in sorted(result["added"].items()))
        print(f"  Note: {new_total} new entries not yet protected ({detail})")
        print("        Run --update before the next release to adopt them.")
    print()
    print("SURFACE CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
