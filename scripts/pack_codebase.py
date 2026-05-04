#!/usr/bin/env python3
"""Pack a codebase into a single AI-friendly markdown file under a token budget.

Walks the current working directory (or --root), respects .gitignore, ranks files
by extension + size, and writes a single markdown file with a table of contents
and per-file blocks. Files over the per-file size cap are summarized to head + tail.

Usage:
    python3 scripts/pack_codebase.py [options]
    ai-toolkit pack-codebase [options]

Options:
    --root PATH             Root directory to pack (default: CWD)
    --output PATH           Output file (default: ./pack-codebase.md)
    --budget N[k|m]         Token budget; supports "100k", "1m" (default: 100k)
    --include GLOB[,GLOB]   Include only matching paths (relative globs)
    --exclude GLOB[,GLOB]   Exclude matching paths (added to gitignore set)
    --max-file-bytes N      Per-file byte cap before head/tail truncation (default: 8000)
    --head-lines N          Lines kept from head when truncating (default: 60)
    --tail-lines N          Lines kept from tail when truncating (default: 20)
    --dry-run               List files that would be included; do not write output
    --json                  Emit a JSON manifest to stdout instead of markdown

Exit codes:
    0  pack succeeded (or dry-run completed)
    1  budget exceeded with no files left to drop
    2  no files matched after include/exclude
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Token estimate: 4 chars per token is the standard rough heuristic for English / code.
CHARS_PER_TOKEN = 4

DEFAULT_BUDGET = "100k"
DEFAULT_MAX_FILE_BYTES = 8000
DEFAULT_HEAD_LINES = 60
DEFAULT_TAIL_LINES = 20

CODE_EXTS = {
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".kts", ".swift", ".rb", ".php",
    ".cs", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx",
    ".dart", ".scala", ".clj", ".ex", ".exs", ".erl", ".lua", ".sh",
    ".bash", ".zsh", ".fish", ".ps1",
}
CONFIG_EXTS = {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env.example"}
CONFIG_NAMES = {"Dockerfile", "Makefile", "Procfile", ".dockerignore", ".gitignore"}
DOC_EXTS = {".md", ".mdx", ".rst", ".txt"}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".avi", ".webm", ".wav", ".ogg",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".so", ".dylib", ".dll", ".exe", ".class", ".jar",
    ".pyc", ".pyo", ".o", ".a", ".node",
}

ALWAYS_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "dist", "build", ".next", ".nuxt", ".output",
    "target", "coverage", ".coverage", "htmlcov", ".tox", ".idea", ".vscode",
    ".DS_Store",
}


@dataclass
class FileEntry:
    path: Path
    rel: str
    size: int
    category: str  # "code" | "config" | "docs" | "other"
    priority: int = 0  # higher = include first
    included: bool = False
    truncated: bool = False
    body: str = ""

    def estimated_tokens(self) -> int:
        return max(len(self.body) // CHARS_PER_TOKEN, 1) if self.body else 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_budget(value: str) -> int:
    v = value.strip().lower()
    if v.endswith("k"):
        return int(float(v[:-1]) * 1_000)
    if v.endswith("m"):
        return int(float(v[:-1]) * 1_000_000)
    return int(v)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pack a codebase into a single AI-friendly markdown file.")
    p.add_argument("--root", default=os.getcwd())
    p.add_argument("--output", default="pack-codebase.md")
    p.add_argument("--budget", default=DEFAULT_BUDGET)
    p.add_argument("--include", default="")
    p.add_argument("--exclude", default="")
    p.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    p.add_argument("--head-lines", type=int, default=DEFAULT_HEAD_LINES)
    p.add_argument("--tail-lines", type=int, default=DEFAULT_TAIL_LINES)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# .gitignore handling (minimal — directory + glob patterns, no negations)
# ---------------------------------------------------------------------------


def load_gitignore_patterns(root: Path) -> list[str]:
    gi = root / ".gitignore"
    if not gi.exists():
        return []
    patterns: list[str] = []
    for line in gi.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        patterns.append(line)
    return patterns


def matches_pattern(rel_path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        pattern = pattern + "**"
    if "/" in pattern:
        return fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(rel_path, pattern.lstrip("/"))
    return any(fnmatch.fnmatch(part, pattern) for part in rel_path.split("/"))


def should_skip(rel_path: str, name: str, patterns: list[str]) -> bool:
    parts = rel_path.split("/")
    if any(part in ALWAYS_SKIP_DIRS for part in parts):
        return True
    return any(matches_pattern(rel_path, p) for p in patterns)


# ---------------------------------------------------------------------------
# Categorization
# ---------------------------------------------------------------------------


def categorize(path: Path) -> tuple[str, int]:
    name = path.name
    suffix = path.suffix.lower()
    if suffix in BINARY_EXTS:
        return ("binary", -1)
    if name in CONFIG_NAMES or suffix in CONFIG_EXTS:
        return ("config", 80)
    if suffix in CODE_EXTS:
        return ("code", 100)
    if suffix in DOC_EXTS:
        return ("docs", 60)
    return ("other", 20)


# ---------------------------------------------------------------------------
# File discovery + body extraction
# ---------------------------------------------------------------------------


def discover_files(
    root: Path,
    include_globs: list[str],
    extra_exclude: list[str],
) -> list[FileEntry]:
    patterns = load_gitignore_patterns(root) + extra_exclude
    entries: list[FileEntry] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = [d for d in dirnames if d not in ALWAYS_SKIP_DIRS]
        if rel_dir and should_skip(rel_dir, os.path.basename(dirpath), patterns):
            dirnames[:] = []
            continue
        for fname in filenames:
            rel = f"{rel_dir}/{fname}" if rel_dir else fname
            if should_skip(rel, fname, patterns):
                continue
            if include_globs and not any(matches_pattern(rel, g) for g in include_globs):
                continue
            full = Path(dirpath) / fname
            try:
                size = full.stat().st_size
            except OSError:
                continue
            category, priority = categorize(full)
            if category == "binary":
                continue
            entries.append(FileEntry(path=full, rel=rel, size=size, category=category, priority=priority))
    return entries


def read_body(entry: FileEntry, max_bytes: int, head_lines: int, tail_lines: int) -> None:
    try:
        text = entry.path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        entry.body = ""
        return
    if entry.size <= max_bytes:
        entry.body = text
        return
    lines = text.splitlines()
    head = "\n".join(lines[:head_lines])
    tail = "\n".join(lines[-tail_lines:]) if tail_lines > 0 else ""
    omitted = max(len(lines) - head_lines - tail_lines, 0)
    parts = [head]
    if omitted > 0:
        parts.append(f"\n... [{omitted} lines omitted — file truncated to fit budget] ...\n")
    if tail:
        parts.append(tail)
    entry.body = "\n".join(parts)
    entry.truncated = True


# ---------------------------------------------------------------------------
# Selection under budget
# ---------------------------------------------------------------------------


def select_under_budget(entries: list[FileEntry], budget_tokens: int) -> tuple[list[FileEntry], int]:
    entries.sort(key=lambda e: (-e.priority, e.size, e.rel))
    used = 0
    chosen: list[FileEntry] = []
    for e in entries:
        cost = e.estimated_tokens()
        if cost == 0:
            continue
        if used + cost > budget_tokens:
            continue
        e.included = True
        chosen.append(e)
        used += cost
    return chosen, used


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def render_markdown(root: Path, chosen: list[FileEntry], budget_tokens: int, used_tokens: int) -> str:
    lines: list[str] = []
    lines.append(f"# Codebase Pack — {root.name}")
    lines.append("")
    lines.append(f"- Root: `{root}`")
    lines.append(f"- Files included: {len(chosen)}")
    lines.append(f"- Estimated tokens: {used_tokens:,} / {budget_tokens:,} budget")
    lines.append(f"- Truncated files: {sum(1 for e in chosen if e.truncated)}")
    lines.append("")
    lines.append("## Table of Contents")
    lines.append("")
    for e in chosen:
        marker = " (truncated)" if e.truncated else ""
        lines.append(f"- `{e.rel}` ({e.category}, {e.size:,} B){marker}")
    lines.append("")
    lines.append("---")
    lines.append("")
    for e in chosen:
        suffix = e.path.suffix.lstrip(".") or "text"
        fence_lang = {"py": "python", "ts": "typescript", "tsx": "tsx", "js": "javascript",
                      "jsx": "jsx", "go": "go", "rs": "rust", "rb": "ruby", "kt": "kotlin",
                      "swift": "swift", "java": "java", "cpp": "cpp", "c": "c", "sh": "bash",
                      "yml": "yaml", "yaml": "yaml", "json": "json", "toml": "toml",
                      "md": "markdown", "php": "php", "cs": "csharp", "dart": "dart"}.get(suffix, suffix)
        lines.append(f"## `{e.rel}`")
        if e.truncated:
            lines.append("")
            lines.append("> _File truncated to fit the token budget._")
        lines.append("")
        lines.append(f"```{fence_lang}")
        lines.append(e.body.rstrip("\n"))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def render_manifest(root: Path, chosen: list[FileEntry], dropped: list[FileEntry], budget_tokens: int, used_tokens: int) -> dict:
    return {
        "root": str(root),
        "budget_tokens": budget_tokens,
        "used_tokens": used_tokens,
        "files_included": [
            {"path": e.rel, "category": e.category, "size": e.size, "tokens": e.estimated_tokens(), "truncated": e.truncated}
            for e in chosen
        ],
        "files_dropped": [
            {"path": e.rel, "category": e.category, "size": e.size, "reason": "over_budget"}
            for e in dropped
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: root is not a directory: {root}", file=sys.stderr)
        return 1
    budget_tokens = parse_budget(args.budget)
    include_globs = [g.strip() for g in args.include.split(",") if g.strip()]
    extra_exclude = [g.strip() for g in args.exclude.split(",") if g.strip()]

    entries = discover_files(root, include_globs, extra_exclude)
    if not entries:
        print("No files matched after include/exclude filters.", file=sys.stderr)
        return 2

    for e in entries:
        read_body(e, args.max_file_bytes, args.head_lines, args.tail_lines)

    chosen, used_tokens = select_under_budget(entries, budget_tokens)
    dropped = [e for e in entries if not e.included]

    if args.json:
        manifest = render_manifest(root, chosen, dropped, budget_tokens, used_tokens)
        print(json.dumps(manifest, indent=2))
        return 0

    if args.dry_run:
        print(f"Would include {len(chosen)} files (~{used_tokens:,} tokens), drop {len(dropped)}.")
        for e in chosen:
            tag = " [trunc]" if e.truncated else ""
            print(f"  + {e.rel} ({e.category}, {e.size} B, ~{e.estimated_tokens()} tok){tag}")
        for e in dropped[:20]:
            print(f"  - {e.rel} ({e.category}, {e.size} B) — over budget")
        if len(dropped) > 20:
            print(f"  ... and {len(dropped) - 20} more dropped.")
        return 0

    output = Path(args.output)
    if not output.is_absolute():
        output = Path.cwd() / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(root, chosen, budget_tokens, used_tokens), encoding="utf-8")
    print(f"Wrote {output} — {len(chosen)} files, ~{used_tokens:,} tokens / {budget_tokens:,} budget.")
    if dropped:
        print(f"Dropped {len(dropped)} file(s) over budget. Re-run with a larger --budget if needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
