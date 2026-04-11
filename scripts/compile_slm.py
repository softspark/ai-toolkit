#!/usr/bin/env python3
"""Compile ai-toolkit into a minimal system prompt for Small Language Models.

Reads all toolkit components (constitution, agents, skills, rules, personas),
scores them by safety criticality and relevance, compresses to fit a token
budget, and emits a single compiled markdown file.

Usage:
    python3 scripts/compile_slm.py [options]
    ai-toolkit compile-slm [options]

Options:
    --budget N          Token budget (default: auto from model size)
    --model-size SIZE   Model size: 7b, 8b, 14b, 32b, 70b (default: auto-detect)
    --persona NAME      Persona preset to prioritize (e.g., backend-lead)
    --lang LANGS        Comma-separated languages to include (e.g., python,typescript)
    --output PATH       Output file path (default: ~/.ai-toolkit/compiled/slm-system-prompt.md)
    --format FORMAT     Output format: raw, ollama, json-string, aider (default: raw)
    --dry-run           Show what would be included without writing output
    --level LEVEL       Compression level: ultra-light, light, standard, extended (default: auto)

Exit codes:
    0  compilation succeeded
    1  compilation failed (budget exceeded, constitution too large, etc.)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (
    toolkit_dir,
    app_dir,
    agents_dir,
    skills_dir,
    frontmatter_field,
    frontmatter_block,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MODEL_BUDGETS: dict[str, dict[str, object]] = {
    "7b":  {"budget": 2048,  "level": "ultra-light"},
    "8b":  {"budget": 2048,  "level": "ultra-light"},
    "14b": {"budget": 4096,  "level": "light"},
    "32b": {"budget": 8192,  "level": "standard"},
    "70b": {"budget": 16384, "level": "extended"},
}

DEFAULT_MODEL_SIZE = "14b"
BUDGET_SAFETY_MARGIN = 0.95

COMPRESSION_LEVELS: dict[str, dict[str, object]] = {
    "ultra-light": {
        "strip_examples": True,
        "strip_rationalizations": True,
        "strip_related_skills": True,
        "strip_verification": True,
        "strip_agent_commands": True,
        "strip_multi_agent": True,
        "max_skills": 5,
        "max_agents": 0,
        "include_rules": False,
    },
    "light": {
        "strip_examples": True,
        "strip_rationalizations": True,
        "strip_related_skills": True,
        "strip_verification": "summary",
        "strip_agent_commands": True,
        "strip_multi_agent": True,
        "max_skills": 10,
        "max_agents": 1,
        "include_rules": True,
    },
    "standard": {
        "strip_examples": "first-only",
        "strip_rationalizations": True,
        "strip_related_skills": True,
        "strip_verification": "summary",
        "strip_agent_commands": True,
        "strip_multi_agent": True,
        "max_skills": 20,
        "max_agents": 3,
        "include_rules": True,
    },
    "extended": {
        "strip_examples": "first-only",
        "strip_rationalizations": "first-only",
        "strip_related_skills": False,
        "strip_verification": False,
        "strip_agent_commands": False,
        "strip_multi_agent": True,
        "max_skills": 40,
        "max_agents": 5,
        "include_rules": True,
    },
}

# Scoring weights
W_SAFETY = 0.40
W_USAGE = 0.25
W_PERSONA = 0.20
W_LANGUAGE = 0.15


# ---------------------------------------------------------------------------
# 1.1 — Token Counter
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Estimate token count without external dependencies.

    Uses two heuristics and returns the higher (conservative) estimate:
    1. Word-based: ~0.75 tokens/word for English prose
    2. Char-based: ~1 token per 4 chars (more accurate for code-heavy content)

    Adds a penalty for code blocks which have higher token density.
    Accuracy target: +/-10% vs tiktoken cl100k_base.
    """
    if not text:
        return 0
    word_est = int(len(text.split()) * 0.75)
    char_est = len(text) // 4
    code_blocks = text.count("```")
    code_penalty = code_blocks * 15
    return max(word_est, char_est) + code_penalty


# ---------------------------------------------------------------------------
# 1.2 — Component Parser + Scorer
# ---------------------------------------------------------------------------

@dataclass
class Component:
    """A single toolkit component scored for SLM compilation."""

    name: str
    type: str  # constitution, agent, skill, rule, persona, hook-rule
    source_file: str
    full_text: str
    compressed_text: str = ""
    tokens_full: int = 0
    tokens_compressed: int = 0
    score: float = 0.0

    # Scoring factors
    safety_criticality: float = 0.0
    usage_frequency: float = 0.0
    persona_relevance: float = 0.0
    language_relevance: float = 0.0

    def compute_score(self) -> None:
        """Compute composite score from weighted factors."""
        self.score = (
            self.safety_criticality * W_SAFETY
            + self.usage_frequency * W_USAGE
            + self.persona_relevance * W_PERSONA
            + self.language_relevance * W_LANGUAGE
        )


def _load_usage_stats() -> dict[str, int]:
    """Load skill invocation counts from stats.json."""
    stats_path = Path.home() / ".ai-toolkit" / "stats.json"
    if not stats_path.is_file():
        return {}
    try:
        data = json.loads(stats_path.read_text(encoding="utf-8"))
        counts: dict[str, int] = {}
        for run in data.get("loop_runs", []):
            cmd = run.get("command", "").lstrip("/")
            if cmd:
                counts[cmd] = counts.get(cmd, 0) + 1
        return counts
    except (json.JSONDecodeError, OSError):
        return {}


def _normalize_usage(counts: dict[str, int]) -> dict[str, float]:
    """Normalize usage counts to 0.0-1.0 range."""
    if not counts:
        return {}
    max_count = max(counts.values())
    if max_count == 0:
        return {}
    return {k: v / max_count for k, v in counts.items()}


def _read_file_text(path: Path) -> str:
    """Read file content, return empty string on failure."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- delimited) from text."""
    if not text.startswith("---"):
        return text
    end = text.find("---", 3)
    if end == -1:
        return text
    return text[end + 3:].lstrip("\n")


def _parse_persona_skills(persona_path: Path) -> list[str]:
    """Extract preferred skill names from a persona file."""
    text = _read_file_text(persona_path)
    skills: list[str] = []
    for match in re.finditer(r"`/(\w[\w-]*)`", text):
        skill_name = match.group(1)
        # Strip workflow type suffixes
        if " " not in skill_name:
            skills.append(skill_name)
    return skills


def parse_components(
    persona: str = "",
    languages: list[str] | None = None,
) -> list[Component]:
    """Parse all toolkit components into a scored list."""
    components: list[Component] = []
    usage_stats = _normalize_usage(_load_usage_stats())
    languages = languages or []

    # Persona skills for boosting
    persona_skills: list[str] = []
    persona_path: Path | None = None
    if persona:
        persona_path = app_dir / "personas" / f"{persona}.md"
        if persona_path.is_file():
            persona_skills = _parse_persona_skills(persona_path)

    # --- Constitution (always score=1.0) ---
    constitution_path = app_dir / "constitution.md"
    if constitution_path.is_file():
        text = _read_file_text(constitution_path)
        body = _strip_frontmatter(text)
        components.append(Component(
            name="Constitution",
            type="constitution",
            source_file=str(constitution_path),
            full_text=body,
            tokens_full=estimate_tokens(body),
            safety_criticality=1.0,
            usage_frequency=1.0,
            persona_relevance=1.0,
            language_relevance=1.0,
        ))
        components[-1].compute_score()

    # --- Guard hooks as text rules (score=0.95) ---
    for hook_name in ("guard-destructive", "guard-path"):
        hook_path = app_dir / "hooks" / f"{hook_name}.sh"
        if hook_path.is_file():
            text = _read_file_text(hook_path)
            # Extract the blocked patterns as a rule summary
            rule_text = _extract_guard_rule(hook_name, text)
            components.append(Component(
                name=f"Guard: {hook_name}",
                type="hook-rule",
                source_file=str(hook_path),
                full_text=rule_text,
                tokens_full=estimate_tokens(rule_text),
                safety_criticality=0.95,
                usage_frequency=0.8,
                persona_relevance=0.5,
                language_relevance=0.5,
            ))
            components[-1].compute_score()

    # --- Persona definition (score=0.90) ---
    if persona_path and persona_path.is_file():
        text = _read_file_text(persona_path)
        body = _strip_frontmatter(text)
        components.append(Component(
            name=f"Persona: {persona}",
            type="persona",
            source_file=str(persona_path),
            full_text=body,
            tokens_full=estimate_tokens(body),
            safety_criticality=0.0,
            usage_frequency=0.8,
            persona_relevance=1.0,
            language_relevance=0.5,
        ))
        components[-1].compute_score()

    # --- Language rules (score=0.85 for matching, 0.1 for non-matching) ---
    rules_dir = app_dir / "rules"
    # Always include common rules
    common_rules_dir = rules_dir / "common"
    if common_rules_dir.is_dir():
        for rule_file in sorted(common_rules_dir.glob("*.md")):
            text = _read_file_text(rule_file)
            body = _strip_frontmatter(text)
            components.append(Component(
                name=f"Rule: common/{rule_file.stem}",
                type="rule",
                source_file=str(rule_file),
                full_text=body,
                tokens_full=estimate_tokens(body),
                safety_criticality=0.5,
                usage_frequency=0.6,
                persona_relevance=0.5,
                language_relevance=0.85,
            ))
            components[-1].compute_score()

    # Language-specific rules
    if languages:
        for lang in languages:
            lang_dir = rules_dir / lang
            if not lang_dir.is_dir():
                continue
            for rule_file in sorted(lang_dir.glob("*.md")):
                text = _read_file_text(rule_file)
                body = _strip_frontmatter(text)
                components.append(Component(
                    name=f"Rule: {lang}/{rule_file.stem}",
                    type="rule",
                    source_file=str(rule_file),
                    full_text=body,
                    tokens_full=estimate_tokens(body),
                    safety_criticality=0.3,
                    usage_frequency=0.5,
                    persona_relevance=0.4,
                    language_relevance=1.0,
                ))
                components[-1].compute_score()

    # --- Skills ---
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            skill_name = frontmatter_field(skill_file, "name")
            if not skill_name:
                skill_name = skill_dir.name
            description = frontmatter_field(skill_file, "description")
            user_invocable = frontmatter_field(skill_file, "user-invocable")

            # Skip non-user-invocable knowledge skills for SLM
            if user_invocable == "false":
                continue

            # Build a compact skill summary (name + description)
            text = _read_file_text(skill_file)
            body = _strip_frontmatter(text)

            # Persona relevance boost
            p_relevance = 0.7 if skill_name in persona_skills else 0.3

            # Usage frequency from stats
            u_freq = usage_stats.get(skill_name, 0.2)

            components.append(Component(
                name=f"Skill: /{skill_name}",
                type="skill",
                source_file=str(skill_file),
                full_text=body,
                tokens_full=estimate_tokens(body),
                safety_criticality=0.1,
                usage_frequency=u_freq,
                persona_relevance=p_relevance,
                language_relevance=0.5,
            ))
            components[-1].compute_score()

    # --- Agents ---
    if agents_dir.is_dir():
        for agent_file in sorted(agents_dir.glob("*.md")):
            agent_name = frontmatter_field(agent_file, "name")
            if not agent_name:
                agent_name = agent_file.stem
            description = frontmatter_field(agent_file, "description")
            text = _read_file_text(agent_file)
            body = _strip_frontmatter(text)

            # Persona relevance: match if agent skills overlap persona skills
            agent_skills_str = frontmatter_field(agent_file, "skills")
            agent_skill_list = [s.strip() for s in agent_skills_str.split(",") if s.strip()]
            overlap = len(set(agent_skill_list) & set(persona_skills))
            p_relevance = min(0.3 + overlap * 0.2, 1.0)

            components.append(Component(
                name=f"Agent: {agent_name}",
                type="agent",
                source_file=str(agent_file),
                full_text=body,
                tokens_full=estimate_tokens(body),
                safety_criticality=0.1,
                usage_frequency=0.3,
                persona_relevance=p_relevance,
                language_relevance=0.3,
            ))
            components[-1].compute_score()

    return components


def _extract_guard_rule(hook_name: str, script_text: str) -> str:
    """Convert a guard hook script into a text rule for SLM system prompt."""
    if hook_name == "guard-destructive":
        # Extract blocked patterns from the script
        patterns: list[str] = []
        for match in re.finditer(r'"([^"]+)"', script_text):
            candidate = match.group(1)
            if any(kw in candidate for kw in ("rm ", "drop ", "delete ", "format", "mkfs", "dd ")):
                patterns.append(candidate)
        if not patterns:
            patterns = ["rm -rf", "DROP TABLE", "FORMAT", "mkfs", "dd if="]
        return (
            "## Destructive Command Guard\n"
            "NEVER execute these commands without explicit user confirmation:\n"
            + "\n".join(f"- `{p}`" for p in patterns)
        )
    if hook_name == "guard-path":
        return (
            "## Path Guard\n"
            "Only read and write files within the current project directory.\n"
            "Never access files outside the working directory without explicit user permission."
        )
    return ""


# ---------------------------------------------------------------------------
# 1.3 — Compression Engine
# ---------------------------------------------------------------------------

def compress_component(component: Component, level_config: dict[str, object]) -> None:
    """Compress a component's text based on compression level settings."""
    text = component.full_text

    # Constitution and hook-rules are never compressed
    if component.type in ("constitution", "hook-rule"):
        component.compressed_text = text
        component.tokens_compressed = estimate_tokens(text)
        return

    # Strip frontmatter (already done in parsing, but safety check)
    text = _strip_frontmatter(text)

    # Strip examples
    strip_examples = level_config.get("strip_examples", True)
    if strip_examples is True:
        text = _strip_sections(text, ["## Example", "### Example", "## Usage Example"])
        text = _strip_code_blocks(text)
    elif strip_examples == "first-only":
        text = _keep_first_code_block(text)

    # Strip rationalization tables
    if level_config.get("strip_rationalizations", True) is True:
        text = _strip_sections(text, [
            "## Common Rationalizations",
            "### Common Rationalizations",
            "## Rationalization",
        ])
    elif level_config.get("strip_rationalizations") == "first-only":
        text = _strip_sections_keep_first(text, [
            "## Common Rationalizations",
            "### Common Rationalizations",
        ])

    # Strip related skills
    if level_config.get("strip_related_skills", True):
        text = _strip_sections(text, [
            "## Related Skills",
            "### Related Skills",
            "## See Also",
        ])

    # Strip or summarize verification
    strip_verification = level_config.get("strip_verification", True)
    if strip_verification is True:
        text = _strip_sections(text, [
            "## Verification Checklist",
            "### Verification",
            "## Verification",
        ])
    elif strip_verification == "summary":
        text = _summarize_sections(text, [
            "## Verification Checklist",
            "### Verification",
            "## Verification",
        ])

    # Strip agent CLI commands
    if level_config.get("strip_agent_commands", True):
        text = _strip_sections(text, [
            "## Allowed CLI Commands",
            "### Allowed CLI Commands",
        ])

    # Strip multi-agent coordination
    if level_config.get("strip_multi_agent", True):
        text = _strip_sections(text, [
            "## Multi-Agent",
            "### Coordination",
            "## Agent Orchestration",
            "## Team Coordination",
        ])

    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    component.compressed_text = text
    component.tokens_compressed = estimate_tokens(text)


def _strip_sections(text: str, headers: list[str]) -> str:
    """Remove entire sections (header through next same-or-higher-level header)."""
    for header in headers:
        level = len(header) - len(header.lstrip("#"))
        pattern = re.compile(
            rf"^{re.escape(header)}.*?(?=^#{{1,{level}}} |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        text = pattern.sub("", text)
    return text


def _strip_sections_keep_first(text: str, headers: list[str]) -> str:
    """Remove all but the first occurrence of matching sections."""
    for header in headers:
        level = len(header) - len(header.lstrip("#"))
        pattern = re.compile(
            rf"^{re.escape(header)}.*?(?=^#{{1,{level}}} |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        matches = list(pattern.finditer(text))
        # Remove all except first
        for match in reversed(matches[1:]):
            text = text[:match.start()] + text[match.end():]
    return text


def _summarize_sections(text: str, headers: list[str]) -> str:
    """Replace verbose verification sections with a one-liner."""
    for header in headers:
        level = len(header) - len(header.lstrip("#"))
        pattern = re.compile(
            rf"^({re.escape(header)}).*?(?=^#{{1,{level}}} |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        text = pattern.sub(f"{header}\nVerify: tests pass, no placeholders, no regressions.\n\n", text)
    return text


def _strip_code_blocks(text: str) -> str:
    """Remove all fenced code blocks."""
    return re.sub(r"```[\s\S]*?```", "", text)


def _keep_first_code_block(text: str) -> str:
    """Keep only the first fenced code block, remove the rest."""
    blocks = list(re.finditer(r"```[\s\S]*?```", text))
    for block in reversed(blocks[1:]):
        text = text[:block.start()] + text[block.end():]
    return text


def compress_all(
    components: list[Component], level: str,
) -> None:
    """Apply compression to all components based on level."""
    config = COMPRESSION_LEVELS.get(level, COMPRESSION_LEVELS["light"])
    for comp in components:
        compress_component(comp, config)


# ---------------------------------------------------------------------------
# 1.4 — Budget Packer
# ---------------------------------------------------------------------------

def pack_components(
    components: list[Component], budget: int, level: str,
) -> tuple[list[Component], list[Component]]:
    """Pack highest-value components into token budget.

    Returns (included, excluded) tuple.
    """
    effective_budget = int(budget * BUDGET_SAFETY_MARGIN)
    config = COMPRESSION_LEVELS.get(level, COMPRESSION_LEVELS["light"])
    max_skills = int(config.get("max_skills", 10))  # type: ignore[arg-type]
    max_agents = int(config.get("max_agents", 1))  # type: ignore[arg-type]
    include_rules = bool(config.get("include_rules", True))

    # Fixed components: constitution, hook-rules, persona (score >= 0.85)
    fixed = [c for c in components if c.score >= 0.85]
    fixed_tokens = sum(c.tokens_compressed for c in fixed)

    # Constitution budget guard
    if fixed_tokens > effective_budget:
        constitution_tokens = sum(
            c.tokens_compressed for c in fixed if c.type == "constitution"
        )
        print(
            f"ERROR: Constitution + safety rules alone require {fixed_tokens} tokens, "
            f"exceeding budget of {effective_budget} (budget={budget} × {BUDGET_SAFETY_MARGIN}).\n"
            f"Minimum safe budget: {int(fixed_tokens / BUDGET_SAFETY_MARGIN) + 1}.\n"
            f"Use --budget {int(fixed_tokens / BUDGET_SAFETY_MARGIN) + 1} or higher.",
            file=sys.stderr,
        )
        sys.exit(1)

    remaining_budget = effective_budget - fixed_tokens

    # Dynamic components: sort by value density (score / tokens)
    dynamic = [c for c in components if c.score < 0.85]

    # Apply type limits
    if not include_rules:
        dynamic = [c for c in dynamic if c.type != "rule"]

    # Sort by value density
    dynamic.sort(
        key=lambda c: c.score / max(c.tokens_compressed, 1),
        reverse=True,
    )

    packed = list(fixed)
    excluded: list[Component] = []
    skill_count = 0
    agent_count = 0

    for comp in dynamic:
        # Enforce type limits
        if comp.type == "skill" and skill_count >= max_skills:
            excluded.append(comp)
            continue
        if comp.type == "agent" and agent_count >= max_agents:
            excluded.append(comp)
            continue

        if comp.tokens_compressed <= remaining_budget:
            packed.append(comp)
            remaining_budget -= comp.tokens_compressed
            if comp.type == "skill":
                skill_count += 1
            elif comp.type == "agent":
                agent_count += 1
        else:
            excluded.append(comp)

    return packed, excluded


# ---------------------------------------------------------------------------
# 1.5 — Markdown Emitter
# ---------------------------------------------------------------------------

# Section order for maximum SLM comprehension
SECTION_ORDER = ["constitution", "hook-rule", "persona", "rule", "skill", "agent"]


def emit_markdown(components: list[Component]) -> str:
    """Emit compiled system prompt as structured markdown."""
    sections: dict[str, list[str]] = {t: [] for t in SECTION_ORDER}

    for comp in components:
        section_type = comp.type if comp.type in SECTION_ORDER else "skill"
        sections[section_type].append(comp.compressed_text)

    parts: list[str] = ["# AI Coding Assistant — System Instructions\n"]

    # Safety Rules (constitution + guard hooks)
    safety_parts = sections["constitution"] + sections["hook-rule"]
    if safety_parts:
        parts.append("## Safety Rules (MANDATORY)\n")
        parts.extend(safety_parts)
        parts.append("")

    # Identity (persona)
    if sections["persona"]:
        parts.append("## Your Identity\n")
        parts.extend(sections["persona"])
        parts.append("")

    # Coding Standards (rules)
    if sections["rule"]:
        parts.append("## Coding Standards\n")
        parts.extend(sections["rule"])
        parts.append("")

    # Key Skills
    if sections["skill"]:
        parts.append("## Key Skills\n")
        for skill_text in sections["skill"]:
            # Compact each skill to header + first paragraph
            lines = skill_text.strip().split("\n")
            compact = "\n".join(lines[:20]) if len(lines) > 20 else skill_text
            parts.append(compact)
            parts.append("")

    # Agents (if any)
    if sections["agent"]:
        parts.append("## Available Agents\n")
        for agent_text in sections["agent"]:
            lines = agent_text.strip().split("\n")
            compact = "\n".join(lines[:15]) if len(lines) > 15 else agent_text
            parts.append(compact)
            parts.append("")

    output = "\n".join(parts)
    # Clean up excessive whitespace
    output = re.sub(r"\n{3,}", "\n\n", output)
    return output.strip() + "\n"


def format_output(markdown: str, fmt: str) -> str:
    """Convert compiled markdown to requested output format."""
    if fmt == "raw":
        return markdown
    if fmt == "ollama":
        # Ollama Modelfile SYSTEM block
        escaped = markdown.replace('"', '\\"')
        return f'FROM {{}}\nSYSTEM """\n{escaped}\n"""\n'
    if fmt == "json-string":
        return json.dumps(markdown)
    if fmt == "aider":
        # Aider --system-prompt-file compatible (just raw markdown)
        return markdown
    return markdown


# ---------------------------------------------------------------------------
# 2.3 — Model Size Detection
# ---------------------------------------------------------------------------

def detect_model_size() -> str | None:
    """Detect running model size from Ollama API."""
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )
        resp = urllib.request.urlopen(req, timeout=2)
        data = json.loads(resp.read())
        models = data.get("models", [])
        if models:
            latest = models[0].get("name", "")
            match = re.search(r"(\d+)[bB]", latest)
            if match:
                return match.group(0).lower()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        pass
    return None


# ---------------------------------------------------------------------------
# 3.2 — Compile Quality Validator
# ---------------------------------------------------------------------------

def validate_output(
    included: list[Component], markdown: str, budget: int,
) -> list[str]:
    """Post-compilation quality checks. Returns list of errors (empty = pass)."""
    errors: list[str] = []
    total_tokens = estimate_tokens(markdown)

    # 1. Constitution must be present
    has_constitution = any(c.type == "constitution" for c in included)
    if not has_constitution:
        errors.append("FAIL: Constitution missing from compiled output")

    # 2. Budget not exceeded
    if total_tokens > budget:
        errors.append(
            f"FAIL: Output ({total_tokens:,} tokens) exceeds budget ({budget:,} tokens)"
        )

    # 3. No empty output
    if len(markdown.strip()) < 100:
        errors.append("FAIL: Compiled output is suspiciously short (<100 chars)")

    # 4. Minimum component count
    if len(included) < 2:
        errors.append(
            f"WARN: Only {len(included)} component(s) included — output may be too minimal"
        )

    # 5. Safety section present in output
    if "Safety Rules" not in markdown and "Constitution" not in markdown:
        errors.append("FAIL: No safety section found in compiled output")

    # 6. Guard hooks compiled as text rules
    has_guard = any(c.type == "hook-rule" for c in included)
    if not has_guard:
        errors.append("WARN: No guard hooks compiled into output — destructive commands unguarded")

    return errors


# ---------------------------------------------------------------------------
# Integration Guides
# ---------------------------------------------------------------------------

INTEGRATION_GUIDES: dict[str, str] = {
    "ollama": """\
## Ollama Setup

1. Compile system prompt:
   ai-toolkit compile-slm --format ollama --model-size {model_size} > Modelfile.ai-toolkit

2. Create custom model:
   ollama create my-assistant -f Modelfile.ai-toolkit

3. Run:
   ollama run my-assistant

Note: Replace the FROM line in the Modelfile with your base model (e.g., FROM llama3.1:8b).""",

    "lm-studio": """\
## LM Studio Setup

1. Compile system prompt:
   ai-toolkit compile-slm --model-size {model_size} --output system-prompt.md

2. In LM Studio:
   - Open Chat Settings (gear icon)
   - Paste contents of system-prompt.md into "System Prompt" field
   - Save as preset for reuse""",

    "aider": """\
## Aider Setup

1. Compile system prompt:
   ai-toolkit compile-slm --format aider --model-size {model_size} --output .ai-toolkit-system.md

2. Run Aider with custom system prompt:
   aider --system-prompt-file .ai-toolkit-system.md

3. Or add to .aider.conf.yml:
   system-prompt-file: .ai-toolkit-system.md""",

    "continue-dev": """\
## Continue.dev Setup

1. Compile system prompt:
   ai-toolkit compile-slm --model-size {model_size} --output system-prompt.md

2. Edit ~/.continue/config.json, add to your model config:
   {{
     "models": [{{
       "title": "Local Assistant",
       "provider": "ollama",
       "model": "llama3.1:8b",
       "systemMessage": "<paste contents of system-prompt.md here>"
     }}]
   }}""",
}


def print_integration_guide(model_size: str, output_path: str) -> None:
    """Print platform-specific integration instructions after compilation."""
    print("\n--- Integration Guides ---", file=sys.stderr)
    for platform, template in INTEGRATION_GUIDES.items():
        print(f"\n{template.format(model_size=model_size)}", file=sys.stderr)
    print(
        f"\nCompiled prompt saved to: {output_path}",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------------
# Dry Run Table
# ---------------------------------------------------------------------------

def print_dry_run(
    included: list[Component],
    excluded: list[Component],
    budget: int,
    level: str,
    persona: str,
) -> None:
    """Print a table showing what would be included in compilation."""
    effective_budget = int(budget * BUDGET_SAFETY_MARGIN)
    total_tokens = sum(c.tokens_compressed for c in included)

    print(f"Budget: {budget} tokens (effective: {effective_budget}) | "
          f"Level: {level} | Persona: {persona or '(none)'}")
    print()

    # Table header
    header = f"{'Component':<40} {'Score':>6} {'Tokens':>7} {'Included':>10}"
    print(header)
    print("-" * len(header))

    # Included components
    for comp in sorted(included, key=lambda c: c.score, reverse=True):
        print(f"{comp.name:<40} {comp.score:>6.2f} {comp.tokens_compressed:>7} {'YES':>10}")

    # Excluded components (top 10)
    for comp in sorted(excluded, key=lambda c: c.score, reverse=True)[:10]:
        reason = "budget" if comp.tokens_compressed > 0 else "limit"
        print(f"{comp.name:<40} {comp.score:>6.2f} {comp.tokens_compressed:>7} {f'NO ({reason})':>10}")

    if len(excluded) > 10:
        print(f"  ... and {len(excluded) - 10} more excluded components")

    print()
    utilization = (total_tokens / budget * 100) if budget > 0 else 0
    print(f"Total: {total_tokens:,} / {budget:,} tokens ({utilization:.1f}% utilization)")
    print(f"Components: {len(included)} included, {len(excluded)} excluded")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for compile-slm command."""
    parser = argparse.ArgumentParser(
        prog="compile-slm",
        description="Compile ai-toolkit into a minimal SLM system prompt.",
    )
    parser.add_argument(
        "--budget", type=int, default=0,
        help="Token budget (default: auto from model size)",
    )
    parser.add_argument(
        "--model-size",
        choices=list(MODEL_BUDGETS.keys()),
        default="",
        help="Model size (default: auto-detect from Ollama)",
    )
    parser.add_argument(
        "--persona", default="",
        help="Persona preset to prioritize (e.g., backend-lead)",
    )
    parser.add_argument(
        "--lang", default="",
        help="Comma-separated languages to include (e.g., python,typescript)",
    )
    parser.add_argument(
        "--output", default="",
        help="Output file path (default: ~/.ai-toolkit/compiled/slm-system-prompt.md)",
    )
    parser.add_argument(
        "--format",
        choices=["raw", "ollama", "json-string", "aider"],
        default="raw",
        help="Output format (default: raw)",
    )
    parser.add_argument(
        "--level",
        choices=list(COMPRESSION_LEVELS.keys()),
        default="",
        help="Compression level (default: auto from model size)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be included without writing output",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for compile-slm."""
    args = build_parser().parse_args(argv)

    # Resolve model size
    model_size = args.model_size
    if not model_size:
        detected = detect_model_size()
        model_size = detected or DEFAULT_MODEL_SIZE
        if detected:
            print(f"Auto-detected model size: {model_size}", file=sys.stderr)
        else:
            print(f"No model detected, using default: {model_size}", file=sys.stderr)

    # Resolve budget and level
    model_config = MODEL_BUDGETS.get(model_size, MODEL_BUDGETS[DEFAULT_MODEL_SIZE])
    budget = args.budget or int(model_config["budget"])  # type: ignore[arg-type]
    level = args.level or str(model_config["level"])

    # Parse languages
    languages = [l.strip() for l in args.lang.split(",") if l.strip()] if args.lang else []

    # Parse components
    components = parse_components(persona=args.persona, languages=languages)

    # Compress
    compress_all(components, level)

    # Pack
    included, excluded = pack_components(components, budget, level)

    # Dry run
    if args.dry_run:
        print_dry_run(included, excluded, budget, level, args.persona)
        return 0

    # Emit
    markdown = emit_markdown(included)
    output = format_output(markdown, args.format)
    total_tokens = estimate_tokens(markdown)

    # Validate
    errors = validate_output(included, markdown, budget)
    for err in errors:
        print(err, file=sys.stderr)
    if any(e.startswith("FAIL") for e in errors):
        return 1

    # Write output
    output_path = args.output
    if not output_path:
        compiled_dir = Path.home() / ".ai-toolkit" / "compiled"
        compiled_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(compiled_dir / "slm-system-prompt.md")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(output, encoding="utf-8")

    print(f"Compiled {len(included)} components into {total_tokens:,} tokens", file=sys.stderr)
    print(f"Level: {level} | Budget: {budget:,} | Model: {model_size}", file=sys.stderr)
    print(f"Output: {output_path}", file=sys.stderr)

    # Integration guides
    if not args.dry_run:
        print_integration_guide(model_size, output_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
