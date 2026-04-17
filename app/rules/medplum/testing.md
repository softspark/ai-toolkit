---
language: medplum
category: testing
version: "1.0.0"
---

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
