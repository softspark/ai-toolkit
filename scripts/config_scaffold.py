#!/usr/bin/env python3
"""Scaffolding for ai-toolkit config inheritance.

- create_base_package(): Scaffold an npm base config package
- create_project_config(): Generate .ai-toolkit.json for a project

Stdlib-only — no external dependencies.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Base config scaffolder
# ---------------------------------------------------------------------------

def create_base_package(
    name: str,
    output_dir: Path | None = None,
) -> Path:
    """Scaffold a base config npm package.

    Args:
        name: Package name (e.g., '@mycompany/ai-toolkit-config').
        output_dir: Where to create the package directory.
                    Defaults to CWD / sanitized-name.

    Returns:
        Path to the created package directory.
    """
    # Sanitize directory name
    dir_name = name.replace("@", "").replace("/", "-")
    pkg_dir = (output_dir or Path.cwd()) / dir_name
    pkg_dir.mkdir(parents=True, exist_ok=True)

    # package.json
    package_json = {
        "name": name,
        "version": "1.0.0",
        "description": f"Shared ai-toolkit configuration for {_org_from_name(name)}",
        "main": "ai-toolkit.config.json",
        "files": ["ai-toolkit.config.json", "rules/", "agents/"],
        "peerDependencies": {
            "@softspark/ai-toolkit": ">=1.5.0"
        },
        "keywords": ["ai-toolkit", "config", "shared"],
    }
    _write_json(pkg_dir / "package.json", package_json)

    # ai-toolkit.config.json (base config with sane defaults)
    base_config: dict[str, Any] = {
        "$schema": "https://softspark.github.io/ai-toolkit/schemas/ai-toolkit-config.json",
        "name": name,
        "version": "1.0.0",
        "description": f"Base AI toolkit configuration for {_org_from_name(name)}",
        "profile": "standard",
        "agents": {
            "enabled": [
                "backend-specialist",
                "code-reviewer",
                "debugger",
                "security-auditor",
                "test-engineer",
            ],
            "disabled": [],
        },
        "rules": {
            "inject": [],
        },
        "constitution": {
            "amendments": [],
        },
        "enforce": {
            "minHookProfile": "standard",
            "requiredPlugins": [],
            "forbidOverride": [],
            "requiredAgents": [],
        },
    }
    _write_json(pkg_dir / "ai-toolkit.config.json", base_config)

    # rules/ directory with placeholder
    rules_dir = pkg_dir / "rules"
    rules_dir.mkdir(exist_ok=True)
    (rules_dir / ".gitkeep").touch()

    # agents/ directory with placeholder
    agents_dir = pkg_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / ".gitkeep").touch()

    # README.md
    readme = _generate_base_readme(name)
    (pkg_dir / "README.md").write_text(readme, encoding="utf-8")

    return pkg_dir


def _org_from_name(name: str) -> str:
    """Extract org name from package name."""
    if name.startswith("@"):
        return name.split("/")[0].lstrip("@")
    return name.split("-")[0] if "-" in name else name


def _generate_base_readme(name: str) -> str:
    """Generate README for base config package."""
    org = _org_from_name(name)
    return f"""# {name}

Shared ai-toolkit configuration for {org}.

## Usage

### In your project

Create `.ai-toolkit.json` in your project root:

```json
{{
  "extends": "{name}",
  "profile": "standard"
}}
```

Then run:

```bash
ai-toolkit install --local
```

### Available commands

```bash
ai-toolkit config validate    # Validate config + extends
ai-toolkit config diff        # Show differences from base
ai-toolkit config check       # CI enforcement check
```

## Customization

### Adding rules

Add `.md` files to `rules/` and reference them in `ai-toolkit.config.json`:

```json
{{
  "rules": {{
    "inject": ["./rules/your-rule.md"]
  }}
}}
```

### Adding agents

Add agent `.md` files to `agents/` and reference them:

```json
{{
  "agents": {{
    "custom": ["./agents/your-agent.md"]
  }}
}}
```

### Enforcement

Use the `enforce` block to set non-overridable constraints:

```json
{{
  "enforce": {{
    "minHookProfile": "standard",
    "requiredAgents": ["security-auditor"],
    "forbidOverride": ["constitution"],
    "requiredPlugins": ["security-pack"]
  }}
}}
```

## Publishing

```bash
npm publish
```

Projects using this config will pick up changes on `ai-toolkit update --local`.
"""


# ---------------------------------------------------------------------------
# Project config generator
# ---------------------------------------------------------------------------

def create_project_config(
    project_dir: Path,
    extends: str = "",
    profile: str = "standard",
) -> Path:
    """Generate .ai-toolkit.json for a project.

    Args:
        project_dir: Project root directory.
        extends: Base config source (npm, git, local).
        profile: Installation profile.

    Returns:
        Path to the created config file.
    """
    config: dict[str, Any] = {}

    if extends:
        config["extends"] = extends

    config["profile"] = profile

    config_path = project_dir / ".ai-toolkit.json"
    _write_json(config_path, config)
    return config_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, data: dict) -> None:
    """Write JSON with consistent formatting."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI: scaffold base config package."""
    if len(sys.argv) < 2:
        print("Usage: config_scaffold.py create-base <package-name> [output-dir]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "create-base":
        if len(sys.argv) < 3:
            print("Usage: config_scaffold.py create-base <package-name> [output-dir]", file=sys.stderr)
            sys.exit(1)
        name = sys.argv[2]
        output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
        pkg_dir = create_base_package(name, output_dir)
        print(json.dumps({
            "created": str(pkg_dir),
            "files": [str(p.relative_to(pkg_dir)) for p in sorted(pkg_dir.rglob("*")) if p.is_file()],
        }, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
