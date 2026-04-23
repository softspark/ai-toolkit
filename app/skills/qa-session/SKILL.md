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

- **MUST** use the project's domain language from `UBIQUITOUS_LANGUAGE.md` — framework jargon in issues excludes non-engineering stakeholders
- **MUST** describe behaviors, not code — "sync service fails to apply patch" not "applyPatch() throws"
- **MUST** include reproduction steps — if they are not clear, ask the user rather than guess
- **NEVER** include file paths, line numbers, or function names in issue bodies — they go stale before triage
- **NEVER** over-interview. Cap clarifying questions at 2-3 per bug; more than that is signal the bug needs a QA session with a product owner, not more questions.
- **CRITICAL**: the developer who picks up the issue should understand it in 30 seconds. Wall-of-text reports get reopened for clarification.
- **MANDATORY**: when breaking one report into multiple issues, file them in dependency order so blockers have real issue numbers to reference

## Gotchas

- Domain language in `UBIQUITOUS_LANGUAGE.md` may be out of date. If it was last updated months ago and new features have shipped, the glossary is an input hint, not a source of truth — confirm terms with the user when unsure.
- "Intermittent" reports are often environmental (one user's browser, one region's data) rather than truly random. Always ask for "how often" and "when did it start" before labeling as race condition.
- `gh issue create` opens `$EDITOR` without `--body`. In automation this hangs — always pass the body file or inline body.
- Users often describe the **workaround** as if it were the bug ("I have to refresh the page"). Drill to the underlying behavior — "what fails before the refresh?" — otherwise the fix targets the symptom.
- Independent sub-issues from one bug report can duplicate work if each gets a different developer. Mention the parent QA session in every sub-issue so reviewers notice the pattern.

## When NOT to Use

- For triaging a **single** known bug with a proposed fix — use `/triage-issue`
- For creating issues from a PRD — use `/prd-to-issues`
- For debugging a reproducible error — use `/debug`
- For code review of a PR that addresses a bug — use `/review`
- For architecture-level problems — use `/architecture-audit`, not bug reports
