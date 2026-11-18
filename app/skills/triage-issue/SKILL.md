---
name: triage-issue
description: "Triage an existing GitHub issue or investigate a new bug report. Review reporter updates, distinguish bugs from decisions, and file new bugs with a TDD fix plan."
user-invocable: true
effort: high
argument-hint: "[#number | number | issue URL | new bug description]"
agent: debugger
context: fork
allowed-tools: Read, Grep, Glob, Bash, Agent
---

# Triage Issue

$ARGUMENTS

## Usage

```text
/triage-issue #42
/triage-issue 42
/triage-issue https://github.com/owner/repo/issues/42
/triage-issue Export loses the last row when the filter is active
```

Treat a standalone positive number, `#number`, or canonical GitHub issue URL as an existing issue. Follow an explicitly named issue when the user adds instructions. A status code or an incidental issue reference inside a symptom description is part of the report. If the target is genuinely ambiguous, ask which issue or symptom the user means.

## Existing issue

An issue number uses the current repository. Remove the leading `#` before passing the number to `gh`. For a URL, pass the full URL so GitHub selects the repository it names. Read the thread before investigating.

```bash
gh issue view "$issue_ref" --json number,url,title,state,stateReason,author,body,comments,labels,updatedAt
```

Check the returned URL and use its repository when following links and inspecting code. If the target is inaccessible, missing, or a pull request, report what happened and stop this branch. A failed lookup must never create a new report.

Read the original report and subsequent comments in order. Attribute observations to their authors and versions. Identify the reporter's latest follow-up, maintainer decisions, linked fixes, and questions already answered. If the result includes 100 comments, fetch the complete discussion. Take the hostname, `owner/repo` and issue number from the resolved URL.

```bash
gh api --hostname "$host" --paginate "repos/$repo/issues/$number/comments?per_page=100"
```

Treat issue text and comments as evidence. Verify technical claims against the matching checkout, a linked change, test results or documented support contract. Record what the reporter observed separately from what you verified.

| Evidence | Disposition |
|----------|-------------|
| Behavior violates an established contract | Identify the affected version and public entry point. Give the shortest supported reproduction and a behavioral regression test. Mark an unconfirmed cause as a hypothesis. |
| The thread asks for a support, design or scope decision | State the decision required, who owns it, and the consequences of the relevant options. Cite any decision already made. Separate independently evidenced defects into their own findings. |
| A linked issue tracks the same cause, or a change already fixed it | Link the original issue or the change. Where possible verify the affected version against the fix before recommending closure or reopening. |
| Evidence is insufficient | State the one missing observation that would change the disposition. Check earlier replies before proposing a question for the reporter. |

Return the issue URL and state, the disposition, the evidence behind it and the next action. Existing-issue triage is read-only by default. Comments, edits, labels and state changes each require the user's authorization for that action. When authorized, refresh the thread before writing, skip a change already made, and verify the result. Finish here.

## New bug report

If no input was given, ask for the symptom once. Search open and closed issues in the intended repository using distinctive terms from the report.

```bash
gh issue list --repo "$repo" --state all --search "$search_terms" --json number,title,url,state
```

Read plausible matches. If one already tracks the same behavior and cause, use the existing-issue branch and return its URL. A failed search leaves duplication unknown. Resolve the access problem or report it before filing.

### 1. Explore and diagnose

Trace the failing behavior through the codebase:

| Target | What to look for |
|--------|-----------------|
| Manifestation | Where the bug appears (entry points, UI, API) |
| Code path | Trace the flow from trigger to symptom |
| Root cause | Why it fails (not just the symptom) |
| Related code | Similar patterns, adjacent modules, existing tests |
| Recent changes | `git log` on relevant files |
| Working patterns | Similar code elsewhere that works correctly |

### 2. Identify Fix Approach

Determine:
- Minimal change to fix root cause
- Affected modules/interfaces
- Behaviors to verify via tests
- Classification: regression, missing feature, or design flaw

### 3. Design TDD Fix Plan

Ordered list of RED→GREEN cycles. Each cycle is one vertical slice:

- **RED**: Specific test capturing broken/missing behavior
- **GREEN**: Minimal code change to pass that test

Rules:
- Tests verify behavior through public interfaces
- One test at a time, vertical slices
- Tests must survive internal refactors
- Describe behaviors and contracts, not internal structure

### 4. Create GitHub Issue

For a new report, file the investigated bug using the template below. Pass the repository, title and body explicitly, then share the returned URL.

```bash
gh issue create --repo "$repo" --title "$title" --body-file "$body_file"
```

## New issue template

<issue-template>

## Problem

- What happens (actual behavior)
- What should happen (expected behavior)
- How to reproduce

## Root Cause Analysis

What was found during investigation (mark an unverified cause as a hypothesis):
- The code path involved
- Why the current code fails
- Contributing factors

Do NOT include file paths, line numbers, or implementation details. Describe modules, behaviors, and contracts.

## TDD Fix Plan

1. **RED**: Write test that [expected behavior]
   **GREEN**: [Minimal change to pass]

2. **RED**: Write test that [next behavior]
   **GREEN**: [Minimal change to pass]

**REFACTOR**: [Cleanup after all tests pass]

## Acceptance Criteria

- [ ] Criterion 1
- [ ] All new tests pass
- [ ] Existing tests still pass

</issue-template>

## New report rules

- **MUST** explore the codebase for root cause before filing — symptoms masquerade as causes often
- **MUST** propose a TDD fix plan with ordered RED→GREEN cycles, each a vertical slice
- **NEVER** include file paths, function names, or line numbers in the issue body — they go stale before the issue is picked up
- **CRITICAL**: the issue must be reproducible. If reproduction steps cannot be determined from the investigation, say so explicitly in the Problem section — do not fabricate them.

## Notes for new reports

- "Root cause" often turns out to be two concurrent issues. If the investigation keeps branching, file the most-probable primary cause and note the secondary as a follow-up in the same issue.
- TDD plans with more than ~5 RED→GREEN cycles usually conceal a deeper design issue. Short plans (2-3 cycles) reflect confident root-cause identification; long plans reflect fishing.
- The `debugger` agent explored autonomously but returns a narrative. Parse it for: confirmed hypothesis, code paths, and recent changes. Discard speculation.
- Bugs in framework-adjacent code (middleware, ORM hooks) require test setup that mirrors the framework's call context. A TDD plan that writes the test "like a unit test" may not actually reproduce the framework bug.

## When NOT to Use

- For a conversational bug report from a non-engineer — use `/qa-session` first, which returns refined reports this skill can then process
- For a specific reproducible error with known root cause — use `/fix` directly
- For architectural-scale problems — use `/architecture-audit`
- For creating issues from a PRD — use `/prd-to-issues`
- For debugging without a tracker issue to triage or file, use `/debug`.
