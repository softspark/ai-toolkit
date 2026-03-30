#!/usr/bin/env python3
"""Pre-commit validation: staged files, secrets detection, commit type suggestion."""
import json, subprocess, re, sys

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()

def main():
    branch = run(["git", "branch", "--show-current"])
    staged_raw = run(["git", "diff", "--cached", "--name-only"])
    staged = staged_raw.split('\n') if staged_raw else []
    stat = run(["git", "diff", "--cached", "--stat"])

    # Detect secrets patterns
    diff = run(["git", "diff", "--cached"])
    secret_patterns = [
        r'(?i)(api[_-]?key|secret|password|token|bearer)\s*[=:]\s*["\'][^"\']{8,}',
        r'(?i)AKIA[0-9A-Z]{16}',  # AWS
        r'sk-[a-zA-Z0-9]{20,}',   # OpenAI
    ]
    secrets = []
    for i, line in enumerate(diff.split('\n')):
        if line.startswith('+') and not line.startswith('+++'):
            for p in secret_patterns:
                if re.search(p, line):
                    secrets.append({"line": i, "pattern": p.split(')')[0].split('(')[-1], "preview": line[:80]})

    # Large files (>1MB)
    large = []
    for f in staged:
        try:
            r = subprocess.run(
                ["git", "cat-file", "-s", f":{f}"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            size = int(r.stdout.strip() or "0")
            if size > 1_000_000:
                large.append({"file": f, "size_mb": round(size/1_000_000, 1)})
        except (ValueError, subprocess.SubprocessError):
            pass

    # Suggest type from file paths
    type_map = {"test": "test", "doc": "docs", "README": "docs", ".yml": "ci", ".yaml": "ci",
                "Dockerfile": "ci", "migration": "feat", "fix": "fix"}
    type_suggestion = "feat"
    for f in staged:
        for key, val in type_map.items():
            if key.lower() in f.lower():
                type_suggestion = val
                break

    # Suggest scope from common directory
    scopes = set()
    for f in staged:
        parts = f.split('/')
        if len(parts) > 1:
            scopes.add(parts[0] if parts[0] != 'src' and parts[0] != 'app' else (parts[1] if len(parts) > 2 else parts[0]))
    scope_suggestion = list(scopes)[0] if len(scopes) == 1 else None

    # Parse additions/deletions
    additions = len([l for l in diff.split('\n') if l.startswith('+') and not l.startswith('+++')])
    deletions = len([l for l in diff.split('\n') if l.startswith('-') and not l.startswith('---')])

    result = {
        "branch": branch,
        "staged_files": len(staged),
        "staged_file_list": staged[:20],
        "additions": additions,
        "deletions": deletions,
        "type_suggestion": type_suggestion,
        "scope_suggestion": scope_suggestion,
        "secrets_detected": secrets,
        "large_files": large,
        "warnings": []
    }
    if secrets:
        result["warnings"].append(f"SECRETS DETECTED: {len(secrets)} potential secrets in staged changes")
    if large:
        result["warnings"].append(f"LARGE FILES: {len(large)} files over 1MB")
    if not staged:
        result["warnings"].append("NO FILES STAGED: nothing to commit")

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
