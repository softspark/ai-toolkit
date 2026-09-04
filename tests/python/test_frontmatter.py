# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
"""Unit tests for scripts/frontmatter.py, the single frontmatter parser.

Run: npm run test:py (pytest, config in pytest.ini). Stdlib parser, pytest is
a dev dependency only; the published package never needs it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from frontmatter import (  # noqa: E402
    FrontmatterError,
    frontmatter_block,
    frontmatter_field,
    frontmatter_sections,
    load_frontmatter,
    parse_frontmatter,
    parse_scalar,
    split_frontmatter,
)

APP = SCRIPTS.parent / "app"
KB = SCRIPTS.parent / "kb"


# ── split ────────────────────────────────────────────────────────────────────

def test_split_returns_block_and_untouched_body() -> None:
    block, body = split_frontmatter("---\nname: x\n---\n\n# Title\nbody\n")
    assert block == "name: x"
    assert body == "\n# Title\nbody\n"


def test_split_without_frontmatter() -> None:
    assert split_frontmatter("# Just prose\n") == (None, "# Just prose\n")


@pytest.mark.parametrize("text", ["----\nnot a delimiter\n", "--- foo\nx\n"])
def test_split_treats_decorated_dashes_as_prose(text: str) -> None:
    assert split_frontmatter(text) == (None, text)


def test_split_rejects_unterminated_block() -> None:
    with pytest.raises(FrontmatterError, match="not terminated"):
        split_frontmatter("---\nname: x\nbody without closing\n")


def test_split_normalises_bom_and_crlf() -> None:
    block, body = split_frontmatter("\ufeff---\r\nname: x\r\n---\r\nbody\r\n")
    assert block == "name: x"
    assert body == "body\n"


def test_split_closing_delimiter_on_last_line() -> None:
    assert split_frontmatter("---\nname: x\n---") == ("name: x", "")


# ── scalars ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("plain", "plain"),
        ('"quoted: with colon"', "quoted: with colon"),
        ("'single ''escaped'' quote'", "single 'escaped' quote"),
        ('"esc \\"q\\" and \\\\ back"', 'esc "q" and \\ back'),
        ('"trailing" # comment', "trailing"),
        ("  spaced  ", "spaced"),
        ("", ""),
        ("Read, Write, Edit", "Read, Write, Edit"),
        ("v1.2.3", "v1.2.3"),
    ],
)
def test_parse_scalar(raw: str, expected: str) -> None:
    assert parse_scalar(raw) == expected


def test_parse_scalar_rejects_colon_space_in_strict() -> None:
    # The legal-pl defect: "IT: body leasing" inside an unquoted description.
    with pytest.raises(FrontmatterError, match="nested mapping"):
        parse_scalar("Contracts (B2B, IT: body leasing)")
    assert parse_scalar("Contracts (B2B, IT: body leasing)", strict=False) == \
        "Contracts (B2B, IT: body leasing)"


def test_parse_scalar_rejects_inline_comment_in_strict() -> None:
    with pytest.raises(FrontmatterError, match="comment"):
        parse_scalar("value # note")
    assert parse_scalar("value # note", strict=False) == "value"


@pytest.mark.parametrize("raw", ["&anchor", "*alias", "!!str x", "{a: 1}", "%YAML"])
def test_parse_scalar_rejects_yaml_indicators(raw: str) -> None:
    with pytest.raises(FrontmatterError, match="indicator"):
        parse_scalar(raw)


def test_parse_scalar_rejects_unterminated_quote() -> None:
    with pytest.raises(FrontmatterError, match="unterminated"):
        parse_scalar('"open')


def test_parse_scalar_rejects_text_after_quote() -> None:
    with pytest.raises(FrontmatterError, match="after quoted"):
        parse_scalar('"a" b')


# ── documents ────────────────────────────────────────────────────────────────

SKILL = """---
name: git-commit
description: "Create a commit: staged changes only"
allowed-tools: Read, Bash
user-invocable: true
disable-model-invocation: true
tags: [git, "commit, message", vcs]
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "echo 'lint first'"
scripts:
  - scripts/ci-detect.py
paths:
  - "**/*.test.*"
  - "**/tests/**"
---

# Git Commit
body
"""


def test_parse_full_skill_document() -> None:
    data = parse_frontmatter(SKILL)
    assert data["name"] == "git-commit"
    assert data["description"] == "Create a commit: staged changes only"
    assert data["allowed-tools"] == "Read, Bash"
    assert data["user-invocable"] == "true"  # never coerced
    assert data["tags"] == ["git", "commit, message", "vcs"]
    assert data["scripts"] == ["scripts/ci-detect.py"]
    assert data["paths"] == ["**/*.test.*", "**/tests/**"]
    assert data["hooks"] == {
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [{"type": "command", "command": "echo 'lint first'"}],
            }
        ]
    }


def test_parse_bare_block_and_empty_document() -> None:
    assert parse_frontmatter("name: x\nversion: \"1.0.0\"") == {"name": "x", "version": "1.0.0"}
    assert parse_frontmatter("# no frontmatter\n") == {}
    assert parse_frontmatter("---\n---\nbody") == {}


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (">-", "folded line one and two"),
        (">", "folded line one and two\n"),
        ("|-", "folded line one\nand two"),
        ("|", "folded line one\nand two\n"),
    ],
)
def test_block_scalars(header: str, expected: str) -> None:
    doc = f"---\ndescription: {header}\n  folded line one\n  and two\nname: n\n---\n"
    data = parse_frontmatter(doc)
    assert data["description"] == expected
    assert data["name"] == "n"


def test_block_scalar_keeps_colons_and_hashes() -> None:
    doc = "---\ndescription: >-\n  IT: body leasing # not a comment\n---\n"
    assert parse_frontmatter(doc)["description"] == "IT: body leasing # not a comment"


def test_comments_and_blank_lines_are_skipped() -> None:
    doc = "---\n# leading comment\nname: x\n\n  # indented comment\nversion: \"1\"\n---\n"
    assert parse_frontmatter(doc) == {"name": "x", "version": "1"}


def test_empty_value_without_block_is_empty_string() -> None:
    assert parse_frontmatter("---\nagent:\nname: x\n---\n") == {"agent": "", "name": "x"}


def test_nested_map_of_scalars() -> None:
    doc = "---\nmeta:\n  owner: me\n  level: \"2\"\nname: x\n---\n"
    assert parse_frontmatter(doc) == {"meta": {"owner": "me", "level": "2"}, "name": "x"}


def test_list_of_flow_lists_and_dash_only_items() -> None:
    doc = "---\nmatrix:\n  - [a, b]\n  -\n    - c\n---\n"
    assert parse_frontmatter(doc) == {"matrix": [["a", "b"], ["c"]]}


@pytest.mark.parametrize(
    ("doc", "message"),
    [
        ("---\nname: a\nname: b\n---\n", "duplicate key"),
        ("---\n\"name\": a\n---\n", "quoted keys"),
        ("---\n\tname: a\n---\n", "tab in indentation"),
        ("---\nname a\n---\n", "expected 'key: value'"),
        ("---\n- item\n---\n", "must be a mapping"),
        ("---\nname: x\n  extra: y\n---\n", "unexpected indentation"),
        ("---\nlist:\n  - a\n  key: b\n---\n", "key where a list item"),
        ("---\nmap:\n  key: a\n  - b\n---\n", "list item where a key"),
        ("---\ntags: [a, [b]]\n---\n", "nested flow"),
        ("---\ntags: [a,\n---\n", "close on the same line"),
        ("---\ndescription: >+\n  x\n---\n", "block scalar header"),
        ("---\ndescription: A: B\n---\n", "nested mapping"),
    ],
)
def test_strict_rejections(doc: str, message: str) -> None:
    with pytest.raises(FrontmatterError, match=message):
        parse_frontmatter(doc)


def test_non_strict_keeps_hazards_as_text() -> None:
    doc = "---\ndescription: A: B # c\nname: x\n---\n"
    assert parse_frontmatter(doc, strict=False) == {"description": "A: B", "name": "x"}


# ── helpers ──────────────────────────────────────────────────────────────────

def test_frontmatter_sections_keeps_raw_lines() -> None:
    block = 'name: x\nhooks:\n  PreToolUse:\n    - matcher: "Bash"\n# c\nagent: y'
    sections = frontmatter_sections(block)
    assert sections["hooks"] == ["hooks:", "  PreToolUse:", '    - matcher: "Bash"', "# c"]
    assert sections["agent"] == ["agent: y"]


def test_file_helpers(tmp_path: Path) -> None:
    f = tmp_path / "SKILL.md"
    f.write_text('---\nname: demo\ndescription: >-\n  two\n  lines\ntags: [a]\n---\nbody\n', encoding="utf-8")
    assert load_frontmatter(f)["name"] == "demo"
    assert frontmatter_field(f, "name") == "demo"
    assert frontmatter_field(f, "description") == "two lines"
    assert frontmatter_field(f, "tags") == ""  # non-scalar yields empty
    assert frontmatter_field(f, "missing") == ""
    assert frontmatter_block(f) == 'name: demo\ndescription: >-\n  two\n  lines\ntags: [a]'
    assert load_frontmatter(tmp_path / "absent.md") == {}
    assert frontmatter_field(tmp_path / "absent.md", "name") == ""


def test_frontmatter_field_survives_a_file_the_subset_rejects(tmp_path: Path) -> None:
    # Generators must keep producing output; validate.py is the gate.
    f = tmp_path / "SKILL.md"
    f.write_text("---\nname: legal\ndescription: IT: body leasing\n---\n", encoding="utf-8")
    assert frontmatter_field(f, "name") == "legal"
    assert frontmatter_field(f, "description") == "IT: body leasing"


# ── corpus: every shipped Markdown file parses strictly ──────────────────────

def _corpus() -> list[Path]:
    files = sorted(APP.rglob("*.md")) + sorted(KB.rglob("*.md"))
    return [f for f in files if f.read_text(encoding="utf-8", errors="replace").startswith("---")]


@pytest.mark.parametrize("path", _corpus(), ids=lambda p: str(p.relative_to(SCRIPTS.parent)))
def test_shipped_frontmatter_parses_strictly(path: Path) -> None:
    data = load_frontmatter(path)
    assert isinstance(data, dict)
    if path.name == "SKILL.md":
        assert isinstance(data.get("name"), str) and data["name"]
        assert isinstance(data.get("description"), str) and data["description"]
