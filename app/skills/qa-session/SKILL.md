---
name: qa-session
description: "Interactive QA session where user reports bugs conversationally and agent files GitHub issues with domain language. Explores codebase in background for context. Use when user wants to report bugs, do QA, file issues conversationally, or mentions QA session."
user-invocable: true
effort: high
argument-hint: "[area to QA or first bug report]"
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# QA Session

$ARGUMENTS

Interactive QA session. User describes problems, agent clarifies, explores codebase, and files GitHub issues.

## Usage

```
/qa-session [area to QA or first bug report]
```

## What This Command Does

1. **Listens** to user's bug report
2. **Clarifies** with 2-3 focused questions max
3. **Explores** codebase in background for context and domain language
4. **Assesses** scope — single issue or breakdown
5. **Files** GitHub issues via `gh issue create`
6. **Continues** until user says done

## For Each Issue

### 1. Listen and Lightly Clarify

Let user describe the problem. Ask **at most 2-3 short questions** on:
- Expected vs actual behavior
- Steps to reproduce
- Consistent or intermittent

Don't over-interview. If clear enough, move on.

### 2. Explore Codebase in Background

Kick off Agent (subagent_type=Explore) in background to:
- Learn domain language (check UBIQUITOUS_LANGUAGE.md)
- Understand what the feature should do
- Identify behavior boundaries

This helps write better issues — but issues must NOT reference files/lines.

### 3. Assess Scope

| Decision | When |
|----------|------|
| **Single issue** | One behavior wrong in one place |
| **Breakdown** | Multiple independent areas, separable concerns, distinct failure modes |

### 4. File GitHub Issues

Use `gh issue create`. Do NOT ask to review — file and share URLs.

**Single issue template:**

```
## What happened
[Actual behavior in plain language]

## What I expected
[Expected behavior]

## Steps to reproduce
1. [Concrete numbered steps]
2. [Use domain terms, not module names]

## Additional context
[Extra observations using domain language]
```

**Breakdown template** (for each sub-issue):

```
## Parent issue
#{parent-issue-number} or "Reported during QA session"

## What's wrong
[This specific behavior problem]

## What I expected
[Expected behavior for this slice]

## Steps to reproduce
1. [Steps specific to THIS issue]

## Blocked by
- #{issue-number} or "None — can start immediately"
```

### 5. Continue Session

After filing, share URLs and ask: "Next issue, or are we done?"

## Rules

- **No file paths or line numbers** in issues — they go stale
- **Use project domain language** (check UBIQUITOUS_LANGUAGE.md)
- **Describe behaviors, not code** — "sync service fails to apply patch" not "applyPatch() throws"
- **Reproduction steps mandatory** — ask if you can't determine them
- **Keep concise** — developer should read issue in 30 seconds
- **Maximize parallelism** — independent issues have no blockers
- **Create in dependency order** — blockers first for real issue numbers
