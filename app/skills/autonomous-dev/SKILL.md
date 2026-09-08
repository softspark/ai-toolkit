---
name: autonomous-dev
description: "Drives a brief, specification, issue or existing PR through implementation, review, tests and QA to a ready PR. Persists ownership, progress and commit-bound evidence for safe resumption. Use for autonomous software delivery or finishing an interrupted development run."
effort: high
argument-hint: "[setup | run <task> | list | resume <run-id> | status <run-id>]"
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Autonomous Development

$ARGUMENTS

Own one software-delivery run from its requested outcome to a reviewed,
verified PR. Continue through reversible decisions within the user's approved
scope, recording assumptions where they can be reviewed. Use existing skills
for their actual work; this skill owns sequencing, state and the exit gate.

## Entry points

| Input | Action |
|---|---|
| `setup` | Inspect the project and create its validation/tracker/QA configuration |
| `run <brief, spec path, Jira key, issue URL or PR URL>` | Resolve the task, reuse existing work, then run the process |
| `list` | List this repository's existing runs without changing state |
| `resume <run-id>` | Read durable state, claim ownership and continue at the first unmet gate |
| `status <run-id>` | Read state and report the next action; change nothing |

A plain task description means `run`. `/workflow autonomous-development`
routes here. A request only to review code stays with `/review`; an incident
stays with the incident-response workflow.

## Setup and authorization

Read [project configuration](reference/project-config.md) on first use or when
project commands change. Check the target repository's instructions, KB, actual
build/test commands and provider identities. Keep `issueTracker`, `codeHost` and
`knowledge` separate. For Jira/RAG projects, read the
[stack integration contract](reference/stack-integrations.md) before discovery
and reuse it for resume, QA and finalization.

Validate the reviewed configuration locally before initializing the run:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/delivery-config.py --config /absolute/project/.ai-toolkit/autonomous.json
python3 ${CLAUDE_SKILL_DIR}/scripts/delivery-config.py --config /absolute/project/.ai-toolkit/autonomous.json --task PROJ-123
```

Pass `--task` only for a Jira key/browse URL; briefs, specs and code-host PRs use
their own source resolution. For Jira, use the returned canonical subject after
checking the real task/instance and Git repository mapping. Preflight does not
contact MCP or prove those live conditions. Configuration records project facts;
it cannot grant publishing permissions, change models or relax host safeguards.

Capture the task, acceptance criteria, exclusions and authorized endpoint before
implementation. The default endpoint is `ready-pr`. An explicit request to run
this process may cover the whole plan; preserve approvals already given instead
of asking at every phase. Ask only for an unresolved decision required by the
task or a missing permission required by the current host. Progress independent
work while the question is pending. Merge and deploy require their own explicit
authorization and are not performed by the state helper.

## Durable state

Use the bundled helper from the installed skill directory:

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/run-state.py --help
python3 ${CLAUDE_SKILL_DIR}/scripts/run-state.py --repo /absolute/project list
python3 ${CLAUDE_SKILL_DIR}/scripts/run-state.py --repo /absolute/project init --subject brief:csv-export --objective "Export filtered orders as CSV" --source-kind brief --source "User task" --target-branch develop
python3 ${CLAUDE_SKILL_DIR}/scripts/run-state.py --repo /absolute/project status --run RUN_ID
```

Use actual values returned by the helper for `RUN_ID`, owner and artifact
directory. Read [state operations](reference/run-state.md) before the first
mutation or a resume. Every writer supplies its per-session owner token. A
GitHub account name is not a unique run owner. Do not initialize a replacement
run to evade an existing claim, failure counter or missing evidence.

Generated state and reports live outside the target repository under its
ai-toolkit session store. Store intentional specifications and regression tests
in the target project's normal locations. Keep terminal output, run reports and
screenshots in the helper's artifact directory so they cannot dirty the code
being verified. The journal records evidence; it does not run tests or certify
the truth of a report. Inspect the actual tool results before recording them.

## Delivery process

Read [execution and recovery](reference/process.md) for the detailed stage
contract. The essential chain is:

1. **Discover and claim.** Resolve the source and search for an existing branch,
   run and PR. For a bug, verify the symptom still exists before changing code.
   For Jira, refresh the scoped task; for RAG, retrieve project SOPs and rules.
   Freeze the relevant task/KB context in the hashed plan.
   Reuse the PR and its branch when present. Use an isolated worktree for new
   work, preserving the user's checkout.
2. **Plan.** Map each acceptance criterion to an implementation slice and its
   verification. Record scope, ownership and dependencies. A small change needs
   a short plan; a specification needs explicit slices and checkpoints.
3. **Implement.** Use the relevant development agent, `/fix` or `/tdd`. Assign
   independent work to available subagents with non-overlapping file ownership;
   use the current host's model and permission settings. Update affected tests
   and docs. Commit the coherent source change before final evidence collection.
4. **Validate and review.** Run the project's configured checks. Use an
   independent reviewer where available, covering spec compliance and code
   quality. Carry inherited PR feedback forward. Fix actionable failures and
   re-run affected gates within the persisted attempt budget.
5. **QA.** For user-facing changes, invoke `/prepare-test-env`, exercise the
   actual acceptance scenarios and capture browser/test evidence. For a change
   that does not need browser QA, record why and which non-UI tests cover it.
6. **Publish or reuse the PR.** Use `/pr` and the
   [tracker contract](reference/tracker.md). Refresh the same PR after fixes.
   Read required checks for its current head, resolve blocking review feedback
   and wait only within the configured CI budget.
7. **Complete.** Record current validation, review, QA and CI evidence and close
   the successful attempt. Require zero `status` blockers and satisfied tracker
   gates, promote/reverify an existing draft if needed, then run `complete`.
   Keep the run resumable until those external operations succeed. Report the PR,
   tested commit and evidence. If a gate is blocked, retain the state and report
   its exact resume command and remaining work.

## Recovery and limits

- Resume from actual Git, tracker and journal state, not the last assistant
  message. Changed code makes earlier evidence stale, even when a label says
  approved. Refresh task requirements and relevant KB/config as well; changed
  acceptance criteria require a revised plan even at the same Git SHA.
  Required CI must refer to the same commit as the PR head.
- Maximum five implementation/recovery attempts, a halt after three consecutive
  failed attempts and at least one minute between attempt starts. The journal
  persists these limits across sessions. Follow any stricter project limits;
  never reset the run to obtain another budget.
- A stopped host has no background continuation guarantee. Leave a durable
  checkpoint before yielding and resume explicitly in the next invocation.
- Release a claim on a deliberate handoff. Preserve state, reports and worktrees
  needed for recovery. Do not steal another session's claim or delete its work.

## Completion and reporting

Completion requires a clean source checkout, the same verified commit, passing
validation and review, applicable QA, satisfied required CI, and the existing
PR identity. An explicit `not-applicable` report is allowed only for a gate
declared optional during setup and with a concrete reason. An unavailable browser,
failed test, pending check or missing permission is a blocker, not an exemption.

`ready-pr` does not set Jira Done. Finish any separately authorized, required
Jira updates before immutable completion, using real transitions and reconciled
receipts. Report KB indexing separately from writing the documentation.

Keep the final report short: outcome, PR, commit, verification and remaining
blocker if any. End with stable chaining lines using actual values:

```text
Run: <run-id>
Status: ready-pr | blocked
PR: <full URL, when created>
Commit: <verified SHA>
Resume: /autonomous-dev resume <run-id>
```

## Gotchas

- Committing after recording checks changes the commit identity. Collect final
  evidence after the code commit, and keep reports outside the checkout.
- Tracker labels are coordination signals, not an atomic lock or proof of QA.
- A reviewer using the same bot account may be unable to submit a formal GitHub
  approval. Attach the review evidence and preserve required human review gates.
- A healthy HTTP endpoint alone does not identify the code it serves. Follow
  `/prepare-test-env` provenance rules before reusing an application instance.

## Related skills

`/plan`, `/write-a-prd`, `/prd-to-plan`, `/debug`, `/fix`, `/tdd`,
`/subagent-development`, `/review`, `/test`, `/lint`, `/build`, `/prepare-test-env`,
`/pr`. Invoke only the ones needed for the current stage; preserve the run's
scope, ownership, approval history and budget across every handoff.
