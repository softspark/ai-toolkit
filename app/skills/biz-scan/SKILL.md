---
name: biz-scan
description: "Scans codebase for business opportunities by analyzing database schemas, API endpoints, tracking events, and feature flags to surface underutilized capabilities, missing KPIs, and monetization gaps. Use when the user asks about revenue opportunities, business metrics, KPI coverage, analytics gaps, or monetization analysis of a codebase."
effort: medium
disable-model-invocation: true
argument-hint: "[area]"
agent: business-intelligence
context: fork
allowed-tools: Read, Grep, Glob
---

# Biz Scan Command

$ARGUMENTS

Triggers the Business Intelligence agent to analyze the codebase for business opportunities and KPI gaps.

## Usage

```bash
/biz-scan [scope]
# /biz-scan schema     : focus on database models and entity relationships
# /biz-scan api        : focus on API endpoints and data exposure
# /biz-scan all        : full codebase scan
```

## Protocol

### 1. Model Scan: Analyze Data Layer

Scan for business-relevant data structures:

```bash
# Find database models, schemas, entities
grep -rl "model\|schema\|entity\|migration" --include="*.py" --include="*.ts" --include="*.rb" .
# Find ORM definitions
grep -rl "prisma\|sequelize\|typeorm\|sqlalchemy\|activerecord" .
```

Catalog: entity names, relationships, fields that map to business concepts (revenue, subscription, usage, billing).

### 2. Logic Scan: Analyze Business Logic

Scan controllers, services, and use cases:

```bash
# Find API endpoints and handlers
grep -rn "router\.\|app\.\(get\|post\|put\|delete\)\|@Controller\|@app\.route" --include="*.ts" --include="*.py" --include="*.js" .
# Find tracking/analytics events
grep -rn "track\|analytics\|event\|metric\|log_event" --include="*.ts" --include="*.py" --include="*.js" .
```

Catalog: exposed endpoints, tracked events, feature flags, A/B tests.

### 3. Synthesis: Match Data vs. Business Goals

Cross-reference findings to identify:

| Category | What to Look For |
|----------|-----------------|
| **Missing KPIs** | Entities with no associated tracking events |
| **Underutilized features** | Endpoints with no analytics or feature-flag coverage |
| **Monetization gaps** | Subscription/billing entities without conversion tracking |
| **Data exposure** | Rich internal data not surfaced via API |

### 4. Report: Generate Opportunity Report

Output a structured markdown report:

```markdown
## Business Opportunity Report: [scope]

### KPI Coverage
| Entity/Feature | Tracked Events | Gap |
|---------------|---------------|-----|
| [name] | [events or "none"] | [what's missing] |

### Opportunities (ranked by estimated impact)
1. **[Opportunity]**: [description, affected entities, suggested action]

### Quick Wins
- [ ] Add tracking to [feature], estimated lift: [low/med/high]

### Data Exposure Gaps
- [Entity] has [N fields] not exposed via any API endpoint
```

## Rules

- **MUST** tie every opportunity to a concrete business metric or KPI name — "improve onboarding" is not an opportunity, "increase trial-to-paid conversion" is
- **MUST** rank the opportunity list by estimated impact (rough order of magnitude is enough) — alphabetical order hides the signal
- **NEVER** propose a new tracking event without first checking for an existing one — duplicate events corrupt analytics pipelines
- **CRITICAL**: output is advisory. Do not modify tracking code in the scan. The product owner decides what ships.
- **MANDATORY**: when the codebase has no analytics layer at all, say so explicitly and stop — the gap is "no instrumentation", not "no opportunities".

## Gotchas

- ORM models and TypeScript/Zod types often drift. An entity may exist in the DB schema but be invisible to the API layer (and vice-versa) — grep both sides before declaring "no tracking coverage".
- Feature flags without analytics wiring are invisible to most scans. A flag can gate a feature with zero rollout data; treat a flag-without-exposure as its own gap category.
- "No tracking event on entity X" often means X is tracked via a parent event (e.g., `order_items` piggybacking on `order_completed`). Walk the event taxonomy one level up before calling a gap.
- Revenue attribution in multi-tenant apps often splits client-side (page views, clicks) from server-side (conversions). Scanning only one side produces systematically wrong conclusions about monetization coverage.
- Migration files may show deleted columns that live code no longer references — always check the current schema (`alembic current`, `prisma migrate status`) before treating a migration-declared field as live.

## When NOT to Use

- For **implementing** a tracking change — use `/fix` or the relevant language skill
- For dashboard design or SQL queries — delegate to the `data-analyst` agent
- For generic code-quality metrics — use `/analyze`
- For security or CVE scans — use `/cve-scan` or `/security-patterns`
- When the project has no product-analytics layer configured — document the gap, do not speculate on events
