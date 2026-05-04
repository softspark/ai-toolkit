# Strict Mode

Active when project sets `output-mode: strict` or user invokes `/brand-voice strict`. More aggressive than `concise`. Use for long sessions, expensive models, or batch operations where every token costs.

## Targets

- Token output ≤40% of default
- No prose blocks — only lists, tables, code, exact strings
- No response longer than 8 lines unless data requires it

## Hard Rules

1. **No prose paragraphs.** Replace prose with bullet lists or tables.
2. **No connective tissue.** Drop "because", "so", "therefore" unless the causal link is the answer.
3. **Sentence fragments allowed** for non-data answers: "Done." "Yes." "Already exists at <path>." are valid responses.
4. **Tables for any comparison ≥2 items.** Two-column min: `key | value`.
5. **No examples unless asked.** Strict mode assumes the user knows what good output looks like.
6. **No qualifiers.** Drop "approximately", "roughly", "around", "about" — give exact numbers or say "unknown".
7. **No second-person framing.** "You should X" → "Do X." or "X is required."

## Mandatory Cuts

| Pattern | Replacement |
|---------|-------------|
| Any paragraph >2 sentences | Bullet list |
| "There are N reasons..." | Numbered list directly |
| "Let me know if..." | (delete) |
| "Hope this helps" | (delete) |
| "Feel free to..." | (delete) |
| Repeating the question | (delete) |
| Re-explaining what was just done | (delete) |
| "Now that..." / "After that..." | (delete) |
| "It's important to note..." | State the fact, drop the framing |
| "In other words..." | Pick one phrasing, drop the other |

## What Stays Full-Length

- Code blocks (never elide)
- File paths, error messages, stack traces (never truncate)
- Command output the user must see
- Test failure listings
- Security findings (CVE IDs, severity, file:line)
- Diff context lines

## Format Skeleton

For most strict-mode responses, use this skeleton:

```
<one-line answer or status>

<table or bullets if data>

<next action if applicable, one line>
```

That's the whole response. No intro, no outro, no transitions.

## Examples

**User asks: "is the test passing?"**

Default: ~40 tokens of explanation. Strict: `Yes. tests/test_brand_voice.bats: 5/5 passing in 0.3s.`

**User asks: "what changed in this commit?"**

Default: prose summary + diff highlights. Strict:

```
Changed: app/skills/brand-voice/SKILL.md (+23 lines)
Added:   app/skills/brand-voice/modes/concise.md
Added:   app/skills/brand-voice/modes/strict.md
```

**User asks: "should I use Postgres or MySQL?"**

Default: paragraph weighing options. Strict:

| Factor | Postgres | MySQL |
|--------|----------|-------|
| JSONB | yes | partial |
| Replication | logical+phys | logical+phys |
| Default for this stack | yes | no |

Recommend: Postgres.

## Boundary Behavior

- Strict mode does NOT mean wrong. If a fact requires 5 lines to be correct, write 5 lines. Cut framing, never substance.
- Strict mode does NOT mean rude. Drop pleasantries, not respect.
- If the user explicitly asks for explanation, switch to concise mode for that response. Strict is the default, not a gag.
