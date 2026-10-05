#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Generate ``.augment/agents/ai-toolkit-*.md`` files for Augment Code.

Each ai-toolkit agent in ``app/agents/`` is mirrored as an Augment native
subagent. Augment's subagent frontmatter (per docs.augmentcode.com/cli/subagents)
documents: name, description, color, model, tools, disabled_tools.

    ---
    name: <slug>
    description: "<single-line description>"
    color: <color-name>       # optional UI hint
    tools: [view, save-file, ...]
    ---

    <body from agent file>

Design choices:

* ``model`` is omitted. The docs state "If not specified, the CLI default model
  is used" and do not document ``inherit`` as a value. ai-toolkit stores short
  aliases (``opus``/``sonnet``/``haiku``) that do not map to Augment's full
  model ids, so we omit the field to defer to the CLI default.
* ``tools`` maps the source permissions to documented native Augment names.
  Unsupported Claude orchestration tools are omitted with a capability note;
  unknown tools and empty native allowlists fail before writes.
  ``disabled_tools`` is never emitted because it overrides the allowlist,
  including when empty.
* Files carry both the ``ai-toolkit-`` prefix and an ownership marker. Cleanup
  also recognizes the legacy generated frontmatter shape. Unowned destinations
  and stale user-authored files are preserved.

Usage:
  python3 scripts/generate_augment_agents.py [target-dir]

Writes files to ``target-dir/.augment/agents/``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emission import agents_dir
from frontmatter import frontmatter_field
from prompt_surfaces import strip_claude_code_only
from secure_fs import apply_owned_edits, lexical_absolute

AGENT_PREFIX = "ai-toolkit-"
MANAGED_MARKER = "<!-- ai-toolkit-managed: augment-agent -->"
TOOL_MAPPING = {
    "Read": ("view",),
    "Grep": ("codebase-retrieval",),
    "Glob": ("view", "codebase-retrieval"),
    "Edit": ("str-replace-editor",),
    "Write": ("save-file",),
    "Bash": ("launch-process",),
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


def _mapped_tools(agent_file: Path) -> tuple[list[str], list[str]]:
    """Translate only granted capabilities; never widen an unknown permission."""
    mapped: list[str] = []
    unsupported: list[str] = []
    for tool in dict.fromkeys(
        item.strip() for item in frontmatter_field(agent_file, "tools").split(",") if item.strip()
    ):
        if tool in UNSUPPORTED_ORCHESTRATION:
            unsupported.append(tool)
            continue
        if tool not in TOOL_MAPPING:
            raise ValueError(f"Unknown Augment source tool in {agent_file}: {tool}")
        for native in TOOL_MAPPING[tool]:
            if native not in mapped:
                mapped.append(native)
    if not mapped:
        raise ValueError(f"Refusing empty native allowlist for Augment agent: {agent_file}")
    return mapped, unsupported


def _render_augment_agent(agent_file: Path) -> str:
    """Render a single Augment subagent .md file from an ai-toolkit agent."""
    name = frontmatter_field(agent_file, "name")
    description = frontmatter_field(agent_file, "description")
    color = frontmatter_field(agent_file, "color")
    tools, unsupported = _mapped_tools(agent_file)

    # Escape description for YAML quoted string
    safe_desc = description.replace('"', "'")

    lines: list[str] = ["---"]
    lines.append(f"name: {name}")
    lines.append(f'description: "{safe_desc}"')
    # `model` is omitted: Augment's docs say the CLI default model is used when
    # absent, and `inherit` is not a documented value. Our short aliases do not
    # map to Augment's provider-qualified ids, so we defer to the CLI default.
    if color:
        lines.append(f"color: {color}")
    tools_flow = ", ".join(tools)
    lines.append(f"tools: [{tools_flow}]")
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

    rendered: list[tuple[Path, str]] = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        name = frontmatter_field(agent_file, "name")
        description = frontmatter_field(agent_file, "description")
        if not name or not description:
            continue
        out_path = agents_out / f"{AGENT_PREFIX}{name}.md"
        rendered.append((out_path, _render_augment_agent(agent_file)))

    for directory in (target_dir, base, agents_out):
        if directory.is_symlink():
            raise RuntimeError(f"Refusing symlinked Augment agents directory: {directory}")
    agents_out.mkdir(parents=True, exist_ok=True)
    written = 0
    for out_path, content in rendered:
        if out_path.is_symlink() or (out_path.exists() and (
            not out_path.is_file() or not _is_managed_agent(out_path.read_bytes())
        )):
            print(f"Warning: preserving unowned Augment agent: {out_path}", file=sys.stderr)
            continue
        out_path.write_text(content, encoding="utf-8")
        written += 1

    removed = _cleanup_stale(agents_out, {path.name for path, _ in rendered})
    return written, removed


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
