# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""Scope language knowledge skills to the stacks a user actually works in.

The global install symlinks every ``<lang>-rules`` / ``<lang>-patterns``
skill into ``~/.claude/skills``. Each one's description then sits in the
model-visible skill listing of every session, whether or not the user has a
single project in that language. This step reads the languages detected
across the registered projects (``projects.json``) and turns the others off
through Claude Code's ``skillOverrides`` setting.

Rules of engagement:

* Evidence first. With no registered project on disk there is nothing to
  judge, so nothing is disabled.
* Only entries this step wrote are ever removed again. They are tracked in
  ``state.json`` under ``managed_skill_overrides``; a user's own override is
  left alone even when it names a language skill.
* ``--language-skills all`` restores every managed entry and persists the
  choice so later ``install`` / ``update`` runs do not prune again.
* Reversible by hand: delete the key from ``~/.claude/settings.json``.

Stdlib-only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from install_steps.detect_language import detect_languages
from install_steps.install_state import load_state, save_state
from install_steps.project_registry import load_registry

LANGUAGE_SKILL_SUFFIXES = ("rules", "patterns")
SCOPE_ALL = "all"
SCOPE_DETECTED = "detected"
VALID_SCOPES = (SCOPE_ALL, SCOPE_DETECTED)
STATE_SCOPE_KEY = "language_skill_scope"
STATE_MANAGED_KEY = "managed_skill_overrides"


def language_skill_names(toolkit_dir: Path) -> dict[str, str]:
    """Map each shipped language knowledge skill to its language.

    A skill counts as a language skill when it is named ``<lang>-rules`` or
    ``<lang>-patterns`` and ``app/rules/<lang>/`` exists. ``flutter-patterns``
    therefore does not (no ``app/rules/flutter``), which is deliberate:
    only skills generated from a language rule set are scoped.
    """
    rules_root = toolkit_dir / "app" / "rules"
    skills_root = toolkit_dir / "app" / "skills"
    if not rules_root.is_dir() or not skills_root.is_dir():
        return {}
    languages = {p.name for p in rules_root.iterdir() if p.is_dir() and p.name != "common"}
    mapping: dict[str, str] = {}
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir() or "-" not in skill_dir.name:
            continue
        lang, _, suffix = skill_dir.name.rpartition("-")
        if suffix in LANGUAGE_SKILL_SUFFIXES and lang in languages:
            mapping[skill_dir.name] = lang
    return mapping


def detected_languages_from_registry(toolkit_dir: Path) -> set[str] | None:
    """Union of languages detected across registered projects that still exist.

    Returns ``None`` when no registered project directory exists, which
    callers must read as "no evidence", not "no languages".
    """
    found: set[str] = set()
    seen_project = False
    for entry in load_registry():
        path = entry.get("path")
        if not isinstance(path, str):
            continue
        project_dir = Path(path)
        if not project_dir.is_dir():
            continue
        seen_project = True
        for module in detect_languages(project_dir, toolkit_dir):
            if module.startswith("rules-") and module != "rules-common":
                found.add(module[len("rules-"):])
    return found if seen_project else None


def _load_settings(settings_path: Path) -> dict[str, Any]:
    if not settings_path.is_file():
        return {}
    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_settings(settings_path: Path, data: dict[str, Any]) -> None:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
        f.write("\n")


def resolve_scope(requested: str, state: dict[str, Any] | None = None) -> str:
    """Pick the effective scope: explicit flag wins, else the persisted choice."""
    if requested in VALID_SCOPES:
        return requested
    persisted = (state if state is not None else load_state()).get(STATE_SCOPE_KEY)
    return persisted if persisted in VALID_SCOPES else SCOPE_DETECTED


def reconcile_language_skill_overrides(
    toolkit_dir: Path,
    settings_path: Path,
    *,
    scope: str,
    dry_run: bool = False,
) -> tuple[list[str], list[str]]:
    """Bring ``skillOverrides`` in line with the detected language set.

    Returns ``(disabled, restored)`` skill names. Prints one line per
    outcome in the install's ``  Verb: detail`` style.
    """
    state = load_state()
    managed: set[str] = {
        name for name in state.get(STATE_MANAGED_KEY, []) if isinstance(name, str)
    }
    skills = language_skill_names(toolkit_dir)
    settings = _load_settings(settings_path)
    overrides = settings.get("skillOverrides")
    if not isinstance(overrides, dict):
        overrides = {}

    disabled: list[str] = []
    restored: list[str] = []

    if scope == SCOPE_ALL:
        languages: set[str] | None = None
    else:
        languages = detected_languages_from_registry(toolkit_dir)

    for name, lang in sorted(skills.items()):
        keep_on = languages is None or lang in languages
        if keep_on:
            if name in managed and overrides.get(name) == "off":
                overrides.pop(name)
                restored.append(name)
            managed.discard(name)
            continue
        if name in overrides:
            # The user (or an earlier run) already has an opinion; a run never
            # adopts an entry it did not write.
            continue
        overrides[name] = "off"
        managed.add(name)
        disabled.append(name)

    if dry_run:
        if languages is None and scope != SCOPE_ALL:
            print("  Would skip: language skill scoping (no registered project on disk)")
        for name in disabled:
            print(f"  Would disable: skill {name} (skillOverrides)")
        for name in restored:
            print(f"  Would restore: skill {name} (skillOverrides)")
        return disabled, restored

    if disabled or restored:
        if overrides:
            settings["skillOverrides"] = overrides
        else:
            settings.pop("skillOverrides", None)
        _save_settings(settings_path, settings)
    save_state({STATE_SCOPE_KEY: scope, STATE_MANAGED_KEY: sorted(managed)})

    if languages is None and scope != SCOPE_ALL:
        print("  Skipped: language skill scoping (no registered project on disk; run install --local in a project first)")
    elif disabled:
        print(f"  Disabled: {len(disabled)} language skill(s) outside your detected stacks "
              f"({', '.join(disabled)})")
    if restored:
        print(f"  Restored: {len(restored)} language skill(s) ({', '.join(restored)})")
    if languages is not None and not disabled and not restored and scope == SCOPE_DETECTED:
        print(f"  Language skills: scoped to {', '.join(sorted(languages)) or 'no detected languages'} (no change)")
    return disabled, restored
