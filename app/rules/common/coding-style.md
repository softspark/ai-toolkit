---
language: common
category: coding-style
version: "1.1.0"
---

# Universal Coding Style

## Principles
- KISS: simplest solution that works. Clever code is a liability. If 200 lines could be 50, rewrite.
- DRY: extract when you repeat 3+ times, not before.
- YAGNI: do not build features "just in case." No abstractions for single-use code.
- Prefer immutability: use `const`, `final`, `val`, `let` by default.
- Fail fast: validate inputs at boundaries, return early on errors.
- State assumptions before coding. If uncertain or multiple interpretations exist, ask — don't pick silently.

## Naming
- Use descriptive names that reveal intent (`remainingRetries`, not `r`).
- Boolean variables/functions: prefix with `is`, `has`, `can`, `should`.
- Functions: verb + noun (`fetchUser`, `calculateTotal`, `validateInput`).
- Avoid abbreviations unless universally understood (`id`, `url`, `http`).
- Collections use plural nouns (`users`, `orderItems`).

## Functions
- Max 20-30 lines per function. If longer, extract.
- Max 3 parameters. Beyond that, use an options/config object.
- Single responsibility: one function does one thing.
- Pure functions preferred: same input, same output, no side effects.
- Avoid boolean parameters: use separate functions or enums.

## File Organization
- One primary concept per file (class, module, component).
- Group imports: stdlib, external, internal, relative.
- Constants at top, public API before private helpers.
- Keep files under 300 lines. Split when they grow.

## Comments
- Code should be self-documenting. Comment *why*, not *what*.
- Delete commented-out code. That is what version control is for.
- Use TODO/FIXME with ticket references: `// TODO(PROJ-123): migrate to v2`.
- Document public APIs with doc comments (JSDoc, docstrings, etc.).

## Formatting
- Use project formatter (Prettier, Black, gofmt, rustfmt). No manual formatting debates.
- Consistent indentation: follow project convention (spaces vs tabs, width).
- Max line length: 80-120 characters depending on language convention.
- Trailing commas in multi-line structures (where language supports).

## Surgical Changes
- Touch only what the task requires. Every changed line should trace to the request.
- Match existing style, even if you would do it differently.
- Do not "improve" adjacent code, comments, or formatting unprompted.
- Orphan cleanup: remove imports/variables/functions that YOUR changes made unused.

## No Dead Code (Constitution Art. VI.1)
- When a refactor leaves a file, class, function, import, l10n key, or variable unused, DELETE it in the same change. Verify via grep that zero references remain in the repo.
- This applies to pre-existing code too, if your work makes its unusedness verifiable. "Legacy", "separate refactor", "out of scope", or "świadome pominięcie" are NOT valid excuses.
- Before claiming the task done: grep for every symbol you removed or renamed; fix orphaned references.

## Fix Every Found Bug (Constitution Art. VI.2)
- A bug, missing test for changed behavior, or stale doc discovered while working on a task MUST be fixed in the same change — not deferred to "second step", "separate PR", or "świadome pominięcie".
- When behavior changes, update integration AND unit tests AND the affected docs alongside. A unit test on a new helper is not sufficient when the behavior is exposed over an API — add the integration test too.
- Legitimate deferral exists ONLY when: (a) the fix requires a user decision — in that case, surface it explicitly and ask, don't bury in a summary; or (b) the issue is genuinely unrelated to the current change surface.
- Before marking done: re-read the diff and confirm no orphaned references, no missing test coverage for changed paths, no stale docs. If any are present, keep working.

## Goal-Driven Execution
- Transform vague tasks into verifiable goals before starting.
- For multi-step work, state a brief plan with verification per step:
  `1. [Step] → verify: [check]`
- Strong success criteria enable independent looping. Weak criteria ("make it work") require clarification — ask first.

## Anti-Patterns to Avoid
- God classes/modules with 500+ lines and multiple responsibilities.
- Deep nesting (>3 levels): use early returns and extract functions.
- Magic numbers/strings: use named constants.
- Mutable global state: use dependency injection instead.
