#!/usr/bin/env python3
"""Extract import graph from source files and generate Mermaid syntax."""

import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', 'vendor', '.cache'}

LANG_MAP = {
    '.py': 'python',
    '.js': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.jsx': 'javascript',
    '.go': 'go',
    '.php': 'php',
}

SOURCE_EXTS = set(LANG_MAP.keys())

IMPORT_PATTERNS = {
    'python': [
        re.compile(r'^\s*import\s+([\w.]+)'),
        re.compile(r'^\s*from\s+([\w.]+)\s+import'),
    ],
    'javascript': [
        re.compile(r'''import\s+.*?from\s+['"]([^'"]+)['"]'''),
        re.compile(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''),
    ],
    'typescript': [
        re.compile(r'''import\s+.*?from\s+['"]([^'"]+)['"]'''),
        re.compile(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''),
    ],
    'go': [
        re.compile(r'^\s*"([^"]+)"'),
        re.compile(r'^\s*import\s+"([^"]+)"'),
    ],
    'php': [
        re.compile(r'^\s*use\s+([\w\\]+)'),
    ],
}

FUNC_CLASS_PATTERNS = {
    'python': {
        'function': re.compile(r'^\s*def\s+(\w+)\s*\('),
        'class': re.compile(r'^\s*class\s+(\w+)'),
    },
    'javascript': {
        'function': re.compile(r'(?:^|\s)function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\('),
        'class': re.compile(r'^\s*class\s+(\w+)'),
    },
    'typescript': {
        'function': re.compile(r'(?:^|\s)function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\('),
        'class': re.compile(r'^\s*(?:class|interface)\s+(\w+)'),
    },
    'go': {
        'function': re.compile(r'^\s*func\s+(?:\([^)]*\)\s+)?(\w+)\s*\('),
        'class': re.compile(r'^\s*type\s+(\w+)\s+(?:struct|interface)'),
    },
    'php': {
        'function': re.compile(r'^\s*(?:public|private|protected|static|\s)*function\s+(\w+)'),
        'class': re.compile(r'^\s*(?:abstract\s+)?class\s+(\w+)'),
    },
}


def detect_language(filepath: str) -> str:
    ext = Path(filepath).suffix
    return LANG_MAP.get(ext, '')


def extract_imports(filepath: str, language: str) -> list:
    patterns = IMPORT_PATTERNS.get(language, [])
    imports = []
    try:
        with open(filepath, 'r', errors='replace') as f:
            for line in f:
                for pat in patterns:
                    m = pat.search(line)
                    if m:
                        # Use first non-None group
                        val = next((g for g in m.groups() if g is not None), None)
                        if val and val not in imports:
                            imports.append(val)
    except OSError:
        pass
    return imports


def extract_symbols(filepath: str, language: str) -> tuple:
    patterns = FUNC_CLASS_PATTERNS.get(language, {})
    functions, classes = [], []
    try:
        with open(filepath, 'r', errors='replace') as f:
            for line in f:
                fp = patterns.get('function')
                if fp:
                    m = fp.search(line)
                    if m:
                        name = next((g for g in m.groups() if g is not None), None)
                        if name and name not in functions:
                            functions.append(name)
                cp = patterns.get('class')
                if cp:
                    m = cp.search(line)
                    if m:
                        name = next((g for g in m.groups() if g is not None), None)
                        if name and name not in classes:
                            classes.append(name)
    except OSError:
        pass
    return functions, classes


def find_source_files(root: str) -> list:
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            if Path(fn).suffix in SOURCE_EXTS:
                result.append(os.path.join(dirpath, fn))
    return result


def build_reverse_map(project_root: str, target_stem: str) -> list:
    imported_by = []
    for src in find_source_files(project_root):
        lang = detect_language(src)
        if not lang:
            continue
        imps = extract_imports(src, lang)
        for imp in imps:
            if target_stem in imp or Path(target_stem).stem in imp:
                rel = os.path.relpath(src, project_root)
                if rel not in imported_by:
                    imported_by.append(rel)
                break
    return imported_by


def generate_mermaid(target_name: str, imports: list, imported_by: list) -> str:
    lines = ['graph TD']
    safe = re.sub(r'[^a-zA-Z0-9_]', '_', target_name)
    lines.append(f'    {safe}["{target_name}"]')
    for imp in imports:
        imp_safe = re.sub(r'[^a-zA-Z0-9_]', '_', imp)
        lines.append(f'    {safe} -->|imports| {imp_safe}["{imp}"]')
    for dep in imported_by:
        dep_safe = re.sub(r'[^a-zA-Z0-9_]', '_', dep)
        lines.append(f'    {dep_safe}["{dep}"] -->|imports| {safe}')
    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: dependency-graph.py <file_or_directory>"}))
        sys.exit(1)

    target = os.path.abspath(sys.argv[1])
    if not os.path.exists(target):
        print(json.dumps({"error": f"Path not found: {target}"}))
        sys.exit(1)

    # Determine project root (walk up to find .git or use parent)
    project_root = target if os.path.isdir(target) else os.path.dirname(target)
    check = project_root
    for _ in range(10):
        if os.path.isdir(os.path.join(check, '.git')):
            project_root = check
            break
        parent = os.path.dirname(check)
        if parent == check:
            break
        check = parent

    files = [target] if os.path.isfile(target) else find_source_files(target)

    all_imports, all_functions, all_classes = [], [], []
    language = ''

    for fp in files:
        lang = detect_language(fp)
        if not lang:
            continue
        if not language:
            language = lang
        imps = extract_imports(fp, lang)
        all_imports.extend(i for i in imps if i not in all_imports)
        funcs, clss = extract_symbols(fp, lang)
        all_functions.extend(f for f in funcs if f not in all_functions)
        all_classes.extend(c for c in clss if c not in all_classes)

    target_name = os.path.relpath(target, project_root)
    imported_by = build_reverse_map(project_root, target_name)

    mermaid = generate_mermaid(target_name, all_imports, imported_by)

    result = {
        "target": target_name,
        "language": language,
        "imports": all_imports,
        "imported_by": imported_by,
        "functions": all_functions,
        "classes": all_classes,
        "mermaid": mermaid,
    }

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
