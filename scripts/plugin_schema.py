# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Plugin manifest schema validation.

Single source of truth for validating plugin.json manifests.
Used by both validate.py and plugin.py.

Stdlib-only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


# Required top-level fields
REQUIRED_FIELDS = (
    "name",
    "description",
    "version",
    "domain",
    "type",
    "status",
)

# Valid status values
VALID_STATUSES = frozenset({"stable", "experimental", "deprecated"})

# Valid plugin types
VALID_TYPES = frozenset(
    {
        "behavioral",
        "language",
        "domain",
        "integration",
        "plugin-pack",
        "policy-pack",
        "hook-pack",
    }
)

# Valid hook event names (must match validate.py VALID_HOOK_EVENTS)
VALID_HOOK_EVENTS = frozenset(
    {
        "SessionStart",
        "SessionEnd",
        "UserPromptSubmit",
        "Notification",
        "MessageDisplay",
        "PreToolUse",
        "PostToolUse",
        "PostToolUseFailure",
        "PostToolBatch",
        "Stop",
        "StopFailure",
        "UserPromptExpansion",
        "SubagentStart",
        "SubagentStop",
        "PreCompact",
        "PostCompact",
        "PermissionRequest",
        "PermissionDenied",
        "Elicitation",
        "ElicitationResult",
        "TaskCreated",
        "TaskCompleted",
        "TeammateIdle",
        "WorktreeCreate",
        "WorktreeRemove",
        "CwdChanged",
        "FileChanged",
        "ConfigChange",
        "DirectoryAdded",
        "Setup",
        "InstructionsLoaded",
    }
)

MCP_REFERENCE_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*")
LOCAL_ENDPOINT_MARKERS = ("localhost", "127.0.0.1", "[::1]")
BUILTIN_MCP_TEMPLATES_DIR = (
    Path(__file__).resolve().parent.parent / "app" / "mcp-templates"
)


def _validate_requires(data: dict) -> list[str]:
    if "requires" not in data:
        return ["Missing required field: requires"]

    requires = data["requires"]
    if not isinstance(requires, dict) or not requires:
        return ["'requires' must be a non-empty dictionary"]

    errors: list[str] = []
    for dependency, constraint in requires.items():
        if not isinstance(dependency, str) or not dependency.strip():
            errors.append("requires keys must be non-empty strings")
            continue
        if not isinstance(constraint, str) or not constraint.strip():
            errors.append(f"requires.{dependency} must be a non-empty string")
    return errors


def validate_manifest(data: dict, pack_dir: Path | None = None) -> list[str]:
    """Validate a plugin manifest dict.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")
    errors.extend(_validate_requires(data))
    name = data.get("name")
    if name and (
        not isinstance(name, str) or MCP_REFERENCE_PATTERN.fullmatch(name) is None
    ):
        errors.append("name must be a safe lowercase-hyphen identifier")

    # Validate status
    status = data.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(
            f"Invalid status '{status}' (valid: {', '.join(sorted(VALID_STATUSES))})"
        )

    # Validate type
    plugin_type = data.get("type", "")
    if plugin_type and plugin_type not in VALID_TYPES:
        errors.append(
            f"Invalid type '{plugin_type}' (valid: {', '.join(sorted(VALID_TYPES))})"
        )

    # Validate includes structure
    includes = data.get("includes")
    if includes is None:
        errors.append("Missing 'includes' field")
    elif not isinstance(includes, dict):
        errors.append("'includes' must be a dictionary")
    else:
        for key in ("agents", "skills", "rules", "hooks", "mcp"):
            val = includes.get(key, [])
            if not isinstance(val, list):
                errors.append(f"includes.{key} must be a list")

        mcp_references = includes.get("mcp", [])
        if isinstance(mcp_references, list):
            invalid_mcp_name = False
            for reference in mcp_references:
                if (
                    not isinstance(reference, str)
                    or MCP_REFERENCE_PATTERN.fullmatch(reference) is None
                ):
                    invalid_mcp_name = True
                    continue
                if pack_dir is not None:
                    errors.extend(_validate_mcp_reference(reference, pack_dir))
            if invalid_mcp_name:
                errors.append(
                    "includes.mcp entries must be safe lowercase-hyphen names"
                )

    # Validate hook_events if present
    hook_events = data.get("hook_events", {})
    if hook_events:
        if not isinstance(hook_events, dict):
            errors.append(
                "'hook_events' must be a dictionary mapping hook filenames to event names"
            )
        else:
            for hook_file, event in hook_events.items():
                if event not in VALID_HOOK_EVENTS:
                    errors.append(
                        f"hook_events['{hook_file}']: invalid event '{event}'"
                    )

    # Validate hook files exist (if pack_dir provided)
    # Hooks can come from the plugin's own hooks/ dir OR from core app/hooks/
    if pack_dir and includes and isinstance(includes, dict):
        hooks_dir = pack_dir / "hooks"
        # Resolve toolkit root to check core hooks
        toolkit_hooks_dir = pack_dir.parent.parent / "hooks"
        for hook_file in includes.get("hooks", []):
            base_name = Path(hook_file).name
            candidates = [
                hooks_dir / hook_file,
                hooks_dir / base_name,
                pack_dir / hook_file,
                toolkit_hooks_dir / base_name,  # core hooks
            ]
            if not any(c.is_file() for c in candidates):
                errors.append(f"Hook file not found: {hook_file}")

    return errors


def _validate_mcp_reference(reference: str, pack_dir: Path) -> list[str]:
    candidates = (
        pack_dir / "mcp" / f"{reference}.json",
        BUILTIN_MCP_TEMPLATES_DIR / f"{reference}.json",
    )
    template_path = next((path for path in candidates if path.is_file()), None)
    if template_path is None:
        return [f"MCP template not found: {reference}"]
    if template_path.is_symlink():
        return [f"MCP template must not be symlinked: {reference}"]
    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [f"Invalid MCP template JSON: {reference}"]
    if not isinstance(template, dict) or template.get("name") != reference:
        return [f"MCP template name mismatch: {reference}"]
    servers = template.get("mcpServers")
    if not isinstance(servers, dict) or not servers:
        return [f"MCP template requires non-empty mcpServers: {reference}"]
    if not all(_is_valid_mcp_server(name, server) for name, server in servers.items()):
        return [f"MCP template has invalid server entries: {reference}"]
    local_remote = any(
        isinstance(server.get("url"), str)
        and any(marker in server["url"].lower() for marker in LOCAL_ENDPOINT_MARKERS)
        for server in servers.values()
    )
    warning = template.get("postInstall", "")
    if local_remote and (
        not isinstance(warning, str) or "unauthenticated" not in warning.lower()
    ):
        return [
            "Local HTTP MCP template must warn that access is unauthenticated: "
            f"{reference}"
        ]
    return []


def _is_valid_mcp_server(name: object, server: object) -> bool:
    if (
        not isinstance(name, str)
        or MCP_REFERENCE_PATTERN.fullmatch(name) is None
        or not isinstance(server, dict)
    ):
        return False
    transports = [key for key in ("command", "url") if key in server]
    return (
        len(transports) == 1
        and isinstance(server[transports[0]], str)
        and bool(server[transports[0]].strip())
    )


def validate_references(
    data: dict,
    agents_dir: Path,
    skills_dir: Path,
    pack_dir: Path | None = None,
) -> list[str]:
    """Validate that referenced agents and skills exist.

    A pack may either reference a core asset (app/agents, app/skills) or ship its
    own under <pack>/agents and <pack>/skills. Checking only the core directories
    reported every self-contained pack as broken even though the installer links
    its skills fine. pack_dir stays optional so existing callers keep working.

    Returns a list of error messages.
    """
    errors: list[str] = []
    includes = data.get("includes", {})

    for agent in includes.get("agents", []):
        candidates = [agents_dir / f"{agent}.md"]
        if pack_dir is not None:
            candidates.append(pack_dir / "agents" / f"{agent}.md")
        if not any(c.is_file() for c in candidates):
            errors.append(f"References missing agent: {agent}")

    for skill in includes.get("skills", []):
        candidates = [skills_dir / skill / "SKILL.md"]
        if pack_dir is not None:
            candidates.append(pack_dir / "skills" / skill / "SKILL.md")
        if not any(c.is_file() for c in candidates):
            errors.append(f"References missing skill: {skill}")

    return errors


def resolve_hook_event(hook_filename: str, manifest: dict) -> str:
    """Resolve the Claude Code event for a hook file.

    Checks hook_events in manifest first, then falls back to
    filename-based guessing.
    """
    # Check explicit mapping first
    hook_events = manifest.get("hook_events", {})
    base_name = Path(hook_filename).name
    if base_name in hook_events:
        return hook_events[base_name]
    if hook_filename in hook_events:
        return hook_events[hook_filename]

    # Fallback: filename-based guessing
    mapping = {
        "observation-capture.sh": "PostToolUse",
        "session-summary.sh": "Stop",
        "status-line.sh": "Stop",
        "output-style.sh": "Stop",
        "session-end.sh": "SessionEnd",
        "guard-destructive.sh": "PreToolUse",
        "quality-gate.sh": "TaskCompleted",
        "user-prompt-submit.sh": "UserPromptSubmit",
        "post-tool-use.sh": "PostToolUse",
    }
    return mapping.get(base_name, "")
