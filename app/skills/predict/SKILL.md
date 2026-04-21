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
# /predict src/auth              — analyze all files under src/auth
# /predict --diff                — analyze uncommitted changes (git diff)
# /predict src/api/routes.ts     — analyze a single file
```

## Protocol

### 1. Scope — Identify Target Files

- If path provided: collect all files under that path
- If `--diff`: run `git diff --name-only` to get changed files
- List each file with its last-modified date and line count

### 2. Trace — Build Dependency Graph

For each target file, find dependents:

```bash
# Find files that import/require the target
grep -rl "import.*from.*[target]" --include="*.ts" --include="*.py" --include="*.js" .
grep -rl "require.*[target]" --include="*.js" --include="*.ts" .
```

Build a graph: `changed file → direct dependents → transitive dependents (1 level)`

### 3. Assess — Calculate Risk Score

Score each changed file on a 1–5 scale:

| Factor | Weight | Scoring |
|--------|--------|---------|
| Dependent count | 30% | 0 deps = 1, 1–3 = 2, 4–10 = 3, 11–20 = 4, 21+ = 5 |
| Test coverage | 30% | Has dedicated test = 1, partial = 3, none = 5 |
| Change surface | 20% | < 10 lines = 1, 10–50 = 2, 50–200 = 3, 200+ = 5 |
| Shared/core file | 20% | Leaf = 1, mid-layer = 3, core/shared = 5 |

**Overall risk** = weighted average rounded to nearest integer.

### 4. Report — Generate Impact Prediction

Output a markdown report:

```markdown
## Impact Prediction: [scope]

| File | Risk | Dependents | Test Coverage | Notes |
|------|------|------------|---------------|-------|
| src/auth/login.ts | 4/5 | 12 files | partial | Core auth flow |

### High-Risk Changes (score ≥ 4)
- [file]: [why it's high risk and what to watch]

### Recommended Actions
- [ ] Add tests for [untested file]
- [ ] Review [high-dependent file] with extra scrutiny
- [ ] Run integration tests covering [affected area]
```
