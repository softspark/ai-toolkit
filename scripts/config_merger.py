#!/usr/bin/env python3
"""Config merger for ai-toolkit extends system.

Implements layered deep merge with:
- Constitution immutability (Articles I-VI absolute, base articles immutable)
- Agent merge with requiredAgents enforcement
- Override validation (override:true + justification required)
- enforce block constraints (minHookProfile, requiredPlugins, forbidOverride, requiredAgents)

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMMUTABLE_ARTICLES = frozenset({1, 2, 3, 4, 5, 6})

HOOK_PROFILE_ORDER = {"minimal": 0, "standard": 1, "strict": 2}

# v1 schema fields that participate in merge
V1_FIELDS = frozenset({
    "$schema", "extends", "name", "version", "description",
    "profile", "agents", "rules", "constitution", "enforce", "overrides",
})


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigMergeError(Exception):
    """Raised when config merge fails due to constraint violation."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MergeResult:
    """Result of merging configs."""

    merged: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    overrides_applied: list[dict[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def merge_config_chain(
    base_configs: list[dict[str, Any]],
    project_config: dict[str, Any],
) -> MergeResult:
    """Merge an ordered chain of base configs with a project config.

    Args:
        base_configs: Ordered list of base config dicts (deepest ancestor first).
        project_config: The project-level .softspark-toolkit.json data.

    Returns:
        MergeResult with the final merged config.

    Raises:
        ConfigMergeError: On constraint violations.
    """
    result = MergeResult(merged={})

    # Layer base configs (deepest ancestor → most immediate parent)
    accumulated_base: dict[str, Any] = {}
    for base in base_configs:
        accumulated_base = _deep_merge(accumulated_base, base)

    # Merge project over accumulated base
    result.merged = _merge_project_over_base(accumulated_base, project_config, result)

    # Validate enforce constraints
    _validate_enforce(accumulated_base, result.merged)

    return result


def merge_two(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Simple two-config merge (base → overlay). No enforcement validation."""
    return _deep_merge(base, overlay)


# ---------------------------------------------------------------------------
# Internal: project-over-base merge (with enforcement)
# ---------------------------------------------------------------------------

def _merge_project_over_base(
    base: dict[str, Any],
    project: dict[str, Any],
    result: MergeResult,
) -> dict[str, Any]:
    """Merge project config over base with special handling for key sections."""
    merged: dict[str, Any] = {}

    all_keys = set(base.keys()) | set(project.keys())

    for key in all_keys:
        # Skip meta fields that don't participate in merge output
        if key in ("$schema", "extends", "name", "version", "description"):
            # Project values win for metadata
            merged[key] = project.get(key) or base.get(key)
            continue

        base_val = base.get(key)
        proj_val = project.get(key)

        if proj_val is None:
            merged[key] = base_val
        elif key == "overrides":
            # Always validate overrides against base enforce, even if base has no overrides
            merged[key] = _validate_overrides(base, proj_val, result)
        elif key == "constitution" and base_val is not None:
            merged[key] = _merge_constitution(base_val, proj_val, base)
        elif base_val is None:
            merged[key] = proj_val
        elif key == "constitution":
            merged[key] = _merge_constitution(base_val, proj_val, base)
        elif key == "agents":
            merged[key] = _merge_agents(base_val, proj_val, base)
        elif key == "rules":
            merged[key] = _merge_rules(base_val, proj_val)
        elif key == "overrides":
            merged[key] = _validate_overrides(base, proj_val, result)
        elif key == "enforce":
            # enforce blocks merge: base wins (projects cannot weaken enforcement)
            merged[key] = _merge_enforce(base_val, proj_val)
        elif key == "profile":
            merged[key] = proj_val  # project can change profile
        elif isinstance(base_val, dict) and isinstance(proj_val, dict):
            merged[key] = _deep_merge(base_val, proj_val)
        elif isinstance(base_val, list) and isinstance(proj_val, list):
            merged[key] = _merge_lists(base_val, proj_val)
        else:
            merged[key] = proj_val  # scalar: project wins

    return merged


# ---------------------------------------------------------------------------
# Merge: constitution (immutability guard)
# ---------------------------------------------------------------------------

def _merge_constitution(
    base: dict[str, Any],
    project: dict[str, Any],
    full_base: dict[str, Any],
) -> dict[str, Any]:
    """Merge constitution — additions only, no modifications.

    Rules:
    1. Articles I-VI (1-6) are ABSOLUTELY immutable — toolkit core.
    2. Articles defined by base configs are immutable — projects cannot modify.
    3. Projects can ADD new articles with article numbers not in base.
    """
    base_amendments = {a["article"]: a for a in base.get("amendments", [])}
    proj_amendments = {a["article"]: a for a in project.get("amendments", [])}

    merged = dict(base_amendments)
    base_name = full_base.get("name", "base config")

    for article_num, amendment in proj_amendments.items():
        if article_num in IMMUTABLE_ARTICLES:
            raise ConfigMergeError(
                f"Cannot modify Constitution Article {article_num} — immutable.\n"
                f"Articles I-VI are defined by ai-toolkit and cannot be overridden.\n"
                f"You can ADD new articles (article 7+)."
            )
        if article_num in base_amendments:
            raise ConfigMergeError(
                f"Cannot modify Constitution Article {article_num} — "
                f"defined by base config '{base_name}'.\n"
                f"Base articles are immutable. You can ADD new articles "
                f"with a higher article number."
            )
        merged[article_num] = amendment

    return {"amendments": sorted(merged.values(), key=lambda a: a["article"])}


# ---------------------------------------------------------------------------
# Merge: agents
# ---------------------------------------------------------------------------

def _merge_agents(
    base: dict[str, Any],
    project: dict[str, Any],
    full_base: dict[str, Any],
) -> dict[str, Any]:
    """Merge agent configs — project can enable/disable but not remove base-required."""
    merged_enabled = set(base.get("enabled", []))
    required_agents = set(full_base.get("enforce", {}).get("requiredAgents", []))

    # Project can add agents
    merged_enabled.update(project.get("enabled", []))

    # Project can disable agents (unless base enforces them)
    for agent in project.get("disabled", []):
        if agent in required_agents:
            raise ConfigMergeError(
                f"Cannot disable agent '{agent}' — required by base config "
                f"'{full_base.get('name', 'unknown')}'.\n"
                f"Required agents: {', '.join(sorted(required_agents))}\n"
                f"Contact your team lead to request an exemption."
            )
        merged_enabled.discard(agent)

    return {
        "enabled": sorted(merged_enabled),
        "disabled": sorted(set(project.get("disabled", [])) - required_agents),
        "custom": base.get("custom", []) + project.get("custom", []),
    }


# ---------------------------------------------------------------------------
# Merge: rules
# ---------------------------------------------------------------------------

def _merge_rules(
    base: dict[str, Any],
    project: dict[str, Any],
) -> dict[str, Any]:
    """Merge rules — union inject lists, apply removals."""
    base_inject = set(base.get("inject", []))
    proj_inject = set(project.get("inject", []))
    proj_remove = set(project.get("remove", []))

    merged_inject = (base_inject | proj_inject) - proj_remove

    return {
        "inject": sorted(merged_inject),
        "remove": sorted(proj_remove),
    }


# ---------------------------------------------------------------------------
# Merge: enforce
# ---------------------------------------------------------------------------

def _merge_enforce(
    base: dict[str, Any],
    project: dict[str, Any],
) -> dict[str, Any]:
    """Merge enforce blocks — base constraints cannot be weakened, only strengthened."""
    merged: dict[str, Any] = dict(base)

    # minHookProfile: take the stricter one
    base_profile = base.get("minHookProfile", "minimal")
    proj_profile = project.get("minHookProfile", "minimal")
    base_level = HOOK_PROFILE_ORDER.get(base_profile, 0)
    proj_level = HOOK_PROFILE_ORDER.get(proj_profile, 0)
    merged["minHookProfile"] = proj_profile if proj_level >= base_level else base_profile

    # Lists: union (project can add, not remove)
    for list_key in ("requiredPlugins", "forbidOverride", "requiredAgents"):
        base_list = set(base.get(list_key, []))
        proj_list = set(project.get(list_key, []))
        merged[list_key] = sorted(base_list | proj_list)

    return merged


# ---------------------------------------------------------------------------
# Override validation
# ---------------------------------------------------------------------------

def _validate_overrides(
    base: dict[str, Any],
    overrides: dict[str, Any],
    result: MergeResult,
) -> dict[str, Any]:
    """Validate project overrides against base enforcement rules."""
    forbidden = set(base.get("enforce", {}).get("forbidOverride", []))

    validated: dict[str, Any] = {}

    for key, override in overrides.items():
        # Check if component is a nested dict with override/justification
        if not isinstance(override, dict):
            raise ConfigMergeError(
                f"Override for '{key}' must be an object with 'override' and 'justification' fields."
            )

        if key in forbidden:
            raise ConfigMergeError(
                f"Cannot override '{key}' — forbidden by base config "
                f"'{base.get('name', 'unknown')}'.\n"
                f"Forbidden overrides: {', '.join(sorted(forbidden))}\n"
                f"Contact your team lead to request an exemption."
            )

        if not override.get("override"):
            raise ConfigMergeError(
                f"Override for '{key}' requires explicit 'override: true'.\n"
                f"This ensures intentional deviation from organizational defaults."
            )

        justification = override.get("justification", "")
        if not justification or len(justification) < 20:
            raise ConfigMergeError(
                f"Override for '{key}' requires a 'justification' field (min 20 chars).\n"
                f"Got: '{justification}' ({len(justification)} chars)\n"
                f"Example: \"Company uses custom lint pipeline via Jenkins\""
            )

        validated[key] = override
        result.overrides_applied.append({
            "key": key,
            "action": override.get("replacement", "custom"),
            "justification": justification,
        })

    return validated


# ---------------------------------------------------------------------------
# Enforce validation (post-merge)
# ---------------------------------------------------------------------------

def _validate_enforce(
    base: dict[str, Any],
    merged: dict[str, Any],
) -> None:
    """Validate that the merged config satisfies base enforce constraints."""
    enforce = base.get("enforce", {})
    if not enforce:
        return

    errors: list[str] = []

    # minHookProfile
    min_profile = enforce.get("minHookProfile")
    if min_profile:
        merged_profile = merged.get("profile", "standard")
        # Map profiles to hook profile levels
        profile_to_hook = {
            "minimal": "minimal",
            "standard": "standard",
            "strict": "strict",
            "full": "strict",
            "offline-slm": "minimal",
        }
        merged_hook = profile_to_hook.get(merged_profile, "standard")
        min_level = HOOK_PROFILE_ORDER.get(min_profile, 0)
        merged_level = HOOK_PROFILE_ORDER.get(merged_hook, 1)
        if merged_level < min_level:
            errors.append(
                f"Profile '{merged_profile}' (hook level: {merged_hook}) "
                f"is below minimum '{min_profile}' required by base config."
            )

    # requiredPlugins — deferred to v2 (plugins field not in v1)

    # requiredAgents
    required_agents = set(enforce.get("requiredAgents", []))
    if required_agents:
        enabled_agents = set(merged.get("agents", {}).get("enabled", []))
        missing = required_agents - enabled_agents
        if missing:
            errors.append(
                f"Required agents missing: {', '.join(sorted(missing))}.\n"
                f"These agents are required by the base config and cannot be disabled."
            )

    if errors:
        raise ConfigMergeError(
            "Enforce constraint violations:\n" + "\n".join(f"  - {e}" for e in errors)
        )


# ---------------------------------------------------------------------------
# Generic merge helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Generic deep merge: overlay wins for scalars, recurse for dicts, union for lists."""
    merged: dict[str, Any] = {}

    for key in set(base.keys()) | set(overlay.keys()):
        base_val = base.get(key)
        over_val = overlay.get(key)

        if over_val is None:
            merged[key] = base_val
        elif base_val is None:
            merged[key] = over_val
        elif isinstance(base_val, dict) and isinstance(over_val, dict):
            merged[key] = _deep_merge(base_val, over_val)
        elif isinstance(base_val, list) and isinstance(over_val, list):
            merged[key] = _merge_lists(base_val, over_val)
        else:
            merged[key] = over_val  # overlay wins

    return merged


def _merge_lists(base: list[Any], overlay: list[Any]) -> list[Any]:
    """Merge two lists: union, preserving order (base first, then new from overlay)."""
    seen = set()
    result: list[Any] = []
    for item in base + overlay:
        # For unhashable items (dicts), use json repr
        key = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# CLI entry point (for testing)
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI: merge base + project config and print result."""
    if len(sys.argv) < 3:
        print("Usage: config_merger.py <base-config.json> <project-config.json>", file=sys.stderr)
        sys.exit(1)

    base_path = Path(sys.argv[1])
    project_path = Path(sys.argv[2])

    with open(base_path) as f:
        base = json.load(f)
    with open(project_path) as f:
        project = json.load(f)

    try:
        result = merge_config_chain([base], project)
        print(json.dumps({
            "merged": result.merged,
            "warnings": result.warnings,
            "overrides_applied": result.overrides_applied,
        }, indent=2))
    except ConfigMergeError as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
