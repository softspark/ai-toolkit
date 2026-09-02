---
name: documentation-standards
description: "KB conventions: YAML frontmatter, 10-category taxonomy (reference/howto/procedures/troubleshooting/best-practices/decisions/runbooks/planning/business/templates). Triggers: kb/, SOP, runbook, howto, frontmatter, knowledge base."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Documentation Standards

Auto-loaded knowledge skill enforcing KB document conventions across all agents and skills.

## Frontmatter Specification (MANDATORY)

Every document in `kb/` MUST start with YAML frontmatter:

```yaml
---
title: "Document Title"                    # REQUIRED — English, descriptive
category: reference                        # REQUIRED — one of the 10 valid categories
service: ai-toolkit                        # REQUIRED — service identifier
tags: [tag1, tag2, tag3]                   # REQUIRED — minimum 1, recommended 3+
last_updated: "YYYY-MM-DD"                 # REQUIRED — ISO format
created: "YYYY-MM-DD"                      # REQUIRED — creation date
description: "One-line summary."           # REQUIRED — for search indexing
version: "1.0.0"                           # optional — semver
---
```

**All 7 fields above are REQUIRED.** Documents without valid frontmatter **fail
`scripts/validate.py` and block CI**.

### `section`: a legacy alias, not a second field

Older documents and the `kb-migration` SOP write `section:` where this
specification writes `category:`. Both names are read in the wild, so a document
may carry both — and when it does **they must hold the same value**. A document
filed as `category: reference` and `section: howto` is indexed twice, found
once, and the reader gets whichever the index ranked higher.

New documents should write `category:`. `section:` is accepted, never required,
and never authoritative on its own.

## Category Taxonomy

| Category | Directory | Purpose | Examples |
|----------|-----------|---------|----------|
| `reference` | `kb/reference/` | Technical specifications, catalogs, architecture notes, API docs | `agents-catalog.md`, `architecture-overview.md` |
| `howto` | `kb/howto/` | Step-by-step task guides | `use-corrective-rag.md`, `configure-mcp-server.md` |
| `procedures` | `kb/procedures/` | SOPs a person follows: release, migration, review | `sop-maintenance.md`, `sop-release.md` |
| `troubleshooting` | `kb/troubleshooting/` | Problem resolution, debugging guides | `database-connection-issues.md` |
| `best-practices` | `kb/best-practices/` | Guidelines, recommendations, standards | `security-checklist.md` |
| `decisions` | `kb/decisions/` | Architecture decision records and design rationale | `adr-004-kb-migration.md` |
| `runbooks` | `kb/runbooks/` | Procedures run against a live system, usually under pressure | `deployment.md`, `incident-response.md` |
| `planning` | `kb/planning/` | Roadmaps, PRDs, work not yet done | `q3-roadmap.md` |
| `business` | `kb/business/` | Domain model, requirements, use cases, user stories | `domain-model.md`, `user-stories.md` |
| `templates` | `kb/templates/` | Reusable document templates | `adr-template.md`, `sop-template.md` |

**Rule:** A document filed under one of the directories above MUST declare that
category. The rule is scoped to those directories deliberately: `kb/history/`
and `kb/summaries/` are lifecycle and runtime locations rather than types, and a
finished plan filed under `history/completed/` is still a `planning` document.

**Templates carry placeholders on purpose.** A file under `templates/` exists to
be copied, so a literal `YYYY-MM-DD` date and `[placeholder]` body text are
correct there rather than defects. Every other convention still applies.

This taxonomy lives in three places: ai-toolkit's `scripts/validate.py`,
rag-mcp's `scripts/validate_kb_frontmatter.py`, and this document. They are one
list, and a change belongs in all three.

## Naming Conventions

- **Filename:** kebab-case, descriptive, no dates (`merge-friendly-install-model.md`)
- **Title:** English, clear, matches filename semantics
- **No prefixes:** no `001-`, no `YYYY-MM-DD-` in filenames (dates go in frontmatter)
- **Max length:** keep filenames under 60 characters

## Language Rule

**All KB content MUST be in English.** No exceptions for:
- Document titles
- Body content
- Code comments within docs
- Table headers and descriptions

## Quality Standards

### Required for every KB document:
- [ ] Valid YAML frontmatter with all 7 required fields
- [ ] Category matches directory
- [ ] Written in English
- [ ] Title is clear and descriptive
- [ ] Content is actionable (not just placeholders)

### Required for procedural docs (howto, procedures):
- [ ] Prerequisites listed
- [ ] Steps are numbered
- [ ] Commands are copy-pasteable
- [ ] Verification section present

### Required for troubleshooting docs:
- [ ] Symptoms described
- [ ] Root cause identified
- [ ] Resolution steps provided
- [ ] Prevention notes included

## Templates

### Reference Document
```yaml
---
title: "AI Toolkit - [Topic]"
category: reference
service: ai-toolkit
tags: [topic, subtopic]
version: "1.0.0"
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
description: "Brief summary."
---

# [Topic]

## Overview
[What this document covers]

## Details
[Technical content]

## Related
- [Other relevant KB docs]
```

### How-To Guide
```yaml
---
title: "How to [Task]"
category: howto
service: ai-toolkit
tags: [howto, task-name]
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
description: "Step-by-step guide for [task]."
---

# How to [Task]

## Prerequisites
- [Requirement]

## Steps

### 1. [Action]
[Instructions + commands]

### 2. [Action]
[Instructions + commands]

## Verification
[How to confirm success]

## Troubleshooting
| Problem | Solution |
|---------|----------|
| [Error] | [Fix]    |
```

### SOP / Procedure
```yaml
---
title: "SOP: [Process Name]"
category: procedures
service: ai-toolkit
tags: [sop, process-name]
created: "YYYY-MM-DD"
last_updated: "YYYY-MM-DD"
description: "Standard procedure for [process]."
---

# SOP: [Process Name]

## Purpose
[Why this procedure exists]

## Prerequisites
- [Requirement]

## Procedure
### Step 1: [Action]
[Detailed instructions]

## Verification
[How to verify success]

## Rollback
[How to revert if needed]
```

## Validation

```bash
# Validates ALL kb/**/*.md frontmatter (title, category, service, tags, created, last_updated, description)
scripts/validate.py

# Checks: required fields present, category is valid, tags non-empty
```

Valid categories are the eight in the table above. `scripts/validate.py` holds
the same set in `VALID_KB_CATEGORIES`; the two are the same list in two places
and a change belongs in both.

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| No frontmatter | Blocks CI, not indexed | Add frontmatter with all required fields |
| Wrong category | Confuses search | Match `category:` to directory name |
| Non-English content | Inconsistent KB | Translate to English |
| Date in filename | Clutters, becomes stale | Use `created:` in frontmatter |
| Empty tags | Hurts search relevance | Add at least 1 meaningful tag |
| Placeholder content | Wastes reader time | Write real content or don't create the doc |
