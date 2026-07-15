#!/usr/bin/env python3
"""Generate GitHub Copilot customization files.

This generator produces five repository customization surfaces without
subscription-tier gating or server-side MCP configuration:

1. ``.github/copilot-instructions.md`` — always-on repository instructions.
   Supported by GitHub.com Copilot Chat, Copilot cloud agent, and VS Code
   Copilot. Generated to stdout by default (backwards compatible).

2. ``.github/instructions/*.instructions.md`` — path-specific instructions.
   Each file has ``applyTo`` frontmatter with a glob pattern. Supported
   by VS Code Copilot and Copilot cloud agent / code review on GitHub.com.
   Written only when ``generate()`` is called with a target directory.

3. ``.github/prompts/*.prompt.md`` — prompt files (slash commands).
   Invoked manually in VS Code Copilot Chat via ``/name``. Written only
   when ``generate()`` is called with a target directory.

4. ``.github/agents/*.agent.md`` — native Copilot custom agents generated
   from ``app/agents``. User-level generation writes the same managed agents
   to ``~/.copilot/agents``.

5. ``.github/skills/*/SKILL.md`` — portable, materialized Copilot skills with
   their referenced scripts and assets. User-level generation writes them to
   the active Copilot configuration root's ``skills/`` directory.

GitHub Copilot code review (generally available 2026-06-18, all tiers) now
automatically reads the root-level ``AGENTS.md`` when generating review
feedback. We already emit that file via ``scripts/generate_agents_md.py``, so
no Copilot-specific emission is added here; ``AGENTS.md`` is tracked in this
tool's ``capability_markers`` in ``scripts/ecosystem_tools.json``.

Copilot hooks are emitted by ``generate_copilot_hooks.py`` because their
transactional JSON/runtime lifecycle is separate from Markdown customization.
Project MCP remains handled by the editor MCP sync path.

Usage:
  # Legacy stdout mode (repo-wide instructions only)
  python3 scripts/generate_copilot.py > .github/copilot-instructions.md

  # Directory mode (path-specific instructions + agents + prompt files)
  python3 scripts/generate_copilot.py <target-dir>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dir_rules_shared import (
    LANG_GLOBS,
    PREFIX,
    build_language_rules,
    build_registered_rules,
    rule_code_style,
    rule_quality_standards,
    rule_security,
    rule_testing,
    rule_workflow,
)
from emission import (
    agents_dir,
    skills_dir,
)
from frontmatter import frontmatter_field
from generator_base import render_generator


MANAGED_MARKER = "<!-- ai-toolkit-managed: github-copilot -->"
SKILL_MANIFEST = ".ai-toolkit-managed-files"
MAX_AGENT_BODY_BYTES = 30_000
_AGENT_START_RE = re.compile(r"\bAgent\s*\(")
_TASK_CALL_RE = re.compile(
    r"\bTask(?:Create|List|Update|Get|Output|Stop)\s*\([^)]*\)",
    re.S,
)
_SAFE_NAME_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_FORBIDDEN_COPILOT_BODY_RE = re.compile(
    r"\$ARGUMENTS|CLAUDE_SKILL_DIR|CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS|"
    r"\bAgent\s*\(|\bTask(?:Create|List|Update|Get|Output|Stop)\b|"
    r"\b(?:TeamCreate|TeamDelete|SendMessage)\b|"
    r"\b(?:spawn_agent|send_input|wait_agent|close_agent|update_plan|fork_context)\b|"
    r"\bview_skill\s*\(|\b(?:subagent_type|agent_type)\s*="
)

# ---------------------------------------------------------------------------
# Shared configuration for the legacy stdout output
# ---------------------------------------------------------------------------

_STDOUT_CONFIG: dict = {
    "title": "# GitHub Copilot Instructions",
    "intro_template": (
        "This repository uses the ai-toolkit — a shared AI development toolkit"
        " with specialized agent personas and skills."
    ),
    "agents_section": "## Available Agent Personas",
    "agents_intro": "Apply the expertise of these agents when working on relevant tasks:",
    "agents_format": "headings",
    "agents_level": "###",
    "skills_section": "## Available Skills",
    "skills_intro": "The following skills are available as slash commands or knowledge sources:",
    "skills_format": "headings",
    "skills_level": "###",
    "guidelines": ["quality_standards"],
}


# ---------------------------------------------------------------------------
# Path-specific .instructions.md emission
# ---------------------------------------------------------------------------

def _instructions_file(content: str, *, apply_to: str,
                       description: str = "") -> str:
    """Wrap markdown content with Copilot ``.instructions.md`` frontmatter."""
    lines = ["---"]
    lines.append(f"applyTo: {json.dumps(apply_to, ensure_ascii=False)}")
    if description:
        lines.append(f"description: {json.dumps(description, ensure_ascii=False)}")
    lines.append("---")
    lines.append("")
    lines.append(MANAGED_MARKER)
    lines.append("")
    lines.append(content.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _make_instruction_files() -> dict[str, callable]:
    """Build the ``.instructions.md`` file registry.

    Filenames use the standard ai-toolkit prefix so they can be cleaned up
    on re-run without touching user files.
    """
    return {
        # Always applies (repo-wide)
        f"{PREFIX}security.instructions.md": lambda: _instructions_file(
            rule_security(),
            apply_to="**",
            description="Security rules — OWASP, secrets, input validation",
        ),
        f"{PREFIX}quality-standards.instructions.md": lambda: _instructions_file(
            rule_quality_standards(),
            apply_to="**",
            description="Quality standards — tests, safety, operational integrity",
        ),
        f"{PREFIX}workflow.instructions.md": lambda: _instructions_file(
            rule_workflow(),
            apply_to="**",
            description="Development workflow — planning, commits, quality gates",
        ),
        f"{PREFIX}code-style.instructions.md": lambda: _instructions_file(
            rule_code_style(),
            apply_to="**",
            description="Code style conventions for all languages",
        ),
        # Scoped to test files only
        f"{PREFIX}testing.instructions.md": lambda: _instructions_file(
            rule_testing(),
            apply_to="**/*.test.*,**/*.spec.*,**/test_*,**/tests/**",
            description="Testing standards and patterns",
        ),
    }


# ---------------------------------------------------------------------------
# Prompt-file emission (.github/prompts/*.prompt.md)
# ---------------------------------------------------------------------------

def _prompt_file(description: str, body: str) -> str:
    """Wrap a skill body with Copilot ``.prompt.md`` frontmatter."""
    lines = ["---"]
    lines.append(f"description: {json.dumps(description, ensure_ascii=False)}")
    lines.append("---")
    lines.append("")
    lines.append(MANAGED_MARKER)
    lines.append("")
    lines.append(body.rstrip("\n"))
    lines.append("")
    return "\n".join(lines)


def _legacy_prompt_file(description: str, body: str) -> str:
    """Render the pre-native prompt format for safe in-place migration."""
    return "\n".join([
        "---",
        f"description: {description}",
        "---",
        "",
        body.rstrip("\n"),
        "",
    ])


def _read_markdown_body(markdown_file: Path) -> str:
    """Read the body after the first frontmatter block without losing rules."""
    text = markdown_file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return text.rstrip()
    for index, line in enumerate(lines[1:], start=1):
        if line.rstrip("\r\n") == "---":
            return "".join(lines[index + 1:]).lstrip("\r\n").rstrip()
    return text.rstrip()


def _read_legacy_prompt_body(skill_file: Path) -> str:
    """Reproduce the previous prompt-body parser for exact migration only."""
    lines: list[str] = []
    fence_count = 0
    for line in skill_file.read_text(encoding="utf-8").splitlines():
        if line == "---":
            fence_count += 1
            continue
        if fence_count >= 2:
            lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _portable_copilot_body(body: str, *, include_execution_note: bool) -> str:
    """Remove Claude-only interpolation and delegation APIs from markdown."""
    body = _replace_agent_calls(body)
    body = _TASK_CALL_RE.sub(
        "Update or inspect progress using Copilot's current planning controls.",
        body,
    )
    body = _replace_dynamic_context(body)
    literal_replacements = {
        "${CLAUDE_SKILL_DIR}/": "./",
        "$CLAUDE_SKILL_DIR/": "./",
        "${CLAUDE_SKILL_DIR}": "the installed ai-toolkit skill directory",
        "CLAUDE_SKILL_DIR": "the installed ai-toolkit skill directory",
        "$ARGUMENTS": "the user-supplied task details",
        "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "Copilot custom-agent support",
        "Agent Teams": "Copilot custom agents",
        "native Agent Tool": "native custom-agent delegation",
        "Native Agent Tool": "Copilot custom-agent delegation",
        "`Agent` tool": "Copilot custom agents",
        "the Agent tool": "Copilot custom agents",
        "via Agent tool": "with Copilot custom-agent delegation",
        "Agent tool": "Copilot custom-agent delegation",
        ".claude/agents/": ".github/agents/",
        "~/.claude/tasks/": "Copilot's current task list",
        "## 🚀 Native Copilot custom agents Integration": (
            "## Copilot custom-agent integration"
        ),
        "Copilot custom agents is enabled (`Copilot custom-agent support=1`)": (
            "Copilot custom-agent delegation is available"
        ),
    }
    for token, replacement in literal_replacements.items():
        body = body.replace(token, replacement)
    api_replacements = {
        "TeamCreate": "coordinate Copilot custom agents",
        "TeamDelete": "finish coordinated custom-agent work",
        "SendMessage": "steer a running custom agent",
        "TaskCreate": "the planning controls available in Copilot",
        "TaskList": "the planning controls available in Copilot",
        "TaskUpdate": "the planning controls available in Copilot",
        "TaskGet": "review delegated progress",
        "TaskOutput": "collect delegated results",
        "TaskStop": "stop delegated work",
        "spawn_agent": "delegate work to a Copilot custom agent",
        "send_input": "steer a running custom agent",
        "wait_agent": "wait for delegated results",
        "close_agent": "stop delegated work",
        "update_plan": "the planning controls available in Copilot",
        "fork_context": "appropriate inherited task context",
    }
    for token, replacement in api_replacements.items():
        body = re.sub(rf"\b{token}\b", replacement, body)
    body = re.sub(
        r"\bagent_type\s*=",
        "a suitable custom-agent role",
        body,
    )
    body = re.sub(
        r"\bview_skill\(\s*['\"]([^'\"]+)['\"]\s*\)",
        lambda match: f"Load the `{match.group(1)}` skill if it is available",
        body,
    )
    body = re.sub(
        r"\bUse (?:Opus|Sonnet|Haiku)(?:\s+[0-9.]+)?\b",
        "Use the model selected by the current Copilot client",
        body,
    )
    body = body.replace(
        ".github/agents/{name}.md",
        ".github/agents/ai-toolkit-{name}.agent.md",
    )
    body = re.sub(
        r"Hooks in `\.claude/hooks\.json` auto-enforce quality:\n"
        r"(?:- .*\n){1,4}",
        "Run repository quality gates explicitly before accepting delegated "
        "work; do not assume Claude hook configuration applies to Copilot.\n",
        body,
    )

    body = body.strip()
    forbidden = _FORBIDDEN_COPILOT_BODY_RE.search(body)
    if forbidden:
        raise ValueError(f"Unsupported Copilot body token: {forbidden.group(0)}")
    if not include_execution_note:
        return body + "\n"
    note = """## GitHub Copilot execution notes

- Treat the current user request as the task input for this prompt.
- Resolve `./` script paths from the installed ai-toolkit skill directory that
  corresponds to this prompt, not from the repository root.
- Use Copilot's current custom-agent and planning controls without assuming a
  particular internal tool signature."""
    return f"{note}\n\n{body}\n"


def _replace_dynamic_context(body: str) -> str:
    """Remove Claude's ``!`command``` prefix outside Markdown code spans."""
    rendered: list[str] = []
    in_fence = False
    for line in body.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            rendered.append(line)
            continue
        if in_fence:
            rendered.append(line)
            continue

        output: list[str] = []
        index = 0
        inline_delimiter = 0
        while index < len(line):
            if line[index] == "`":
                run_end = index
                while run_end < len(line) and line[run_end] == "`":
                    run_end += 1
                run_length = run_end - index
                if inline_delimiter == 0:
                    inline_delimiter = run_length
                elif inline_delimiter == run_length:
                    inline_delimiter = 0
                output.append(line[index:run_end])
                index = run_end
                continue
            if inline_delimiter == 0 and line.startswith("!`", index):
                closing = line.find("`", index + 2)
                if closing != -1:
                    output.append(f"`{line[index + 2:closing]}`")
                    index = closing + 1
                    continue
            output.append(line[index])
            index += 1
        rendered.append("".join(output))
    return "".join(rendered)


def _replace_agent_calls(body: str) -> str:
    """Replace balanced Claude Agent calls without leaving argument fragments."""
    rendered: list[str] = []
    cursor = 0
    while match := _AGENT_START_RE.search(body, cursor):
        rendered.append(body[cursor:match.start()])
        cursor = _balanced_call_end(body, match.end() - 1)
        rendered.append(
            "Delegate this independent work to a suitable Copilot custom agent."
        )
    rendered.append(body[cursor:])
    return "".join(rendered)


def _balanced_call_end(text: str, opening_parenthesis: int) -> int:
    """Return the first offset after a balanced, quote-aware call."""
    depth = 1
    quote: str | None = None
    is_escaped = False
    for index in range(opening_parenthesis + 1, len(text)):
        character = text[index]
        if quote is not None:
            if is_escaped:
                is_escaped = False
            elif character == "\\":
                is_escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"'}:
            quote = character
        elif character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return index + 1
    raise ValueError(f"Unbalanced Agent call at character {opening_parenthesis}")


def _user_invocable_skills() -> list[tuple[str, str, str, str]]:
    """Return user-invocable skills and their current/legacy bodies.

    Only skills whose SKILL.md is suitable for slash-command invocation are
    returned. Knowledge-only skills (``user-invocable: false``) are filtered
    out; user-invoked task skills may set ``disable-model-invocation: true``.
    """
    if not skills_dir.is_dir():
        return []
    result: list[tuple[str, str, str, str]] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.name.startswith("_") or not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            continue
        name = frontmatter_field(skill_file, "name")
        description = frontmatter_field(skill_file, "description")
        if not name or not description:
            continue
        # Honour the same visibility filter used by generate_opencode_commands
        user_invocable = frontmatter_field(skill_file, "user-invocable")
        if user_invocable == "false":
            continue
        body = _read_markdown_body(skill_file)
        if not body:
            continue
        result.append((
            name,
            description,
            body,
            _read_legacy_prompt_body(skill_file),
        ))
    return result


# ---------------------------------------------------------------------------
# Native agent rendering and managed file synchronization
# ---------------------------------------------------------------------------

def _render_agent(agent_file: Path) -> tuple[str, str, str]:
    """Return ``(name, description, Copilot agent markdown)``."""
    name = frontmatter_field(agent_file, "name")
    description = frontmatter_field(agent_file, "description")
    if not name or not description or not _SAFE_NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid Copilot agent metadata: {agent_file}")

    body = _portable_copilot_body(
        _read_markdown_body(agent_file),
        include_execution_note=False,
    ).rstrip()
    body_with_marker = f"{MANAGED_MARKER}\n\n{body}\n"
    if len(body_with_marker.encode("utf-8")) > MAX_AGENT_BODY_BYTES:
        raise ValueError(
            f"Copilot agent body exceeds {MAX_AGENT_BODY_BYTES} bytes: {agent_file}"
        )
    content = "\n".join([
        "---",
        f"name: {json.dumps(name, ensure_ascii=False)}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        "---",
        "",
        body_with_marker.rstrip(),
        "",
    ])
    return name, description, content


def _user_agent_names(directory: Path) -> set[str]:
    """Collect logical names declared by non-managed Copilot agent files."""
    names: set[str] = set()
    for path in sorted(directory.glob("*.agent.md")):
        if path.is_symlink():
            _warn_preserved(path, "path is a symlink")
            continue
        if _is_managed(path):
            continue
        try:
            name = frontmatter_field(path, "name")
        except (OSError, UnicodeError) as error:
            _warn_preserved(path, f"cannot read frontmatter ({error})")
            continue
        if name:
            names.add(name)
        else:
            _warn_preserved(path, "missing a readable logical name")
    return names


def _prepare_output_dir(base: Path, child_name: str) -> Path:
    """Create a customization directory without following managed-root symlinks."""
    output_dir = base / child_name
    if base.is_symlink():
        raise RuntimeError(f"Refusing symlinked Copilot customization root: {base}")
    if output_dir.is_symlink():
        raise RuntimeError(f"Refusing symlinked Copilot output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    if base.is_symlink() or output_dir.is_symlink():
        raise RuntimeError(f"Copilot output path became a symlink: {output_dir}")
    return output_dir


def _is_managed(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return MANAGED_MARKER in path.read_text(encoding="utf-8").splitlines()[:12]
    except (OSError, UnicodeError):
        return False


def _legacy_instructions_content(content: str) -> str:
    """Recreate the previous generator output for exact safe migration."""
    legacy = content.replace(f"{MANAGED_MARKER}\n\n", "", 1)
    lines = legacy.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("description: "):
            continue
        value = line.removeprefix("description: ")
        try:
            lines[index] = f"description: {json.loads(value)}"
        except json.JSONDecodeError:
            pass
    return "\n".join(lines) + "\n"


def _may_replace(path: Path, legacy_content: str | None) -> bool:
    if path.is_symlink():
        return False
    if not path.exists() or _is_managed(path):
        return True
    if legacy_content is None or not path.is_file():
        return False
    try:
        return path.read_text(encoding="utf-8") == legacy_content
    except (OSError, UnicodeError):
        return False


def _warn_preserved(path: Path, reason: str) -> None:
    print(
        f"Warning: preserving user Copilot file '{path}': {reason}",
        file=sys.stderr,
    )


def _stage_managed(
    destination: Path,
    content: str,
    legacy_content: str | None,
) -> Path | None:
    """Stage a managed/legacy file beside its destination."""
    if not _may_replace(destination, legacy_content):
        _warn_preserved(destination, "destination is user-owned or a symlink")
        return None

    fd, temp_name = tempfile.mkstemp(
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return temp_path
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    finally:
        if fd >= 0:
            os.close(fd)


def _sync_managed_files(
    directory: Path,
    desired: dict[str, tuple[str, str | None]],
    *,
    suffix: str,
    label: str,
) -> None:
    """Write desired files first, then remove only stale managed files."""
    staged: list[tuple[Path, Path, str | None, str]] = []
    try:
        for name, (content, legacy_content) in sorted(desired.items()):
            destination = directory / name
            temp_path = _stage_managed(destination, content, legacy_content)
            if temp_path is not None:
                staged.append((temp_path, destination, legacy_content, name))

        for temp_path, destination, legacy_content, name in staged:
            if not _may_replace(destination, legacy_content):
                _warn_preserved(
                    destination,
                    "destination became user-owned during generation",
                )
                continue
            os.replace(temp_path, destination)
            print(f"  Generated: {label}/{name}")
    finally:
        for temp_path, _, _, _ in staged:
            temp_path.unlink(missing_ok=True)

    for path in sorted(directory.glob(f"{PREFIX}*{suffix}")):
        if path.name in desired or path.is_symlink() or not _is_managed(path):
            continue
        path.unlink()
        print(f"  Removed stale: {label}/{path.name}")


# ---------------------------------------------------------------------------
# Portable skill emission (.github/skills or user-level skills/)
# ---------------------------------------------------------------------------

def _render_skill_markdown(skill_dir: Path) -> tuple[str, str]:
    """Return ``(logical_name, portable SKILL.md)`` for a source skill."""
    skill_file = skill_dir / "SKILL.md"
    name = frontmatter_field(skill_file, "name")
    description = frontmatter_field(skill_file, "description")
    if not name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise ValueError(f"Invalid Copilot skill name: {skill_file}")
    if not description:
        raise ValueError(f"Missing Copilot skill description: {skill_file}")
    body = _portable_copilot_body(
        _read_markdown_body(skill_file),
        include_execution_note=False,
    ).rstrip()
    execution_note = """## GitHub Copilot skill execution notes

- Resolve relative script, reference, template, and asset paths against this
  skill directory. Copilot exposes the complete directory when loading a skill.
- Use Copilot's current custom-agent and planning controls without assuming a
  Claude-specific tool signature."""
    content = "\n".join([
        "---",
        f"name: {name}",
        f"description: {json.dumps(description, ensure_ascii=False)}",
        "---",
        "",
        MANAGED_MARKER,
        "",
        execution_note,
        "",
        body,
        "",
    ])
    return name, content


def _skill_source_files(skill_dir: Path) -> dict[Path, tuple[bytes, int]]:
    """Collect portable skill files, excluding generated bytecode and caches."""
    files: dict[Path, tuple[bytes, int]] = {}
    needs_detect_utils = False
    for source in sorted(skill_dir.rglob("*")):
        relative = source.relative_to(skill_dir)
        if "__pycache__" in relative.parts or source.name == ".DS_Store":
            continue
        if source.is_symlink():
            raise RuntimeError(f"Refusing symlinked Copilot skill source: {source}")
        if not source.is_file() or source.name.endswith((".pyc", ".pyo")):
            continue
        if relative == Path("SKILL.md"):
            continue
        content = source.read_bytes()
        if source.suffix == ".py":
            text = content.decode("utf-8")
            if "from _lib.detect_utils import" in text:
                needs_detect_utils = True
                text = text.replace(
                    "from _lib.detect_utils import",
                    "from detect_utils import",
                )
                content = text.encode("utf-8")
        mode = source.stat().st_mode & 0o777
        files[relative] = (content, mode or 0o644)

    if needs_detect_utils:
        helper = skills_dir / "_lib" / "detect_utils.py"
        if helper.is_symlink() or not helper.is_file():
            raise RuntimeError(f"Missing Copilot skill helper: {helper}")
        files[Path("scripts/detect_utils.py")] = (
            helper.read_bytes(),
            helper.stat().st_mode & 0o777 or 0o644,
        )
    return files


def _is_managed_skill_dir(path: Path) -> bool:
    skill_file = path / "SKILL.md"
    return path.is_dir() and not path.is_symlink() and _is_managed(skill_file)


def _managed_skill_paths(path: Path) -> set[Path]:
    manifest = path / SKILL_MANIFEST
    if not manifest.is_file() or manifest.is_symlink():
        return {Path("SKILL.md")}
    try:
        value = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {Path("SKILL.md")}
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return {Path("SKILL.md")}
    result = {Path(item) for item in value}
    result.add(Path(SKILL_MANIFEST))
    return result


def _has_user_skill_extras(path: Path) -> bool:
    managed = _managed_skill_paths(path)
    return any(
        item.is_file() and item.relative_to(path) not in managed
        for item in path.rglob("*")
        if not item.is_symlink()
    ) or any(item.is_symlink() for item in path.rglob("*"))


def _copy_user_skill_extras(existing: Path, staging: Path,
                            generated_paths: set[Path]) -> None:
    """Preserve files a user added inside a previously managed skill."""
    old_managed = _managed_skill_paths(existing)
    for source in sorted(existing.rglob("*")):
        relative = source.relative_to(existing)
        if relative in old_managed or source.is_dir():
            continue
        if source.is_symlink():
            raise RuntimeError(f"Refusing symlinked user Copilot skill asset: {source}")
        if not source.is_file():
            continue
        if relative in generated_paths:
            raise RuntimeError(
                f"Copilot skill update would overwrite a user asset: {source}"
            )
        destination = staging / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _stage_skill(skills_root: Path, source_dir: Path,
                 existing: Path | None) -> tuple[Path, str]:
    name, markdown = _render_skill_markdown(source_dir)
    assets = _skill_source_files(source_dir)
    generated_paths = {Path("SKILL.md"), *assets.keys(), Path(SKILL_MANIFEST)}
    staging = Path(tempfile.mkdtemp(
        dir=skills_root,
        prefix=f".ai-toolkit-{name}.",
    ))
    try:
        skill_file = staging / "SKILL.md"
        skill_file.write_text(markdown, encoding="utf-8")
        os.chmod(skill_file, 0o644)
        for relative, (content, mode) in sorted(assets.items()):
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            os.chmod(destination, mode)
        (staging / SKILL_MANIFEST).write_text(
            json.dumps(
                sorted(path.as_posix() for path in generated_paths),
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )
        if existing is not None:
            _copy_user_skill_extras(existing, staging, generated_paths)
        return staging, name
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _replace_skill_dir(staging: Path, destination: Path) -> None:
    """Replace one managed skill with a same-filesystem rollback directory."""
    backup: Path | None = None
    try:
        if destination.exists():
            if destination.is_symlink() or not _is_managed_skill_dir(destination):
                raise RuntimeError(
                    f"Refusing user-owned Copilot skill collision: {destination}"
                )
            backup = Path(tempfile.mkdtemp(
                dir=destination.parent,
                prefix=f".{destination.name}.backup.",
            ))
            backup.rmdir()
            os.replace(destination, backup)
        os.replace(staging, destination)
    except Exception:
        if destination.exists() and backup is not None:
            shutil.rmtree(destination)
        if backup is not None and backup.exists():
            os.replace(backup, destination)
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        if backup is not None and backup.exists():
            shutil.rmtree(backup)


def _user_skill_names(skills_root: Path) -> set[str]:
    names: set[str] = set()
    for child in sorted(skills_root.iterdir()):
        if child.is_symlink():
            _warn_preserved(child, "skill directory is a symlink")
            continue
        if not child.is_dir() or _is_managed_skill_dir(child):
            continue
        skill_file = child / "SKILL.md"
        if not skill_file.is_file() or skill_file.is_symlink():
            continue
        try:
            name = frontmatter_field(skill_file, "name")
        except (OSError, UnicodeError):
            continue
        if name:
            names.add(name)
    return names


def _sync_copilot_skills(customization_root: Path, *, label: str) -> None:
    skill_root = _prepare_output_dir(customization_root, "skills")
    user_names = _user_skill_names(skill_root)
    expected_dirs: set[str] = set()
    for source_dir in sorted(skills_dir.iterdir()):
        if source_dir.name.startswith("_") or not (source_dir / "SKILL.md").is_file():
            continue
        logical_name = frontmatter_field(source_dir / "SKILL.md", "name")
        if not logical_name:
            raise ValueError(f"Missing Copilot skill name: {source_dir}")
        destination_name = f"{PREFIX}{logical_name}"
        destination = skill_root / destination_name
        if destination.is_symlink():
            raise RuntimeError(f"Refusing symlinked Copilot skill: {destination}")
        if logical_name in user_names:
            _warn_preserved(
                destination,
                f"logical name '{logical_name}' belongs to a user skill",
            )
            continue
        expected_dirs.add(destination_name)
        existing = destination if destination.exists() else None
        if existing is not None and not _is_managed_skill_dir(existing):
            raise RuntimeError(f"Refusing user-owned Copilot skill collision: {destination}")
        staging, rendered_name = _stage_skill(skill_root, source_dir, existing)
        if rendered_name != logical_name:
            shutil.rmtree(staging, ignore_errors=True)
            raise ValueError(f"Copilot skill name changed while rendering: {source_dir}")
        _replace_skill_dir(staging, destination)

    for path in sorted(skill_root.glob(f"{PREFIX}*")):
        if path.name in expected_dirs or path.is_symlink() or not _is_managed_skill_dir(path):
            continue
        if _has_user_skill_extras(path):
            _warn_preserved(path, "stale managed skill contains user-added assets")
            continue
        shutil.rmtree(path)
        print(f"  Removed stale: {label}/{path.name}")
    print(f"  Generated: {label}/ ({len(expected_dirs)} portable skills)")


# ---------------------------------------------------------------------------
# Directory-mode generation
# ---------------------------------------------------------------------------


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None,
             emit_agents: bool = True,
             emit_prompts: bool = True,
             emit_instructions: bool = True,
             emit_skills: bool = True,
             config_root: Path | None = None) -> None:
    """Write Copilot instructions, custom agents, skills, and prompt files.

    By default writes to ``<target_dir>/.github/`` (project-local). Pass
    ``config_root=~/.copilot`` for the Copilot CLI user-level global layout,
    where instructions and agents land below ``~/.copilot/``.

    ``.github/copilot-instructions.md`` is intentionally not written here —
    the legacy ``main()`` entry point still emits it to stdout so existing
    scripts (including ``ai-toolkit install``) keep working unchanged.
    """
    github_dir = target_dir / ".github"
    customization_root = config_root if config_root is not None else github_dir
    instr_root = customization_root
    instr_label = "$COPILOT_HOME/instructions" if config_root is not None else ".github/instructions"
    agent_label = "$COPILOT_HOME/agents" if config_root is not None else ".github/agents"
    skill_label = "$COPILOT_HOME/skills" if config_root is not None else ".github/skills"

    if emit_instructions:
        instr_dir = _prepare_output_dir(instr_root, "instructions")

        instruction_files: dict[str, callable] = dict(_make_instruction_files())

        # Language-specific instructions (auto-applied by file glob)
        for filename, content_fn in build_language_rules(language_modules).items():
            lang = filename.removeprefix(f"{PREFIX}lang-").removesuffix(".md")
            globs = LANG_GLOBS.get(lang)
            apply_to = ",".join(globs) if globs else "**"
            new_name = f"{PREFIX}lang-{lang}.instructions.md"
            instruction_files[new_name] = (lambda fn, language_name, a: lambda: _instructions_file(
                fn(),
                apply_to=a,
                description=f"{language_name.title()} language rules",
            ))(content_fn, lang, apply_to)

        # User-registered custom rules (always-on)
        for filename, content_fn in build_registered_rules(rules_dir).items():
            stem = filename.removeprefix(f"{PREFIX}custom-").removesuffix(".md")
            new_name = f"{PREFIX}custom-{stem}.instructions.md"
            instruction_files[new_name] = (lambda fn, n: lambda: _instructions_file(
                fn(),
                apply_to="**",
                description=f"Custom rule: {n}",
            ))(content_fn, stem)

        desired_instructions: dict[str, tuple[str, str | None]] = {}
        for name, content_fn in instruction_files.items():
            content = content_fn()
            desired_instructions[name] = (
                content,
                _legacy_instructions_content(content),
            )
        _sync_managed_files(
            instr_dir,
            desired_instructions,
            suffix=".instructions.md",
            label=instr_label,
        )

    if emit_agents:
        agent_dir = _prepare_output_dir(customization_root, "agents")
        user_names = _user_agent_names(agent_dir)
        desired_agents: dict[str, tuple[str, str | None]] = {}
        source_names: set[str] = set()
        for agent_file in sorted(agents_dir.glob("*.md")):
            name, _, content = _render_agent(agent_file)
            if name in source_names:
                raise ValueError(f"Duplicate Copilot agent name: {name}")
            source_names.add(name)
            if name in user_names:
                _warn_preserved(
                    agent_dir / f"{PREFIX}{name}.agent.md",
                    f"logical name '{name}' belongs to a user agent",
                )
                continue
            filename = f"{PREFIX}{name}.agent.md"
            desired_agents[filename] = (content, None)
        _sync_managed_files(
            agent_dir,
            desired_agents,
            suffix=".agent.md",
            label=agent_label,
        )

    if emit_skills:
        _sync_copilot_skills(customization_root, label=skill_label)

    if emit_prompts:
        prompt_dir = _prepare_output_dir(github_dir, "prompts")

        skills = _user_invocable_skills()
        desired_prompts: dict[str, tuple[str, str | None]] = {}
        for name, description, body, legacy_body in skills:
            if not _SAFE_NAME_RE.fullmatch(name):
                raise ValueError(f"Invalid Copilot prompt name: {name}")
            filename = f"{PREFIX}{name}.prompt.md"
            portable_body = _portable_copilot_body(
                body,
                include_execution_note=True,
            )
            content = _prompt_file(description, portable_body)
            desired_prompts[filename] = (
                content,
                _legacy_prompt_file(description, legacy_body),
            )
        _sync_managed_files(
            prompt_dir,
            desired_prompts,
            suffix=".prompt.md",
            label=".github/prompts",
        )


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point.

    With no argument: emit the repo-wide ``copilot-instructions.md`` to stdout
    (preserves the historical contract).

    With a directory argument: write the path-specific ``instructions/`` and
    native ``agents/`` and ``prompts/`` files under ``<target>/.github/``. The
    caller is responsible for redirecting the stdout generator separately if
    they want the full set.
    """
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        from paths import RULES_DIR
        generate(target, rules_dir=RULES_DIR)
        return

    render_generator(_STDOUT_CONFIG)


if __name__ == "__main__":
    main()
