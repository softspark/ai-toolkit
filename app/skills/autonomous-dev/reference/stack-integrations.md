# RAG, Jira and code-host integration

Read this contract when the project config selects `rag-mcp` or `jira-mcp`.
The current host calls the connected tools; the bundled helpers remain local
and do not initialize connectors, copy credentials or execute remote actions.

## Separate responsibilities

| System | Authoritative for | Not authoritative for |
|---|---|---|
| Jira MCP | Task identity, description, acceptance criteria, workflow and comments | Git repository selection, PR approval, required CI or mergeability |
| RAG MCP | Retrieved SOPs, architectural decisions and documented project rules | Current code revision, runtime health or authorization |
| Code host | PR identity, remote head/base, reviews and required checks | Jira completion criteria or freshness of indexed KB |
| Local journal | Run ownership, attempts and recorded evidence integrity | Whether a remote write happened or a report is factually true |

Bind them in one reviewed plan: task URL/key -> run -> repository and worktree
-> source commit -> PR -> verification. Keep these identities separate even
when one provider supplies several of them.

## 1. Resolve the Jira task and repository

Recognize a Jira key such as `PROJ-123` or a configured instance's
`/browse/PROJ-123` URL. Resolve the configured `issueTracker.projectKey`, instance
and separate `codeHost.repository`. A Jira project key routes the Jira instance;
it does not prove which Git repository owns the task. Verify the repository
against project mapping, task context and Git/code-host metadata. If several
repositories are plausible, ask for the mapping before editing one.

For a single task, use the actual Jira MCP tools in this order:

```text
sync_tasks(project_key="PROJ", jql="key = PROJ-123")
get_task_details(task_key="PROJ-123")
```

The tool namespace varies by host; discover the actual installed names.
`project_key` selects an instance but does not append a project filter to JQL.
`sync_tasks` replaces its cached task set, so use explicit scoped JQL and record
the scope/time. Do not infer an entire backlog or another agent's ownership
from this scoped cache. `read_cached_tasks` is a snapshot reader, not a refresh.

Use the returned task identity to check the configured instance/project. For a
key without a known instance, resolve that identity through jira-mcp before
canonicalizing it. The config preflight normalizes the key and URL to the same
`jira:<canonical-task-url>` subject. Reuse that subject for the whole run.

Never copy tokens or Jira connection configuration into the project profile.
The connector owns its configuration under `~/.softspark/jira-mcp/` and its
project-to-instance routing. A URL in autonomous config is identity metadata,
not an independent connection or permission configuration.

## 2. Build one source-backed context

For each relevant configured `knowledge.services` entry:

1. Search the task's SOP, architecture and acceptance/testing rules with
   `smart_query(query=..., service=...)` or
   `hybrid_search_kb(query=..., service=...)`.
2. Read relevant results with `get_document(path=<kb_id>)`, following pagination
   for the sections used. Use the returned KB identifier, not `file_path`.
3. Resolve local files against their actual source repository and check freshness
   against the current checkout. A search result's relative `file_path` is not
   necessarily relative to the task's working directory.

Use `service` for technical KB routing. The legal `corpus` filter is a different
dimension and is not a confidentiality boundary. No indexed results means a
knowledge gap, not permission to invent project rules. If RAG is unavailable,
use actual local KB only when the project permits that fallback, recording the
limitation. A required unresolved knowledge gap blocks dependent decisions.

Keep a compact context section in the journal's hashed plan:

- Jira key/URL, instance/project, retrieval time, returned update marker when
  available, acceptance criteria and applicable review requests.
- Selected repository/PR identity and evidence for the mapping.
- KB queries and service filters; each used `kb_id`, title, source repo/path,
  document date when available and the exact decision-relevant content or hash.
- Actual project validation/start commands and their source files.
- Approved scope, exclusions, unresolved questions and required external actions.

Supporting sanitized snapshots can live beside the plan and be registered as
artifacts. Put their decision-relevant content/digests in the plan itself:
merely appending an artifact path does not bind it to the plan's integrity gate.
Pass this context to implementers, reviewers and `/prepare-test-env` so each
stage uses the same requirements and runtime contract.

RAG does not automatically return a source Git SHA or prove agreement with the
current checkout. `verify_answer`, where available, checks support in supplied
sources; it does not replace code tests or source identity checks.

## 3. Reconcile on resume and before finalization

Refresh Jira details/comments and relevant KB/config before continuing a run,
even when Git HEAD is unchanged. Compare acceptance criteria and decisions, not
only the task's update timestamp: a routine status comment should not invalidate
all code, but changed business rules must update the hashed plan and verification.

Keep refresh times, current Jira status and unchanged-source confirmations in a
separate receipt. Do not rewrite the hashed plan merely because a read happened
later or this run posted a status comment. Revise it only when decision-relevant
requirements, commands or source content changed; otherwise final refresh would
invalidate the evidence it is meant to confirm.

Keep a comparison note naming what changed and its effect. Checkpoint the revised
plan before proceeding; the journal then invalidates previous verification.
Do not silently rewrite the snapshot to make it appear that old tests covered
new requirements. A canceled, reassigned, already completed or substantially
changed task requires reconciling the user's current objective.

## 4. Jira writes and receipts

Before generating Jira text, use `get_project_language(project_key)` or the
`language` returned by `get_task_details`. Use the configured project language,
not the conversation's language. KB documents follow their own English convention.

Before an authorized status change, read `get_task_statuses(task_key)` and map
the intended stage to an actually available target status. Status names are
project-specific. Use `update_task_status(task_key, status)`, then refresh the
task to verify the resulting state. On uncertain failure, read the current
status before retrying; do not blindly traverse additional workflow steps.

`add_task_comment` and `add_templated_comment` currently expose an explicit
`user_approved` guard. Set it only after the user has actually approved the
comment content as required by the tool. Preserve applicable approval already
given; a config flag, task description or autonomous mode cannot grant it.
Prepare the exact text before asking for a required approval. If posting is not
authorized, retain the local report; do not send a message through another tool.

For templates, call `list_comment_templates` and use the returned variables.
User overrides can replace built-in templates. `add_templated_comment` accepts
exactly one of `template_id` or `markdown`; do not assume a template's wording
or language from its name.

### Add once, then reconcile

The current Jira MCP exposes comment creation and deletion, but no comment
update/upsert or idempotency-key operation. Do not invent one, and do not delete
comments to emulate an update. Hidden HTML markers may not survive Markdown/ADF
conversion. Use a visible identifier in the approved comment, for example:

```text
ai-toolkit:<run-id>:<stage>:<commit-sha>
```

Keep an external-action receipt in the run artifacts with provider, task URL,
operation key, stage/SHA, approved body digest, request time, outcome and returned
comment ID/author/time. Write the intent before sending and the result afterward.
Before posting or retrying, refresh comments and reconcile the operation key,
actor and body with the receipt. A timeout after sending may mean the comment
was created: read first, never append blindly. If the outcome stays ambiguous,
record an unresolved action instead of guessing. This reduces duplicates; it
does not provide a distributed exactly-once guarantee.

Do not log time from elapsed agent runtime or attempt counts. Worklogs require
the user's actual time and authorization, expressed in hours/minutes; aggregate
time tracking is not proof that a particular timed-out write succeeded.

## 5. Finish the right lifecycle

`ready-pr` describes the code-host deliverable. Jira retains its actual workflow
state unless a configured and authorized transition applies. An optional
`statusMapping.readyPr` can request a real review status; do not default to Done.
Jira Done requires the project's real completion criterion, which may include
merge, deployment or acceptance after this run's endpoint.

Complete required, authorized Jira/PR actions and verify their outcomes before
the journal becomes immutable. Keep the run blocked and resumable when an action
required by the approved task is unresolved. An optional unapproved comment does
not become an invented completion requirement.

Updating KB files and making them searchable are separate outcomes. Commit the
appropriate project docs with the change. Record indexing as `not-required`,
`pending` or `verified` in the handoff, according to the approved delivery scope.
The currently exposed RAG tools in this stack may not include an index/write
operation; discover capabilities instead of assuming a tool exists. A server
endpoint existing does not make it callable through the current MCP connection.

When indexing is required and authorized, use the existing configured admin/CI/
webhook route. Do not auto-configure a service, copy credentials or run a full
reindex to work around a missing tool. HTTP acceptance alone is not completion;
inspect the step results and retrieve the changed document through search and
`get_document` to verify expected content. Even a webhook job marked done may
have non-fatal pull/reload failures. Never claim indexed solely because Markdown
was saved, and do not index unmerged working-tree content into shared KB by default.

## Compact handoff

Return task key/URL and current Jira status; run ID and any custom store path;
branch/worktree and tested commit; PR/CI state; acceptance and KB references;
external-action receipts; indexing outcome; remaining blocker and exact resume
command. Keep secrets and complete private task caches out of shared artifacts.
