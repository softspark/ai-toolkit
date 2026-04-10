---
name: documentation-standards
description: "Loaded when creating or updating KB documents, architecture notes, SOPs, or any file in kb/ directory"
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
category: reference                        # REQUIRED — one of 5 valid categories
service: ai-toolkit                        # REQUIRED — service identifier
tags: [tag1, tag2, tag3]                   # REQUIRED — minimum 1, recommended 3+
last_updated: "YYYY-MM-DD"                 # REQUIRED — ISO format
created: "YYYY-MM-DD"                      # REQUIRED — creation date
description: "One-line summary."           # REQUIRED — for search indexing
version: "1.0.0"                           # optional — semver
---
```

**All 7 fields above are REQUIRED.** Documents without valid frontmatter **fail `validate.sh` and block CI**.

## Category Taxonomy

| Category | Directory | Purpose | Examples |
|----------|-----------|---------|----------|
| `reference` | `kb/reference/` | Technical specifications, catalogs, architecture notes, API docs | `agents-catalog.md`, `architecture-overview.md` |
| `howto` | `kb/howto/` | Step-by-step task guides | `use-corrective-rag.md`, `configure-mcp-server.md` |
| `procedures` | `kb/procedures/` | SOPs, runbooks, operational processes | `maintenance-sop.md`, `incident-response.md` |
| `troubleshooting` | `kb/troubleshooting/` | Problem resolution, debugging guides | `database-connection-issues.md` |
| `best-practices` | `kb/best-practices/` | Guidelines, recommendations, standards | `security-checklist.md` |

**Rule:** The `category:` frontmatter field MUST match the directory the file lives in.

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

Valid categories: `reference`, `howto`, `procedures`, `troubleshooting`, `best-practices`, `planning`.

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| No frontmatter | Blocks CI, not indexed | Add frontmatter with all required fields |
| Wrong category | Confuses search | Match `category:` to directory name |
| Non-English content | Inconsistent KB | Translate to English |
| Date in filename | Clutters, becomes stale | Use `created:` in frontmatter |
| Empty tags | Hurts search relevance | Add at least 1 meaningful tag |
| Placeholder content | Wastes reader time | Write real content or don't create the doc |
