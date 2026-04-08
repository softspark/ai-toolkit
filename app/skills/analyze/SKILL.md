---
name: analyze
description: "Analyze code quality, complexity, and patterns"
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

## Related Skills
- Found quality issues? → `/refactor` to fix them systematically
- Security issues detected? → `/cve-scan` for dependency audit
- Want deeper architecture review? → `/architecture-audit` for friction discovery
- Performance hotspots found? → `/workflow performance-optimization`
