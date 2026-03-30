#!/usr/bin/env python3
"""Detect code smells deterministically: long functions, deep nesting, large files."""

import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.next', 'vendor', '.cache'}

SOURCE_EXTS = {'.py', '.ts', '.js', '.tsx', '.jsx', '.go', '.php', '.dart'}

THRESHOLDS = {
    'long_function_lines': 50,
    'deep_nesting_levels': 4,
    'large_file_lines': 300,
    'many_functions': 15,
}

FUNC_PATTERNS = {
    '.py': re.compile(r'^(\s*)def\s+(\w+)\s*\('),
    '.js': re.compile(r'^(\s*)(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()'),
    '.jsx': re.compile(r'^(\s*)(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()'),
    '.ts': re.compile(r'^(\s*)(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()'),
    '.tsx': re.compile(r'^(\s*)(?:(?:async\s+)?function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()'),
    '.go': re.compile(r'^(\s*)func\s+(?:\([^)]*\)\s+)?(\w+)\s*\('),
    '.php': re.compile(r'^(\s*)(?:public|private|protected|static|\s)*function\s+(\w+)'),
    '.dart': re.compile(r'^(\s*)(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*(?:async\s*)?\{'),
}


def find_source_files(root: str) -> list:
    result = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            if Path(fn).suffix in SOURCE_EXTS:
                result.append(os.path.join(dirpath, fn))
    return result


def measure_nesting(line: str, ext: str) -> int:
    """Measure nesting depth from indentation."""
    if not line.strip():
        return 0
    if ext == '.py':
        # Python: 4 spaces = 1 level
        spaces = len(line) - len(line.lstrip())
        return spaces // 4
    else:
        # Brace languages: count { minus } up to this point is complex,
        # so use indentation heuristic (2 or 4 spaces = 1 level)
        spaces = len(line) - len(line.lstrip())
        tab_count = line.count('\t')
        if tab_count > 0:
            return tab_count
        indent_size = 2 if spaces % 2 == 0 and spaces % 4 != 0 else 4
        return spaces // indent_size


def analyze_file(filepath: str, project_root: str) -> dict:
    ext = Path(filepath).suffix
    rel_path = os.path.relpath(filepath, project_root)
    smells = []

    try:
        with open(filepath, 'r', errors='replace') as f:
            lines = f.readlines()
    except OSError:
        return {"file": rel_path, "smells": [], "functions": 0}

    total_lines = len(lines)
    func_pattern = FUNC_PATTERNS.get(ext)
    if not func_pattern:
        return {"file": rel_path, "smells": [], "functions": 0}

    # Find function boundaries
    functions = []
    for i, line in enumerate(lines):
        m = func_pattern.match(line)
        if m:
            name = next((g for g in m.groups()[1:] if g is not None), 'anonymous')
            indent = len(m.group(1).expandtabs(4))
            functions.append({"name": name, "start": i + 1, "indent": indent})

    # Calculate function lengths
    for idx, func in enumerate(functions):
        if idx + 1 < len(functions):
            end = functions[idx + 1]["start"] - 1
        else:
            end = total_lines
        func["length"] = end - func["start"] + 1

    # Detect max nesting per function
    for func in functions:
        start_idx = func["start"] - 1
        end_idx = start_idx + func["length"]
        max_depth = 0
        for i in range(start_idx, min(end_idx, total_lines)):
            depth = measure_nesting(lines[i], ext)
            # Relative nesting: subtract function's own indent level
            relative_depth = depth - (func["indent"] // 4) - 1
            if relative_depth > max_depth:
                max_depth = relative_depth
        func["max_nesting"] = max(max_depth, 0)

    # Flag smells
    for func in functions:
        if func["length"] > THRESHOLDS['long_function_lines']:
            smells.append({
                "type": "long_function",
                "severity": "high" if func["length"] > 100 else "medium",
                "file": rel_path,
                "function": func["name"],
                "line": func["start"],
                "detail": f"{func['length']} lines (threshold: {THRESHOLDS['long_function_lines']})",
            })
        if func["max_nesting"] > THRESHOLDS['deep_nesting_levels']:
            smells.append({
                "type": "deep_nesting",
                "severity": "high" if func["max_nesting"] > 6 else "medium",
                "file": rel_path,
                "function": func["name"],
                "line": func["start"],
                "detail": f"depth {func['max_nesting']} (threshold: {THRESHOLDS['deep_nesting_levels']})",
            })

    if total_lines > THRESHOLDS['large_file_lines']:
        smells.append({
            "type": "large_file",
            "severity": "high" if total_lines > 600 else "medium",
            "file": rel_path,
            "function": None,
            "line": None,
            "detail": f"{total_lines} lines (threshold: {THRESHOLDS['large_file_lines']})",
        })

    if len(functions) > THRESHOLDS['many_functions']:
        smells.append({
            "type": "too_many_functions",
            "severity": "medium",
            "file": rel_path,
            "function": None,
            "line": None,
            "detail": f"{len(functions)} functions (threshold: {THRESHOLDS['many_functions']}, possible God class)",
        })

    return {"file": rel_path, "smells": smells, "functions": len(functions)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: refactor-scan.py <file_or_directory>"}))
        sys.exit(1)

    target = os.path.abspath(sys.argv[1])
    if not os.path.exists(target):
        print(json.dumps({"error": f"Path not found: {target}"}))
        sys.exit(1)

    # Determine project root
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

    all_smells = []
    files_scanned = 0

    for fp in files:
        result = analyze_file(fp, project_root)
        files_scanned += 1
        all_smells.extend(result["smells"])

    # Sort by severity (high first)
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_smells.sort(key=lambda s: severity_order.get(s["severity"], 99))

    # Generate recommendation
    if not all_smells:
        recommendation = "No code smells detected. Codebase looks clean."
    elif len(all_smells) <= 3:
        recommendation = "Minor issues found. Address them in your next refactoring pass."
    elif len(all_smells) <= 10:
        recommendation = "Several code smells detected. Prioritize high-severity items."
    else:
        recommendation = "Significant technical debt detected. Consider a dedicated refactoring sprint."

    output = {
        "target": os.path.relpath(target, project_root),
        "smells": all_smells,
        "files_scanned": files_scanned,
        "total_smells": len(all_smells),
        "recommendation": recommendation,
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
