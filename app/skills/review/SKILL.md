---
name: review
description: "Review code for quality, security, and correctness"
user-invocable: true
effort: high
argument-hint: "[target: branch, pr, file path, or staged changes]"
agent: code-reviewer
context: fork
allowed-tools: Read, Grep, Glob, Bash
---

# Code Review

$ARGUMENTS

Reviews code changes for quality and issues.

## Changed files context

- Changes: !`git diff --stat main...HEAD 2>/dev/null || git diff --cached --stat 2>/dev/null || echo "no changes detected"`

## Automated Diff Analysis

Before starting manual review, run the diff analyzer script to get a structured risk assessment:

```bash
python3 "$(dirname "$0")/scripts/diff-analyzer.py" [base_branch]
# Default base branch: main
# Example: python3 scripts/diff-analyzer.py develop
```

The script outputs JSON with:
- **files**: each changed file with additions, deletions, category (security/test/config/migration/infra/docs/logic), and risk level
- **risk_score**: overall assessment (high/medium/low)
- **hotspots**: top 5 files by additions
- **secrets_scan**: potential secret leaks detected in added lines
- **test_coverage_estimate**: whether test files accompany logic changes (good/partial/none)
- **parallel_review_recommended**: boolean flag

If the script reports `parallel_review_recommended: true`, use the Parallel Review (Agent Teams) mode below.

---

## Parallel Review (Agent Teams)

For significant PRs or large changesets, create a parallel review team:

```
Create an agent team to review [target]:
- Teammate 1 (security-auditor): "Review for security vulnerabilities, auth issues,
  injection risks, secret leaks. Report with severity ratings." Use Opus.
- Teammate 2 (performance-optimizer): "Check for N+1 queries, memory leaks,
  unnecessary allocations, caching opportunities. Report with impact ratings." Use Opus.
- Teammate 3 (test-engineer): "Validate test coverage, edge cases, mock quality,
  missing assertions. Report coverage gaps." Use Opus.
Each reviewer should report findings independently. Do NOT modify files.
```

After all reviewers complete:
1. Synthesize findings into unified Code Review Report
2. Prioritize by severity (Critical > Major > Minor)
3. Issue verdict: APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION

> **When to use**: PRs with >5 files changed, cross-module changes, security-sensitive code.
> **READ-ONLY**: No teammate should modify files during review.

---

## Sequential Review (Default)

1. **Reads** changed files
2. **Analyzes** for issues
3. **Checks** best practices
4. **Reports** findings

## Review Scope

| Target | What's Reviewed |
|--------|-----------------|
| (none) | Staged changes |
| `branch` | Branch vs main |
| `pr` | Pull request changes |
| `file.ts` | Specific file |

## Review Checklist

### Code Quality
- [ ] Clear naming
- [ ] Proper error handling
- [ ] No code duplication
- [ ] Appropriate abstractions

### Security
- [ ] No hardcoded secrets
- [ ] Input validation
- [ ] Proper auth checks
- [ ] SQL injection prevention

### Performance
- [ ] No N+1 queries
- [ ] Appropriate caching
- [ ] No memory leaks
- [ ] Optimized loops

### Testing
- [ ] Tests for new code
- [ ] Edge cases covered
- [ ] Mocks appropriate

## Output Format

```markdown
## Code Review Report

### Summary
- **Files Changed**: [count]
- **Lines Added**: [+count]
- **Lines Removed**: [-count]
- **Issues Found**: [count]

### Findings

#### Critical
- **[file:line]**: [issue]
  - [explanation]
  - Suggested fix: [code]

#### Suggestions
- **[file:line]**: [suggestion]
  - [explanation]

### Positive Notes
- [What's good about the code]

### Verdict
[APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION]
```

## READ-ONLY

This skill only analyzes. It does NOT modify any files.
