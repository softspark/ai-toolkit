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
_TASK_API_RE = re.compile(r"\bTask(?:Create|List|Update|Get|Output|Stop)\b")
_PLATFORM_LABELS = {"codex": "Codex", "opencode": "OpenCode"}
_ADAPTATION_BODY_TOKENS = frozenset({
    "$ARGUMENTS",
    "CLAUDE_SKILL_DIR",
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
    "spawn_agent",
    "send_input",
    "wait_agent",
    "close_agent",
    "update_plan",
    "fork_context",
    "agent_type=",
    "TeamCreate",
    "TeamDelete",
    "SendMessage",
})


def _translation_note(platform: str) -> str:
    label = _PLATFORM_LABELS[platform]
    return f"""
## {label} Translation Layer

This generated {label} variant preserves the workflow intent using durable,
client-independent guidance:

- Use {label}-native subagents to delegate independent work when parallelism
  materially improves speed or quality.
- Give each delegated task a narrow objective, relevant context, explicit file
  ownership, and a clear expected result.
- Use the subagent controls available in the current client to steer or stop
  delegated work without assuming a particular tool signature.
- Wait for delegated results only when the next critical-path step depends on
  them, then integrate the results in the parent task.
- Track progress using the planning mechanism available in the current client
  or an explicit local checklist.
- Treat a team as coordinated {label}-native subagents with non-overlapping work.
- Resolve `./` paths in command examples from the installed skill directory
  that contains this `SKILL.md` file.
"""


def _semantic_replacements(platform: str) -> dict[str, str]:
    label = _PLATFORM_LABELS[platform]
    native_subagent = f"{label}-native subagent"
    return {
        "${CLAUDE_SKILL_DIR}/": "./",
        "$CLAUDE_SKILL_DIR/": "./",
        "${CLAUDE_SKILL_DIR}": "the installed skill directory",
        "CLAUDE_SKILL_DIR": "the installed skill directory",
        "$ARGUMENTS": "the user-supplied task details",
        "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": f"{label} subagent support",
        "spawn_agent": f"delegate independent work to a {native_subagent}",
        "send_input": "steer a running subagent",
        "wait_agent": "wait for delegated results",
        "close_agent": "stop or finish delegated work",
        "update_plan": "the planning mechanism available in the current client",
        "fork_context": "appropriate inherited task context",
        "agent_type=": "a suitable subagent role",
        "TeamCreate": f"coordinate {label}-native subagents",
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
    """Return True when a source skill needs portable client adaptation."""
    if set(skill_tools(skill_file)) & CLAUDE_ONLY_TOOLS:
        return True
    text = skill_file.read_text(encoding="utf-8")
    if any(token in text for token in _ADAPTATION_BODY_TOKENS):
        return True
    return bool(_AGENT_CALL_RE.search(text) or _TASK_API_RE.search(text))


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
    return _build_portable_skill_text(skill_file, "codex")


def build_opencode_skill_text(skill_file: Path) -> str:
    """Render an OpenCode-facing skill without leaking Codex branding."""
    return _build_portable_skill_text(skill_file, "opencode")


def _build_portable_skill_text(skill_file: Path, platform: str) -> str:
    """Render a client-specific skill using semantic, signature-free guidance."""
    if platform not in _PLATFORM_LABELS:
        raise ValueError(f"Unsupported skill adaptation platform: {platform}")
    text = skill_file.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return _adapt_body(text, platform) if is_codex_adapted_skill(skill_file) else text

    body = match.group("body")
    adapted = is_codex_adapted_skill(skill_file)

    if adapted:
        body = _adapt_body(body, platform)
        name = frontmatter_field(skill_file, "name")
        description = (
            codex_skill_description(skill_file)
            if platform == "codex"
            else frontmatter_field(skill_file, "description")
        )
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
        return _create_adapted_wrapper(skill_dir, target, replace_managed_link=True)
    if target.exists() and not _is_adapted_wrapper(target):
        return "skipped"
    if not target.exists():
        return _create_adapted_wrapper(skill_dir, target)

    return _update_adapted_wrapper(skill_dir, target)


def _create_adapted_wrapper(
    skill_dir: Path,
    target: Path,
    *,
    replace_managed_link: bool = False,
) -> str:
    """Build a complete sibling wrapper and expose it with one atomic rename."""
    staging = Path(tempfile.mkdtemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
    ))
    removed_link = False
    try:
        _write_text_fsync(
            staging / "SKILL.md",
            build_codex_skill_text(skill_dir / "SKILL.md"),
        )
        _write_text_fsync(
            staging / ADAPTED_MARKER,
            "generated by ai-toolkit for Codex\n",
        )
        _sync_auxiliaries(skill_dir, staging)
        _fsync_directory(staging)

        if replace_managed_link:
            if not _points_to(target, skill_dir):
                raise RuntimeError(f"Codex skill target changed during sync: {target}")
            target.unlink()
            removed_link = True
        elif target.exists() or target.is_symlink():
            raise RuntimeError(f"Codex skill target appeared during sync: {target}")

        os.replace(staging, target)
        _fsync_directory(target.parent)
        return "adapted"
    except Exception:
        _remove_staged_wrapper(staging)
        if removed_link and not target.exists() and not target.is_symlink():
            target.symlink_to(skill_dir)
        raise


def _update_adapted_wrapper(skill_dir: Path, target: Path) -> str:
    """Atomically refresh SKILL.md while leaving the managed marker stable."""
    skill_output = target / "SKILL.md"
    marker = target / ADAPTED_MARKER
    if skill_output.is_symlink() or marker.is_symlink():
        return "skipped"
    temp_path = _stage_text(
        skill_output,
        build_codex_skill_text(skill_dir / "SKILL.md"),
    )
    try:
        os.replace(temp_path, skill_output)
        _fsync_directory(target)
    finally:
        temp_path.unlink(missing_ok=True)
    _sync_auxiliaries(skill_dir, target)
    return "adapted"


def _write_text_fsync(destination: Path, content: str) -> None:
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_staged_wrapper(staging: Path) -> None:
    if staging.is_symlink() or not staging.is_dir():
        return
    for child in staging.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()
    try:
        staging.rmdir()
    except OSError:
        pass


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


def _adapt_body(body: str, platform: str) -> str:
    label = _PLATFORM_LABELS[platform]
    body = _AGENT_CALL_RE.sub(
        f"Delegate this independent work to a suitable {label}-native subagent.",
        body,
    )
    body = body.replace("Agent Teams", f"coordinated {label}-native subagents")
    body = body.replace("`Agent` tool", f"{label}-native subagents")
    body = body.replace("the `Agent` tool", f"{label}-native subagents")
    body = body.replace("Agent tool", f"{label}-native subagents")
    for token, replacement in _semantic_replacements(platform).items():
        body = body.replace(token, replacement)
    return f"{_translation_note(platform).strip()}\n\n{body.strip()}\n"
