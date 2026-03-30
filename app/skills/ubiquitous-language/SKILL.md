---
name: ubiquitous-language
description: "Extract a DDD-style ubiquitous language glossary from the conversation, flagging ambiguities and proposing canonical terms. Saves to UBIQUITOUS_LANGUAGE.md. Use when user wants to define domain terms, build a glossary, harden terminology, or mentions DDD or domain model."
user-invocable: true
effort: medium
argument-hint: "[domain or context to extract terms from]"
allowed-tools: Read, Write, Edit, Grep, Glob
---

# Ubiquitous Language

$ARGUMENTS

Extract and formalize domain terminology into a consistent glossary.

## Usage

```
/ubiquitous-language [domain or context]
```

## What This Command Does

1. **Scans** conversation for domain-relevant nouns, verbs, and concepts
2. **Identifies** ambiguities, synonyms, and overloaded terms
3. **Proposes** canonical glossary with opinionated term choices
4. **Writes** to `UBIQUITOUS_LANGUAGE.md`

## Process

1. Scan conversation for domain terms
2. Identify problems:
   - Same word used for different concepts (ambiguity)
   - Different words used for same concept (synonyms)
   - Vague or overloaded terms
3. Propose canonical glossary
4. Write to `UBIQUITOUS_LANGUAGE.md`
5. Output summary inline

## Output Format

```markdown
# Ubiquitous Language

## {Domain Group}

| Term | Definition | Aliases to avoid |
|------|-----------|-----------------|
| **Order** | A customer's request to purchase one or more items | Purchase, transaction |

## Relationships

- An **Invoice** belongs to exactly one **Customer**

## Example dialogue

> **Dev:** "When a **Customer** places an **Order**..."
> **Domain expert:** "..."

## Flagged ambiguities

- "account" was used to mean both **Customer** and **User** — ...
```

## Rules

- **Be opinionated** — pick the best term, list others as aliases to avoid
- **Flag conflicts explicitly** — call out ambiguous usage with clear recommendations
- **Domain terms only** — skip generic programming concepts (array, function, endpoint)
- **Tight definitions** — one sentence max, define what it IS not what it does
- **Show relationships** — bold term names, express cardinality
- **Group naturally** — multiple tables when clusters emerge, one table if cohesive
- **Example dialogue** — 3-5 exchanges showing terms used precisely
- **Keep existing** — when re-running, read existing file and update incrementally
