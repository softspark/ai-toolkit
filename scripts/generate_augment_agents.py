#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate ``.augment/agents/ai-toolkit-*.md`` files for Augment Code.

Each ai-toolkit agent in ``app/agents/`` is mirrored as an Augment native
subagent. Auggie 1.x and 0.x read the same files but use different tool names.
See https://docs.augmentcode.com/cli/subagents and its versioned 0.x reference.

    ---
    name: <slug>
    description: "<single-line description>"
    color: <color-name>       # optional UI hint
    tools: [read, grep, find]
    extensions: false        # 1.x only: keep permissions within the allowlist
    ---

    <body from agent file>

Design choices:

* Omit ``model`` and ``thinking``. In 1.x the subagent uses the current
  model. In 0.x it uses the CLI default.
* ``tools`` maps the source permissions to documented native Augment names.
  Unsupported Claude orchestration tools are omitted with a capability note;
  unknown tools and empty native allowlists fail before writes.
  The generated allowlist is the complete set of granted tools.
* Files carry both the ``ai-toolkit-`` prefix and an ownership marker. Cleanup
  also recognizes the legacy generated frontmatter shape. Unowned destinations
  and stale user-authored files are preserved.

Usage:
  python3 scripts/generate_augment_agents.py [target-dir]

Writes files to ``target-dir/.augment/agents/``.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import agents_dir
from doctor import _probe_version
from frontmatter import frontmatter_field
from mcp_editors import ConfigUpdate, apply_config_updates
from prompt_surfaces import strip_claude_code_only
from secure_fs import apply_owned_edits, lexical_absolute

AGENT_PREFIX = "ai-toolkit-"
MANAGED_MARKER = "<!-- ai-toolkit-managed: augment-agent -->"
V0_TOOLS = {
    "Read": ("view",),
    "Grep": ("codebase-retrieval",),
    "Glob": ("view", "codebase-retrieval"),
    "Edit": ("str-replace-editor",),
    "Write": ("save-file",),
    "Bash": ("launch-process",),
}
V1_TOOLS = {
    "Read": ("read",),
    "Grep": ("grep",),
    "Glob": ("find",),
    "Edit": ("edit",),
    "Write": ("write",),
    "Bash": ("bash",),
}
UNSUPPORTED_ORCHESTRATION = frozenset({
    "Agent", "TeamCreate", "TeamDelete", "SendMessage",
    "TaskCreate", "TaskList", "TaskUpdate",
})


def _agent_body(agent_file: Path) -> str:
    """Return the markdown body of an agent file (content after frontmatter)."""
    text = agent_file.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return text.strip() + "\n"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text.strip() + "\n"
    return parts[2].lstrip("\n")


def _mapped_tools(agent_file: Path, mapping: dict[str, tuple[str, ...]]) -> tuple[list[str], list[str]]:
    """Translate only granted capabilities; never widen an unknown permission."""
    mapped: list[str] = []
    unsupported: list[str] = []
    for tool in dict.fromkeys(
        item.strip() for item in frontmatter_field(agent_file, "tools").split(",") if item.strip()
    ):
        if tool in UNSUPPORTED_ORCHESTRATION:
            unsupported.append(tool)
            continue
        if tool not in mapping:
            raise ValueError(f"Unknown Augment source tool in {agent_file}: {tool}")
        for native in mapping[tool]:
            if native not in mapped:
                mapped.append(native)
    if not mapped:
        raise ValueError(f"Refusing empty native allowlist for Augment agent: {agent_file}")
    return mapped, unsupported


def _render_augment_agent(agent_file: Path, major: int = 1) -> str:
    """Render a single Augment subagent .md file from an ai-toolkit agent."""
    name = frontmatter_field(agent_file, "name")
    description = frontmatter_field(agent_file, "description")
    color = frontmatter_field(agent_file, "color")
    tools, unsupported = _mapped_tools(agent_file, V0_TOOLS if major == 0 else V1_TOOLS)

    # Escape description for YAML quoted string
    safe_desc = description.replace('"', "'")

    lines: list[str] = ["---"]
    lines.append(f"name: {name}")
    lines.append(f'description: "{safe_desc}"')
    if color:
        if major == 1:
            color = {"teal": "cyan", "magenta": "purple"}.get(color, color)
        lines.append(f"color: {color}")
    tools_flow = ", ".join(tools)
    lines.append(f"tools: [{tools_flow}]")
    if major == 1:
        lines.append("extensions: false")
    lines.append("---")
    lines.append("")
    lines.extend([MANAGED_MARKER, ""])
    if unsupported:
        lines.extend([
            "Augment capability note: the following Claude orchestration tools are "
            f"unavailable in this exported agent: {', '.join(unsupported)}. "
            "Do not simulate these tools or claim delegation occurred. Ignore source "
            "instructions that require them; use the native allowlist and report "
            "delegation-dependent work to the caller.",
            "",
        ])
    body = strip_claude_code_only(_agent_body(agent_file)).rstrip()
    if body:
        lines.append(body)
    lines.append("")
    return "\n".join(lines)


def _cleanup_stale(agents_out: Path, expected: set[str]) -> int:
    """Remove stale ai-toolkit-* agent files whose source no longer exists.

    Both an owned shape and the ``ai-toolkit-`` prefix are required.
    """
    if not agents_out.is_dir():
        return 0
    removed = 0
    for f in sorted(agents_out.glob(f"{AGENT_PREFIX}*.md")):
        if f.name in expected or f.is_symlink() or not f.is_file():
            continue
        if _is_managed_agent(f.read_bytes()):
            f.unlink()
            removed += 1
    return removed


def _target_major(agents_out: Path) -> int:
    """Use the installed client, preserving an existing generation when it is absent."""
    executable = shutil.which("auggie")
    if executable:
        probe = _probe_version(executable)
        if probe.version:
            major = int(probe.version.split(".")[0])
            if major in (0, 1):
                return major
        raise RuntimeError(f"Unsupported Auggie version: {probe.version or probe.error}")

    for path in sorted(agents_out.glob(f"{AGENT_PREFIX}*.md")):
        source = agents_dir / f"{path.stem.removeprefix(AGENT_PREFIX)}.md"
        if not source.is_file() or path.is_symlink() or not path.is_file():
            continue
        content = path.read_bytes()
        if _is_managed_agent(content):
            header = content.partition(b"\n---\n")[0]
            return 1 if b"\nextensions: false" in header else 0
    return 1


def generate(
    target_dir: Path, config_root: Path | None = None
) -> tuple[int, int]:
    """Write Augment agent files and return (written, removed_stale).

    By default writes to ``target_dir/.augment/agents/`` (project-local).
    Pass ``config_root=~/.augment`` for the global layout, which writes
    directly under ``agents/`` without the ``.augment/`` prefix.
    """
    base = config_root if config_root is not None else target_dir / ".augment"
    agents_out = base / "agents"
    for directory in (target_dir, base, agents_out):
        if directory.is_symlink():
            raise RuntimeError(f"Refusing symlinked Augment agents directory: {directory}")
    major = _target_major(agents_out)

    updates = []
    expected: set[str] = set()
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or f"{AGENT_PREFIX}{name}.md" in expected:
            raise ValueError(f"Invalid or duplicate Augment agent name: {name!r}")
        out_path = agents_out / f"{AGENT_PREFIX}{name}.md"
        expected.add(out_path.name)
        rendered = _render_augment_agent(agent_file, major).encode("utf-8")
        if out_path.is_symlink() or (out_path.exists() and not out_path.is_file()):
            print(f"Warning: preserving unowned Augment agent: {out_path}", file=sys.stderr)
            continue
        original = out_path.read_bytes() if out_path.exists() else None
        if original is not None and not _is_managed_agent(original):
            print(f"Warning: preserving unowned Augment agent: {out_path}", file=sys.stderr)
            continue
        updates.append(ConfigUpdate(out_path, original, rendered))

    apply_config_updates(updates)
    return len(updates), _cleanup_stale(agents_out, expected)


def _is_managed_agent(content: bytes) -> bool:
    """Recognize current ownership markers and the previous generated shape."""
    if not content.startswith(b"---\nname: "):
        return False
    header, separator, body = content.partition(b"\n---\n")
    marked = bool(separator) and body.lstrip(b"\n").startswith(MANAGED_MARKER.encode() + b"\n")
    legacy = bool(separator) and re.fullmatch(
        rb'---\nname: [^\n]+\ndescription: "[^"\n]*"\n'
        rb'(?:color: [^\n]+\n)?tools: \[[^\n]*\]\ndisabled_tools: \[\]',
        header,
    ) is not None
    return marked or legacy


def _owned_agent_edit(content: bytes) -> bytes | None:
    return None if _is_managed_agent(content) else content


def _apply(target_dir: Path, config_root: Path | None, *, dry_run: bool) -> int:
    target = lexical_absolute(target_dir)
    if target.is_symlink() or not target.is_dir():
        raise RuntimeError(f"Unsafe Augment target directory: {target}")
    base = lexical_absolute(config_root) if config_root is not None else target / ".augment"
    agents_out = base / "agents"
    for directory in (base, agents_out):
        if directory.is_symlink():
            raise RuntimeError(f"Refusing symlinked Augment agents directory: {directory}")
    files = sorted(
        path for path in agents_out.glob(f"{AGENT_PREFIX}*.md")
        if path.is_file() and not path.is_symlink()
    ) if agents_out.is_dir() else []
    return apply_owned_edits(
        {path: _owned_agent_edit for path in files},
        target,
        label="Augment agent",
        prune=(agents_out, base) if base != target else (agents_out,),
        dry_run=dry_run,
    )


def discover(target_dir: Path, *, config_root: Path | None = None) -> int:
    """Count managed ``ai-toolkit-*.md`` agents ``cleanup`` would remove."""
    return _apply(target_dir, config_root, dry_run=True)


def cleanup(target_dir: Path, *, config_root: Path | None = None) -> int:
    """Remove every managed Augment agent; user agents are preserved."""
    return _apply(target_dir, config_root, dry_run=False)


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    written, removed = generate(target)
    msg = f"Generated: .augment/agents/ ({written} agents"
    if removed:
        msg += f", {removed} stale removed"
    msg += ")"
    print(msg)


if __name__ == "__main__":
    main()
