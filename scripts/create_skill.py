#!/usr/bin/env python3
"""ai-toolkit create skill -- Scaffold a new skill from a template.

Usage:
  create_skill.py <name> --template=<type> [--description="..."] [--output-dir=<path>]

Templates: linter, reviewer, generator, workflow, knowledge
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import toolkit_dir


def _parse_args(argv: list[str]) -> dict[str, str]:
    """Parse CLI arguments into a dict."""
    result: dict[str, str] = {
        "name": "",
        "template": "",
        "description": "",
        "output_dir": str(toolkit_dir / "app" / "skills"),
    }

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("--template="):
            result["template"] = arg.split("=", 1)[1]
        elif arg == "--template":
            i += 1
            result["template"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--description="):
            result["description"] = arg.split("=", 1)[1]
        elif arg == "--description":
            i += 1
            result["description"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("--output-dir="):
            result["output_dir"] = arg.split("=", 1)[1]
        elif arg == "--output-dir":
            i += 1
            result["output_dir"] = argv[i] if i < len(argv) else ""
        elif arg.startswith("-"):
            print(f"Unknown option: {arg}", file=sys.stderr)
            sys.exit(1)
        else:
            result["name"] = arg
        i += 1

    return result


def main() -> None:
    """Scaffold a new skill from a template."""
    args = _parse_args(sys.argv[1:])
    name = args["name"]
    template = args["template"]
    description = args["description"]
    output_dir = Path(args["output_dir"])
    templates_dir = toolkit_dir / "app" / "templates" / "skill"

    # Validate name
    if not name:
        print("Error: skill name is required", file=sys.stderr)
        print("Usage: ai-toolkit create skill <name> --template=<type>", file=sys.stderr)
        sys.exit(1)

    if re.search(r"[^a-z0-9-]", name):
        print(f"Error: skill name must be lowercase with hyphens only (got: {name})", file=sys.stderr)
        sys.exit(1)

    if len(name) > 64:
        print(f"Error: skill name must be at most 64 characters (got: {len(name)})", file=sys.stderr)
        sys.exit(1)

    # Validate template
    if not template:
        print("Error: --template is required", file=sys.stderr)
        print("Available templates: linter, reviewer, generator, workflow, knowledge", file=sys.stderr)
        sys.exit(1)

    template_file = templates_dir / template / "SKILL.md.template"
    if not template_file.is_file():
        available = " ".join(
            d.name for d in sorted(templates_dir.iterdir()) if d.is_dir()
        ) if templates_dir.is_dir() else "(none)"
        print(f"Error: unknown template '{template}'", file=sys.stderr)
        print(f"Available templates: {available}", file=sys.stderr)
        sys.exit(1)

    # Check target does not exist
    target_dir = output_dir / name
    if target_dir.is_dir():
        print(f"Error: skill '{name}' already exists at {target_dir}", file=sys.stderr)
        sys.exit(1)

    # Default description
    if not description:
        description = f"Provides {name} functionality"

    # Create skill from template
    target_dir.mkdir(parents=True, exist_ok=True)
    content = template_file.read_text(encoding="utf-8")
    content = content.replace("{{NAME}}", name).replace("{{DESCRIPTION}}", description)
    (target_dir / "SKILL.md").write_text(content, encoding="utf-8")

    print(f"Created: {target_dir}/SKILL.md (from {template} template)")
    print()
    print("Next steps:")
    print(f"  1. Edit {target_dir}/SKILL.md")
    print("  2. Run: ai-toolkit validate")


if __name__ == "__main__":
    main()
