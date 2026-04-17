---
title: "Medplum Documentation Map"
category: reference
service: ai-toolkit
tags: [medplum, fhir, healthcare, ehr, sdk, api, clinical, interoperability]
version: "1.0.0"
created: "2026-04-17"
last_updated: "2026-04-17"
description: "Comprehensive navigable index of Medplum documentation covering SDK, FHIR resources, clinical workflows, security, integrations, and terminology."
---

# Medplum Documentation Map

## Overview

Medplum is an open-source healthcare platform built on FHIR R4. It provides a FHIR-compliant datastore, TypeScript SDK, React component library, bot automation engine, and compliance infrastructure (HIPAA, SOC2, HITRUST).

| Item | Value |
|------|-------|
| Docs | `https://www.medplum.com/docs/` |
| API Base | `https://api.medplum.com/fhir/R4/` |
| App | `https://app.medplum.com/` |
| Storybook | `https://storybook.medplum.com/` |
| GraphiQL | `https://graphiql.medplum.com/` |

### Key Packages

| Package | Purpose |
|---------|---------|
| `@medplum/core` | SDK client, FHIR helpers, FHIRPath, HL7 parsing |
| `@medplum/fhirtypes` | TypeScript type definitions for all FHIR R4 resources |
| `@medplum/react` | React UI components (Mantine 7+, React 18+) |
| `@medplum/mock` | MockClient for unit testing |
| `@medplum/cli` | Command-line interface for FHIR operations |

---

## Documentation Sections

| Section | Path | Description |
|---------|------|-------------|
| FHIR Basics | `/docs/fhir-basics` | Resources, references, search, CodeableConcepts, identifiers, ValueSets, Subscriptions |
| FHIR Datastore | `/docs/fhir-datastore` | CRUD, binary data, batch requests, profiles, history, deduplication, USCDI |
| Search | `/docs/search` | Basic search, advanced parameters, `_filter`, pagination, `_include`/`_revinclude`, chaining |
| Terminology | `/docs/terminology` | CodeSystem, ValueSet, ConceptMap operations; LOINC, SNOMED, ICD-10 |
| GraphQL | `/docs/graphql` | Queries, mutations, connections, nested resolution, reverse references, array filtering |
| React Components | `/docs/react` | MedplumProvider, hooks, Mantine integration, tree-shaking, useSubscription |
| Analytics | `/docs/analytics` | Analytics and reporting capabilities |
| Auth | `/docs/auth` | OAuth2 flows, client credentials, external IDPs, Google, mTLS, MFA, token exchange, sessions |
| User Management | `/docs/user-management` | Project vs server users, registration, invitations |
| Access Control | `/docs/access` | Access policies, compartments, SMART scopes, IP rules, multi-tenant, field-level control |
| AI | `/docs/ai` | AI operations, AWS integration, MCP server |
| Bots | `/docs/bots` | Bot basics, cron jobs, questionnaire handlers, Lambda layers, secrets, webhooks, HL7, PDFs, unit testing |
| Subscriptions | `/docs/subscriptions` | Event-driven notifications, WebSocket, webhook resending |
| CLI | `/docs/cli` | Command-line FHIR operations, external servers |
| Integrations | `/docs/integration` | DoseSpot, Health Gorilla, Stedi, Candid Health, eFax, HL7, FHIRcast, SMART, CDS Hooks, C-CDA |
| Agent | `/docs/agent` | On-prem agent for HL7/DICOM bridging |
| Self-Hosting | `/docs/self-hosting` | Self-hosted deployment |
| Compliance | `/docs/compliance` | HIPAA, SOC2, HITRUST, ONC, CLIA/CAP, CFR11, GMP, ISO9001 |
| API Reference | `/docs/api` | REST endpoints, FHIR resources (150+), operations (40+), datatypes (40+), Medplum custom resources |
| SDK Reference | `/docs/sdk/core` | MedplumClient, utility functions, interfaces, types |

---

## Clinical Workflows

| Workflow | Path | Key Resources |
|----------|------|---------------|
| Intake & Registration | `/docs/intake` | Patient, QuestionnaireResponse, Encounter |
| Charting | `/docs/charting` | Condition, AllergyIntolerance, Observation (vitals), DocumentReference |
| Scheduling | `/docs/scheduling` | Schedule, Slot, Appointment, AppointmentResponse |
| Labs & Imaging | `/docs/labs-imaging` | ServiceRequest, DiagnosticReport, Observation, ImagingStudy |
| Medications | `/docs/medications` | MedicationRequest, Medication, MedicationAdministration |
| Care Plans | `/docs/careplans` | CarePlan, CareTeam, Task, PlanDefinition, Goal |
| Communications | `/docs/communications` | Communication, CommunicationRequest (threads, messaging, SMS) |
| Billing | `/docs/billing` | Claim, Coverage, ExplanationOfBenefit, ChargeItem |

### Clinical Configuration

| Feature | Path | Resources |
|---------|------|-----------|
| Provider Directory | `/docs/administration/provider-directory` | Practitioner, PractitionerRole, Organization, Location |
| Questionnaires | `/docs/questionnaires` | Questionnaire, QuestionnaireResponse, SDC extensions |
| Diagnostic Catalog | `/docs/careplans/diagnostic-catalog` | CodeSystem, ValueSet (LOINC panels) |
| Clinical Protocols | `/docs/careplans/protocols` | PlanDefinition, ActivityDefinition |

---

## SDK Reference — MedplumClient

### CRUD Operations

| Method | Description |
|--------|-------------|
| `createResource(resource)` | Create new FHIR resource (server assigns ID) |
| `readResource(resourceType, id)` | Read resource by type and ID |
| `updateResource(resource)` | Update existing resource (must include ID) |
| `patchResource(resourceType, id, operations)` | Apply JSON Patch operations |
| `deleteResource(resourceType, id)` | Delete resource by type and ID |
| `upsertResource(resource, query)` | Atomic create-or-update via search query |
| `createResourceIfNoneExist(resource, query)` | Conditional create if no match found |

### Search

| Method | Description |
|--------|-------------|
| `search(resourceType, query)` | Execute FHIR search, returns Bundle |
| `searchResources(resourceType, query)` | Returns resource array (unwrapped Bundle) |
| `searchOne(resourceType, query)` | Returns first matching resource |
| `searchResourcePages(resourceType, query)` | Async generator for paginated results |
| `fhirSearchUrl(resourceType, query)` | Build search URL from parameters |

### Authentication

| Method | Description |
|--------|-------------|
| `startLogin(loginRequest)` | Initiate user login flow |
| `startClientLogin(clientId, clientSecret)` | OAuth2 client credentials flow |
| `startGoogleLogin(loginRequest)` | Google Sign-In authentication |
| `setAccessToken(accessToken, refreshToken)` | Manually set auth tokens |
| `setBasicAuth(clientId, clientSecret)` | Configure basic auth |
| `signOut()` | Revoke token and clear cache |
| `isAuthenticated(gracePeriod)` | Check current auth status |
| `getProfile()` | Get current user profile (sync) |
| `getProfileAsync()` | Get current user profile (async fetch) |

### Advanced Operations

| Method | Description |
|--------|-------------|
| `executeBatch(bundle)` | Process batch or transaction Bundle |
| `executeBot(id, body, contentType)` | Run bot by ID or Identifier |
| `graphql(query, operationName, variables)` | Execute GraphQL queries |
| `readHistory(resourceType, id)` | Get all resource versions |
| `readPatientEverything(id)` | Patient $everything operation |
| `validateResource(resource)` | Validate resource against profiles |
| `valueSetExpand(params)` | Expand ValueSet for code lookups |
| `readResourceGraph(resourceType, id, graphName)` | Fetch linked resources via $graph |

### Media & Files

| Method | Description |
|--------|-------------|
| `createBinary(data, filename, contentType)` | Create Binary resource from data |
| `createAttachment(data, filename, contentType)` | Create Attachment element with Binary |
| `createPdf(docDefinition, filename)` | Generate PDF as Binary (pdfmake) |
| `uploadMedia(contents, contentType, filename)` | Upload and create Media resource |
| `download(url)` | Download URL as blob |

### Subscriptions & Real-time

| Method | Description |
|--------|-------------|
| `subscribeToCriteria(criteria, props)` | Subscribe to WebSocket notifications |
| `unsubscribeFromCriteria(criteria, props)` | Unsubscribe from criteria |
| `getSubscriptionManager()` | Access WebSocket subscription manager |

---

## SDK Utility Functions

| Function | Description |
|----------|-------------|
| `createReference(resource)` | Create a FHIR Reference from a resource |
| `getReferenceString(resource)` | Get `ResourceType/id` string |
| `getDisplayString(resource)` | Human-readable display for any resource |
| `formatHumanName(name)` | Format FHIR HumanName as string |
| `formatAddress(address)` | Format FHIR Address as string |
| `formatCodeableConcept(cc)` | Format CodeableConcept as string |
| `formatDate(date)` | Format FHIR date as human-readable |
| `formatDateTime(dateTime)` | Format FHIR dateTime as human-readable |
| `formatQuantity(quantity)` | Human-readable Quantity string |
| `getCodeBySystem(cc, system)` | Find code for a given system in CodeableConcept |
| `setCodeBySystem(cc, system, code)` | Set code for a given system |
| `getIdentifier(resource, system)` | Get identifier value for a system |
| `setIdentifier(resource, system, value)` | Set identifier for a system |
| `getExtension(resource, urls)` | Get extension by URL |
| `getExtensionValue(resource, urls)` | Get extension value by URL |
| `parseReference(ref)` | Parse reference string to ResourceType/ID |
| `resolveId(reference)` | Extract ID from reference |
| `isResource(value)` | Type guard for FHIR resource |
| `isReference(value)` | Type guard for FHIR Reference |
| `deepClone(value)` | Deep clone a FHIR resource |
| `deepEquals(a, b)` | Compare resources (ignoring versionId) |
| `normalizeOperationOutcome(error)` | Normalize error to OperationOutcome |
| `normalizeErrorString(error)` | Normalize error to displayable string |
| `getQuestionnaireAnswers(response)` | Extract answers as map by linkId |
| `evalFhirPath(expression, resource)` | Evaluate FHIRPath expression |
| `validateResource(resource)` | Validate against StructureDefinition |
| `generateId()` | Cross-platform UUID generator |

---

## FHIR Search Syntax

### Parameter Types

| Type | Behavior | Example |
|------|----------|---------|
| `string` | Case-insensitive prefix match | `name=eve` matches Eve, Evelyn |
| `token` | Exact match, supports system namespace | `identifier=http://sys\|val` |
| `date` | Supports comparison prefixes | `birthdate=1940-03-29` |
| `reference` | Links to other resources | `subject=Patient/123` |
| `quantity` | Numeric with units | `value-quantity=gt40` |
| `number` | Plain numeric | `probability=gt0.8` |

### Operators

| Operator | Syntax | Example |
|----------|--------|---------|
| AND | Multiple parameters | `name=Simpson&birthdate=1940-03-29` |
| OR | Comma-separated | `status=completed,cancelled` |

### Modifiers

| Modifier | Purpose | Example |
|----------|---------|---------|
| `:not` | Exclude values | `status:not=completed` |
| `:missing` | Include/exclude absent params | `birthdate:missing=true` |
| `:contains` | Substring match (string only) | `name:contains=eve` |
| `:exact` | Case-sensitive exact match | `name:exact=Eve` |

### Comparison Prefixes (date, quantity, number)

| Prefix | Meaning |
|--------|---------|
| `eq` | Equal (default) |
| `ne` | Not equal |
| `gt` | Greater than |
| `lt` | Less than |
| `ge` | Greater than or equal |
| `le` | Less than or equal |
| `sa` | Starts after |
| `eb` | Ends before |

### Special Parameters

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `_sort` | Sort results (prefix `-` for descending) | `_sort=-_lastUpdated` |
| `_count` | Results per page | `_count=20` |
| `_offset` | Pagination offset | `_offset=40` |
| `_total` | Include total count | `_total=accurate` |
| `_include` | Include forward-referenced resources | `_include=Observation:patient` |
| `_revinclude` | Include backward-referencing resources | `_revinclude=Provenance:target` |
| `_include:iterate` | Recursive inclusion (multi-hop) | `_include:iterate=Patient:general-practitioner` |

---

## Core FHIR Resources

### Clinical

| Resource | Purpose |
|----------|---------|
| `Patient` | Demographics, identifiers, contacts |
| `Practitioner` | Provider demographics, qualifications |
| `PractitionerRole` | Provider role at organization/location |
| `Organization` | Healthcare organization |
| `Encounter` | Patient visit or interaction |
| `Condition` | Diagnosis or health concern |
| `Observation` | Measurements, vitals, lab results |
| `DiagnosticReport` | Lab/imaging report aggregating observations |
| `ServiceRequest` | Order for a procedure, lab, or referral |
| `MedicationRequest` | Prescription or medication order |
| `AllergyIntolerance` | Allergy or adverse reaction record |
| `Procedure` | Performed clinical procedure |
| `CarePlan` | Treatment plan with activities and goals |
| `CareTeam` | Group of practitioners caring for a patient |
| `Goal` | Patient health objective |
| `Task` | Actionable work item |

### Administrative

| Resource | Purpose |
|----------|---------|
| `Schedule` | Provider availability container |
| `Slot` | Bookable time block within a Schedule |
| `Appointment` | Scheduled visit with participants |
| `Coverage` | Insurance/payer information |
| `Claim` | Billing claim submission |
| `Communication` | Message between participants |
| `Questionnaire` | Form/survey definition |
| `QuestionnaireResponse` | Completed form responses |

### Infrastructure

| Resource | Purpose |
|----------|---------|
| `Bundle` | Collection of resources (transaction, batch, searchset) |
| `Subscription` | Event-driven notification trigger |
| `AuditEvent` | Security/privacy audit log entry |
| `Binary` | Raw binary data (files, images) |
| `DocumentReference` | Metadata about a document/attachment |
| `OperationOutcome` | Processing result with issues/errors |
| `ValueSet` | Set of codes for a specific use |
| `CodeSystem` | Collection of codes in a domain |
| `StructureDefinition` | Resource profile/schema definition |
| `PlanDefinition` | Clinical protocol/workflow template |

### Medplum Custom Resources

| Resource | Purpose |
|----------|---------|
| `Bot` | Serverless function definition |
| `ClientApplication` | OAuth2 client registration |
| `Project` | Top-level tenant/organization container |
| `ProjectMembership` | User membership with role/access policy |
| `AccessPolicy` | Resource-level access control rules |
| `Agent` | On-prem integration agent |
| `UserConfiguration` | User UI preferences |

---

## Security & Identity

### Authentication Flows

| Flow | Use Case | SDK Method |
|------|----------|------------|
| Client Credentials | Service-to-service, backend | `startClientLogin(clientId, secret)` |
| Authorization Code | User-facing web apps | `startLogin()` + `processCode()` |
| Google Sign-In | Google SSO | `startGoogleLogin()` |
| External IDP | Auth0, Cognito, Okta | `signInWithExternalAuth()` |
| JWT Bearer | Server-issued JWT assertion | `startJwtBearerLogin()` |
| Token Exchange | Convert external tokens | `exchangeExternalAccessToken()` |
| mTLS | Certificate-based auth | Server config |

### Access Policy Features

| Feature | Description |
|---------|-------------|
| Resource type rules | Allow/deny per resource type (read, write, create, delete) |
| Read-only fields | `readonlyFields` array on resource type |
| Hidden fields | `hiddenFields` array on resource type |
| Criteria filtering | FHIR search query (e.g., `Patient?address-state=CA`) |
| Compartments | Patient-based data isolation via `_compartment` |
| Parameterized | Variables: `%profile`, `%profile.id`, `%patient`, custom |
| Write constraints | FHIRPath expressions for state machine enforcement |
| SMART scopes | `patient/*.read`, `user/*.write` style scopes |
| IP rules | Restrict by IP address/CIDR |

---

## Automation

### Bot Handler Pattern

```typescript
import { BotEvent, MedplumClient } from '@medplum/core';
import { Patient } from '@medplum/fhirtypes';

export async function handler(medplum: MedplumClient, event: BotEvent): Promise<any> {
  const patient = event.input as Patient;
  // event.secrets — project secrets map
  // event.bot — reference to this Bot resource
  // event.traceId — request correlation ID
  return true;
}
```

### Bot Execution Triggers

| Trigger | Method |
|---------|--------|
| HTTP POST | `POST /fhir/R4/Bot/<ID>/$execute` |
| FHIR Subscription | Subscription criteria → rest-hook to `Bot/<ID>` |
| Cron schedule | Bot with cron expression in properties |
| Manual | Execute button in Medplum App |

### Subscription Pattern

```typescript
// Server-side: create Subscription resource
const sub = await medplum.createResource({
  resourceType: 'Subscription',
  status: 'active',
  criteria: 'Patient?name=Simpson',
  channel: { type: 'rest-hook', endpoint: 'Bot/<BOT_ID>' }
});

// Client-side: WebSocket subscription
medplum.subscribeToCriteria('Patient?name=Simpson');
```

---

## Integrations

| Integration | Path | Purpose |
|-------------|------|---------|
| DoseSpot | `/docs/integration/dosespot` | E-prescribing (enrollment, favorites, Rx) |
| Health Gorilla | `/docs/integration/health-gorilla` | Lab orders, receiving results |
| Stedi | `/docs/integration/stedi` | EDI/X12 eligibility checks |
| Candid Health | `/docs/integration/candid-health` | Revenue cycle management |
| eFax | `/docs/integration/efax` | Fax send/receive |
| HL7 v2 | `/docs/integration/hl7-interfacing` | ADT, ORM/OBR/OBX message interfacing |
| FHIRcast | `/docs/fhircast` | Real-time clinical context synchronization |
| SMART App Launch | `/docs/integration/smart-app-launch` | Embedded app launch framework |
| CDS Hooks | `/docs/integration/cds-hooks` | Clinical decision support at workflow triggers |
| C-CDA | `/docs/integration/c-cda` | Continuity of Care Document export |
| On-Prem Agent | `/docs/agent` | Bridge to on-prem HL7/DICOM systems |
| Log Streaming | `/docs/integration/log-streaming` | External log aggregation |

---

## Terminology Systems

| System | URI | Usage |
|--------|-----|-------|
| LOINC | `http://loinc.org` | Lab tests, vitals, clinical observations |
| SNOMED CT | `http://snomed.info/sct` | Clinical findings, procedures, body structures |
| ICD-10 | `http://hl7.org/fhir/sid/icd-10-cm` | Diagnoses, billing codes |
| RxNorm | `http://www.nlm.nih.gov/research/umls/rxnorm` | Medications (ingredients, brands, dose forms) |
| NDC | `http://hl7.org/fhir/sid/ndc` | Drug product codes (packaging level) |
| CPT | `http://www.ama-assn.org/go/cpt` | Procedure billing codes |
| UCUM | `http://unitsofmeasure.org` | Units of measure |
| US NPI | `http://hl7.org/fhir/sid/us-npi` | National Provider Identifier |
| US SSN | `http://hl7.org/fhir/sid/us-ssn` | Social Security Number |

---

## Compliance

| Standard | Path | Scope |
|----------|------|-------|
| HIPAA | `/docs/compliance/hipaa` | PHI protection, BAA, audit logging |
| SOC 2 Type II | `/docs/compliance/soc2` | Security, availability, confidentiality |
| HITRUST | `/docs/compliance/hitrust` | Healthcare security framework |
| ONC | `/docs/compliance/onc` | Health IT certification |
| CLIA/CAP | `/docs/compliance/clia-cap` | Laboratory certification |
| 21 CFR Part 11 | `/docs/compliance/cfr11` | Electronic records/signatures |
| ISO 9001 | `/docs/compliance/iso9001` | Quality management |
| HTI-1/HTI-4 | `/docs/compliance/hti-4` | Health tech interoperability rules |

---

## React Components (@medplum/react)

### Setup

Requires: React 18+, Mantine 7+, PostCSS with Mantine preset, `@medplum/core`, `@medplum/react`.

Provider nesting: `BrowserRouter` → `MedplumProvider` → `MantineProvider`.

### Key Components

| Component | Purpose |
|-----------|---------|
| `<MedplumProvider>` | Provides MedplumClient context to app |
| `<SignInForm>` | Authentication form |
| `<ResourceTable>` | Display resource fields in table |
| `<ResourceForm>` | Edit resource with auto-generated form |
| `<SearchControl>` | Search interface with filters and results |
| `<QuestionnaireForm>` | Render and submit FHIR Questionnaire |
| `<QuestionnaireBuilder>` | Build/edit Questionnaire resources |
| `<ChatControl>` | Communication thread interface |

### Key Hooks

| Hook | Purpose |
|------|---------|
| `useMedplum()` | Access MedplumClient instance |
| `useMedplumContext()` | Access client + profile + loading state |
| `useResource(ref)` | Read resource by reference |
| `useSearch(type, query)` | Execute search with React Suspense |
| `useSubscription(criteria)` | WebSocket subscription with auto-cleanup |

---

## Bundle Transaction Pattern

```typescript
const bundle = await medplum.executeBatch({
  resourceType: 'Bundle',
  type: 'transaction',
  entry: [
    {
      fullUrl: 'urn:uuid:patient-1',
      resource: { resourceType: 'Patient', name: [{ family: 'Smith' }] },
      request: { method: 'POST', url: 'Patient' }
    },
    {
      resource: {
        resourceType: 'Observation',
        subject: { reference: 'urn:uuid:patient-1' },  // internal ref
        code: { coding: [{ system: 'http://loinc.org', code: '8867-4' }] }
      },
      request: { method: 'POST', url: 'Observation' }
    }
  ]
});
```

Key patterns:
- `urn:uuid:` for internal references resolved server-side
- `ifNoneExist` on request for conditional creates
- `ifMatch` with `W/"versionId"` for optimistic concurrency
- Conditional references: `Practitioner?identifier=http://hl7.org/fhir/sid/us-npi|123`
- Async processing via `Prefer: respond-async` header for large bundles

---

## GraphQL Patterns

```graphql
# Search with nested resolution
{
  PatientList(name: "Eve", address_city: "Philadelphia") {
    id
    name { family given }
  }
}

# Reverse references
{
  Patient(id: "123") {
    encounters: EncounterList(_reference: patient) {
      id
      status
    }
  }
}

# Inline fragments for reference resolution
{
  DiagnosticReport(id: "456") {
    result {
      resource { ... on Observation { valueQuantity { value unit } } }
    }
  }
}
```

Notes: Search uses snake_case params (not kebab-case). `:not`, `:missing`, `:contains` modifiers not supported in GraphQL. Schema introspection disabled by default.
