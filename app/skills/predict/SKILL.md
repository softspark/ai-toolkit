---
name: predict
description: "Analyzes code diffs and file changes to identify potential regressions, maps dependency impact across the codebase, and generates a risk-scored impact report. Use when reviewing pull requests, assessing code change risk, checking for breaking changes, or analyzing the blast radius of a diff."
effort: medium
disable-model-invocation: true
argument-hint: "[change description]"
agent: predictive-analyst
context: fork
allowed-tools: Read, Grep, Glob
---

# Predict Command

$ARGUMENTS

Triggers the Predictive Analyst to assess the impact and regression risk of proposed changes.

## Usage

```bash
/predict [path_or_diff]
# /predict src/auth              : analyze all files under src/auth
# /predict --diff                : analyze uncommitted changes (git diff)
# /predict src/api/routes.ts     : analyze a single file
```

## Protocol

### 1. Scope: Identify Target Files

- If path provided: collect all files under that path
- If `--diff`: run `git diff --name-only` to get changed files
- List each file with its last-modified date and line count

### 2. Trace: Build Dependency Graph

For each target file, find dependents:

```bash
# Find files that import/require the target
grep -rl "import.*from.*[target]" --include="*.ts" --include="*.py" --include="*.js" .
grep -rl "require.*[target]" --include="*.js" --include="*.ts" .
```

Build a graph: `changed file, direct dependents, transitive dependents (1 level)`

### 3. Assess: Calculate Risk Score

Score each changed file on a 1 to 5 scale:

| Factor | Weight | Scoring |
|--------|--------|---------|
| Dependent count | 30% | 0 deps = 1, 1 to 3 = 2, 4 to 10 = 3, 11 to 20 = 4, 21+ = 5 |
| Test coverage | 30% | Has dedicated test = 1, partial = 3, none = 5 |
| Change surface | 20% | < 10 lines = 1, 10 to 50 = 2, 50 to 200 = 3, 200+ = 5 |
| Shared/core file | 20% | Leaf = 1, mid-layer = 3, core/shared = 5 |

**Overall risk** = weighted average rounded to nearest integer.

### 4. Report: Generate Impact Prediction

Output a markdown report:

```markdown
## Impact Prediction: [scope]

| File | Risk | Dependents | Test Coverage | Notes |
|------|------|------------|---------------|-------|
| src/auth/login.ts | 4/5 | 12 files | partial | Core auth flow |

### High-Risk Changes (score >= 4)
- [file]: [why it's high risk and what to watch]

### Recommended Actions
- [ ] Add tests for [untested file]
- [ ] Review [high-dependent file] with extra scrutiny
- [ ] Run integration tests covering [affected area]
```

## Rules

- **MUST** base risk scores on measurable signals (dependent count, coverage, diff size) — not vibes or adjective scales
- **MUST** name at least one specific action per high-risk file — "review carefully" is not an action
- **NEVER** predict regressions beyond what the signals justify. A single file with 20 dependents is a signal; a generic "this might break things" is noise.
- **NEVER** skip the test-coverage factor — a high-dependent file with 100% coverage is lower risk than a low-dependent file with none
- **CRITICAL**: the report ranks files by weighted risk score, not alphabetically. Readers will stop after the first 5 entries.
- **MANDATORY**: state the confidence level explicitly. Predictions from a 5-line diff are HIGH confidence; predictions from 500-line refactors are LOW.

## Gotchas

- `grep -rl "import.*from.*[target]"` is easily fooled by comments and string literals. Use the language's real AST tools (`ts-morph`, `ast-grep`, `pyflakes`) for accurate dependency graphs on anything beyond trivial diffs.
- Dynamic imports (`importlib.import_module`, `require(variable)`, JavaScript `await import()`) are invisible to grep. Flag explicitly when the target uses them.
- Test coverage reported by CI may exclude generated code, migrations, and `__init__.py`. "Has dedicated test = score 1" assumes a real assertion exists — check the test file rather than just the path match.
- A 5-line diff in a "core" file is often more dangerous than a 500-line diff in a leaf file. The `change_surface` weight alone is misleading; combine with `shared/core` weight for meaningful signals.
- Predictions about regressions are calibrated against the current test suite, not unknown production behaviors. A "low-risk" verdict means "tests likely pass", not "users will not notice".

## When NOT to Use

- For **executing** a change after prediction — use `/fix`, `/refactor`, or the relevant skill
- For PR review of logic quality — use `/review`
- For CI pipeline risk analysis — use `/ci-cd-patterns`
- For code quality metrics (complexity, duplication) — use `/analyze`
- For a brand-new codebase with no change history — this skill needs dependents to measure; use `/explore` first
