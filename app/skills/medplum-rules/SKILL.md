---
name: medplum-rules
description: "Medplum (FHIR healthcare) coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: medplum.config.mts, medplum.config.ts, FHIR, Medplum, Bot, Subscription, Questionnaire. Load when writing, reviewing, or editing Medplum (FHIR healthcare) code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Medplum (FHIR healthcare) Rules

These rules come from `app/rules/medplum/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Medplum (FHIR healthcare). Apply them when writing or
reviewing Medplum (FHIR healthcare) code.

# Medplum / FHIR Coding Style

## Resource Structure
- Every FHIR object must include `resourceType` as first field.
- Use PascalCase for resource types (`Patient`, `ServiceRequest`), camelCase for fields (`birthDate`, `valueQuantity`).
- Never hardcode resource IDs. Let the server assign them on create.
- Include `meta.profile` when creating resources that must conform to a StructureDefinition.

## References
- Use `createReference(resource)` from `@medplum/core` to build Reference objects.
- Always include `display` on references for human readability.
- Use `getReferenceString(resource)` for comparisons and logging — returns `ResourceType/id`.
- Use `parseReference(ref)` to extract resourceType and id from a reference string.
- Never concatenate strings to build references manually.

## CodeableConcepts & Coding
- Always include `system`, `code`, and `display` in every Coding element.
- Use standard terminology URIs: `http://loinc.org`, `http://snomed.info/sct`, `http://hl7.org/fhir/sid/icd-10-cm`.
- Use `getCodeBySystem(cc, system)` to find codes; `setCodeBySystem(cc, system, code)` to set them.
- Prefer `CodeableConcept` over plain `Coding` when the FHIR spec allows both — it supports multiple codings and free text.

## Identifiers
- Use `identifier` arrays with `system` + `value` for external IDs (MRN, NPI, SSN).
- Use `getIdentifier(resource, system)` and `setIdentifier(resource, system, value)` helpers.
- Identifier systems must be absolute URIs (e.g., `http://hl7.org/fhir/sid/us-npi`).
- Use `createResourceIfNoneExist(resource, 'identifier=system|value')` for idempotent creates.

## Extensions
- Use the `extension` array with `url` and typed `value[x]` fields.
- Prefer official HL7/US Core extensions over custom ones where they exist.
- Use `getExtension(resource, url)` and `getExtensionValue(resource, url)` helpers.

## Bundles
- Use `urn:uuid:<uuid>` for internal references between entries in a transaction Bundle.
- Every Bundle entry must have `request.method` (`POST`, `PUT`, `DELETE`) and `request.url`.
- Include `fullUrl` on entries that are referenced by other entries.
- Use conditional references (`Practitioner?identifier=npi|123`) for existing resources.

## HIPAA-Aware Coding
- Identifiers like SSN, MRN, and insurance IDs are PHI — never log raw values to console or external services.
- Use a safe logging utility (e.g., `safeLog()`) for any output that might contain patient data. Never `console.log` raw FHIR resources.
- Reference `display` strings may contain patient names — treat as PHI in logs and error messages.
- Every new data access path or admin operation must include corresponding `AuditEvent` creation. No exceptions.
- When audit logging fails (Medplum unreachable), write to a fallback store — audit events must never be silently dropped.
- See `security.md` rules for full HIPAA, access policy, and PHI handling requirements.

## Formatting
- Use `formatHumanName()`, `formatAddress()`, `formatDate()`, `formatQuantity()` for display strings.
- Use `getDisplayString(resource)` as a universal fallback for any resource's display name.
- Never manually concatenate name parts — FHIR names have `given[]`, `family`, `prefix[]`, `suffix[]`.

# Medplum Frameworks

## @medplum/core — SDK Client
- Use `MedplumClient` for all FHIR operations. Never use raw `fetch` against Medplum endpoints.
- Use `medplum.createResource()`, `readResource()`, `updateResource()`, `deleteResource()` for CRUD.
- Use `medplum.searchResources()` for typed arrays. Use `medplum.searchOne()` when expecting a single result.
- Use `medplum.executeBatch()` for transaction Bundles — groups multiple operations atomically.
- Use `medplum.upsertResource(resource, query)` for atomic create-or-update.
- Use `medplum.createResourceIfNoneExist(resource, query)` for idempotent creation.
- Configure `autoBatchTime` on MedplumClient to auto-batch concurrent GET requests. Use `Promise.all()` instead of sequential `await` to benefit from batching.

## @medplum/fhirtypes — Type Safety
- Import FHIR types directly: `import { Patient, Observation } from '@medplum/fhirtypes'`.
- Use TypeScript types for all FHIR resources — never use `any` for resource data.
- Cast `event.input` in bot handlers: `const patient = event.input as Patient`.
- Use optional chaining for nested FHIR fields: `patient.name?.[0]?.given?.[0]`.

## @medplum/react — UI Components
- Wrap app with `<MedplumProvider client={medplum}>` at the root.
- Use `useMedplum()` hook to access the MedplumClient instance in components.
- Use `useMedplumContext()` for client + profile + loading state together.
- Use `<ResourceForm>` for auto-generated CRUD forms, `<ResourceTable>` for display.
- Use `<SearchControl>` for searchable/filterable resource lists.
- Use `<QuestionnaireForm>` to render FHIR Questionnaires and capture responses.
- Use `useSubscription(criteria)` for real-time WebSocket data in React components.
- Requires Mantine 7+ and PostCSS with Mantine preset. Import `@mantine/core/styles.css`.

## Bot Development
- Export a single `handler` function: `export async function handler(medplum: MedplumClient, event: BotEvent)`.
- Access trigger resource via `event.input`. Access secrets via `event.secrets`.
- Use `event.contentType` to determine input format (`application/fhir+json`, `text/plain`, `x-application/hl7-v2+er7`).
- Deploy bots via CLI for CI/CD: `medplum bot deploy <bot-name>`.
- Apply AccessPolicies to bots — restrict to minimum required resource types.
- Use Subscriptions with `channel.type: 'rest-hook'` and `channel.endpoint: 'Bot/<ID>'` for event-driven execution.

## GraphQL
- Append `List` to resource type for searches: `PatientList(name: "Eve")`.
- Use snake_case for search parameters in GraphQL (not kebab-case): `address_city`, not `address-city`.
- Use inline fragments for reference resolution: `... on Observation { valueQuantity { value } }`.
- Use `_reference` for reverse lookups: `EncounterList(_reference: patient)`.

## CLI (@medplum/cli)
- Use `medplum login` for auth, `medplum get`/`medplum post` for FHIR operations.
- Use `medplum bot deploy` for bot deployment in CI/CD pipelines.
- Use `medplum bulk export` for bulk data operations.

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

# Medplum / FHIR Security

## Authentication
- Use client credentials flow (`startClientLogin`) for backend services and integrations.
- Use authorization code flow (`startLogin` + `processCode`) for user-facing web apps.
- Never store tokens in `localStorage` in production — use secure HTTP-only cookies or server-side sessions.
- Use `refreshIfExpired()` before critical operations. Set `gracePeriod` to refresh proactively.
- Use `setBasicAuth(clientId, clientSecret)` only for server-side code, never in browser.
- Rotate client secrets via `$rotate-client-secret` operation periodically.

## Access Policies
- Every non-admin user must have an AccessPolicy. Never leave users with default full access.
- Scope to specific resource types: list only the types the user needs.
- Use `readonly: true` or explicit `interaction` arrays to restrict write access.
- Use `criteria` with FHIR search syntax to filter visible resources (e.g., `Patient?organization=Organization/123`).
- Use `hiddenFields` to prevent sensitive fields from being returned (e.g., SSN).
- Use `readonlyFields` to allow viewing but prevent modification of specific fields.
- Use `writeConstraint` FHIRPath expressions for business rules (e.g., prevent status rollback on finalized resources).
- Test access policies by logging in as a test user with the policy applied.

## HIPAA & Audit Logging
- Medplum automatically creates AuditEvent resources for all FHIR operations.
- Never log PHI (patient names, identifiers, health data) to application console or external services.
- Use structured audit references: reference the Patient and the accessing Practitioner in audit records.
- For custom audit trails, create AuditEvent resources with `type`, `agent`, `entity`, and `outcome`.
- Ensure audit events are never silently dropped — if Medplum is unreachable, write to a fallback store.

## PHI Handling
- Never include PHI in URLs, query parameters, or HTTP headers.
- Use POST-based search for queries containing sensitive criteria.
- Use `Binary` resources with `securityContext` for sensitive file attachments.
- Encrypt data at rest and in transit (TLS 1.2+). Medplum hosted handles this automatically.
- Apply data retention policies — use `$expunge` operation for permanent deletion when required.

## SMART Scopes
- Use `patient/*.read` style scopes for patient-facing apps.
- Use `user/*.read` style scopes for practitioner-facing apps.
- Validate scopes server-side on every request — do not trust client-side scope claims.
- Use `launch/patient` context for apps launched within a patient context.
- Define minimal scopes: request only the resource types and operations needed.

## Multi-Tenant Isolation
- Use Medplum Projects for tenant isolation — each project is a separate data silo.
- Never share AccessPolicies across projects/tenants.
- Validate `meta.project` on operations when building multi-tenant middleware.
- Use separate ClientApplications per tenant for backend integrations.

## Secrets Management
- Use Bot secrets (`event.secrets`) for API keys, connection strings, and credentials.
- Never hardcode secrets in bot source code or resource data.
- Use Medplum project-level secrets storage — accessible only by project admins.
- Rotate secrets on a regular schedule and after any suspected compromise.

# Medplum / FHIR Testing

## MockClient
- Use `MockClient` from `@medplum/mock` for unit tests — it simulates the full MedplumClient API in memory.
- Pre-populate test data with `mockClient.createResource()` before running test assertions.
- MockClient supports `search`, `searchResources`, `searchOne`, `readResource`, `updateResource`, `deleteResource`.
- MockClient does not require network access — tests run fast and offline.
- Use `new MockClient()` per test to ensure isolation between test cases.

## Bot Unit Testing
- Test the handler function directly: `await handler(mockClient, mockEvent)`.
- Create mock `BotEvent` objects with `input`, `contentType`, `secrets`, and `bot` fields.
- Verify resource creation: call `mockClient.searchResources()` after handler execution.
- Test error paths: pass invalid input resources and assert the handler throws or returns errors.
- Test different content types: `application/fhir+json`, `text/plain`, `x-application/hl7-v2+er7`.
- Mock `event.secrets` for bots that depend on external API keys.

## Resource Validation
- Use `validateResource(resource)` from `@medplum/core` to check resources against StructureDefinitions.
- Test that required fields produce `OperationOutcome` errors when missing.
- Test custom profiles: create a `StructureDefinition` resource, then validate resources against it.
- Use the `$validate` operation for server-side validation in integration tests.
- Test the Data Absent Reason extension when required fields may legitimately be empty.

## Search Testing
- Test search parameter behavior: exact match vs prefix match vs substring (`name`, `name:exact`, `name:contains`).
- Verify `_include` returns related resources in the Bundle.
- Test pagination with `_count` and `_offset` parameters.
- Test token search with and without system namespace: `identifier=value` vs `identifier=system|value`.
- Test date range searches with comparison prefixes: `ge`, `le`, `gt`, `lt`.

## Integration Testing
- Use Medplum Docker image (`medplum/medplum-server`) for local integration tests.
- Test full workflows end-to-end: create patient → create observation → search → verify.
- Verify Bundle transactions are atomic: intentionally fail one entry and confirm rollback.
- Test access policies by authenticating as users with different policies.
- Test Subscription triggers: create a Subscription, modify a matching resource, verify Bot execution.

## Test Data Factories
- Create typed factory functions: `createTestPatient(overrides?)`, `createTestObservation(overrides?)`.
- Use realistic but synthetic data — never use real patient data in tests.
- Include only minimal required fields by default. Let tests add specific fields via overrides.
- Use `generateId()` from `@medplum/core` for unique test identifiers.
- Use standard test identifier systems: `http://example.com/test-mrn` to avoid collision with real systems.

## Assertions
- Assert on `OperationOutcome` for error responses: check `issue[].severity`, `issue[].code`, `issue[].expression`.
- Use `isOk(outcome)` and `isNotFound(outcome)` from `@medplum/core` for status checks.
- Use `deepEquals(a, b)` for resource comparison (ignores `meta.versionId` and `meta.lastUpdated`).
- Assert reference integrity: verify `subject.reference` matches expected `Patient/id` format.
