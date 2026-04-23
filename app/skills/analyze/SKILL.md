---
name: analyze
description: "Analyze code quality, complexity, and patterns across a codebase. Use when the user asks for a quality report, hotspot scan, or systemic architecture signal — not for fixing bugs or reviewing a single PR."
user-invocable: true
effort: medium
argument-hint: "[path or pattern]"
allowed-tools: Read, Grep, Glob
---

# Code Analysis

$ARGUMENTS

Analyze code quality, complexity, and patterns.

## Usage

```
/analyze [path] [--type=<type>]
```

## What This Command Does

1. **Scans** codebase or specific path
2. **Analyzes** code quality metrics
3. **Identifies** patterns and anti-patterns
4. **Reports** findings with recommendations

## Analysis Types

| Type | Description |
|------|-------------|
| `quality` | Code quality metrics (default) |
| `security` | Security vulnerability scan |
| `complexity` | Cyclomatic complexity |
| `dependencies` | Dependency analysis |
| `coverage` | Test coverage gaps |

## Output Format

```markdown
## Code Analysis Report

### Summary
- **Files Analyzed**: [count]
- **Issues Found**: [count]
- **Quality Score**: [score]/100

### Metrics
| Metric | Value | Threshold |
|--------|-------|-----------|
| Complexity | [avg] | <10 |
| Duplication | [%] | <5% |
| Coverage | [%] | >70% |

### Issues by Severity
- Critical: [count]
- High: [count]
- Medium: [count]
- Low: [count]

### Top Issues
1. **[Issue]** - [file:line]
   - [Description]
   - Fix: [Recommendation]

### Patterns Detected
- [Pattern 1]: [locations]
- [Pattern 2]: [locations]

### Recommendations
1. [Recommendation with priority]
```

## Automated Complexity Analysis

Run the bundled script for a quick complexity report:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/complexity.py .
```

Reports file counts by type, largest files, TODO/FIXME counts, and total code lines.

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "The linter is green, the code is fine" | Linters catch syntax, not design flaws — analysis covers architecture and patterns |
| "We know where the problems are" | Intuition misses systemic issues — data-driven analysis reveals hidden hotspots |
| "Analysis takes too long" | A 5-minute scan prevents weeks of debugging — front-load the investment |
| "It's legacy code, analysis won't help" | Legacy code benefits most — find the critical paths before they break |

## Tools Used

| Language | Tools |
|----------|-------|
| Python | ruff, mypy, pylint |
| JavaScript | eslint, tsc |
| Go | golangci-lint |
| Rust | clippy |

## Rules

- **MUST** report measured values — never assert "this is fine" without numbers
- **NEVER** modify source files (read-only skill)
- **CRITICAL**: if the requested analysis type is unsupported for the detected language, say so explicitly and stop — do not fake metrics

## Gotchas

- Linters that exit `0` still may have **skipped** files (gitignore rules, no-match patterns, parse errors). Always read the "N files checked" line before reporting "clean".
- Coverage percentages silently exclude generated code, migrations, and `__init__.py` by default. Report coverage with the exclude list, not the headline number alone.
- `ruff` and `pylint` disagree on several rules (line length, import order) — pick one as the source of truth for the project and note the choice in the report.
- `mypy --strict` on a codebase that was not authored under strict mode will return hundreds of spurious findings. Start with `--ignore-missing-imports` and a file allowlist before claiming the codebase is untyped.

## When NOT to Use

- For a single-PR code review — use `/review` instead
- For fixing a specific bug — use `/debug` or `/fix`
- For architectural friction and module design — use `/architecture-audit`
- For a vulnerability scan of dependencies — use `/cve-scan`

## Related Skills
- Found quality issues? → `/refactor` to fix them systematically
- Security issues detected? → `/cve-scan` for dependency audit
- Want deeper architecture review? → `/architecture-audit` for friction discovery
- Performance hotspots found? → `/workflow performance-optimization`
