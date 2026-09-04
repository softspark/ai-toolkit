# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit

"""The one YAML-frontmatter parser for every Markdown file the toolkit reads.

The toolkit emits its own frontmatter and ``validate.py`` polices it, so this
is deliberately a *subset* of YAML, not a YAML implementation. Anything the
subset cannot represent is an error, never a silent guess: a stricter parser
downstream (Claude Code, Codex, an editor plugin) must not see a different
document than the toolkit saw.

Supported grammar (indentation-based, two spaces per level recommended, any
consistent indent accepted):

* ``key: value`` with a plain scalar, ``"double"`` / ``'single'`` quoted
  scalar, or a flow list of scalars ``[a, "b"]``.
* ``key: >-`` / ``>`` / ``|`` / ``|-`` block scalars on the following indented
  lines.
* ``key:`` followed by an indented block list (``- item``) or nested map.
  List items may themselves be maps (``- matcher: "Bash"`` + indented keys).
* ``# comment`` lines; a `` #`` after a quoted scalar.

Rejected in strict mode (the default) because a YAML parser would read them
as something else: a plain scalar containing ``: `` or `` #``, anchors and
tags (``&``, ``*``, ``!``), flow maps (``{``), duplicate keys, quoted keys,
tabs in indentation, and an unterminated block. ``strict=False`` keeps the
plain-scalar hazards as literal text for read-only tools (doctor, surface
manifest) that must describe a broken file rather than refuse it.

Stdlib-only. Values come back as ``str``, ``list``, or ``dict``; nothing is
coerced to bool or int, callers decide.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Union

__all__ = [
    "FrontmatterError",
    "frontmatter_block",
    "frontmatter_field",
    "frontmatter_sections",
    "load_frontmatter",
    "parse_frontmatter",
    "parse_scalar",
    "split_frontmatter",
]

Value = Union[str, list[Any], dict[str, Any]]

_DELIMITER = "---"
_BLOCK_INDICATORS = (">", "|")
_RESERVED_INDICATORS = ("&", "*", "!", "{", "%", "@", "`")


class FrontmatterError(ValueError):
    """A frontmatter block that the toolkit subset cannot represent."""


# ---------------------------------------------------------------------------
# Splitting
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return ``(block, body)``.

    ``block`` is the text between the ``---`` delimiter lines without the
    delimiters, or ``None`` when the document has no frontmatter. ``body`` is
    everything after the closing delimiter line, with the delimiter's own
    newline removed and nothing else stripped, so callers keep whatever
    ``strip()`` policy they already had.

    A leading BOM and CRLF line endings are normalised. An opening delimiter
    without a closing one is an error, not "no frontmatter": treating it as
    body would ship the half-block as prose.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    if "\r" in text:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith(_DELIMITER):
        return None, text
    first_newline = text.find("\n")
    if first_newline == -1:
        opening = text
    else:
        opening = text[:first_newline]
    if opening.rstrip() != _DELIMITER:
        # `----` or `--- foo` is prose, not a delimiter.
        return None, text
    if first_newline == -1:
        raise FrontmatterError("frontmatter opened on the last line and never closed")
    cursor = first_newline + 1
    while True:
        line_end = text.find("\n", cursor)
        line = text[cursor:] if line_end == -1 else text[cursor:line_end]
        if line.rstrip() == _DELIMITER:
            block = text[first_newline + 1:cursor]
            body = "" if line_end == -1 else text[line_end + 1:]
            return block.rstrip("\n"), body
        if line_end == -1:
            raise FrontmatterError("frontmatter block is not terminated by a '---' line")
        cursor = line_end + 1


# ---------------------------------------------------------------------------
# Scalars
# ---------------------------------------------------------------------------

def _unescape_double(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch == "\\" and i + 1 < len(raw):
            nxt = raw[i + 1]
            out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, "\\" + nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _split_quoted(raw: str, quote: str) -> tuple[str, str]:
    """Return ``(inner, remainder)`` for a scalar that starts with ``quote``."""
    i = 1
    while i < len(raw):
        ch = raw[i]
        if quote == '"' and ch == "\\":
            i += 2
            continue
        if ch == quote:
            if quote == "'" and i + 1 < len(raw) and raw[i + 1] == "'":
                i += 2
                continue
            return raw[1:i], raw[i + 1:]
        i += 1
    raise FrontmatterError(f"unterminated {quote} quoted scalar: {raw}")


def _reject_trailing(remainder: str, raw: str) -> None:
    rest = remainder.strip()
    if rest and not rest.startswith("#"):
        raise FrontmatterError(f"unexpected text after quoted scalar: {raw}")


def parse_scalar(raw: str, *, strict: bool = True) -> str:
    """Decode one scalar value as it appears after ``key:``."""
    value = raw.strip()
    if not value:
        return ""
    if value[0] == '"':
        inner, rest = _split_quoted(value, '"')
        _reject_trailing(rest, value)
        return _unescape_double(inner)
    if value[0] == "'":
        inner, rest = _split_quoted(value, "'")
        _reject_trailing(rest, value)
        return inner.replace("''", "'")
    if value[0] in _RESERVED_INDICATORS:
        raise FrontmatterError(
            f"scalar starts with YAML indicator '{value[0]}' (anchor, tag, or flow map); "
            f"quote it: {value}"
        )
    if strict and (": " in value or value.endswith(":")):
        raise FrontmatterError(
            f"plain scalar contains ': ' and would parse as a nested mapping; "
            f"quote it or use a '>-' block: {value}"
        )
    if " #" in value or value.startswith("#"):
        if strict:
            raise FrontmatterError(
                f"plain scalar contains ' #' and would be cut as a comment; quote it: {value}"
            )
        return value.split(" #", 1)[0].rstrip()
    return value


def _parse_flow_list(raw: str, *, strict: bool) -> list[str]:
    inner = raw.strip()[1:-1]
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(inner):
        ch = inner[i]
        if quote:
            current.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(inner):
                current.append(inner[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            current.append(ch)
        elif ch == ",":
            items.append("".join(current))
            current = []
        elif ch in "[{":
            raise FrontmatterError(f"nested flow collections are unsupported: {raw}")
        else:
            current.append(ch)
        i += 1
    if quote:
        raise FrontmatterError(f"unterminated quote in flow list: {raw}")
    if current or items:
        items.append("".join(current))
    result: list[str] = []
    for item in items:
        if not item.strip():
            if strict:
                raise FrontmatterError(f"empty item in flow list: {raw}")
            continue
        result.append(parse_scalar(item, strict=strict))
    return result


# ---------------------------------------------------------------------------
# Block structure
# ---------------------------------------------------------------------------

class _Line:
    __slots__ = ("indent", "number", "text")

    def __init__(self, number: int, raw: str) -> None:
        if raw[: len(raw) - len(raw.lstrip(" \t"))].find("\t") != -1:
            raise FrontmatterError(f"line {number}: tab in indentation")
        self.number = number
        self.indent = len(raw) - len(raw.lstrip(" "))
        self.text = raw.strip()


def _logical_lines(block: str) -> list[_Line]:
    lines: list[_Line] = []
    for number, raw in enumerate(block.splitlines(), start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append(_Line(number, raw))
    return lines


def _split_key(line: _Line) -> tuple[str, str]:
    text = line.text
    if text[0] in "\"'":
        raise FrontmatterError(f"line {line.number}: quoted keys are unsupported")
    sep = text.find(":")
    if sep <= 0:
        raise FrontmatterError(f"line {line.number}: expected 'key: value', got: {text}")
    after = text[sep + 1:]
    if after and not after[0].isspace():
        raise FrontmatterError(f"line {line.number}: expected 'key: value', got: {text}")
    key = text[:sep].strip()
    if not key or any(ch.isspace() for ch in key):
        raise FrontmatterError(f"line {line.number}: invalid key: {text}")
    return key, after.strip()


def _block_scalar(lines: list[_Line], index: int, parent_indent: int,
                  indicator: str, raw_lines: list[str]) -> tuple[str, int]:
    """Collect an indented block scalar. Returns ``(value, next_index)``."""
    fold = indicator[0] == ">"
    chomp = indicator.endswith("-")
    collected: list[str] = []
    while index < len(lines) and lines[index].indent > parent_indent:
        collected.append(raw_lines[lines[index].number - 2])
        index += 1
    if not collected:
        return "", index
    indent = min(len(line) - len(line.lstrip(" ")) for line in collected)
    stripped = [line[indent:] for line in collected]
    if fold:
        value = " ".join(part.strip() for part in stripped)
    else:
        value = "\n".join(stripped)
    return (value if chomp else value + "\n"), index


def _parse_value(lines: list[_Line], index: int, parent_indent: int,
                 raw: str, raw_lines: list[str], *, strict: bool) -> tuple[Value, int]:
    """Parse the value that follows ``key:`` on ``lines[index - 1]``."""
    if raw:
        if raw[0] in _BLOCK_INDICATORS:
            if raw not in (">", ">-", "|", "|-"):
                raise FrontmatterError(f"unsupported block scalar header: {raw}")
            return _block_scalar(lines, index, parent_indent, raw, raw_lines)
        if raw[0] == "[":
            if not raw.endswith("]"):
                raise FrontmatterError(f"flow list must close on the same line: {raw}")
            return _parse_flow_list(raw, strict=strict), index
        return parse_scalar(raw, strict=strict), index
    # Nothing after the colon: an indented list or map follows, or the value is empty.
    if index < len(lines) and lines[index].indent > parent_indent:
        return _parse_block(lines, index, raw_lines, strict=strict)
    return "", index


def _parse_block(lines: list[_Line], index: int, raw_lines: list[str],
                 *, strict: bool) -> tuple[Value, int]:
    """Parse a map or list whose first line is ``lines[index]``."""
    indent = lines[index].indent
    if lines[index].text.startswith("- ") or lines[index].text == "-":
        return _parse_list(lines, index, indent, raw_lines, strict=strict)
    return _parse_map(lines, index, indent, raw_lines, strict=strict)


def _parse_map(lines: list[_Line], index: int, indent: int, raw_lines: list[str],
               *, strict: bool) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while index < len(lines) and lines[index].indent == indent:
        line = lines[index]
        if line.text.startswith("- "):
            raise FrontmatterError(f"line {line.number}: list item where a key was expected")
        key, raw = _split_key(line)
        if key in result:
            raise FrontmatterError(f"line {line.number}: duplicate key '{key}'")
        value, index = _parse_value(lines, index + 1, indent, raw, raw_lines, strict=strict)
        result[key] = value
    if index < len(lines) and lines[index].indent > indent:
        raise FrontmatterError(f"line {lines[index].number}: unexpected indentation")
    return result, index


def _parse_list(lines: list[_Line], index: int, indent: int, raw_lines: list[str],
                *, strict: bool) -> tuple[list[Any], int]:
    result: list[Any] = []
    while index < len(lines) and lines[index].indent == indent:
        line = lines[index]
        if not (line.text.startswith("- ") or line.text == "-"):
            raise FrontmatterError(f"line {line.number}: key where a list item was expected")
        item_text = line.text[1:].strip()
        if not item_text:
            # `-` alone: a nested block on the following lines.
            value, index = _parse_value(lines, index + 1, indent, "", raw_lines, strict=strict)
            result.append(value)
            continue
        # A list item that is itself a map starts with `key: value`; its
        # remaining keys sit on following lines indented past the dash.
        if _looks_like_key(item_text):
            key, raw = _split_key(_Line(line.number, " " * (indent + 2) + item_text))
            item_indent = indent + 2
            value, index = _parse_value(lines, index + 1, item_indent, raw, raw_lines, strict=strict)
            item: dict[str, Any] = {key: value}
            while index < len(lines) and lines[index].indent > indent:
                if lines[index].indent != item_indent:
                    raise FrontmatterError(f"line {lines[index].number}: unexpected indentation")
                nkey, nraw = _split_key(lines[index])
                if nkey in item:
                    raise FrontmatterError(f"line {lines[index].number}: duplicate key '{nkey}'")
                value, index = _parse_value(lines, index + 1, item_indent, nraw, raw_lines, strict=strict)
                item[nkey] = value
            result.append(item)
            continue
        if item_text[0] == "[":
            result.append(_parse_flow_list(item_text, strict=strict))
        else:
            result.append(parse_scalar(item_text, strict=strict))
        index += 1
    return result, index


def _looks_like_key(text: str) -> bool:
    if text[0] in "\"'[":
        return False
    sep = text.find(":")
    if sep <= 0:
        return False
    after = text[sep + 1:]
    key = text[:sep]
    return (not after or after[0].isspace()) and not any(ch.isspace() for ch in key)


# ---------------------------------------------------------------------------
# Public parsing API
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str, *, strict: bool = True) -> dict[str, Any]:
    """Parse a whole document (or a bare block) into a dict.

    Accepts either a full Markdown document starting with ``---`` or the
    block text on its own (as ``split_frontmatter`` returns it). A document
    without frontmatter yields ``{}``.
    """
    block: str | None
    if text.lstrip("\ufeff").startswith(_DELIMITER):
        block, _ = split_frontmatter(text)
    else:
        block = text
    if block is None or not block.strip():
        return {}
    raw_lines = block.replace("\r\n", "\n").split("\n")
    lines = _logical_lines(block)
    if not lines:
        return {}
    if lines[0].indent != 0:
        raise FrontmatterError(f"line {lines[0].number}: top-level entry must not be indented")
    if lines[0].text.startswith("- "):
        raise FrontmatterError("frontmatter must be a mapping, not a list")
    result, index = _parse_map(lines, 0, 0, raw_lines, strict=strict)
    if index != len(lines):
        raise FrontmatterError(f"line {lines[index].number}: unexpected content")
    return result


def load_frontmatter(path: str | Path, *, strict: bool = True) -> dict[str, Any]:
    """``parse_frontmatter`` over a file; a missing file yields ``{}``."""
    filepath = Path(path)
    if not filepath.is_file():
        return {}
    return parse_frontmatter(filepath.read_text(encoding="utf-8"), strict=strict)


def frontmatter_sections(block: str) -> dict[str, list[str]]:
    """Group the raw lines of a block by top-level key, verbatim.

    For tools that re-emit a section unchanged (``generate_opencode_skills``
    copies ``hooks:`` through) and must not normalise quoting or indentation.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in block.splitlines():
        if line and not line[0].isspace() and not line.startswith("#") and ":" in line:
            current = line.split(":", 1)[0].strip()
            sections[current] = [line]
        elif current is not None:
            sections[current].append(line)
    return sections


# ---------------------------------------------------------------------------
# Compatibility helpers (pre-v4.31 API, kept for the 19 existing importers)
# ---------------------------------------------------------------------------

def frontmatter_block(filepath: str | Path) -> str:
    """Return the raw frontmatter text (excluding ``---`` delimiters)."""
    filepath = Path(filepath)
    if not filepath.is_file():
        return ""
    try:
        block, _ = split_frontmatter(filepath.read_text(encoding="utf-8"))
    except FrontmatterError:
        return ""
    return block or ""


def frontmatter_field(filepath: str | Path, field: str) -> str:
    """Return one top-level scalar field from a file, or ``""``.

    Tolerant by design: this is the read path for generators that must keep
    producing output while ``validate.py`` is what rejects a broken file.
    Block scalars are folded to one line; a list or map value yields ``""``.
    """
    filepath = Path(filepath)
    if not filepath.is_file():
        return ""
    try:
        data = parse_frontmatter(filepath.read_text(encoding="utf-8"), strict=False)
    except FrontmatterError:
        return _legacy_field(filepath, field)
    value = data.get(field, "")
    if isinstance(value, str):
        return value.replace("\n", " ").strip()
    return ""


def _legacy_field(filepath: Path, field: str) -> str:
    """Line scan for files the subset parser refuses, so nothing regresses."""
    in_frontmatter = False
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")
            if stripped == _DELIMITER:
                if in_frontmatter:
                    break
                in_frontmatter = True
                continue
            if in_frontmatter and stripped.startswith(f"{field}:"):
                value = stripped[len(field) + 1:].strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                return value
    return ""
