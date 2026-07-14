"""Adapt ai-toolkit skills for Codex CLI.

Compatible skills are symlinked as-is. Skills that rely on Claude-only
delegation primitives are rendered into Codex-specific wrappers that keep the
same references/assets but rewrite the main SKILL.md guidance to use native
Codex subagents and plan tracking.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    from frontmatter import frontmatter_field
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from frontmatter import frontmatter_field


CLAUDE_ONLY_TOOLS = frozenset({
    "Agent", "TeamCreate", "TeamDelete", "SendMessage",
    "TaskCreate", "TaskList", "TaskUpdate", "TaskGet", "TaskOutput", "TaskStop",
    "Skill", "EnterPlanMode", "ExitPlanMode",
})

ADAPTED_MARKER = ".ai-toolkit-codex-adapted"

_FRONTMATTER_RE = re.compile(r"\A---\n(?P<frontmatter>.*?)\n---\n?(?P<body>.*)\Z", re.S)
_AGENT_CALL_RE = re.compile(r"\bAgent\s*\([^)]*\)", re.S)

_CODEX_NOTE = """
## Codex Translation Layer

This generated Codex variant preserves the workflow intent using durable,
client-independent guidance:

- Use Codex-native subagents to delegate independent work when parallelism
  materially improves speed or quality.
- Give each delegated task a narrow objective, relevant context, explicit file
  ownership, and a clear expected result.
- Use the subagent controls available in the current client to steer or stop
  delegated work without assuming a particular tool signature.
- Wait for delegated results only when the next critical-path step depends on
  them, then integrate the results in the parent task.
- Track progress using the planning mechanism available in the current client
  or an explicit local checklist.
- Treat a team as coordinated Codex-native subagents with non-overlapping work.
"""

_SEMANTIC_REPLACEMENTS = {
    "$ARGUMENTS": "the task details supplied by the user",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "Codex subagent support",
    "spawn_agent": "delegate independent work to a Codex-native subagent",
    "send_input": "steer a running subagent",
    "wait_agent": "wait for delegated results",
    "close_agent": "stop or finish delegated work",
    "update_plan": "the planning mechanism available in the current client",
    "TeamCreate": "coordinate Codex-native subagents",
    "TeamDelete": "finish coordinated subagent work",
    "SendMessage": "steer a running subagent",
    "TaskCreate": "the available planning mechanism",
    "TaskList": "the available planning mechanism",
    "TaskUpdate": "the available planning mechanism",
    "TaskGet": "review delegated progress",
    "TaskOutput": "collect delegated results",
    "TaskStop": "stop delegated work",
}


def skill_tools(skill_file: Path) -> list[str]:
    """Return ordered allowed-tools entries from a skill frontmatter block."""
    tools_str = frontmatter_field(skill_file, "allowed-tools") or ""
    return [tool.strip() for tool in tools_str.split(",") if tool.strip()]


def is_codex_adapted_skill(skill_file: Path) -> bool:
    """Return True if a skill needs Claude→Codex delegation adaptation."""
    return bool(set(skill_tools(skill_file)) & CLAUDE_ONLY_TOOLS)


def codex_skill_description(skill_file: Path) -> str:
    """Return the skill description shown in Codex-facing generators."""
    description = frontmatter_field(skill_file, "description")
    if not description:
        return ""
    if is_codex_adapted_skill(skill_file):
        return (
            f"{description} Codex-adapted: uses Codex-native subagents and "
            "current-client planning controls."
        )
    return description


def build_codex_skill_text(skill_file: Path) -> str:
    """Render the Codex-facing SKILL.md contents for a source skill."""
    text = skill_file.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return text

    body = match.group("body")
    adapted = is_codex_adapted_skill(skill_file)

    if adapted:
        body = _adapt_body(body)
        name = frontmatter_field(skill_file, "name")
        description = codex_skill_description(skill_file)
        rendered_frontmatter = "\n".join(
            (f"name: {name}", f"description: {json.dumps(description, ensure_ascii=False)}")
        )
    else:
        frontmatter = _parse_frontmatter(match.group("frontmatter"))
        rendered_frontmatter = _render_frontmatter(frontmatter)

    return f"---\n{rendered_frontmatter}\n---\n{body.rstrip()}\n"


def sync_codex_skill(skill_dir: Path, skills_dst: Path) -> str:
    """Install one skill into `.agents/skills/` and return its mode."""
    skill_file = skill_dir / "SKILL.md"
    adapted = is_codex_adapted_skill(skill_file)

    if adapted:
        return _sync_adapted_skill(skill_dir, skills_dst)
    return _sync_native_skill(skill_dir, skills_dst)


def prepare_codex_skills_dir(target_dir: Path) -> Path:
    """Create the documented Codex skill root without following symlinks."""
    agents_dir = target_dir / ".agents"
    skills_dst = agents_dir / "skills"
    _assert_safe_skill_roots(agents_dir, skills_dst)
    skills_dst.mkdir(parents=True, exist_ok=True)
    _assert_safe_skill_roots(agents_dir, skills_dst)
    return skills_dst


def unmanaged_codex_skill_names(skills_dst: Path, skills_src: Path) -> set[str]:
    """Return logical names declared by user-owned destination entries."""
    names: set[str] = set()
    for item in sorted(skills_dst.iterdir()):
        if _is_managed_entry(item, skills_src):
            continue
        skill_file = item / "SKILL.md"
        try:
            name = frontmatter_field(skill_file, "name")
        except (OSError, UnicodeError):
            continue
        if name:
            names.add(name)
    return names


def cleanup_codex_skills(
    skills_dst: Path,
    skills_src: Path,
    blocked_names: set[str] | None = None,
) -> None:
    """Remove stale or shadowed toolkit-managed entries without touching user data."""
    _assert_safe_skill_roots(skills_dst.parent, skills_dst)
    skills_src_resolved = skills_src.resolve()
    blocked_names = blocked_names or set()
    for item in skills_dst.iterdir():
        src = skills_src / item.name
        if item.name in blocked_names and _is_managed_entry(item, skills_src):
            if item.is_symlink():
                item.unlink()
            else:
                _remove_managed_wrapper(item, skills_src_resolved)
            continue
        if item.is_symlink():
            target = _symlink_target(item)
            if src.is_dir() and target == src.resolve():
                continue
            if _is_relative_to(target, skills_src_resolved):
                item.unlink()
                continue
        if _is_adapted_wrapper(item) and not src.is_dir():
            _remove_managed_wrapper(item, skills_src_resolved)


def _assert_safe_skill_roots(agents_dir: Path, skills_dst: Path) -> None:
    if agents_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked Codex agents directory: {agents_dir}")
    if skills_dst.is_symlink():
        raise RuntimeError(f"Refusing symlinked Codex skills directory: {skills_dst}")


def _symlink_target(path: Path) -> Path:
    raw_target = Path(os.readlink(path))
    if not raw_target.is_absolute():
        raw_target = path.parent / raw_target
    return raw_target.resolve(strict=False)


def _points_to(path: Path, target: Path) -> bool:
    return path.is_symlink() and _symlink_target(path) == target.resolve()


def _is_adapted_wrapper(path: Path) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    marker = path / ADAPTED_MARKER
    return not marker.is_symlink() and marker.is_file()


def _is_managed_entry(path: Path, skills_src: Path) -> bool:
    if _is_adapted_wrapper(path):
        return True
    if not path.is_symlink():
        return False
    return _is_relative_to(_symlink_target(path), skills_src.resolve())


def _sync_native_skill(skill_dir: Path, skills_dst: Path) -> str:
    target = skills_dst / skill_dir.name
    if target.is_symlink():
        return "linked" if _points_to(target, skill_dir) else "skipped"
    if _is_adapted_wrapper(target):
        if not _remove_managed_wrapper(target, skill_dir.parent.resolve()):
            return "skipped"
    elif target.exists():
        return "skipped"
    target.symlink_to(skill_dir)
    return "linked"


def _sync_adapted_skill(skill_dir: Path, skills_dst: Path) -> str:
    target = skills_dst / skill_dir.name
    if target.is_symlink():
        if not _points_to(target, skill_dir):
            return "skipped"
        target.unlink()
    elif target.exists() and not _is_adapted_wrapper(target):
        return "skipped"

    created = not target.exists()
    target.mkdir(parents=False, exist_ok=True)
    skill_output = target / "SKILL.md"
    marker = target / ADAPTED_MARKER
    if skill_output.is_symlink() or marker.is_symlink():
        return "skipped"
    try:
        _atomic_write_wrapper(
            target,
            {
                skill_output: build_codex_skill_text(skill_dir / "SKILL.md"),
                marker: "generated by ai-toolkit for Codex\n",
            },
        )
    except Exception:
        if created:
            try:
                target.rmdir()
            except OSError:
                pass
        raise
    _sync_auxiliaries(skill_dir, target)
    return "adapted"


def _stage_text(destination: Path, content: str) -> Path:
    fd, temp_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        handle = os.fdopen(fd, "w", encoding="utf-8")
        fd = -1
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return temp_path
    except Exception:
        if fd >= 0:
            os.close(fd)
        temp_path.unlink(missing_ok=True)
        raise


def _atomic_write_wrapper(target: Path, files: dict[Path, str]) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for destination, content in files.items():
            staged.append((_stage_text(destination, content), destination))
        for temp_path, destination in staged:
            if destination.is_symlink():
                raise RuntimeError(f"Refusing symlinked Codex skill file: {destination}")
            os.replace(temp_path, destination)
    finally:
        for temp_path, _ in staged:
            temp_path.unlink(missing_ok=True)


def _sync_auxiliaries(skill_dir: Path, target: Path) -> None:
    expected = {child.name for child in skill_dir.iterdir() if child.name != "SKILL.md"}
    for child in sorted(skill_dir.iterdir()):
        if child.name == "SKILL.md":
            continue
        destination = target / child.name
        if destination.is_symlink():
            if _points_to(destination, child):
                continue
            continue
        if destination.exists():
            continue
        destination.symlink_to(child)

    source_root = skill_dir.resolve()
    for destination in target.iterdir():
        if destination.name in expected | {"SKILL.md", ADAPTED_MARKER}:
            continue
        if destination.is_symlink() and _is_relative_to(
            _symlink_target(destination), source_root
        ):
            destination.unlink()


def _remove_managed_wrapper(path: Path, skills_src_resolved: Path) -> bool:
    if not _is_adapted_wrapper(path):
        return False
    children = list(path.iterdir())
    for child in children:
        if child.name in {"SKILL.md", ADAPTED_MARKER}:
            if child.is_symlink() or not child.is_file():
                return False
            continue
        if not child.is_symlink():
            return False
        if not _is_relative_to(_symlink_target(child), skills_src_resolved):
            return False
    for child in children:
        child.unlink()
    path.rmdir()
    return True


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _parse_frontmatter(frontmatter_text: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line in frontmatter_text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        entries.append((key.strip(), value.strip()))
    return entries


def _render_frontmatter(entries: list[tuple[str, str]]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in entries)


def _adapt_body(body: str) -> str:
    body = _AGENT_CALL_RE.sub(
        "Delegate this independent work to a suitable Codex-native subagent.",
        body,
    )
    body = body.replace("Agent Teams", "coordinated Codex-native subagents")
    body = body.replace("`Agent` tool", "Codex-native subagents")
    body = body.replace("the `Agent` tool", "Codex-native subagents")
    body = body.replace("Agent tool", "Codex-native subagents")
    for token, replacement in _SEMANTIC_REPLACEMENTS.items():
        body = body.replace(token, replacement)
    return f"{_CODEX_NOTE.strip()}\n\n{body.strip()}\n"
