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

- **MUST** be opinionated — pick the best term and list alternatives as aliases to avoid
- **MUST** flag every ambiguity (one word → two concepts) and every synonym (two words → one concept) with an explicit recommendation
- **MUST** write tight definitions (one sentence) that define what the term **is**, not what it does
- **NEVER** include generic programming concepts (array, function, endpoint, class) — this glossary is for the **domain**, not the toolchain
- **NEVER** silently overwrite an existing `UBIQUITOUS_LANGUAGE.md` — read the current file first, then update incrementally preserving prior decisions
- **CRITICAL**: show relationships with cardinality ("an Order belongs to exactly one Customer"). Vocabulary without relationships is a word list, not a language.
- **MANDATORY**: include 3-5 example dialogue exchanges showing correct usage. Abstract glossaries without dialogue rarely get adopted.

## Gotchas

- Domain terms often **overlap** with framework jargon (e.g., "Service" in DDD vs "Service" in Angular). If the framework already claims a term, prefer a domain-specific alternative to avoid collision.
- Stakeholders resist terminology change even when their current terms are ambiguous. "Account" replacing "User" triggers more discussion than expected — plan for negotiation in the example dialogue section.
- Glossaries rot when features ship without updating them. A `UBIQUITOUS_LANGUAGE.md` last updated 6 months ago is a snapshot, not a source of truth. Flag staleness in the header and re-run this skill periodically.
- Relationships between terms are easy to hand-wave with "related to". Pin down the cardinality (`0..1`, `1..*`, `1..1`) — vague relationships produce schema ambiguity later.
- The opinionated canonical choice may contradict marketing or legal language. Note conflicts explicitly rather than hiding them; the domain model and the marketing site can legitimately diverge.

## When NOT to Use

- For writing a **PRD** (full requirements) — use `/write-a-prd`
- For generating user-facing documentation — use `/docs`
- For implementation planning — use `/plan` or `/prd-to-plan`
- For enforcing language in commit messages or code reviews — use `/brand-voice` (distinct concern: writing style, not domain terms)
- When the project is a single-developer throwaway — glossary overhead is not justified
