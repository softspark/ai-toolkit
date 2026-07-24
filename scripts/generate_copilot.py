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

import hashlib
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
import secure_fs
from secure_fs import SecureDestination, run_secure_transaction


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


def _load_legacy_managed_hashes() -> dict[str, frozenset[str]]:
    """Load exact pre-marker output hashes shipped by releases v3.0-v4.14."""
    manifest = Path(__file__).with_name("copilot_legacy_hashes.json")
    value = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Invalid Copilot legacy hash manifest: {manifest}")
    result: dict[str, frozenset[str]] = {}
    for name, hashes in value.items():
        valid_name = (
            isinstance(name, str)
            and Path(name).name == name
            and name.startswith(PREFIX)
            and name.endswith((".instructions.md", ".prompt.md"))
        )
        valid_hashes = (
            isinstance(hashes, list)
            and bool(hashes)
            and all(
                isinstance(digest, str)
                and re.fullmatch(r"[0-9a-f]{64}", digest)
                for digest in hashes
            )
        )
        if not valid_name or not valid_hashes:
            raise ValueError(f"Invalid Copilot legacy hash entry: {name!r}")
        result[name] = frozenset(hashes)
    return result


_LEGACY_MANAGED_SHA256 = _load_legacy_managed_hashes()

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


def _desired_agent_files(
    directory: Path,
) -> dict[str, tuple[str, str | None]]:
    """Render managed agents while honoring user-owned logical names."""
    user_names = _user_agent_names(directory)
    desired: dict[str, tuple[str, str | None]] = {}
    source_names: set[str] = set()
    for agent_file in sorted(agents_dir.glob("*.md")):
        name, _, content = _render_agent(agent_file)
        if name in source_names:
            raise ValueError(f"Duplicate Copilot agent name: {name}")
        source_names.add(name)
        if name in user_names:
            _warn_preserved(
                directory / f"{PREFIX}{name}.agent.md",
                f"logical name '{name}' belongs to a user agent",
            )
            continue
        desired[f"{PREFIX}{name}.agent.md"] = (content, None)
    return desired


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


def _is_managed_content(content: bytes) -> bool:
    try:
        lines = content.decode("utf-8").splitlines()[:12]
    except UnicodeError:
        return False
    return MANAGED_MARKER in lines


def _is_managed(path: Path) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        return _is_managed_content(path.read_bytes())
    except OSError:
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


def _matches_legacy_managed(
    filename: str,
    content: bytes,
    legacy_content: str | None,
) -> bool:
    """Recognize exact pre-marker output without trusting the filename alone."""
    if legacy_content is not None and content == legacy_content.encode("utf-8"):
        return True
    expected = _LEGACY_MANAGED_SHA256.get(filename, frozenset())
    return hashlib.sha256(content).hexdigest() in expected


def _may_replace(path: Path, legacy_content: str | None) -> bool:
    if path.is_symlink():
        return False
    if not path.exists() or _is_managed(path):
        return True
    if legacy_content is None or not path.is_file():
        return False
    try:
        return _matches_legacy_managed(
            path.name,
            path.read_bytes(),
            legacy_content,
        )
    except OSError:
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
    trusted_root: Path,
) -> None:
    """Write desired files first, then remove only stale managed files."""
    stale_candidates = _managed_cleanup_candidates(
        directory,
        set(desired),
        {},
        suffix=suffix,
        label=label,
        trusted_root=trusted_root,
    )
    if stale_candidates:
        _sync_managed_files_with_cleanup(
            directory,
            desired,
            stale_candidates,
            label=label,
            trusted_root=trusted_root,
        )
        return

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



def _require_secure_cleanup() -> None:
    if secure_fs.SECURE_DIR_FD:
        return
    raise RuntimeError(
        "Copilot managed cleanup requires POSIX dir_fd and O_NOFOLLOW; "
        "No files were changed"
    )


def _cleanup_is_required(
    directory: Path,
    keep: set[str],
    *,
    suffix: str,
) -> bool:
    """Detect cleanup work before any Copilot surface is mutated."""
    if not directory.exists():
        return False
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError(f"Refusing unsafe Copilot output directory: {directory}")
    return any(
        path.name not in keep and not path.is_symlink() and path.is_file()
        for path in directory.glob(f"{PREFIX}*{suffix}")
    )


def _managed_cleanup_candidates(
    directory: Path,
    keep: set[str],
    legacy_files: dict[str, str],
    *,
    suffix: str,
    label: str,
    trusted_root: Path,
) -> list[tuple[SecureDestination, str | None]]:
    """Pin regular stale candidates without following user symlinks."""
    if not directory.exists():
        return []
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError(f"Refusing unsafe Copilot output directory: {directory}")
    candidates: list[tuple[SecureDestination, str | None]] = []
    for path in sorted(directory.glob(f"{PREFIX}*{suffix}")):
        if path.name in keep:
            continue
        if path.is_symlink() or not path.is_file():
            _warn_preserved(path, "stale file is not provably managed")
            continue
        candidates.append((
            SecureDestination(
                path=path,
                trusted_root=trusted_root,
                label=f"Copilot {label}/{path.name}",
            ),
            legacy_files.get(path.name),
        ))
    return candidates


def _sync_managed_files_with_cleanup(
    directory: Path,
    desired: dict[str, tuple[str, str | None]],
    stale_candidates: list[tuple[SecureDestination, str | None]],
    *,
    label: str,
    trusted_root: Path,
) -> None:
    """Atomically update desired files and remove stale managed output."""
    _require_secure_cleanup()
    write_candidates: list[
        tuple[SecureDestination, bytes, str | None]
    ] = []
    for name, (content, legacy_content) in sorted(desired.items()):
        path = directory / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            _warn_preserved(path, "destination is user-owned or a symlink")
            continue
        write_candidates.append((
            SecureDestination(
                path=path,
                trusted_root=trusted_root,
                label=f"Copilot {label}/{name}",
            ),
            content.encode("utf-8"),
            legacy_content,
        ))

    destinations = [item[0] for item in write_candidates]
    destinations.extend(item[0] for item in stale_candidates)
    messages: list[str] = []

    def update_and_remove(transaction) -> None:
        for destination, content, legacy_content in write_candidates:
            initial = transaction.initial_content(destination)
            if initial is not None and not (
                _is_managed_content(initial)
                or _matches_legacy_managed(
                    destination.path.name,
                    initial,
                    legacy_content,
                )
            ):
                _warn_preserved(
                    destination.path,
                    "destination is user-owned or a symlink",
                )
                continue
            transaction.atomic_write(destination, content)
            messages.append(f"  Generated: {label}/{destination.path.name}")

        for destination, legacy_content in stale_candidates:
            initial = transaction.initial_content(destination)
            if initial is None:
                continue
            if not (
                _is_managed_content(initial)
                or _matches_legacy_managed(
                    destination.path.name,
                    initial,
                    legacy_content,
                )
            ):
                _warn_preserved(
                    destination.path,
                    "stale file is not provably managed",
                )
                continue
            transaction.unlink(destination)
            messages.append(f"  Removed stale: {label}/{destination.path.name}")

    run_secure_transaction(destinations, update_and_remove)
    for message in messages:
        print(message)


def _cleanup_managed_files(
    directory: Path,
    keep: set[str],
    legacy_files: dict[str, str],
    *,
    suffix: str,
    label: str,
    trusted_root: Path,
) -> None:
    """Remove stale managed or exact legacy files, preserving user content."""
    candidates = _managed_cleanup_candidates(
        directory,
        keep,
        legacy_files,
        suffix=suffix,
        label=label,
        trusted_root=trusted_root,
    )
    if not candidates:
        return
    _require_secure_cleanup()

    def remove_stale(transaction) -> None:
        for destination, legacy_content in candidates:
            content = transaction.initial_content(destination)
            if content is None:
                continue
            if not (
                _is_managed_content(content)
                or _matches_legacy_managed(
                    destination.path.name,
                    content,
                    legacy_content,
                )
            ):
                _warn_preserved(
                    destination.path,
                    "stale file is not provably managed",
                )
                continue
            transaction.unlink(destination)
            print(f"  Removed stale: {label}/{destination.path.name}")

    run_secure_transaction(
        [destination for destination, _ in candidates],
        remove_stale,
    )


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


def _is_skill_remnant(path: Path) -> bool:
    """Asset-only leftover of a legacy managed skill.

    Pre-manifest toolkit versions tracked only SKILL.md as managed, so their
    cleanup removed SKILL.md and left reference/ and scripts/ assets behind.
    Without SKILL.md the directory is not a functional Copilot skill, so it is
    safe to rebuild in place; a directory that still has any SKILL.md (managed
    or not) is never classified as a remnant.
    """
    return (
        path.is_dir()
        and not path.is_symlink()
        and not (path / "SKILL.md").exists()
        and not (path / "SKILL.md").is_symlink()
    )


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
                            generated_paths: set[Path],
                            *, skip_stale_assets: bool = False) -> None:
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
            if skip_stale_assets:
                continue
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
            _copy_user_skill_extras(
                existing, staging, generated_paths,
                skip_stale_assets=_is_skill_remnant(existing),
            )
        return staging, name
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _replace_skill_dir(staging: Path, destination: Path) -> None:
    """Replace one managed skill with a same-filesystem rollback directory."""
    backup: Path | None = None
    try:
        if destination.exists():
            if destination.is_symlink() or not (
                _is_managed_skill_dir(destination)
                or _is_skill_remnant(destination)
            ):
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
            if not _is_skill_remnant(existing):
                raise RuntimeError(f"Refusing user-owned Copilot skill collision: {destination}")
            print(
                f"Note: rebuilding asset-only Copilot skill remnant '{destination}'",
                file=sys.stderr,
            )
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


def _desired_instruction_files(
    language_modules: list[str] | None,
    rules_dir: Path | None,
) -> dict[str, tuple[str, str]]:
    instruction_files: dict[str, callable] = dict(_make_instruction_files())
    for filename, content_fn in build_language_rules(language_modules).items():
        language = filename.removeprefix(f"{PREFIX}lang-").removesuffix(".md")
        apply_to = ",".join(LANG_GLOBS.get(language, ())) or "**"
        new_name = f"{PREFIX}lang-{language}.instructions.md"
        instruction_files[new_name] = (
            lambda fn, name, pattern: lambda: _instructions_file(
                fn(),
                apply_to=pattern,
                description=f"{name.title()} language rules",
            )
        )(content_fn, language, apply_to)
    for filename, content_fn in build_registered_rules(rules_dir).items():
        stem = filename.removeprefix(f"{PREFIX}custom-").removesuffix(".md")
        new_name = f"{PREFIX}custom-{stem}.instructions.md"
        instruction_files[new_name] = (
            lambda fn, name: lambda: _instructions_file(
                fn(),
                apply_to="**",
                description=f"Custom rule: {name}",
            )
        )(content_fn, stem)
    desired: dict[str, tuple[str, str]] = {}
    for name, content_fn in instruction_files.items():
        content = content_fn()
        desired[name] = (content, _legacy_instructions_content(content))
    return desired


def _desired_prompt_files() -> dict[str, tuple[str, str]]:
    desired: dict[str, tuple[str, str]] = {}
    for name, description, body, legacy_body in _user_invocable_skills():
        if not _SAFE_NAME_RE.fullmatch(name):
            raise ValueError(f"Invalid Copilot prompt name: {name}")
        portable_body = _portable_copilot_body(body, include_execution_note=True)
        desired[f"{PREFIX}{name}.prompt.md"] = (
            _prompt_file(description, portable_body),
            _legacy_prompt_file(description, legacy_body),
        )
    return desired


def preflight_cleanup(
    target_dir: Path,
    *,
    config_root: Path | None = None,
) -> None:
    """Validate profile-cleanup paths before an installer mutates any surface."""
    target_dir = Path(target_dir).expanduser().absolute()
    github_dir = target_dir / ".github"
    customization_root = (
        github_dir
        if config_root is None
        else Path(config_root).expanduser().absolute()
    )
    trusted_root = target_dir if config_root is None else customization_root
    desired_agents = _desired_agent_files(customization_root / "agents")
    candidates = _managed_cleanup_candidates(
        customization_root / "agents",
        set(desired_agents),
        {},
        suffix=".agent.md",
        label=(
            ".github/agents"
            if config_root is None
            else "$COPILOT_HOME/agents"
        ),
        trusted_root=trusted_root,
    )
    candidates.extend(_managed_cleanup_candidates(
        customization_root / "instructions",
        set(),
        {},
        suffix=".instructions.md",
        label=(
            ".github/instructions"
            if config_root is None
            else "$COPILOT_HOME/instructions"
        ),
        trusted_root=trusted_root,
    ))
    if config_root is None:
        candidates.extend(_managed_cleanup_candidates(
            github_dir / "prompts",
            set(),
            {},
            suffix=".prompt.md",
            label=".github/prompts",
            trusted_root=target_dir,
        ))
    if not candidates:
        return
    _require_secure_cleanup()
    run_secure_transaction(
        [destination for destination, _ in candidates],
        lambda _transaction: None,
    )


def generate(target_dir: Path, *,
             language_modules: list[str] | None = None,
             rules_dir: Path | None = None,
             emit_agents: bool = True,
             emit_prompts: bool = True,
             emit_instructions: bool = True,
             emit_skills: bool = True,
             cleanup_disabled: bool = False,
             config_root: Path | None = None) -> None:
    """Write Copilot instructions, custom agents, skills, and prompt files.

    By default writes to ``<target_dir>/.github/`` (project-local). Pass
    ``config_root=~/.copilot`` for the Copilot CLI user-level global layout,
    where instructions and agents land below ``~/.copilot/``.

    ``.github/copilot-instructions.md`` is intentionally not written here —
    the legacy ``main()`` entry point still emits it to stdout so existing
    scripts (including ``ai-toolkit install``) keep working unchanged.

    ``cleanup_disabled=True`` is the installer-only profile-transition mode:
    disabled instruction and prompt surfaces are removed only when their
    ownership marker or exact historical output hash proves toolkit ownership.
    """
    github_dir = target_dir / ".github"
    customization_root = config_root if config_root is not None else github_dir
    customization_trusted_root = (
        target_dir if config_root is None else customization_root.parent
    )
    instr_root = customization_root
    instr_label = "$COPILOT_HOME/instructions" if config_root is not None else ".github/instructions"
    agent_label = "$COPILOT_HOME/agents" if config_root is not None else ".github/agents"
    skill_label = "$COPILOT_HOME/skills" if config_root is not None else ".github/skills"

    desired_instructions = (
        _desired_instruction_files(language_modules, rules_dir)
        if emit_instructions or cleanup_disabled
        else {}
    )
    agent_dir_path = customization_root / "agents"
    if emit_agents and (
        customization_root.is_symlink() or agent_dir_path.is_symlink()
    ):
        raise RuntimeError(
            f"Refusing symlinked Copilot output directory: {agent_dir_path}"
        )
    desired_agents = (
        _desired_agent_files(agent_dir_path) if emit_agents else {}
    )
    needs_project_prompt_state = (
        emit_prompts or (cleanup_disabled and config_root is None)
    )
    desired_prompts = (
        _desired_prompt_files() if needs_project_prompt_state else {}
    )

    cleanup_checks: list[tuple[Path, set[str], str]] = []
    if emit_instructions or cleanup_disabled:
        cleanup_checks.append((
            instr_root / "instructions",
            set(desired_instructions) if emit_instructions else set(),
            ".instructions.md",
        ))
    if emit_agents:
        cleanup_checks.append((
            agent_dir_path,
            set(desired_agents),
            ".agent.md",
        ))
    if needs_project_prompt_state:
        cleanup_checks.append((
            github_dir / "prompts",
            set(desired_prompts) if emit_prompts else set(),
            ".prompt.md",
        ))
    if any(
        _cleanup_is_required(directory, keep, suffix=suffix)
        for directory, keep, suffix in cleanup_checks
    ):
        _require_secure_cleanup()

    if emit_instructions:
        instr_dir = _prepare_output_dir(instr_root, "instructions")
        _sync_managed_files(
            instr_dir,
            desired_instructions,
            suffix=".instructions.md",
            label=instr_label,
            trusted_root=customization_trusted_root,
        )
    elif cleanup_disabled:
        _cleanup_managed_files(
            instr_root / "instructions",
            set(),
            {name: legacy for name, (_, legacy) in desired_instructions.items()},
            suffix=".instructions.md",
            label=instr_label,
            trusted_root=customization_trusted_root,
        )

    if emit_agents:
        agent_dir = _prepare_output_dir(customization_root, "agents")
        _sync_managed_files(
            agent_dir,
            desired_agents,
            suffix=".agent.md",
            label=agent_label,
            trusted_root=customization_trusted_root,
        )

    if emit_skills:
        _sync_copilot_skills(customization_root, label=skill_label)

    if emit_prompts:
        prompt_dir = _prepare_output_dir(github_dir, "prompts")
        _sync_managed_files(
            prompt_dir,
            desired_prompts,
            suffix=".prompt.md",
            label=".github/prompts",
            trusted_root=target_dir,
        )
    elif cleanup_disabled and config_root is None:
        _cleanup_managed_files(
            github_dir / "prompts",
            set(),
            {name: legacy for name, (_, legacy) in desired_prompts.items()},
            suffix=".prompt.md",
            label=".github/prompts",
            trusted_root=target_dir,
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
