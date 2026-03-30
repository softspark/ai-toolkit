#!/usr/bin/env python3
"""AI Toolkit Skill Evaluation.

Validates all skills against the Agent Skills standard.
Checks frontmatter fields, naming, classification, reference links,
template directories, and dependency resolution.

Usage:
  evaluate_skills.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import frontmatter_block, frontmatter_field, skills_dir

# Deprecated frontmatter fields and their replacements
_DEPRECATED_FIELDS: list[tuple[str, str]] = [
    ("version", "deprecated 'version' field in frontmatter"),
    ("color", "deprecated 'color' field in frontmatter"),
    ("tools", "deprecated 'tools' field (use 'allowed-tools')"),
    ("delegate-agent", "deprecated 'delegate-agent' field (rename to 'agent:')"),
    ("run-mode", "deprecated 'run-mode' field (rename to 'context:')"),
]


def _fm_has(fm_text: str, field: str) -> bool:
    """Check if frontmatter text contains a field line."""
    return any(
        line.startswith(f"{field}:")
        for line in fm_text.splitlines()
    )


def _fm_value(fm_text: str, field: str) -> str:
    """Extract a field value from raw frontmatter text."""
    for line in fm_text.splitlines():
        if line.startswith(f"{field}:"):
            val = line[len(field) + 1:].strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
            return val
    return ""


def _check_frontmatter_fields(fm: str, skill_path: Path, line_count: int) -> list[str]:
    """Check required fields, name format, description, line count, and deprecated fields."""
    issues: list[str] = []

    if not _fm_has(fm, "name"):
        issues.append("missing name field")
    if not _fm_has(fm, "description"):
        issues.append("missing description field")

    name_value = _fm_value(fm, "name")
    if name_value:
        if len(name_value) > 64:
            issues.append(f"name exceeds 64 chars ({len(name_value)})")
        if re.search(r"[^a-z0-9-]", name_value):
            issues.append(f"name has invalid chars: {name_value}")

    desc_value = _fm_value(fm, "description")
    if desc_value and re.match(r"^(I |You |We )", desc_value):
        issues.append("description not in third person")

    if line_count > 500:
        issues.append(f"SKILL.md has {line_count} lines (max: 500)")

    for field, message in _DEPRECATED_FIELDS:
        if _fm_has(fm, field):
            issues.append(message)

    return issues


def _check_references_and_templates(skill_path: Path, content: str) -> list[str]:
    """Check reference links, orphan files, and template directories."""
    issues: list[str] = []

    ref_dir = skill_path / "reference"
    if ref_dir.is_dir():
        for match in re.finditer(r"\(reference/([^)]+)\)", content):
            ref_link = match.group(0).strip("()")
            if not (skill_path / ref_link).is_file():
                issues.append(f"broken reference link: {ref_link}")
        for ref_file in sorted(ref_dir.glob("*.md")):
            if f"reference/{ref_file.name}" not in content:
                issues.append(f"orphan reference file: reference/{ref_file.name}")

    tmpl_dir = skill_path / "templates"
    if tmpl_dir.is_dir():
        tmpl_files = [f for f in tmpl_dir.rglob("*") if f.is_file()]
        if not tmpl_files:
            issues.append("empty templates/ directory")

    return issues


def _determine_type_label(fm: str) -> str:
    """Determine skill type from frontmatter fields."""
    has_disable = _fm_has(fm, "disable-model-invocation") and "true" in _fm_value(fm, "disable-model-invocation")
    has_user_invocable_false = _fm_has(fm, "user-invocable") and "false" in _fm_value(fm, "user-invocable")

    if has_disable:
        return "task"
    elif has_user_invocable_false:
        return "knowledge"
    return "hybrid"


def _evaluate_skill(skill_path: Path) -> tuple[str, list[str]]:
    """Evaluate a single skill directory.

    Returns:
        (type_label, issues) where type_label is "task", "knowledge", or "hybrid"
        and issues is a list of problem descriptions (empty if passing).
    """
    skill_file = skill_path / "SKILL.md"

    if not skill_file.is_file():
        return ("unknown", ["Missing SKILL.md"])

    fm = frontmatter_block(skill_file)
    content = skill_file.read_text(encoding="utf-8")
    line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

    issues = _check_frontmatter_fields(fm, skill_path, line_count)
    issues.extend(_check_references_and_templates(skill_path, content))

    return (_determine_type_label(fm), issues)


def _evaluate_all_skills() -> tuple[int, int, int, int, int]:
    """Evaluate all skills and print per-skill results.

    Returns (total, pass_count, fail_count, task_count, knowledge_count).
    """
    pass_count = 0
    fail_count = 0
    total = 0
    task_count = 0
    knowledge_count = 0

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("_"):
            continue
        total += 1
        skill_file = skill_path / "SKILL.md"

        if not skill_file.is_file():
            print(f"FAIL: {skill_path.name} - Missing SKILL.md")
            fail_count += 1
            continue

        content = skill_file.read_text(encoding="utf-8")
        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

        type_label, issues = _evaluate_skill(skill_path)

        if issues:
            print(f"FAIL: {skill_path.name} ({line_count} lines)")
            for issue in issues:
                print(f"  {issue}")
            print()
            fail_count += 1
        else:
            print(f"PASS: {skill_path.name} ({type_label}, {line_count} lines)")
            pass_count += 1

        if type_label == "task":
            task_count += 1
        elif type_label == "knowledge":
            knowledge_count += 1

    return total, pass_count, fail_count, task_count, knowledge_count


def _collect_quality_metrics() -> tuple[int, int, int, int, int, int]:
    """Collect quality metrics across all skills.

    Returns (ref_count, tmpl_count, inject_count, over500, depends_count, orphan_deps).
    """
    ref_count = sum(1 for _ in skills_dir.rglob("reference/*.md"))
    tmpl_count = sum(1 for _ in skills_dir.rglob("templates/*") if _.is_file())

    inject_count = 0
    over500 = 0
    depends_count = 0
    orphan_deps = 0

    for sf in skills_dir.glob("*/SKILL.md"):
        text = sf.read_text(encoding="utf-8")
        lc = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        if "!`" in text:
            inject_count += 1
        if lc > 500:
            over500 += 1
        fm = frontmatter_block(sf)
        dep_line = _fm_value(fm, "depends-on")
        if dep_line:
            depends_count += 1
            for dep in dep_line.split(","):
                dep = dep.strip()
                if not dep:
                    continue
                if not (skills_dir / dep / "SKILL.md").is_file():
                    orphan_deps += 1

    return ref_count, tmpl_count, inject_count, over500, depends_count, orphan_deps


def main() -> None:
    """Run evaluation across all skills and print report."""
    print("AI Toolkit Skill Evaluation")
    print("================================")
    print()

    if not skills_dir.is_dir():
        print("No skills directory found.")
        sys.exit(1)

    total, pass_count, fail_count, task_count, knowledge_count = _evaluate_all_skills()
    hybrid_count = total - task_count - knowledge_count

    print()
    print("================================")
    print(f"Total: {total} skills")
    print(f"Pass:  {pass_count}")
    print(f"Fail:  {fail_count}")
    print()

    print("Classification:")
    print(f"  Task:      {task_count}")
    print(f"  Hybrid:    {hybrid_count}")
    print(f"  Knowledge: {knowledge_count}")
    print()

    ref_count, tmpl_count, inject_count, over500, depends_count, orphan_deps = _collect_quality_metrics()

    print("Quality Metrics:")
    print(f"  Reference files:        {ref_count}")
    print(f"  Template files:         {tmpl_count}")
    print(f"  Dynamic injection:      {inject_count} skills")
    print(f"  Over 500 lines:         {over500}")
    print(f"  Skills with depends-on: {depends_count}")
    print(f"  Orphan dependencies:    {orphan_deps}")
    print()

    if fail_count > 0:
        print("EVALUATION: ISSUES FOUND")
        sys.exit(1)
    else:
        print("EVALUATION: ALL SKILLS PASS")


if __name__ == "__main__":
    main()
