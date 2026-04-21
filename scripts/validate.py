#!/usr/bin/env python3
"""AI Toolkit Validator.

Checks all agent and skill files for correctness, validates hook events,
planned assets, plugin packs, KB documents, metadata contracts, and
content quality.

Usage:
    python3 scripts/validate.py [--strict] [toolkit-dir]

Exit codes:
    0  validation passed
    1  validation failed (errors found, or warnings in --strict mode)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir as default_toolkit_dir, frontmatter_field
from plugin_schema import validate_manifest as _validate_plugin_manifest_schema
from plugin_schema import validate_references as _validate_plugin_references


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TOOLS = frozenset({
    "Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "Agent",
    "WebSearch", "WebFetch", "TodoRead", "TodoWrite",
    "TeamCreate", "TeamDelete", "SendMessage",
    "TaskCreate", "TaskList", "TaskUpdate", "TaskGet", "TaskOutput", "TaskStop",
    "NotebookEdit", "ExitPlanMode", "EnterPlanMode",
    "ExitWorktree", "EnterWorktree", "RemoteTrigger",
})

VALID_HOOK_EVENTS = frozenset({
    "SessionStart", "Notification", "PreToolUse", "PostToolUse", "Stop",
    "PreCompact", "SubagentStop", "UserPromptSubmit", "TaskCompleted",
    "TeammateIdle", "SubagentStart", "SessionEnd", "PermissionRequest", "Setup",
})

VALID_KB_CATEGORIES = frozenset({
    "reference", "howto", "procedures", "troubleshooting", "best-practices",
    "planning",
})

PLANNED_ASSETS = [
    "app/.claude-plugin/plugin.json",
    "scripts/doctor.py",
    "scripts/benchmark_ecosystem.py",
    "scripts/harvest_ecosystem.py",
    "app/hooks/pre-compact.sh",
    "app/hooks/post-tool-use.sh",
    "app/hooks/user-prompt-submit.sh",
    "app/hooks/subagent-start.sh",
    "app/hooks/subagent-stop.sh",
    "app/hooks/session-end.sh",
    "app/hooks/track-usage.sh",
    "app/skills/hook-creator/SKILL.md",
    "app/skills/command-creator/SKILL.md",
    "app/skills/agent-creator/SKILL.md",
    "app/skills/plugin-creator/SKILL.md",
    "kb/reference/claude-ecosystem-benchmark-snapshot.md",
    "kb/reference/plugin-pack-conventions.md",
    "benchmarks/ecosystem-dashboard.json",
]

CORE_FILES = [
    "app/constitution.md",
    "app/ARCHITECTURE.md",
    "scripts/install.py",
    "app/hooks.json",
    "README.md",
]


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter_lines(filepath: Path) -> list[str]:
    """Return frontmatter lines (between --- delimiters), excluding delimiters."""
    lines: list[str] = []
    in_fm = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                if in_fm:
                    break
                in_fm = True
                continue
            if in_fm:
                lines.append(stripped)
    return lines


def _has_frontmatter(filepath: Path) -> bool:
    """Check if file starts with ---."""
    with open(filepath, encoding="utf-8") as f:
        first_line = f.readline().rstrip("\n")
    return first_line == "---"


def _fm_field(lines: list[str], field: str) -> str:
    """Extract a field value from frontmatter lines."""
    for line in lines:
        if line.startswith(f"{field}:"):
            value = line[len(field) + 1:].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            return value
    return ""


def _fm_has(lines: list[str], field: str) -> bool:
    """Check if frontmatter has a field."""
    return any(line.startswith(f"{field}:") for line in lines)


def _body_line_count(filepath: Path) -> int:
    """Count lines after the second --- delimiter."""
    count = 0
    delimiters_seen = 0
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                delimiters_seen += 1
                continue
            if delimiters_seen >= 2:
                count += 1
    return count


def _body_nonblank_count(filepath: Path) -> int:
    """Count non-blank lines after the second --- delimiter."""
    count = 0
    delimiters_seen = 0
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == "---":
                delimiters_seen += 1
                continue
            if delimiters_seen >= 2 and stripped.strip():
                count += 1
    return count


# ---------------------------------------------------------------------------
# Validation sections
# ---------------------------------------------------------------------------

class ValidationResult:
    """Accumulates errors and warnings."""

    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def error(self, msg: str) -> None:
        print(f"  ERROR: {msg}")
        self.errors += 1

    def warn(self, msg: str) -> None:
        print(f"  WARNING: {msg}")
        self.warnings += 1


def validate_agents(tk_dir: Path, vr: ValidationResult) -> int:
    """Validate agent .md files. Returns agent count."""
    print("## Agents")
    agents_dir = tk_dir / "app" / "agents"
    agent_count = 0

    if not agents_dir.is_dir():
        vr.error("app/agents directory not found")
        print()
        return 0

    for filepath in sorted(agents_dir.glob("*.md")):
        agent_count += 1
        name = filepath.stem

        if not _has_frontmatter(filepath):
            vr.error(f"{name} - Missing YAML frontmatter")
            continue

        fm_lines = _parse_frontmatter_lines(filepath)

        # Check required fields
        for field in ("name", "description", "tools", "model"):
            if not _fm_has(fm_lines, field):
                vr.error(f"{name} - Missing field: {field}")

        # Check skill references exist
        skills_val = _fm_field(fm_lines, "skills")
        if skills_val:
            for skill in (s.strip() for s in skills_val.split(",")):
                if not skill:
                    continue
                if not (tk_dir / "app" / "skills" / skill / "SKILL.md").is_file():
                    vr.warn(f"{name} - References non-existent skill: {skill}")

        # Check tool names against whitelist
        tools_val = _fm_field(fm_lines, "tools")
        if tools_val:
            for tool in (t.strip() for t in tools_val.split(",")):
                if not tool:
                    continue
                if tool not in VALID_TOOLS:
                    vr.warn(f"agent/{name}.md: unknown tool '{tool}' (not a standard Claude Code tool)")

    print(f"  Found: {agent_count} agents")
    print()
    return agent_count


def _validate_skill_frontmatter(tk_dir: Path, skill_path: Path,
                                fm_lines: list[str], vr: ValidationResult) -> None:
    """Validate frontmatter fields for a single skill."""
    name = skill_path.name
    skill_file = skill_path / "SKILL.md"

    if not _fm_has(fm_lines, "name"):
        vr.error(f"{name} - Missing name field")
    if not _fm_has(fm_lines, "description"):
        vr.error(f"{name} - Missing description field")

    name_value = _fm_field(fm_lines, "name").strip()
    if name_value:
        if len(name_value) > 64:
            vr.error(f"{name} - Name exceeds 64 characters")
        if re.search(r"[^a-z0-9-]", name_value):
            vr.error(f"{name} - Name contains invalid characters (must be lowercase, numbers, hyphens)")

    body_lines = _body_line_count(skill_file)
    if body_lines > 500:
        vr.warn(f"skills/{name}/SKILL.md: body is {body_lines} lines (recommended < 500)")

    desc_value = _fm_field(fm_lines, "description")
    if len(desc_value) > 1024:
        vr.warn(f"{name} - Description exceeds 1024 characters")


def _validate_skill_references(tk_dir: Path, skill_path: Path,
                               fm_lines: list[str], vr: ValidationResult) -> None:
    """Validate agent refs, depends-on, context/agent co-occurrence, and reference links."""
    name = skill_path.name
    skill_file = skill_path / "SKILL.md"

    has_context_fork = _fm_field(fm_lines, "context").strip() == "fork"
    has_agent = _fm_has(fm_lines, "agent")
    if has_context_fork and not has_agent:
        vr.warn(f"skills/{name}/SKILL.md: has 'context: fork' but missing 'agent:' field")
    if has_agent and not has_context_fork:
        vr.warn(f"skills/{name}/SKILL.md: has 'agent:' but missing 'context: fork'")

    agent_value = _fm_field(fm_lines, "agent").strip()
    if agent_value:
        if not (tk_dir / "app" / "agents" / f"{agent_value}.md").is_file():
            vr.error(f"skills/{name}/SKILL.md: agent '{agent_value}' not found in app/agents/")

    depends_val = _fm_field(fm_lines, "depends-on")
    if depends_val:
        for dep in (d.strip() for d in depends_val.split(",")):
            if not dep:
                continue
            if not (tk_dir / "app" / "skills" / dep / "SKILL.md").is_file():
                vr.error(f"skills/{name}/SKILL.md: depends-on '{dep}' not found in app/skills/")

    if _fm_has(fm_lines, "version"):
        vr.warn(f"{name} - Uses deprecated 'version' field in frontmatter")
    if _fm_has(fm_lines, "delegate-agent"):
        vr.warn(f"{name} - Uses deprecated 'delegate-agent' field (rename to 'agent:')")
    if _fm_has(fm_lines, "run-mode"):
        vr.warn(f"{name} - Uses deprecated 'run-mode' field (rename to 'context:')")

    ref_dir = skill_path / "reference"
    if ref_dir.is_dir():
        content = skill_file.read_text(encoding="utf-8")
        for match in re.finditer(r"\(reference/([^)]+)\)", content):
            ref_link = f"reference/{match.group(1)}"
            if not (skill_path / ref_link).is_file():
                vr.error(f"{name} - Broken reference link: {ref_link}")


def validate_skills(tk_dir: Path, vr: ValidationResult) -> int:
    """Validate skill directories. Returns skill count."""
    print("## Skills")
    skills_dir = tk_dir / "app" / "skills"
    skill_count = 0

    if not skills_dir.is_dir():
        vr.error("app/skills directory not found")
        print()
        return 0

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("_"):
            continue
        skill_count += 1
        name = skill_path.name
        skill_file = skill_path / "SKILL.md"

        if not skill_file.is_file():
            vr.error(f"{name} - Missing SKILL.md")
            continue

        if not _has_frontmatter(skill_file):
            vr.error(f"{name} - SKILL.md missing frontmatter")
            continue

        fm_lines = _parse_frontmatter_lines(skill_file)
        _validate_skill_frontmatter(tk_dir, skill_path, fm_lines, vr)
        _validate_skill_references(tk_dir, skill_path, fm_lines, vr)

    print(f"  Found: {skill_count} skills")
    print()
    return skill_count


def validate_legacy_commands(tk_dir: Path, vr: ValidationResult) -> None:
    """Check for legacy command files."""
    commands_dir = tk_dir / "app" / "commands"
    if commands_dir.is_dir():
        cmd_count = sum(1 for f in commands_dir.glob("*.md") if f.is_file())
        if cmd_count > 0:
            print("## Legacy Commands")
            vr.warn(f"{cmd_count} command files found in app/commands/ (should be migrated to skills)")
            print()


def validate_hook_events(tk_dir: Path, vr: ValidationResult) -> None:
    """Validate hook event names in hooks.json."""
    print("## Hook Events")
    hooks_file = tk_dir / "app" / "hooks.json"

    if not hooks_file.is_file():
        vr.error("app/hooks.json not found")
        print()
        return

    try:
        with open(hooks_file, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        vr.error(f"Could not parse app/hooks.json: {exc}")
        print()
        return

    hooks = data.get("hooks", {})
    for event in hooks:
        if event in VALID_HOOK_EVENTS:
            print(f"  OK: {event}")
        else:
            vr.error(f"Unknown hook event: {event}")

    # Count hook scripts
    hooks_dir = tk_dir / "app" / "hooks"
    script_count = sum(1 for f in hooks_dir.glob("*.sh") if f.is_file()) if hooks_dir.is_dir() else 0
    print(f"  Found: {script_count} hook scripts")
    print()


def validate_planned_assets(tk_dir: Path, vr: ValidationResult) -> None:
    """Validate that planned assets exist and are non-empty."""
    print("## Planned Assets")

    for rel_path in PLANNED_ASSETS:
        full = tk_dir / rel_path
        if full.is_file() and full.stat().st_size > 0:
            print(f"  OK: {rel_path}")
        else:
            vr.error(f"Missing or empty {rel_path}")

    # Validate plugin manifest JSON
    plugin_manifest = tk_dir / "app" / ".claude-plugin" / "plugin.json"
    if plugin_manifest.is_file():
        try:
            with open(plugin_manifest, encoding="utf-8") as f:
                d = json.load(f)
            assert d["name"]
            assert d["version"]
            assert d["description"]
            print("  OK: plugin manifest JSON is valid")
        except (json.JSONDecodeError, KeyError, AssertionError):
            vr.error("Invalid plugin manifest JSON or missing required fields")

    # Validate benchmark dashboard JSON
    benchmark_dashboard = tk_dir / "benchmarks" / "ecosystem-dashboard.json"
    if benchmark_dashboard.is_file():
        try:
            with open(benchmark_dashboard, encoding="utf-8") as f:
                d = json.load(f)
            assert d["generated_at"]
            assert d["snapshot_date"]
            assert d["freshness"]["status"]
            assert isinstance(d["repos"], list) and len(d["repos"]) > 0
            assert isinstance(d["comparison_matrix"], list) and len(d["comparison_matrix"]) > 0
            print("  OK: benchmark dashboard JSON is valid")
        except (json.JSONDecodeError, KeyError, AssertionError):
            vr.error("Invalid benchmark dashboard JSON or missing required fields")

    print()


def _validate_pack_manifest(manifest: Path, pack_name: str) -> dict | None:
    """Parse and validate a plugin pack manifest. Returns data dict or None on failure."""
    try:
        with open(manifest, encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    errors = _validate_plugin_manifest_schema(d, manifest.parent)
    if errors:
        return None
    return d


def _validate_pack_refs(tk_dir: Path, pack_path: Path, d: dict,
                        pack_name: str, vr: ValidationResult) -> None:
    """Validate agent/skill references and hook shebangs for a plugin pack."""
    ref_errors = _validate_plugin_references(
        d,
        agents_dir=tk_dir / "app" / "agents",
        skills_dir=tk_dir / "app" / "skills",
    )
    for err in ref_errors:
        vr.error(f"app/plugins/{pack_name}/plugin.json {err}")

    hooks_dir = pack_path / "hooks"
    if hooks_dir.is_dir():
        for hook in sorted(hooks_dir.glob("*.sh")):
            with open(hook, encoding="utf-8") as f:
                first_line = f.readline().rstrip("\n")
            rel = str(hook.relative_to(tk_dir))
            if re.match(r"^#!/(usr/)?bin/(env )?bash", first_line):
                print(f"  OK: {rel}")
            else:
                vr.error(f"{rel} missing bash shebang")


def validate_plugin_packs(tk_dir: Path, vr: ValidationResult) -> None:
    """Validate plugin pack manifests and references."""
    print("## Plugin Packs")
    plugin_dir = tk_dir / "app" / "plugins"

    if not plugin_dir.is_dir():
        vr.error("app/plugins directory not found")
        print()
        return

    pack_count = 0
    for pack_path in sorted(plugin_dir.iterdir()):
        if not pack_path.is_dir():
            continue
        pack_name = pack_path.name
        manifest = pack_path / "plugin.json"

        if not manifest.is_file():
            if pack_name == "plugins":
                continue
            vr.error(f"plugin pack {pack_name} missing plugin.json")
            continue

        d = _validate_pack_manifest(manifest, pack_name)
        if d is None:
            vr.error(f"Invalid plugin pack manifest: app/plugins/{pack_name}/plugin.json")
            pack_count += 1
            continue

        print(f"  OK: {pack_name}/plugin.json")
        _validate_pack_refs(tk_dir, pack_path, d, pack_name, vr)
        pack_count += 1

    print(f"  Found: {pack_count} plugin packs")
    print()


def validate_kb_documents(tk_dir: Path, vr: ValidationResult) -> None:
    """Validate KB document frontmatter."""
    print("## KB Documents")
    kb_dir = tk_dir / "kb"
    kb_count = 0
    kb_errors = 0

    if not kb_dir.is_dir():
        vr.error("kb/ directory not found")
        print()
        return

    for kb_file in sorted(kb_dir.rglob("*.md")):
        if kb_file.name == "README.md":
            continue
        kb_name = str(kb_file.relative_to(tk_dir))
        kb_count += 1

        if not _has_frontmatter(kb_file):
            vr.error(f"{kb_name} - Missing YAML frontmatter")
            kb_errors += 1
            continue

        fm_lines = _parse_frontmatter_lines(kb_file)

        # Required fields
        for field in ("title", "category", "service", "tags", "last_updated", "created", "description"):
            if not _fm_has(fm_lines, field):
                vr.error(f"{kb_name} - Missing required field: {field}")
                kb_errors += 1

        # Validate category
        kb_category = _fm_field(fm_lines, "category").strip()
        if kb_category and kb_category not in VALID_KB_CATEGORIES:
            vr.error(f"{kb_name} - Invalid category '{kb_category}' (valid: {', '.join(sorted(VALID_KB_CATEGORIES))})")
            kb_errors += 1

        # Validate tags is not empty
        tags_val = _fm_field(fm_lines, "tags")
        if tags_val:
            # Tags format: [tag1, tag2]
            tag_items = re.findall(r"[a-z][\w-]*", tags_val)
            if len(tag_items) < 1:
                vr.warn(f"{kb_name} - Tags array is empty (minimum 1 tag recommended)")

    if kb_errors == 0:
        print(f"  OK: {kb_count} KB documents validated")
    else:
        print(f"  Found: {kb_count} KB documents ({kb_errors} with errors)")
    print()


def validate_core_files(tk_dir: Path, vr: ValidationResult) -> None:
    """Check that core files exist."""
    print("## Core Files")
    for rel in CORE_FILES:
        if (tk_dir / rel).is_file():
            print(f"  OK: {rel}")
        else:
            vr.error(f"Missing {rel}")
    print()


def _count_bats_tests(tk_dir: Path) -> str:
    """Count @test entries in bats files. Returns count as string or empty."""
    tests_dir = tk_dir / "tests"
    if not tests_dir.is_dir():
        return ""
    total = 0
    for bats_file in tests_dir.glob("*.bats"):
        content = bats_file.read_text(encoding="utf-8")
        total += len(re.findall(r"^@test ", content, re.MULTILINE))
    return str(total) if total > 0 else ""


def _extract_readme_badges(tk_dir: Path) -> tuple[str, str, str]:
    """Extract agent, skill, and test badge counts from README.md."""
    readme = tk_dir / "README.md"
    if not readme.is_file():
        return "", "", ""
    readme_content = readme.read_text(encoding="utf-8")
    readme_agents = ""
    readme_skills = ""
    readme_tests = ""
    m = re.search(r"agents-(\d+)", readme_content)
    if m:
        readme_agents = m.group(1)
    m = re.search(r"skills-(\d+)", readme_content)
    if m:
        readme_skills = m.group(1)
    m = re.search(r"tests-(\d+)", readme_content)
    if m:
        readme_tests = m.group(1)
    return readme_agents, readme_skills, readme_tests


def validate_metadata_contracts(
    tk_dir: Path,
    agent_count: int,
    skill_count: int,
    vr: ValidationResult,
) -> str:
    """Validate README badge counts match actual counts. Returns actual_tests."""
    print("## Metadata Contracts")

    actual_tests = _count_bats_tests(tk_dir)
    readme_agents, readme_skills, readme_tests = _extract_readme_badges(tk_dir)

    if readme_agents and readme_agents != str(agent_count):
        vr.error(f"README agent badge ({readme_agents}) != actual ({agent_count})")
    else:
        print(f"  OK: agents ({agent_count})")

    if readme_skills and readme_skills != str(skill_count):
        vr.error(f"README skill badge ({readme_skills}) != actual ({skill_count})")
    else:
        print(f"  OK: skills ({skill_count})")

    if not actual_tests:
        print("  SKIP: tests (tests/ not present in this installation)")
    elif readme_tests and readme_tests != actual_tests:
        vr.error(f"README test badge ({readme_tests}) != actual ({actual_tests})")
    else:
        print(f"  OK: tests ({actual_tests})")

    # Cross-validate versions: package.json vs manifest.json vs plugin.json
    _validate_version_sync(tk_dir, vr)

    print()
    return actual_tests


def _validate_version_sync(tk_dir: Path, vr: ValidationResult) -> None:
    """Ensure package.json, manifest.json, and plugin.json versions match."""
    import json as _json

    version_files = {
        "package.json": tk_dir / "package.json",
        "manifest.json": tk_dir / "manifest.json",
        "plugin.json": tk_dir / "app" / ".claude-plugin" / "plugin.json",
    }

    versions: dict[str, str] = {}
    for name, path in version_files.items():
        if path.is_file():
            try:
                data = _json.loads(path.read_text(encoding="utf-8"))
                versions[name] = data.get("version", "")
            except Exception:
                pass

    if len(versions) < 2:
        return  # Not enough files to compare (e.g., installed copy without source)

    unique = set(versions.values())
    if len(unique) == 1:
        print(f"  OK: version sync ({unique.pop()})")
    else:
        detail = ", ".join(f"{k}={v}" for k, v in versions.items())
        vr.error(f"Version mismatch across files: {detail}")

    # Check README "What's New" section matches current version
    pkg_version = versions.get("package.json", "")
    if pkg_version:
        readme = tk_dir / "README.md"
        if readme.is_file():
            content = readme.read_text(encoding="utf-8")
            m = re.search(r"## What's New in v([\d.]+)", content)
            if m:
                whats_new_ver = m.group(1)
                if whats_new_ver == pkg_version:
                    print(f"  OK: README \"What's New\" (v{whats_new_ver})")
                else:
                    vr.error(
                        f"README \"What's New in v{whats_new_ver}\" "
                        f"is stale (package.json is v{pkg_version})"
                    )


ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def validate_constitution_drift(tk_dir: Path, vr: ValidationResult) -> None:
    """Detect article-count drift between constitution.md and downstream docs."""
    print()
    print("## Constitution Drift")

    constitution = tk_dir / "app" / "constitution.md"
    if not constitution.is_file():
        return

    content = constitution.read_text(encoding="utf-8")
    matches = re.findall(r"^## Article ([IVX]+):", content, re.MULTILINE)
    if not matches:
        vr.error("Constitution has no '## Article <roman>:' headings")
        return

    count = len(matches)
    if count > len(ROMAN_NUMERALS):
        vr.error(f"Constitution has {count} articles (more than {len(ROMAN_NUMERALS)} supported)")
        return
    max_roman = ROMAN_NUMERALS[count - 1]

    docs = [
        tk_dir / "README.md",
        tk_dir / "app" / "ARCHITECTURE.md",
        tk_dir / "kb" / "reference" / "architecture-overview.md",
        tk_dir / "kb" / "reference" / "enterprise-config-guide.md",
    ]

    count_pat = re.compile(r"\b(\d+)\s+(?:immutable\s+safety\s+)?articles?\b", re.IGNORECASE)
    range_pat = re.compile(r"\bArticles?\s+I-([IVX]+)\b")
    drift = 0
    for doc in docs:
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8")
        for m in count_pat.finditer(text):
            n = int(m.group(1))
            if 1 <= n <= len(ROMAN_NUMERALS) and n != count:
                vr.error(
                    f"{doc.relative_to(tk_dir)} references '{n} articles' "
                    f"but constitution has {count}"
                )
                drift += 1
        for m in range_pat.finditer(text):
            end = m.group(1).upper()
            if end != max_roman and end in ROMAN_NUMERALS:
                vr.error(
                    f"{doc.relative_to(tk_dir)} references 'Articles I-{end}' "
                    f"but constitution has I-{max_roman}"
                )
                drift += 1

    if drift == 0:
        print(f"  OK: constitution has {count} articles (I-{max_roman}), docs consistent")
    print()


def validate_content_quality(tk_dir: Path, vr: ValidationResult) -> None:
    """Check content quality: name matches directory, non-empty body."""
    print()
    print("## Content Quality")
    skills_dir = tk_dir / "app" / "skills"

    if not skills_dir.is_dir():
        return

    for skill_path in sorted(skills_dir.iterdir()):
        if not skill_path.is_dir() or skill_path.name.startswith("_"):
            continue
        skill_file = skill_path / "SKILL.md"
        if not skill_file.is_file():
            continue
        dir_name = skill_path.name

        # Check name matches directory
        file_name = frontmatter_field(skill_file, "name").strip()
        if file_name and file_name != dir_name:
            vr.warn(f"{dir_name} - name field '{file_name}' != directory name")

        # Check non-empty body after frontmatter
        body_nonblank = _body_nonblank_count(skill_file)
        if body_nonblank == 0:
            vr.error(f"{dir_name} - SKILL.md has no content after frontmatter")

    print("  Done: content quality checks")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _run_all_checks(tk_dir: Path, vr: ValidationResult) -> tuple[int, int, str]:
    """Run all validation checks. Returns (agent_count, skill_count, actual_tests)."""
    agent_count = validate_agents(tk_dir, vr)
    skill_count = validate_skills(tk_dir, vr)
    validate_legacy_commands(tk_dir, vr)
    validate_hook_events(tk_dir, vr)
    validate_planned_assets(tk_dir, vr)
    validate_plugin_packs(tk_dir, vr)
    validate_kb_documents(tk_dir, vr)
    validate_core_files(tk_dir, vr)
    actual_tests = validate_metadata_contracts(tk_dir, agent_count, skill_count, vr)
    validate_constitution_drift(tk_dir, vr)
    validate_content_quality(tk_dir, vr)
    return agent_count, skill_count, actual_tests


def main() -> None:
    strict = False
    tk_dir = default_toolkit_dir

    for arg in sys.argv[1:]:
        if arg == "--strict":
            strict = True
        elif not arg.startswith("-"):
            tk_dir = Path(arg)

    print("AI Toolkit Validator")
    print("========================")
    print(f"Toolkit: {tk_dir}")
    print()

    vr = ValidationResult()
    agent_count, skill_count, actual_tests = _run_all_checks(tk_dir, vr)

    print("========================")
    print(f"Summary: {agent_count} agents, {skill_count} skills, {actual_tests or 'n/a'} tests")
    print(f"Errors: {vr.errors} | Warnings: {vr.warnings}")

    if vr.errors > 0:
        print("VALIDATION FAILED")
        sys.exit(1)
    else:
        print("VALIDATION PASSED")
        if strict and vr.warnings > 0:
            print()
            print(f"STRICT MODE: {vr.warnings} warning(s) treated as errors")
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
