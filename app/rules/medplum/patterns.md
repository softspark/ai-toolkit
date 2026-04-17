---
language: medplum
category: patterns
version: "1.0.0"
---

# Medplum / FHIR Patterns

## Bundle Transactions
- Use `type: 'transaction'` for atomic multi-resource operations — all-or-nothing.
- Use `type: 'batch'` when operations are independent and partial failure is acceptable.
- Use `urn:uuid:<uuid>` in `fullUrl` for forward references between entries.
- Reference other entries via `{ reference: 'urn:uuid:<uuid>' }`.
- Use `ifNoneExist` on POST entries for conditional creation (idempotent).
- Use `ifMatch: 'W/"versionId"'` on PUT entries for optimistic concurrency.
- Use conditional references for existing resources: `Practitioner?identifier=http://hl7.org/fhir/sid/us-npi|123`.
- For large bundles (>50MB), use `Prefer: respond-async` header.

## Search Patterns
- Use `_include=ResourceType:searchParam` to fetch referenced resources in one call.
- Use `_revinclude=ResourceType:searchParam` to fetch resources referencing your results.
- Use `:iterate` modifier for multi-hop traversal: `_include:iterate=Patient:general-practitioner`.
- Use `_count` + `_offset` for pagination; use `searchResourcePages()` for async iteration.
- Use `:contains` modifier for substring search on string params: `name:contains=eve`.
- Use `:not` modifier to exclude: `status:not=completed`.
- Use comma-separated values for OR: `status=active,on-hold`.
- Use multiple parameters for AND: `name=Simpson&birthdate=1940-03-29`.
- Prefer `searchResources()` over `search()` — returns typed array, not raw Bundle.

## Subscription & Bot Workflows
- Create a `Subscription` resource with `criteria` (FHIR search query) and `channel.type: 'rest-hook'`.
- Point `channel.endpoint` to `Bot/<BOT_ID>` for automated processing.
- Use `subscribeToCriteria()` client-side for WebSocket real-time updates.
- Never subscribe to `AuditEvent` changes — prevents notification spirals.
- Use cron-based bots for scheduled tasks (e.g., daily reports, batch processing).

## Access Policies
- Define `AccessPolicy.resource[]` with `resourceType` and optional `criteria`, `readonly`, `hiddenFields`, `readonlyFields`.
- Use `%profile` variable to scope data to the current user: `Observation?performer=%profile`.
- Use `%patient` variable for patient-portal access: `Observation?subject=%patient`.
- Use compartment-based access for patient-scoped isolation.
- Use `writeConstraint` with FHIRPath for state machine enforcement (e.g., prevent status rollback).
- Apply least privilege: start with no access, add specific resource types.

## Conditional Operations
- Use `createResourceIfNoneExist(resource, query)` for idempotent creates keyed on identifier.
- Use `upsertResource(resource, query)` for atomic create-or-update in a single request.
- Use `If-None-Exist` header on POST for server-side conditional creation.

## Patient Deduplication
- Match on `identifier` systems (MRN, SSN, insurance ID) for deterministic matching.
- Use probabilistic matching on name + birthdate + address for fuzzy matches.
- Use Patient `link` field with `type: 'replaced-by'` for merge workflows.
- Prefer `createResourceIfNoneExist()` at ingestion to prevent duplicates.

## Questionnaire Workflows
- Create `Questionnaire` resources for form definitions. Use `linkId` for question identification.
- Use `QuestionnaireResponse` for captured answers. Link to Questionnaire via `questionnaire` field.
- Use `getQuestionnaireAnswers(response)` to extract answers as a map keyed by `linkId`.
- Automate post-submission processing with a Bot subscribed to `QuestionnaireResponse` creation.
- Use SDC (Structured Data Capture) extensions for advanced rendering and extraction.
