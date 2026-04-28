#!/usr/bin/env python3
"""Generate language-rules knowledge skills from app/rules/<lang>/*.md.

Each language directory under ``app/rules/`` (except ``common/``) is compiled
into a single ``app/skills/<lang>-rules/SKILL.md`` knowledge skill. The skill
is ``user-invocable: false`` so Claude loads it contextually when the
description triggers match (file extensions, framework names).

This is the proper progressive-disclosure replacement for the v1.3.8 pointer
block in ``.claude/CLAUDE.md``: instead of nudging Claude to Read absolute
nvm-pinned paths on demand, the rules ride on the Agent Skills mechanism.

Common rules (``app/rules/common/``) stay inlined in ``CLAUDE.md`` because
they are language-agnostic and should be visible regardless of context.

Idempotent: rerunning overwrites generated SKILL.md but leaves any other
files in the skill directory alone.

Usage:
    python3 scripts/generate_language_rules_skills.py            # write all
    python3 scripts/generate_language_rules_skills.py --check    # dry-run
    python3 scripts/generate_language_rules_skills.py --langs python,rust
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent.parent
RULES_DIR = ROOT / "app" / "rules"
SKILLS_DIR = ROOT / "app" / "skills"

# Per-language description triggers. Concrete file extensions and framework
# names give Claude a high-signal match against user prompts and file paths,
# so the skill activates reliably when the user is actually working in that
# language.
TRIGGERS: dict[str, dict[str, str]] = {
    "python": {
        "label": "Python",
        "triggers": ".py, .pyi, pyproject.toml, requirements.txt, Pipfile, FastAPI, Django, Flask, pytest, SQLAlchemy, ruff, mypy",
    },
    "typescript": {
        "label": "TypeScript/JavaScript",
        "triggers": ".ts, .tsx, .js, .jsx, package.json, tsconfig.json, React, Next.js, Vue, Vite, Vitest, Jest, ESLint",
    },
    "golang": {
        "label": "Go",
        "triggers": ".go, go.mod, go.sum, Gin, Echo, Gorilla, testing, gofmt",
    },
    "rust": {
        "label": "Rust",
        "triggers": ".rs, Cargo.toml, Cargo.lock, Tokio, Axum, Serde, clippy, cargo test",
    },
    "java": {
        "label": "Java",
        "triggers": ".java, pom.xml, build.gradle, Spring, Spring Boot, JPA, Hibernate, JUnit, Maven, Gradle",
    },
    "kotlin": {
        "label": "Kotlin",
        "triggers": ".kt, .kts, build.gradle.kts, Ktor, Jetpack Compose, coroutines, kotlinx",
    },
    "swift": {
        "label": "Swift",
        "triggers": ".swift, Package.swift, .xcodeproj, SwiftUI, Combine, async/await, XCTest",
    },
    "dart": {
        "label": "Dart/Flutter",
        "triggers": ".dart, pubspec.yaml, Flutter, Riverpod, Bloc, widget, StatelessWidget, StatefulWidget",
    },
    "csharp": {
        "label": "C#/.NET",
        "triggers": ".cs, .csproj, .sln, ASP.NET, ASP.NET Core, EF Core, LINQ, NUnit, xUnit, dotnet",
    },
    "php": {
        "label": "PHP",
        "triggers": ".php, composer.json, Laravel, Symfony, PHPUnit, PSR-12, Composer",
    },
    "cpp": {
        "label": "C++",
        "triggers": ".cpp, .cc, .cxx, .hpp, .h, CMakeLists.txt, Makefile, GoogleTest, clang-tidy",
    },
    "ruby": {
        "label": "Ruby",
        "triggers": ".rb, Gemfile, .gemspec, Rails, ActiveRecord, Sidekiq, RSpec, Sorbet, rubocop",
    },
    "medplum": {
        "label": "Medplum (FHIR healthcare)",
        "triggers": "medplum.config.mts, medplum.config.ts, FHIR, Medplum, Bot, Subscription, Questionnaire",
    },
}


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) if present."""
    if not text.startswith("---"):
        return text.lstrip("\n")
    end = text.find("\n---", 3)
    if end == -1:
        return text.lstrip("\n")
    return text[end + 4:].lstrip("\n")


def _category_title(stem: str) -> str:
    """Convert filename stem (e.g. ``coding-style``) to a section title."""
    return " ".join(part.capitalize() for part in stem.split("-"))


def _build_skill_body(lang_dir: Path) -> str:
    """Concatenate all rule category files into a skill body."""
    parts: list[str] = []
    for f in sorted(lang_dir.glob("*.md")):
        body = _strip_frontmatter(f.read_text(encoding="utf-8")).rstrip()
        # If the source file already starts with a top-level "# Title", keep
        # it. Otherwise, prepend a "## Category" header so the skill body
        # has structure.
        if body.lstrip().startswith("#"):
            parts.append(body)
        else:
            parts.append(f"## {_category_title(f.stem)}\n\n{body}")
    return "\n\n".join(parts) + "\n"


def _build_description(lang: str) -> str:
    meta = TRIGGERS.get(lang)
    if not meta:
        return (
            f"{lang.capitalize()} coding rules: coding-style, frameworks, "
            f"patterns, security, testing. Load when writing or reviewing "
            f"{lang.capitalize()} code."
        )
    label = meta["label"]
    triggers = meta["triggers"]
    return (
        f"{label} coding rules from ai-toolkit: coding-style, frameworks, "
        f"patterns, security, testing. "
        f"Triggers: {triggers}. "
        f"Load when writing, reviewing, or editing {label} code."
    )


def _build_skill_md(lang: str, lang_dir: Path) -> str:
    description = _build_description(lang)
    body = _build_skill_body(lang_dir)
    label = TRIGGERS.get(lang, {}).get("label", lang.capitalize())
    frontmatter = dedent(
        f"""\
        ---
        name: {lang}-rules
        description: "{description}"
        effort: medium
        user-invocable: false
        allowed-tools: Read
        ---

        # {label} Rules

        These rules come from `app/rules/{lang}/` in ai-toolkit. They cover
        the project's standards for coding style, frameworks, patterns,
        security, and testing in {label}. Apply them when writing or
        reviewing {label} code.

        """
    )
    return frontmatter + body


def discover_languages() -> list[str]:
    """List language directories under app/rules/ excluding ``common``."""
    if not RULES_DIR.is_dir():
        return []
    out: list[str] = []
    for d in sorted(RULES_DIR.iterdir()):
        if not d.is_dir() or d.name == "common":
            continue
        if any(d.glob("*.md")):
            out.append(d.name)
    return out


def generate(langs: list[str] | None = None, check: bool = False) -> int:
    """Generate skills. Returns count of skills written (or that would be)."""
    languages = langs if langs else discover_languages()
    written = 0
    for lang in languages:
        lang_dir = RULES_DIR / lang
        if not lang_dir.is_dir():
            print(f"  SKIP: {lang} (directory missing)", file=sys.stderr)
            continue
        skill_dir = SKILLS_DIR / f"{lang}-rules"
        skill_md = skill_dir / "SKILL.md"
        content = _build_skill_md(lang, lang_dir)

        if check:
            existing = skill_md.read_text(encoding="utf-8") if skill_md.is_file() else ""
            status = "OK" if existing == content else "DIFF"
            print(f"  [{status}] {skill_md.relative_to(ROOT)}")
            if existing != content:
                written += 1
            continue

        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md.write_text(content, encoding="utf-8")
        print(f"  Wrote: {skill_md.relative_to(ROOT)}")
        written += 1
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument(
        "--langs",
        default="",
        help="Comma-separated language list (default: all)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: report which skills would change without writing",
    )
    args = ap.parse_args()
    langs = [s.strip() for s in args.langs.split(",") if s.strip()] or None
    n = generate(langs=langs, check=args.check)
    if args.check and n > 0:
        print(f"\n{n} skill(s) out of date. Re-run without --check.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
