---
language: common
category: coding-style
version: "1.0.0"
---

# Universal Coding Style

## Principles
- KISS: simplest solution that works. Clever code is a liability.
- DRY: extract when you repeat 3+ times, not before.
- YAGNI: do not build features "just in case."
- Prefer immutability: use `const`, `final`, `val`, `let` by default.
- Fail fast: validate inputs at boundaries, return early on errors.

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

## Anti-Patterns to Avoid
- God classes/modules with 500+ lines and multiple responsibilities.
- Deep nesting (>3 levels): use early returns and extract functions.
- Magic numbers/strings: use named constants.
- Mutable global state: use dependency injection instead.
