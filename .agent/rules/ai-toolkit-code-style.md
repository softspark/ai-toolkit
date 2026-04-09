# Code Style

* Follow language-specific conventions: PEP 8 (Python), StandardJS/Prettier (TypeScript), gofmt (Go), rustfmt (Rust)
* Use descriptive names: functions as verbs (`calculateTotal`), booleans as questions (`isValid`), constants as UPPER_SNAKE
* Keep functions short — single responsibility, max ~30 lines
* Prefer immutability: use `const`/`final`/`let` over mutable variables where possible
* No magic numbers — extract to named constants
* Avoid deep nesting (max 3 levels) — use early returns and guard clauses
* DRY: extract shared logic only when used 3+ times; premature abstraction is worse than duplication
* YAGNI: do not build features or abstractions for hypothetical future requirements
