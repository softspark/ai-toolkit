---
name: docs
description: "Generate and update README, API docs, and architecture notes"
user-invocable: true
effort: high
argument-hint: "[type: readme/api/architecture-note]"
agent: documenter
context: fork
allowed-tools: Read, Write, Grep, Glob
---

# Generate Documentation

$ARGUMENTS

Generate or update documentation.

## Usage

```
/docs [type] [target]
```

## What This Command Does

1. **Analyzes** code structure
2. **Extracts** documentation info
3. **Generates** documentation files
4. **Updates** existing docs

## Documentation Types

| Type | Description |
|------|-------------|
| `readme` | Generate/update README |
| `api` | API documentation |
| `architecture-note` | Architecture note |
| `changelog` | Generate changelog |
| `comments` | Add code comments |
| `kb` | Knowledge base entry (enforces KB structure) |

## KB Document Rules (MANDATORY)

When creating or updating documents in the `kb/` directory, follow the `documentation-standards` knowledge skill (auto-loaded). Key rules:

- **7 required frontmatter fields:** title, category, service, tags, created, last_updated, description
- **5 valid categories:** reference, howto, procedures, troubleshooting, best-practices
- **Category must match directory** (e.g., `category: howto` → `kb/howto/`)
- **English only.** No exceptions.
- **validate.sh rejects docs without valid frontmatter.**

Full spec: see `app/skills/documentation-standards/SKILL.md`.

## Templates

### README Generation
```markdown
# [Project Name]

[Auto-generated description]

## Installation
[Detected from package manager]

## Usage
[Extracted from code/examples]

## API
[Extracted from code]

## License
[Detected]
```

### Architecture Note Template
```markdown
# Architecture Note: [TITLE]

## Status
Proposed

## Context
[What is the issue?]

## Decision
[What was decided?]

## Consequences
[What are the results?]

## Date
[Today's date]
```

## Output Format

```markdown
## Documentation Report

### Generated
- [file 1]
- [file 2]

### Updated
- [file 3]: [what changed]

### Skipped
- [file 4]: [reason]

### Next Steps
- [ ] Review generated docs
- [ ] Add missing details
- [ ] Commit changes
```

## Configuration

Documentation settings in:
- `.claude/settings.json`
- Project's doc config

## REVIEW BEFORE COMMIT

Generated documentation should be reviewed.
AI may miss context or make assumptions.

## Documentation Inventory

Run the bundled script to audit documentation coverage and find gaps:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/doc-inventory.py .
```

## Parallel Documentation (large codebases)

If the inventory script reports `doc_coverage_percent < 50` and the project has multiple modules, use Agent Teams for parallel documentation:

```
Create an agent team for documentation:
- Teammate 1 (documenter): "Document the [module-1] directory. Generate docstrings for all public functions." Use Sonnet.
- Teammate 2 (documenter): "Document the [module-2] directory. Generate docstrings for all public functions." Use Sonnet.
- Teammate 3 (documenter): "Generate README sections: installation, usage, API reference." Use Opus.
Teammates should NOT overlap — each owns their assigned scope.
```
