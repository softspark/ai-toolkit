---
language: medplum
category: frameworks
version: "1.0.0"
---

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
