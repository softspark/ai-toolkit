# Tracker, PR and evidence contract

Project configuration selects `issueTracker` for task data and `codeHost` for
PRs and CI. Use the available GitHub CLI or an existing connector through its
actual documented interface. Verify the repository/account and project language
before writing.
Do not invent provider tool names or silently substitute another tracker.

Jira and RAG projects also follow [the stack contract](stack-integrations.md),
including scoped refresh, source snapshots, comment receipts and indexing.

## Required capabilities

| Capability | Purpose |
|---|---|
| Read source issue/spec PR and comments | Recover the approved task and prior decisions |
| Search open PRs by repository and head branch | Reuse work, including interrupted publication |
| Read head/base SHA, diff and review feedback | Identify the exact source and unresolved asks |
| Create/update a PR and attach evidence | Publish the deliverable when authorized |
| Read required checks and review/mergeability state | Prove readiness for the current remote head |

If a connector lacks a required operation, record a blocker at that boundary.
Local implementation can continue when independent. A Jira issue with a GitHub
code repository uses Jira for task data and GitHub for PR/CI data; neither
identifier replaces the other. Follow connector-specific freshness, language
and transition rules.

## Ownership and idempotency

Use the local journal's run ID and owner token for transactional ownership on
the current filesystem. It does not supply a distributed lock across machines.
Where authorized, an existing assignee/claim label plus a run-ID comment signals
tracker ownership. Respect another live run even if it uses the same account.
Labels never replace the per-session owner token.

Before creating a PR, search its exact repository/head branch and inspect any
match. A checkpointed PR URL is authoritative only after verifying it still
points to that branch. If it is closed or merged, report its actual state;
do not reopen it or create a replacement without resolving the task's intent.

For GitHub or another provider whose actual API supports editing the current
actor's comments, a stable marker can identify a summary for idempotent updates:

```html
<!-- ai-toolkit:autonomous-dev:<run-id> -->
```

Update a matching comment only if it belongs to the current authorized actor.
Do not edit another person's comments. Write comments only where the user and
current host have authorized them; otherwise put the evidence in the PR body
or local report and state the limitation.

The current Jira MCP has no update-comment operation. Use the visible run/stage/
SHA marker and add-once reconciliation in the stack contract instead of hidden
HTML markers. Respect the tools' explicit content-approval guard. A timeout must
be reconciled through a fresh read before another comment is sent.

## PR content

Use the project's PR template. State the resulting behavior and linked task,
then tests actually run, their results, applicable QA evidence and unresolved
conditions. Link the run and its tested commit. Local artifact paths are not
accessible to remote reviewers: attach sanitized evidence through the configured
provider or include the necessary results in the PR body. Never publish
credentials, local session stores or private logs wholesale.

When label management is enabled, use the repository's existing names and valid
transitions for review, changes requested, QA and ready status. Do not create a
new label taxonomy unasked. A label is a convenience, not a completion gate.

## Readiness

Collect the following against the actual remote head:

- Nonempty validation report with commands and exit status.
- Review report covering the spec, source and inherited blocking feedback.
- Applicable QA evidence from the current source.
- Required CI checks, including any required merge/queue checks.
- Required human approvals, unresolved review conversations and mergeability.
- Refreshed task acceptance criteria and relevant KB/config context; any change
  to the approved contract is reflected in the hashed plan and verification.

The journal checks local evidence freshness and required result values. It does
not query the tracker or enforce branch protection itself. The process must read
and satisfy those external gates before reporting ready. An account that cannot
approve its own PR cannot substitute its local review for a required approval.

No CI checks appearing is not automatically a pass: verify the repository has
no required CI and document that at setup. Missing privileges to inspect checks
are a blocker. Never bypass required checks through administrative merge access.

`ready-pr` is not Jira Done. Apply only configured, authorized transitions whose
actual workflow targets and project completion criteria have been checked.
