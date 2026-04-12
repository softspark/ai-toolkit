#!/usr/bin/env python3
"""Config validator for ai-toolkit extends system.

Validates .softspark-toolkit.json against schema, checks enforce constraints,
verifies constitution integrity, and validates referenced files exist.

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PROFILES = {"minimal", "standard", "strict", "full", "offline-slm"}
VALID_HOOK_PROFILES = {"minimal", "standard", "strict"}
HOOK_PROFILE_ORDER = {"minimal": 0, "standard": 1, "strict": 2}
IMMUTABLE_ARTICLES = frozenset({1, 2, 3, 4, 5})
MIN_JUSTIFICATION_LEN = 20


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("\n".join(errors))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_project_config(
    config: dict[str, Any],
    project_root: Path | None = None,
) -> list[str]:
    """Validate a project-level .softspark-toolkit.json.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    # Schema validation (structural)
    _validate_schema(config, errors)

    # File existence checks
    if project_root:
        _validate_file_references(config, project_root, errors)

    return errors


def validate_base_config(
    config: dict[str, Any],
    config_root: Path | None = None,
) -> list[str]:
    """Validate a base ai-toolkit.config.json.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []

    # Base configs should have name and version
    if not config.get("name"):
        errors.append("Base config missing required field 'name'.")
    if not config.get("version"):
        errors.append("Base config missing required field 'version'.")

    # Schema validation
    _validate_schema(config, errors)

    # Enforce block validation
    _validate_enforce_block(config.get("enforce", {}), errors)

    # File existence checks
    if config_root:
        _validate_file_references(config, config_root, errors)

    return errors


def validate_merged_config(
    merged: dict[str, Any],
    base: dict[str, Any],
) -> list[str]:
    """Validate a merged config against base enforce constraints.

    Returns list of error strings (empty = valid).
    """
    errors: list[str] = []
    enforce = base.get("enforce", {})

    if not enforce:
        return errors

    _validate_enforce_constraints(merged, enforce, errors)

    return errors


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def _validate_schema(config: dict[str, Any], errors: list[str]) -> None:
    """Validate structural correctness of config."""

    # extends: must be string if present
    extends = config.get("extends")
    if extends is not None and not isinstance(extends, str):
        errors.append(f"'extends' must be a string, got {type(extends).__name__}.")
    if isinstance(extends, str) and not extends.strip():
        errors.append("'extends' cannot be empty string.")

    # profile: must be valid enum
    profile = config.get("profile")
    if profile is not None and profile not in VALID_PROFILES:
        errors.append(
            f"Invalid profile '{profile}'. Valid: {', '.join(sorted(VALID_PROFILES))}."
        )

    # agents: structural check
    agents = config.get("agents")
    if agents is not None:
        _validate_agents_block(agents, errors)

    # rules: structural check
    rules = config.get("rules")
    if rules is not None:
        _validate_rules_block(rules, errors)

    # constitution: structural check
    constitution = config.get("constitution")
    if constitution is not None:
        _validate_constitution_block(constitution, errors)

    # enforce: structural check
    enforce = config.get("enforce")
    if enforce is not None:
        _validate_enforce_block(enforce, errors)

    # overrides: structural check
    overrides = config.get("overrides")
    if overrides is not None:
        _validate_overrides_block(overrides, errors)


def _validate_agents_block(agents: Any, errors: list[str]) -> None:
    """Validate agents section structure."""
    if not isinstance(agents, dict):
        errors.append("'agents' must be an object.")
        return

    valid_keys = {"enabled", "disabled", "custom"}
    unknown = set(agents.keys()) - valid_keys
    if unknown:
        errors.append(f"Unknown keys in 'agents': {', '.join(sorted(unknown))}.")

    for key in ("enabled", "disabled", "custom"):
        val = agents.get(key)
        if val is not None:
            if not isinstance(val, list):
                errors.append(f"'agents.{key}' must be an array.")
            elif not all(isinstance(item, str) for item in val):
                errors.append(f"'agents.{key}' items must be strings.")


def _validate_rules_block(rules: Any, errors: list[str]) -> None:
    """Validate rules section structure."""
    if not isinstance(rules, dict):
        errors.append("'rules' must be an object.")
        return

    valid_keys = {"inject", "remove"}
    unknown = set(rules.keys()) - valid_keys
    if unknown:
        errors.append(f"Unknown keys in 'rules': {', '.join(sorted(unknown))}.")

    for key in ("inject", "remove"):
        val = rules.get(key)
        if val is not None:
            if not isinstance(val, list):
                errors.append(f"'rules.{key}' must be an array.")
            elif not all(isinstance(item, str) for item in val):
                errors.append(f"'rules.{key}' items must be strings.")


def _validate_constitution_block(constitution: Any, errors: list[str]) -> None:
    """Validate constitution section structure."""
    if not isinstance(constitution, dict):
        errors.append("'constitution' must be an object.")
        return

    amendments = constitution.get("amendments")
    if amendments is None:
        return
    if not isinstance(amendments, list):
        errors.append("'constitution.amendments' must be an array.")
        return

    seen_articles: set[int] = set()
    for i, amendment in enumerate(amendments):
        if not isinstance(amendment, dict):
            errors.append(f"'constitution.amendments[{i}]' must be an object.")
            continue

        article = amendment.get("article")
        if not isinstance(article, int) or article < 1:
            errors.append(f"'constitution.amendments[{i}].article' must be a positive integer.")
            continue

        if article in seen_articles:
            errors.append(f"Duplicate constitution article number: {article}.")
        seen_articles.add(article)

        if not amendment.get("title"):
            errors.append(f"'constitution.amendments[{i}].title' is required.")
        if not amendment.get("text"):
            errors.append(f"'constitution.amendments[{i}].text' is required.")


def _validate_enforce_block(enforce: Any, errors: list[str]) -> None:
    """Validate enforce section structure."""
    if not isinstance(enforce, dict):
        errors.append("'enforce' must be an object.")
        return

    valid_keys = {"minHookProfile", "requiredPlugins", "forbidOverride", "requiredAgents"}
    unknown = set(enforce.keys()) - valid_keys
    if unknown:
        errors.append(f"Unknown keys in 'enforce': {', '.join(sorted(unknown))}.")

    min_profile = enforce.get("minHookProfile")
    if min_profile is not None and min_profile not in VALID_HOOK_PROFILES:
        errors.append(
            f"Invalid minHookProfile '{min_profile}'. "
            f"Valid: {', '.join(sorted(VALID_HOOK_PROFILES))}."
        )

    for key in ("requiredPlugins", "forbidOverride", "requiredAgents"):
        val = enforce.get(key)
        if val is not None:
            if not isinstance(val, list):
                errors.append(f"'enforce.{key}' must be an array.")
            elif not all(isinstance(item, str) for item in val):
                errors.append(f"'enforce.{key}' items must be strings.")


def _validate_overrides_block(overrides: Any, errors: list[str]) -> None:
    """Validate overrides section structure."""
    if not isinstance(overrides, dict):
        errors.append("'overrides' must be an object.")
        return

    for key, override in overrides.items():
        if not isinstance(override, dict):
            errors.append(f"'overrides.{key}' must be an object.")
            continue

        if not override.get("override"):
            errors.append(f"'overrides.{key}' missing 'override: true'.")

        justification = override.get("justification", "")
        if not justification or len(justification) < MIN_JUSTIFICATION_LEN:
            errors.append(
                f"'overrides.{key}.justification' too short "
                f"({len(justification)} chars, min {MIN_JUSTIFICATION_LEN})."
            )


# ---------------------------------------------------------------------------
# Enforce constraint validation (post-merge)
# ---------------------------------------------------------------------------

def _validate_enforce_constraints(
    merged: dict[str, Any],
    enforce: dict[str, Any],
    errors: list[str],
) -> None:
    """Check merged config against enforce constraints."""

    # minHookProfile
    min_profile = enforce.get("minHookProfile")
    if min_profile:
        profile_to_hook = {
            "minimal": "minimal",
            "standard": "standard",
            "strict": "strict",
            "full": "strict",
            "offline-slm": "minimal",
        }
        merged_profile = merged.get("profile", "standard")
        merged_hook = profile_to_hook.get(merged_profile, "standard")
        if HOOK_PROFILE_ORDER.get(merged_hook, 1) < HOOK_PROFILE_ORDER.get(min_profile, 0):
            errors.append(
                f"Profile '{merged_profile}' (hook: {merged_hook}) "
                f"below minimum '{min_profile}'."
            )

    # requiredAgents
    required = set(enforce.get("requiredAgents", []))
    if required:
        enabled = set(merged.get("agents", {}).get("enabled", []))
        missing = required - enabled
        if missing:
            errors.append(f"Required agents missing: {', '.join(sorted(missing))}.")

    # requiredPlugins — informational in v1 (plugins field deferred)
    required_plugins = enforce.get("requiredPlugins", [])
    if required_plugins:
        # v1: just warn, no plugins field to check against
        pass


# ---------------------------------------------------------------------------
# File reference validation
# ---------------------------------------------------------------------------

def _validate_file_references(
    config: dict[str, Any],
    root: Path,
    errors: list[str],
) -> None:
    """Check that referenced files actually exist."""

    # Custom agents
    for agent_path in config.get("agents", {}).get("custom", []):
        full = root / agent_path
        if not full.is_file():
            errors.append(f"Custom agent file not found: {agent_path} (resolved: {full})")

    # Rule files
    for rule_path in config.get("rules", {}).get("inject", []):
        full = root / rule_path
        if not full.is_file():
            errors.append(f"Rule file not found: {rule_path} (resolved: {full})")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI: validate .softspark-toolkit.json and print results."""
    if len(sys.argv) < 2:
        print("Usage: config_validator.py <config.json> [--strict]", file=sys.stderr)
        sys.exit(1)

    config_path = Path(sys.argv[1])
    strict = "--strict" in sys.argv

    try:
        with open(config_path) as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"valid": False, "errors": [str(e)]}))
        sys.exit(1)

    project_root = config_path.parent
    is_base = "name" in config and "version" in config

    if is_base:
        errors = validate_base_config(config, project_root)
    else:
        errors = validate_project_config(config, project_root)

    if errors:
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        if strict:
            sys.exit(1)
        print(json.dumps({"valid": False, "errors": errors}))
    else:
        print(json.dumps({"valid": True, "errors": []}))


if __name__ == "__main__":
    main()
