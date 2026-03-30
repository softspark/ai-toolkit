#!/usr/bin/env python3
"""Inventory documentation files and find gaps in coverage."""

import json
import os
import re
import sys
import time
from pathlib import Path

IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', 'vendor', '.cache'}

SOURCE_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.php', '.dart'}

STANDARD_DOCS = ['README.md', 'CHANGELOG.md', 'CONTRIBUTING.md', 'LICENSE', 'LICENSE.md']

STALE_THRESHOLD_DAYS = 90


def find_files(root: str, extensions: set) -> list:
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            if Path(fn).suffix in extensions or fn in extensions:
                result.append(os.path.join(dirpath, fn))
    return result


def find_doc_files(root: str) -> list:
    docs = []
    # Check standard docs in root
    for doc in STANDARD_DOCS:
        p = os.path.join(root, doc)
        if os.path.isfile(p):
            docs.append(os.path.relpath(p, root))
    # Check docs/ directory
    docs_dir = os.path.join(root, 'docs')
    if os.path.isdir(docs_dir):
        for dirpath, dirnames, filenames in os.walk(docs_dir):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for fn in filenames:
                if fn.endswith(('.md', '.rst', '.txt', '.adoc')):
                    docs.append(os.path.relpath(os.path.join(dirpath, fn), root))
    return docs


def count_public_symbols(filepath: str) -> tuple:
    """Returns (total_public, documented_count)."""
    ext = Path(filepath).suffix
    total, documented = 0, 0
    try:
        with open(filepath, 'r', errors='replace') as f:
            lines = f.readlines()
    except OSError:
        return 0, 0

    if ext == '.py':
        for i, line in enumerate(lines):
            m = re.match(r'^(def|class)\s+(\w+)', line)
            if m and not m.group(2).startswith('_'):
                total += 1
                # Check for docstring on next non-empty line
                for j in range(i + 1, min(i + 4, len(lines))):
                    stripped = lines[j].strip()
                    if stripped.startswith(('"""', "'''")):
                        documented += 1
                        break
                    if stripped and not stripped.startswith(('#', ')')):
                        break

    elif ext in ('.js', '.ts', '.tsx', '.jsx'):
        for i, line in enumerate(lines):
            if re.search(r'export\s+(function|class|const|let|interface|type|enum)\s+', line):
                total += 1
                # Check for JSDoc before export
                for j in range(max(0, i - 5), i):
                    if '/**' in lines[j]:
                        documented += 1
                        break

    elif ext == '.go':
        for i, line in enumerate(lines):
            m = re.match(r'^func\s+(?:\([^)]*\)\s+)?([A-Z]\w*)', line)
            if m:
                total += 1
                # Check for // comment on preceding line
                if i > 0 and lines[i - 1].strip().startswith('//'):
                    documented += 1
            m = re.match(r'^type\s+([A-Z]\w*)', line)
            if m:
                total += 1
                if i > 0 and lines[i - 1].strip().startswith('//'):
                    documented += 1

    elif ext == '.php':
        for i, line in enumerate(lines):
            m = re.match(r'\s*(?:public|protected)\s+function\s+(\w+)', line)
            if m and not m.group(1).startswith('_'):
                total += 1
                for j in range(max(0, i - 5), i):
                    if '/**' in lines[j]:
                        documented += 1
                        break

    elif ext == '.dart':
        for i, line in enumerate(lines):
            m = re.match(r'^(?:class|enum)\s+(\w+)', line)
            if not m:
                m = re.match(r'^(\w+\s+\w+)\s*\(', line)
            if m:
                total += 1
                for j in range(max(0, i - 5), i):
                    if '///' in lines[j]:
                        documented += 1
                        break

    return total, documented


def get_mtime(filepath: str) -> float:
    try:
        return os.path.getmtime(filepath)
    except OSError:
        return 0.0


def main():
    root = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    if not os.path.isdir(root):
        print(json.dumps({"error": f"Not a directory: {root}"}))
        sys.exit(1)

    existing_docs = find_doc_files(root)
    missing_docs = [d for d in STANDARD_DOCS if d not in existing_docs]

    # Count public symbols across source files
    source_files = find_files(root, SOURCE_EXTS)
    total_public, total_documented = 0, 0
    latest_code_mtime = 0.0

    for sf in source_files:
        pub, doc = count_public_symbols(sf)
        total_public += pub
        total_documented += doc
        mt = get_mtime(sf)
        if mt > latest_code_mtime:
            latest_code_mtime = mt

    coverage = round((total_documented / total_public * 100), 1) if total_public > 0 else 0.0

    # Check for stale docs
    stale_docs = []
    threshold = STALE_THRESHOLD_DAYS * 86400
    for doc in existing_docs:
        doc_path = os.path.join(root, doc)
        doc_mtime = get_mtime(doc_path)
        if latest_code_mtime > 0 and doc_mtime > 0:
            if (latest_code_mtime - doc_mtime) > threshold:
                days_behind = int((latest_code_mtime - doc_mtime) / 86400)
                stale_docs.append({"file": doc, "days_behind_code": days_behind})

    result = {
        "existing_docs": existing_docs,
        "missing_docs": missing_docs,
        "public_functions_total": total_public,
        "documented_count": total_documented,
        "doc_coverage_percent": coverage,
        "stale_docs": stale_docs,
    }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
