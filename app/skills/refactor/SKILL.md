---
name: refactor
description: "Refactor code for quality and maintainability"
user-invocable: true
effort: high
argument-hint: "[target and goal]"
agent: code-reviewer
context: fork
allowed-tools: Read, Edit, Grep, Glob, Bash
---

# Refactor Code

$ARGUMENTS

Plan and execute code refactoring.

## Usage

```
/refactor [target] [--pattern=<pattern>]
```

## What This Command Does

1. **Analyzes** target code
2. **Identifies** refactoring opportunities
3. **Plans** refactoring steps
4. **Executes** with user approval

## Refactoring Patterns

| Pattern | Description |
|---------|-------------|
| `extract-function` | Extract code block to function |
| `extract-component` | Extract UI component |
| `rename` | Rename symbol across codebase |
| `move` | Move code to better location |
| `inline` | Inline unnecessary abstraction |
| `simplify` | Simplify complex logic |

## Safety Rules

- Run tests before refactoring
- Make atomic commits
- Preserve behavior (no feature changes)
- Run tests after each step
- Don't mix refactoring with features

## Output Format

```markdown
## Refactoring Plan: [Target]

### Current State
- **Location**: [file:line]
- **Issues**: [what's wrong]

### Proposed Changes
1. [Change 1]
2. [Change 2]

### Impact Analysis
- **Files affected**: [count]
- **Risk level**: [Low/Medium/High]

### Test Coverage
- [x] Unit tests exist
- [ ] Integration tests needed

### Rollback
```
git revert [commit]
```
```

## Approval Required

Before executing:
- [ ] Plan reviewed
- [ ] Tests passing
- [ ] Backup created

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It works, don't touch it" | Working code that's hard to maintain slows every future change |
| "We'll refactor it later" | Later never comes — refactor when the pain is fresh and context is loaded |
| "It's too risky to change" | That's exactly why it needs refactoring — risk compounds with complexity |
| "Just one more hack won't hurt" | Each hack makes the next one easier to justify — break the cycle now |
| "We need to rewrite from scratch" | Incremental refactoring is safer and delivers value continuously |

## READ BEFORE WRITE

This command analyzes and plans first.
Execution requires explicit approval.

## MANDATORY: Documentation Update

After refactoring, update documentation:

### Required Updates
| Change Type | Update |
|-------------|--------|
| API changes | API documentation |
| Architecture | architecture note if significant |
| Patterns | Best practices docs |
| Breaking changes | Migration guide |

### Post-Refactoring Checklist
- [ ] Tests still pass
- [ ] No behavior changes
- [ ] **Documentation updated if interfaces changed**
- [ ] Code comments updated

## Automated Smell Detection

Run the bundled script to find refactoring opportunities:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/refactor-scan.py src/
```

## Parallel Refactoring (complex cases)

If the scan reports >5 smells across multiple files, use Agent Teams:

```
Create an agent team for refactoring:
- Teammate 1 (code-reviewer): "Plan the refactoring strategy for [identified smells]. Document what to change and why." Use Opus. READ-ONLY.
- Teammate 2 (backend-specialist): "Implement the refactoring changes identified by the reviewer." Use Opus.
Teammate 1 completes first, then Teammate 2 acts on the plan.
```

## Related Skills
- Need a safe refactor plan? → `/refactor-plan` for incremental steps as GitHub RFC
- Want to validate architecture? → `/analyze` for code quality metrics
- Need tests before refactoring? → `/tdd` to build safety net first
- Architecture decision needed? → `/council` for multi-perspective evaluation

## Rules

- **MUST** run the full test suite before starting — a green baseline is the only way to tell the refactor did not break anything
- **MUST** preserve behavior end-to-end; if behavior must change, stop and ask — "while we're here" changes are how refactors introduce bugs
- **NEVER** mix refactoring with feature changes in the same commit — they fail review and rollback differently
- **NEVER** refactor untested code without adding tests first — the refactor has nothing to assert against
- **CRITICAL**: commits stay small and individually reversible. A 2000-line refactor commit cannot be code-reviewed and cannot be bisected.
- **MANDATORY**: dead-code cleanup is part of the refactor per Constitution Art. VI.1 — orphaned references left behind from a refactor are a quality regression, not "later work"

## Gotchas

- "Behavior-preserving" refactors still change **observable** things: timing, memory allocation, error message text, log line format. Downstream consumers may rely on these — scan for log parsers or monitoring rules before changing prose in exceptions.
- IDE rename refactors miss dynamic references (string-keyed dicts, reflection, `getattr`, dynamic imports). After a rename, grep for the old name in strings and comments — the IDE will not.
- Git history diffing is confused by combined move + content changes. Split moves into their own commit (`git mv` + tiny commit) so later reviewers can use `git log --follow`.
- Preserving backward compatibility is a spectrum. "Keep the old function as a thin wrapper" sounds safe but often defers the cleanup forever — prefer deprecate-with-warning followed by a scheduled removal.
- Refactor-to-DRY abstractions made from 2 use cases often need to be torn down when the 3rd use case arrives (Rule of Three). Resist abstracting until the third repetition makes the shape obvious.
- Test suites that rely on mocks frequently pass during refactors that silently break real behavior (the mock reflects the old shape). Run integration tests, not just unit, before marking done.

## When NOT to Use

- For **planning** a refactor (no execution) — use `/refactor-plan`
- For architectural audit of shallow modules — use `/architecture-audit`
- For fixing a specific bug — use `/fix` or `/debug`
- For adding a feature — use `/plan` then the relevant language skill
- When tests do not exist or are red — write tests first (`/tdd`) before refactoring
