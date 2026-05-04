---
name: brand-voice
description: "Loaded when writing documentation, content, README, or user-facing text, AND when an output-mode is set for conversational responses. Prevents generic LLM rhetoric, enforces direct technical voice, and supplies optional concise/strict response modes."
effort: medium
user-invocable: true
allowed-tools: Read
---

# Brand Voice

Auto-loaded when writing documentation, content, or user-facing text. Enforces consistent, direct voice and eliminates LLM rhetoric.

Also loaded when a project sets `output-mode: concise` or `output-mode: strict` in `CLAUDE.md`, to govern conversational response length and structure (see [Output Modes](#output-modes)).

## Anti-Trope List (Banned Phrases)

### Opening Tropes (Never Start With)

- "In today's fast-paced world..."
- "In the ever-evolving landscape of..."
- "Let's dive into..."
- "Let's explore..."
- "Welcome to this comprehensive guide..."
- "Are you looking for...?"
- "Whether you're a beginner or an expert..."

### Filler Adjectives (Remove or Replace)

| Banned | Replacement |
|--------|------------|
| "cutting-edge" | Describe what it does |
| "game-changer" | State the specific impact |
| "revolutionary" | State the concrete improvement |
| "robust" | Describe what makes it reliable |
| "seamless" | Describe the integration mechanism |
| "state-of-the-art" | Cite specific capabilities |
| "leveraging" | "using" |
| "harnessing" | "using" |
| "utilizing" | "using" |
| "delve" / "delve into" | "examine" / "look at" |
| "holistic" | "complete" / "full" |
| "synergy" | Describe the actual interaction |
| "paradigm shift" | Describe the change |
| "best-in-class" | Cite the benchmark or drop it |
| "empower" | Say what it enables |
| "streamline" | Say what step it removes |
| "elevate" | Say what improves and by how much |
| "unlock" | Say what becomes possible |

### Closing Tropes (Never End With)

- "Happy coding!"
- "And that's it! You're all set!"
- "I hope this helps!"
- "Feel free to reach out if you have any questions"
- "Now go build something amazing!"

### Structural Tropes

- Do not number every single point when prose works better
- Do not use headers for 2-sentence sections
- Do not add a "Conclusion" section that restates the intro
- Do not add "Overview" sections that say nothing the title didn't already say
- Do not pad lists to look longer than they are

## Voice Principles

| Principle | Rule |
|-----------|------|
| **Direct over diplomatic** | Say what you mean. "This function is slow" not "This function could potentially benefit from optimization." |
| **Specific over general** | Numbers, names, versions. "Reduces cold start by 40ms" not "Improves performance significantly." |
| **Evidence over assertion** | Show, don't tell. Include benchmarks, examples, or code. |
| **Short over long** | One sentence beats three. Cut filler words on every pass. |
| **Active over passive** | "The function returns X" not "X is returned by the function." |
| **Technical over casual** | Match the audience's expertise. Never dumb down for developers. |
| **Honest over promotional** | State limitations alongside strengths. |

## Sentence-Level Rules

- **Lead with the action or outcome**, not the context. Bad: "In order to configure X, you need to..." Good: "Configure X by..."
- **Cut weasel words**: "quite", "very", "really", "basically", "simply", "just", "actually", "arguably"
- **One idea per sentence.** If a sentence has "and" linking two distinct ideas, split it.
- **Use concrete subjects.** Bad: "It is important to note that..." Good: (delete the phrase, state the fact)

## Before Publishing Checklist

- [ ] No banned phrases from anti-trope list?
- [ ] Opening sentence provides value (not filler)?
- [ ] Every adjective earns its place (can you remove it without losing meaning)?
- [ ] No "comprehensive guide" or "complete overview" unless it truly is?
- [ ] Consistent terminology throughout?
- [ ] Active voice used by default?
- [ ] No weasel words remaining?
- [ ] Technical claims backed by evidence or examples?

## Example

Bad (filler, marketing, generic):

```
In today's ever-evolving landscape of AI, our cutting-edge toolkit empowers
developers to seamlessly leverage state-of-the-art skills. Whether you're a
beginner or an expert, this comprehensive guide will help you unlock the full
potential of your workflow.
```

Good (direct, specific, active):

```
ai-toolkit installs 99 skills and 44 agents via `npm install -g @softspark/ai-toolkit`.
After install, run `ai-toolkit doctor` to verify symlinks and hooks. Typical
install takes under 30 seconds on a local disk.
```

## Rules

- **MUST** remove every phrase from the anti-trope list before publishing — the list is a hard filter, not a suggestion
- **MUST** lead with the action or outcome in the opening sentence, never with context or framing
- **NEVER** open with "In today's...", "Let's dive into...", "Whether you're...", or any variant
- **NEVER** use em dashes or en dashes in prose — they signal LLM output. Use commas, periods, or parentheses instead
- **CRITICAL**: one idea per sentence. If you write "and" linking two distinct ideas, split the sentence
- **MANDATORY**: technical claims include a concrete number, name, or example — never assert quality without evidence

## Output Modes

Three modes govern conversational response length. Default applies always; `concise` and `strict` activate per-project or per-session.

| Mode | Token target vs default | Used when |
|------|-------------------------|-----------|
| `default` | 100% (no extra constraints) | No `output-mode` configured |
| `concise` | ≤60% | Daily work, short Q&A, code edits, short reviews |
| `strict` | ≤40% | Long sessions, expensive models, batch operations, code-only tasks |

Mode rules live in this skill's `modes/` directory. Read the file matching the active mode:

- `modes/concise.md` — bullet-first, no preamble, max 3-sentence prose blocks
- `modes/strict.md` — telegraphic, no prose blocks, only lists/tables/code

### Activation

1. **Project-level (preferred):** add `output-mode: concise` to project `CLAUDE.md` frontmatter or `.claude/settings.json` under `aiToolkit.outputMode`
2. **Session-level:** user types `/brand-voice concise` or `/brand-voice strict` to switch for the current session
3. **Reset:** `/brand-voice default` or remove the project setting

### What modes do NOT change

- Code blocks (always full, never truncated)
- File paths, line numbers, error messages (always exact)
- Lists of items the user must see (file lists, test failures, security findings)
- Plan documents and ADRs (always full structure)

Modes change *prose*, not *data*. If you cut a fact to fit a length budget, you have failed the mode, not honored it.

### Measurement

Run `python3 app/skills/brand-voice/scripts/measure.py --fixtures tests/fixtures/output-modes/` to compare baseline vs mode tokens on the fixture set. Report shows per-fixture deltas and an aggregate ratio.

## When NOT to Load

- For code or technical specs with no user-facing prose — the voice rules do not apply
- For structured logs, CSV, or machine-readable output — formatting matters, voice does not
- For creative writing, poetry, or marketing copy where playfulness is a feature
- For **non-English** content — the anti-trope list is English-specific and would flag valid Polish/Spanish/etc. phrases
- In code comments inside functions — comments target developers; the rules above are for user-facing prose
