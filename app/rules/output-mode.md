# Output Mode

`output-mode: concise`

Default response mode for this project is **concise**. The `brand-voice` skill (when present in ai-toolkit) auto-loads its `concise` rules; assistants without that skill should still apply the directives below.

## Concise Mode Directives

- **No preamble.** Skip "I'll now...", "Sure, let me...", "Great question!" and similar warm-ups. Start with the answer.
- **Lead with the result.** Conclusion or output first; explanation only if asked or non-obvious.
- **Max 3 sentences per closed question.** Yes/no, single-fact, or "where is X" answers stay under three sentences.
- **Tables and lists over prose** when comparing options, listing steps, or showing values.
- **No trailing summaries.** If the diff or output already shows what changed, do not restate it.
- **Drop filler adjectives.** No "nice", "great", "powerful", "robust" unless the user asked for evaluation.
- **Cite file paths as `path:line`** instead of paragraphs describing where things live.
- **Reserve longer prose** for: architecture proposals, trade-off analyses, plans with risks. Everything else: terse.

## When to escalate to verbose

- User explicitly asks: "explain in detail", "walk me through", "give me the full picture".
- Reporting a non-obvious failure mode where missing context would mislead.
- Architecture / RFC / ADR / trade-off documents — those have their own structure.

## How to override

- Per-session: `/brand-voice default` (or `/brand-voice strict` for even tighter)
- Per-project: change this rule's `output-mode:` value in the project's `CLAUDE.md`
- Permanent removal: re-run `ai-toolkit install --skip rules` or strip the `<!-- TOOLKIT:output-mode -->` block manually
