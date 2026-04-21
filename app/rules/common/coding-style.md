---
language: common
category: coding-style
version: "1.2.0"
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

## JSON Wire Format Conventions
- Field names (keys): `camelCase`. Aligns with JSON:API spec, Google JSON Style Guide, and framework defaults (Symfony Serializer, Spring Jackson, `json_serializable` for Dart). No public major API uses `snake_case` keys in modern designs except ecosystem-bound cases (Rails/Django APIs defaulting to ecosystem convention).
- Enum / status / permission / domain values: `UPPER_SNAKE_CASE`. Community consensus: [Protocol Buffers style guide](https://protobuf.dev/programming-guides/style/) (mandatory), [Google AIP-126 / api-linter](https://linter.aip.dev/126/upper-snake-values) (enforced), [Zalando Rule #240](https://opensource.zalando.com/restful-api-guidelines/), Java/Kotlin/C++/Python enum convention. `lowercase snake_case` (Stripe-style) is a legitimate outlier but not consensus.
- Avoid `camelCase` for enum values — no major public API uses it, loses visual distinction between keys and values.
- Pick one convention per project and enforce it with a CI grep gate. Mixing conventions inside a single API surface is the worst outcome.
- External contracts (Stripe, GitHub, webhooks you receive) follow their own convention — map to your project convention at the adapter boundary, do not leak their keys past it.

## Anti-Patterns to Avoid
- God classes/modules with 500+ lines and multiple responsibilities.
- Deep nesting (>3 levels): use early returns and extract functions.
- Magic numbers/strings: use named constants.
- Mutable global state: use dependency injection instead.
