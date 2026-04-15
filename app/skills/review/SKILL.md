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
python3 ${CLAUDE_SKILL_DIR}/scripts/diff-analyzer.py [base_branch]
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

### Security (OWASP Top 10)
- [ ] A01: Proper auth/authorization on all endpoints
- [ ] A02: No weak crypto, HTTPS for external comms
- [ ] A03: Input validation, parameterized queries, output encoding (XSS)
- [ ] A04: Threat model assumptions documented for new features
- [ ] A05: No debug mode, default credentials, or verbose errors in prod config
- [ ] A06: Dependencies checked for known CVEs
- [ ] A07: No hardcoded secrets, session management correct
- [ ] A08: Integrity checks on deserialized data, CI/CD pipeline safety
- [ ] A09: Security-relevant events logged (without PII)
- [ ] A10: External URL handling validates scheme/host (SSRF prevention)

### API / Contract Changes
- [ ] Backward compatibility preserved (no silent breaking changes)
- [ ] API versioning updated if contract changed
- [ ] Schema validation on request/response
- [ ] Error responses follow project convention

### Concurrency / Async
- [ ] Shared mutable state protected (locks, atomics, channels)
- [ ] No fire-and-forget promises without error handling
- [ ] Database transactions scoped correctly (no long-held locks)
- [ ] Race condition risk assessed for concurrent access paths

### Migrations / Schema Changes
- [ ] Migration is reversible (has rollback path)
- [ ] No table locks on large tables during peak hours
- [ ] Data backfill handles NULL/missing values
- [ ] Indexes added for new query patterns

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
- **Overall Confidence**: [1-10] — how confident the reviewer is in the assessment

### Findings

#### Critical
- **[file:line]**: [issue]
  - Severity: critical | Confidence: [1-10]
  - Evidence: [specific code reference and reasoning]
  - Suggested fix: [code]

#### Major
- **[file:line]**: [issue]
  - Severity: major | Confidence: [1-10]
  - Evidence: [specific code reference and reasoning]
  - Suggested fix: [code]

#### Minor
- **[file:line]**: [issue]
  - Severity: minor | Confidence: [1-10]
  - Evidence: [line number + reasoning]

#### Nit
- **[file:line]**: [suggestion]
  - Severity: nit | Confidence: [1-10]

### Confidence Guide

| Score | Meaning |
|-------|---------|
| 9-10 | Certain — verified via code, tests, or documentation |
| 7-8 | High — strong evidence, minor assumptions |
| 5-6 | Medium — plausible issue, needs author confirmation |
| 3-4 | Low — speculative, based on patterns not proof |
| 1-2 | Guess — flag for discussion, don't block on this |

### Positive Notes
- [What's good about the code]

### Verdict
[APPROVE / REQUEST_CHANGES / NEEDS_DISCUSSION]
```

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "Small change, quick scan is enough" | Small changes introduce subtle bugs — apply consistent review regardless of size |
| "Tests pass, so the code is correct" | Tests validate specific scenarios, not all behaviors — verify missing coverage |
| "It's just a refactor, no need for deep review" | Refactors change invariants — verify behavior preservation, not just compilation |
| "The author is senior, they know what they're doing" | Seniority doesn't prevent mistakes — review the code, not the person |
| "We're in a hurry, ship it" | Rushed reviews create tech debt that costs 10x more to fix later |

## Self-Evaluation (LLM-as-Judge)

After completing the review, perform a self-evaluation pass:

### Check for Blind Spots
1. **Did I verify, or assume?** — For each finding, confirm you read the actual code (not inferred from context)
2. **Did I miss the inverse?** — If you flagged X as a problem, did you check if NOT doing X is also a problem elsewhere?
3. **Did I anchor on the first issue?** — Review whether early findings biased you toward similar patterns, missing different issue classes
4. **Did I check the unhappy path?** — Error handling, edge cases, failure modes — not just the golden path
5. **Did I flag uncertainty?** — Findings with confidence < 6 should be clearly marked as "needs author input"

### Calibrate Confidence
- If all findings are confidence 7+, you may be overconfident — re-examine the weakest finding
- If any finding lacks a file:line reference, downgrade it or remove it
- If you found zero issues, state what you specifically checked (not "looks good")

## READ-ONLY

This skill only analyzes. It does NOT modify any files.

## Related Skills
- Issues found? → `/debug` to trace root causes
- Missing tests? → `/tdd` to add test-first coverage
- Security findings? → `/cve-scan` for dependency vulnerabilities
- Architecture concerns? → `/analyze` for deeper code quality metrics
