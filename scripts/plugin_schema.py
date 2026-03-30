"""Plugin manifest schema validation.

Single source of truth for validating plugin.json manifests.
Used by both validate.py and plugin.py.

Stdlib-only.
"""
from __future__ import annotations

from pathlib import Path


# Required top-level fields
REQUIRED_FIELDS = ("name", "description", "version", "domain", "type", "status")

# Valid status values
VALID_STATUSES = frozenset({"stable", "experimental", "deprecated"})

# Valid plugin types
VALID_TYPES = frozenset({"behavioral", "language", "domain", "integration"})

# Valid hook event names (must match validate.py VALID_HOOK_EVENTS)
VALID_HOOK_EVENTS = frozenset({
    "SessionStart", "Notification", "PreToolUse", "PostToolUse", "Stop",
    "PreCompact", "SubagentStop", "UserPromptSubmit", "TaskCompleted",
    "TeammateIdle", "SubagentStart", "SessionEnd", "PermissionRequest", "Setup",
})


def validate_manifest(data: dict, pack_dir: Path | None = None) -> list[str]:
    """Validate a plugin manifest dict.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in data or not data[field]:
            errors.append(f"Missing required field: {field}")

    # Validate status
    status = data.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(f"Invalid status '{status}' (valid: {', '.join(sorted(VALID_STATUSES))})")

    # Validate includes structure
    includes = data.get("includes")
    if includes is None:
        errors.append("Missing 'includes' field")
    elif not isinstance(includes, dict):
        errors.append("'includes' must be a dictionary")
    else:
        for key in ("agents", "skills", "rules", "hooks"):
            val = includes.get(key, [])
            if not isinstance(val, list):
                errors.append(f"includes.{key} must be a list")

    # Validate hook_events if present
    hook_events = data.get("hook_events", {})
    if hook_events:
        if not isinstance(hook_events, dict):
            errors.append("'hook_events' must be a dictionary mapping hook filenames to event names")
        else:
            for hook_file, event in hook_events.items():
                if event not in VALID_HOOK_EVENTS:
                    errors.append(f"hook_events['{hook_file}']: invalid event '{event}'")

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


def validate_references(
    data: dict,
    agents_dir: Path,
    skills_dir: Path,
) -> list[str]:
    """Validate that referenced agents and skills exist.

    Returns a list of error messages.
    """
    errors: list[str] = []
    includes = data.get("includes", {})

    for agent in includes.get("agents", []):
        if not (agents_dir / f"{agent}.md").is_file():
            errors.append(f"References missing agent: {agent}")

    for skill in includes.get("skills", []):
        if not (skills_dir / skill / "SKILL.md").is_file():
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
