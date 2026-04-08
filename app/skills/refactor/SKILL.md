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
