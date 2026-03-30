---
name: explore
description: "Explore codebase structure, stack, and architecture"
user-invocable: true
effort: medium
argument-hint: "[path or question]"
allowed-tools: Read, Grep, Glob
---

# Codebase Exploration

$ARGUMENTS

Explore and understand a codebase structure.

## Project context

- Config files: !`find . -maxdepth 2 -type f -name "*.json" -o -name "*.toml" -o -name "*.yaml" -o -name "*.yml" 2>/dev/null | head -20`

## Usage

```
/explore [path]
```

## What This Command Does

1. **Maps** project structure
2. **Identifies** technology stack
3. **Finds** key files and patterns
4. **Reports** architecture overview

## Output Format

```markdown
## Codebase Analysis Report

### Project Type
- **Language**: [TypeScript/Python/PHP/etc.]
- **Framework**: [Next.js/FastAPI/Laravel/etc.]
- **Package Manager**: [npm/pnpm/pip/composer]

### Directory Structure
```
project/
├── src/           # Source code
├── tests/         # Test files
├── config/        # Configuration
└── ...
```

### Key Files
| File | Purpose |
|------|---------|
| `src/index.ts` | Entry point |
| `src/api/` | API routes |

### Dependencies
- **Runtime**: [list]
- **Dev**: [list]

### Patterns Detected
- [Pattern 1]
- [Pattern 2]

### Entry Points
- [Entry 1]
- [Entry 2]
```

## Technology Detection

| Marker | Technology |
|--------|------------|
| `package.json` | Node.js |
| `tsconfig.json` | TypeScript |
| `next.config.*` | Next.js |
| `nuxt.config.*` | Nuxt |
| `pyproject.toml` | Python |
| `composer.json` | PHP |
| `pubspec.yaml` | Flutter/Dart |
| `Cargo.toml` | Rust |
| `go.mod` | Go |

## When to Use

- Starting work on unfamiliar codebase
- Before planning major changes
- Understanding dependencies
- Finding specific code patterns

## READ-ONLY

This skill ONLY reads and analyzes.
It does NOT write or modify any files.

## Visual Output

For an interactive HTML tree visualization of the codebase:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/visualize.py .
```

This generates `codebase-map.html` with collapsible directories, file sizes, and type-colored indicators.

## KB Integration

```python
smart_query("codebase analysis: {technology}")
hybrid_search_kb("project structure {framework}")
```
