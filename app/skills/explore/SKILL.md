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

## Rules

- **MUST** use `Glob` and `Grep` before `Read` — scan for shape before opening files
- **MUST** deliver a map of the codebase (entry points, layers, module boundaries), not a file listing — a tree without interpretation is noise
- **NEVER** read every file sequentially; target reads via grep patterns and filename globs
- **NEVER** modify any file — this is a read-only skill
- **CRITICAL**: when the repo contains generated code (`node_modules`, `vendor/`, `dist/`, `build/`), exclude it from scans or the signal drowns in generated noise
- **MANDATORY**: summarize the stack once at the top (language, framework, package manager, test runner) before diving into structure

## Gotchas

- `find .` and `ls -R` ignore `.gitignore` by default and include `node_modules`, `vendor/`, `.venv/`, `target/`. Use `git ls-files` or `fd` / `rg` for a git-aware listing, or explicitly prune.
- `package.json` says `"type": "module"` → ESM; absence → CommonJS. Mixing them without noticing produces "Cannot use import statement outside a module" errors later; call out the setting in the report.
- Frameworks with file-based routing (Next.js, Nuxt, SvelteKit) treat the `app/` or `pages/` tree as the router. A directory listing alone does not reveal routes — the framework convention does. Name the framework first, then the routes.
- `pyproject.toml` can declare multiple project layouts (src/, flat, namespace packages). "Where is the main code" is not obvious without reading `[tool.setuptools.packages]` or `[tool.poetry.packages]`.
- Large monorepos use workspaces (`pnpm-workspace.yaml`, `nx.json`, `turbo.json`) with apps and packages. Treating the root as the project conceals the actual component boundaries — surface the workspace topology first.

## When NOT to Use

- To explain a specific module's design — use `/explain`
- To find a specific identifier or symbol — use `Grep` directly or `/search`
- To audit architecture for deepening candidates — use `/architecture-audit`
- To scaffold a new project — use `/app-builder`
- When the user already knows the codebase — skip the overview and jump to the concrete task
