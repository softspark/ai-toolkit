---
language: python
category: coding-style
version: "1.0.0"
---

# Python Coding Style

## Type Hints
- Type all public function signatures (parameters + return).
- Use `str | None` (PEP 604) over `Optional[str]` on Python 3.10+.
- Use `from __future__ import annotations` for forward references.
- Use `TypeAlias` or `type` (3.12+) for complex type aliases.
- Use `Protocol` for structural subtyping instead of ABCs where possible.

## Naming
- snake_case: variables, functions, methods, modules.
- PascalCase: classes, type aliases, Protocols.
- UPPER_SNAKE: module-level constants.
- Prefix private: `_internal_helper`. No double underscore unless name mangling needed.
- Prefix unused: `_` for intentionally unused variables.

## Functions
- Prefer keyword arguments for functions with >2 params.
- Use `*` to force keyword-only: `def fetch(*, limit: int, offset: int)`.
- Return early to reduce nesting. Avoid deep if/else chains.
- Use `@staticmethod` only for pure utility. Prefer module-level functions.

## Imports
- Group: stdlib, third-party, local. Separated by blank lines.
- Use absolute imports. Relative imports only within packages.
- Never `from module import *`. Be explicit.
- Use `if TYPE_CHECKING:` for import-only-for-types to avoid circular imports.

## Data Structures
- Use `dataclasses` for plain data containers.
- Use Pydantic `BaseModel` for validated data / API schemas.
- Use `NamedTuple` for lightweight immutable records.
- Use `Enum` for fixed sets of values. Prefer `StrEnum` on 3.11+.
- Prefer `dict` / `list` literals over `dict()` / `list()` constructors.

## Modern Python
- Use f-strings for formatting. Never `.format()` or `%` for new code.
- Use `pathlib.Path` over `os.path` for file operations.
- Use `contextlib.suppress(KeyError)` over bare try/except for simple cases.
- Use walrus operator `:=` when it genuinely improves readability.
- Use `match/case` (3.10+) for complex conditionals on structured data.

## Tooling
- Formatter: `ruff format` or `black`. No manual formatting.
- Linter: `ruff check`. Fix all errors before committing.
- Type checker: `mypy --strict` or `pyright` in CI.
