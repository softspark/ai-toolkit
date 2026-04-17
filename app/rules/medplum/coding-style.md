---
language: medplum
category: coding-style
version: "1.0.0"
---

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
