---
language: medplum
category: security
version: "1.0.0"
---

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
