# Error Contracts and Safe Retries

Use this reference for API failure paths. Apply the host's current contract and
keep unrelated endpoints, schemas and workflows outside the requested change.

## Classify before wording

- Trace the original exception and persisted/provider state. A truncated message
  or a generic unique-constraint error does not identify the affected entity.
- Prefer typed domain exceptions and structured database/provider codes. If a
  constraint name is available only in text, read its diagnostic header rather
  than matching a submitted value in the detail section.
- Distinguish malformed input, authorization, current-state conflict and a
  dependency failure. Preserve deliberate domain-specific status conventions;
  do not mechanically rewrite every existing 400.
- Catch known domain failures narrowly and preserve the exception cause. A
  catch-all that copies arbitrary exception text into a 4xx response both leaks
  internals and blames the caller for server failures.

## Give a supported explanation and a safe action

A useful message identifies the affected operation/resource, the cause that is
actually known, and the next safe action. Use a neutral fallback when the cause
is unknown or disclosing it would reveal protected information.

| Observation | Response direction |
|---|---|
| A resource already has an open session | Explain the existing-session conflict |
| A provider request received no response | Explain the missing response, not a supposed provider rejection |
| The date parser rejected a timestamp | Identify the date/time problem, not an unrelated score or amount |
| An internal persistence invariant failed | Report a server failure, not a missing client field |
| A refund may have been accepted remotely | Require reconciliation before another refund |

Keep SQL, traces, internal paths and provider internals out of ordinary failure
text. Preserve original causes in access-controlled, redacted diagnostics.
Sanitized administrator connection tests and expected row-level validation may
legitimately provide more detail; do not erase useful authorized diagnostics.

## Preserve the wire contract

- Keep existing envelopes, machine codes, field paths and supported media types.
  A client-owned error code must not silently become localized server prose.
- Preserve JSON object/list types, including empty nested `{}` and `[]`.
  Test the round trip when adding a response filter or normalizer.
- Keep recovery headers such as `Allow`, `Retry-After`, authentication challenges
  and concurrency preconditions.
- Verify the host's actual locale selection and fallback. Do not invent a
  profile/tenant/header precedence or assume every existing literal is translated.
- Cover router/firewall errors outside the main API framework and account for
  cloned requests or error subrequests before relying on request attributes.
- Inspect error fields returned with HTTP 200 by background-job status APIs and
  downloadable failure reports. Retain domain validation; sanitize unexpected
  worker failures without changing retry/accounting behavior.

## Do not infer rollback from the response

A transaction can commit before serialization or response delivery fails. A
remote service can accept an operation before its reply is lost. An HTTP error,
including a 5xx, therefore does not prove that nothing happened.

Use the operation's existing idempotency/reconciliation contract. Confirm state
before creating another write. Do not recommend blind replay of an uncertain
payment, refund or other external mutation, and do not remove a database
invariant merely to make its error disappear.

## Verify behavior at the boundary

Choose tests for the paths actually changed:

- real constraints, including migration-only indexes omitted by test schemas;
- expected refusals versus unexpected runtime/provider failures;
- idempotent replay, conflicts and recovery after the conflict is resolved;
- HTTP status, public text/code, field paths, locale and recovery headers;
- supported response formats and empty object/list preservation;
- known versus uncertain write outcomes and background-job error fields;
- diagnostic retention without public technical details.

Test actual rate-limit exhaustion and recovery. A non-consuming peek may report
that the peek was accepted even when no request budget remains; the configured
limiter's behavior determines the guard.

Run tests serially when they share or reset a database. Parallel test runners
need isolated databases/stores; a filtered test must not reset the fixtures of
an in-progress full suite.

For additional project evidence, when RAG-MCP is available, retrieve
`shared/rag-mcp/best-practices/api-error-contracts.md`. The guidance above is
self-contained and does not require that integration.
