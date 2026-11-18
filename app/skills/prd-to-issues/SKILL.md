---
name: prd-to-issues
description: "Splits a PRD into vertical-slice GitHub issues with HITL/AFK tagging and dependencies. Triggers: PRD to issues, create tickets, break down PRD, work items."
effort: medium
disable-model-invocation: true
argument-hint: "[PRD issue number]"
allowed-tools: Read, Grep, Glob, Bash
---

# PRD to Issues

$ARGUMENTS

Break a PRD into independently-grabbable GitHub issues using vertical slices (tracer bullets).

## Usage

```
/prd-to-issues [PRD issue number]
```

## What This Command Does

1. **Fetches** PRD from GitHub issue
2. **Explores** codebase for context
3. **Drafts** vertical slices with HITL/AFK classification
4. **Quizzes** user on breakdown
5. **Publishes** slices in dependency order, reconciles earlier attempts and verifies native GitHub blocker links.

## Process

### 1. Locate the PRD

Fetch with `gh issue view <number>` (with comments). If no number provided, ask.

### 2. Draft Vertical Slices

Each issue is a thin vertical slice cutting through ALL layers end-to-end.

| Classification | Description |
|---------------|-------------|
| **AFK** | Can be implemented and merged without human interaction (prefer) |
| **HITL** | Requires human decision — architectural choice, design review, etc. |

### 3. Quiz the User

Present as numbered list. For each slice show:

- **Title**: short descriptive name
- **Type**: HITL / AFK
- **Blocked by**: which other slices must complete first
- **User stories covered**: which stories from the PRD

Ask:
- Granularity right? (too coarse / too fine)
- Dependency relationships correct?
- HITL vs AFK classification correct?
- Any slices to merge or split?

Iterate until approved.

### 4. Publish the approved slices

Keep a stable lowercase key for each slice. Save the approved titles, keys,
classification, story references and blockers with the plan. Check for issues
already created from this PRD, including closed issues. Reuse verified older
issues by number when resolving blockers. Resolve ambiguous matches before
creating more issues.

Publish one slice at a time in dependency order. Supply the approved body as a
UTF-8 file containing **What to build**, the HITL/AFK classification, **Acceptance
criteria** and **User stories addressed**. The bundled publisher adds the parent
and blockers from the verified numbers. For example, given PRD 42 and blocker 51:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/publish_slice.py" \
  --repo owner/project --parent 42 --key export-report --title "Export the report" \
  --body-file /path/to/approved-export.md --blocked-by 51 \
  --receipts /path/to/private-run/prd-publication.sqlite
```

Use the real repository and an existing private run directory outside the checkout.
For GitHub Enterprise, set `--host` to its hostname. Repeat `--blocked-by` for
multiple blockers and omit it for a root slice. Keep the same publisher account,
keys, body files and receipt database across retries and worktrees. Coordinate
one publisher per PRD across machines. Report the receipt location for resumption.

The publisher checks open and closed issues for a stable marker, verifies the
child's ownership and records an attempt before each write. On interruption,
rerun the same command. If a pending write still cannot be confirmed, report
its key and stop that slice until the outcome can be reconciled. Creating a
second issue with a different key or receipt directory risks a duplicate.
Keep existing child titles and the approved body intact. A maintainer can
append notes after the marker, separated by a blank line. If the approved
section has changed, reconcile the human edit before proceeding.

An operator can release a pending receipt after the original publisher has
stopped and independent evidence establishes the request never took effect
and cannot still complete (for example, a recorded interruption before POST).
Use the same command with `--release-unapplied issue` for creation or
`--release-unapplied 51` for that blocker. This checks fresh remote state and
only clears the corresponding pending local receipt. Rerun normally afterward.
A missing search result alone leaves an ambiguous write pending. Review a
previously confirmed dependency that someone removed before restoring it.

For each blocker, the publisher fetches its issue database ID, sends it to the
child's `dependencies/blocked_by` endpoint and reads the edge back. Its JSON
result reports `native` for a verified edge or `text-only` when that endpoint
is unavailable or forbidden. The child's body keeps the blocker link in both
cases. Report text-only edges explicitly. Rate limits, failed verification and
validation errors remain actionable errors. Only child issues are created or
linked. [GitHub issue dependency API](https://docs.github.com/en/rest/issues/issue-dependencies)

## Issue Template

<issue-template>

## Parent PRD

#{prd-issue-number}

## What to build

Concise description of this vertical slice. End-to-end behavior, not layer-by-layer. Reference parent PRD sections, don't duplicate.

**Type:** AFK or HITL

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Blocked by

- Blocked by #{issue-number} (if any)

Or "None — can start immediately" if no blockers.

## User stories addressed

Reference by number from the parent PRD:

- User story 3
- User story 7

</issue-template>

## Rules

- **MUST** slice vertically — every issue cuts through schema, API, UI, tests end-to-end. Horizontal slices (all-schema, then all-API) defer integration risk.
- **MUST** create issues in dependency order so blockers have real issue numbers to reference
- **NEVER** close or modify the parent PRD issue — it is the reference anchor for every child issue
- **NEVER** include file paths, line numbers, or function names in issue bodies — they go stale before the issue is picked up
- **CRITICAL**: maximize parallelism. Independent issues have zero `Blocked by` entries; if every issue has blockers, the slicing is wrong.
- **MANDATORY**: every issue lists the user stories it addresses by number from the parent PRD — traceability matters more than brevity

## Gotchas

- Keep each approved body in its own file. The publisher sends its contents as JSON over stdin to `gh api`.
- Dependency chains longer than 3 hops (A blocks B blocks C blocks D) almost always mean the slicing is too thin. Collapse the chain into fewer, wider slices.
- GitHub assigns issue numbers alongside PR numbers. Resolve each blocker to its actual number before publishing a dependent slice.
- AFK issues (no human interaction) appear attractive but the label is aspirational. Real AFK requires green CI, clear acceptance criteria, and no design ambiguity — misclassifying HITL as AFK creates reopens.
- User stories referenced by "number from the PRD" drift if the PRD gets edited. Quote the story text inline if it is short, or pin to a PRD anchor (`#issue-42 > User Story 7`) to resist drift.

## When NOT to Use

- For breaking a PRD into a **plan** (phases, no issues yet) — use `/prd-to-plan`
- For writing the PRD itself — use `/write-a-prd`
- For filing a single bug — use `/qa-session` or `/triage-issue`
- For a plan that exists but has no PRD — use `/plan` then revisit this skill
- For triaging existing issues (not creating new ones) — this skill is create-only
