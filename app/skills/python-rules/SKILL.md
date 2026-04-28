---
name: python-rules
description: "Python coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .py, .pyi, pyproject.toml, requirements.txt, Pipfile, FastAPI, Django, Flask, pytest, SQLAlchemy, ruff, mypy. Load when writing, reviewing, or editing Python code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Python Rules

These rules come from `app/rules/python/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Python. Apply them when writing or
reviewing Python code.

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

# Python Frameworks

## FastAPI
- Use Pydantic v2 models for request/response schemas.
- Use dependency injection (`Depends()`) for shared logic (auth, DB sessions).
- Use `APIRouter` to organize routes by domain.
- Return Pydantic models directly -- FastAPI handles serialization.
- Use `BackgroundTasks` for non-critical async work (emails, logging).
- Use `lifespan` context manager for startup/shutdown (not `on_event`).

## Django
- Use class-based views for CRUD, function-based for custom logic.
- Use `select_related` and `prefetch_related` to prevent N+1 queries.
- Use Django REST Framework serializers for API validation.
- Use Django ORM migrations. Never modify database schema manually.
- Use `transaction.atomic()` for multi-model operations.
- Use signals sparingly: prefer explicit service calls.

## SQLAlchemy 2.0
- Use the 2.0-style with `select()` statements, not legacy `query()`.
- Use `Mapped[type]` annotations for typed column definitions.
- Use `sessionmaker` with `expire_on_commit=False` for API responses.
- Use `async_sessionmaker` with `asyncpg` for async applications.
- Always use `session.begin()` context manager for transaction scope.

## Pydantic v2
- Use `model_validator(mode="before")` for cross-field validation.
- Use `field_validator` for single-field validation.
- Use `model_config = ConfigDict(strict=True)` for strict type coercion.
- Use `Annotated[str, Field(min_length=1)]` for reusable constrained types.
- Use `model_dump(exclude_unset=True)` for PATCH operations.

## CLI (click / typer)
- Use Typer for new CLI tools (type-hint-driven, less boilerplate).
- Use `click.group()` for multi-command CLIs.
- Use `rich` for formatted terminal output (tables, progress bars).

## Task Queues
- Use Celery with Redis/RabbitMQ for background job processing.
- Use `arq` for lightweight async job queues.
- Always set task timeouts. Never let tasks run indefinitely.
- Use idempotent tasks: safe to retry on failure.

## Package Management
- Use `uv` for fast dependency resolution and virtual environments.
- Use `pyproject.toml` for all project configuration (no setup.py/setup.cfg).
- Pin dependencies with lockfile (`uv.lock`, `poetry.lock`).

# Python Patterns

## Error Handling
- Catch specific exceptions, never bare `except:` or `except Exception`.
- Use custom exception hierarchies: `class AppError(Exception)` as base.
- Add context when re-raising: `raise AppError("context") from original`.
- Use `contextlib.suppress()` for expected, ignorable exceptions.
- Log exceptions with `logger.exception("msg")` to include traceback.

## Context Managers
- Use `with` for any resource that needs cleanup (files, connections, locks).
- Create custom context managers with `@contextmanager` decorator.
- Use `contextlib.AsyncExitStack` for dynamic async resource management.
- Use `atexit.register()` for process-level cleanup only.

## Async
- Use `asyncio` for I/O-bound concurrency. Use `multiprocessing` for CPU-bound.
- Use `asyncio.gather()` for concurrent independent operations.
- Use `asyncio.TaskGroup` (3.11+) for structured concurrency.
- Never mix `asyncio.run()` inside already-running event loops.
- Use `async for` and `async with` for streaming and resource patterns.

## Dataclass Patterns
- Use `frozen=True` for immutable value objects.
- Use `field(default_factory=list)` for mutable defaults, never `field(default=[])`.
- Use `__post_init__` for validation, not complex logic.
- Use `slots=True` (3.10+) for memory efficiency in high-volume objects.

## Functional Patterns
- Use `functools.lru_cache` for pure function memoization.
- Use `itertools` for efficient iteration (chain, islice, groupby).
- Use generators (`yield`) for lazy sequences and large data processing.
- Prefer comprehensions over `map/filter` with lambdas.
- Use `functools.partial` to create specialized versions of functions.

## Dependency Injection
- Use constructor injection: pass dependencies as `__init__` params.
- Use `Protocol` classes to define dependency interfaces.
- Use factory functions to wire dependencies at application startup.
- Avoid global state and singletons. Use module-level instances if needed.

## Anti-Patterns
- Mutable default arguments: use `None` and create inside function.
- Catching `Exception` broadly: masks bugs and interrupts.
- Using `type()` for type checking: use `isinstance()`.
- Nested try/except: flatten with early returns or separate functions.
- Using `global` keyword: pass state through parameters or classes.

# Python Security

## Input Validation
- Validate all input with Pydantic models at API boundaries.
- Use `constr`, `conint`, `conlist` for constrained types.
- Never use `eval()`, `exec()`, or `compile()` with user input.
- Never use `pickle.loads()` on untrusted data (arbitrary code execution).

## SQL Injection
- Use ORM query builders (SQLAlchemy, Django ORM) for all queries.
- For raw SQL, always use parameterized queries: `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`.
- Never use f-strings or `.format()` to build SQL queries.
- Use `text()` with `:param` syntax in SQLAlchemy raw queries.

## SSTI (Server-Side Template Injection)
- Use Jinja2 with autoescaping enabled: `Environment(autoescape=True)`.
- Never render user input as a template string.
- Use `markupsafe.Markup` only for trusted HTML content.

## Command Injection
- Never use `os.system()` or `subprocess.run(shell=True)` with user input.
- Use `subprocess.run()` with list arguments: `subprocess.run(["ls", "-la", path])`.
- Use `shlex.quote()` if shell=True is absolutely necessary.

## Path Traversal
- Use `pathlib.Path.resolve()` and verify the result is within allowed directory.
- Never concatenate user input into file paths without validation.
- Use `os.path.commonpath()` to verify path containment.

## Secrets
- Use `secrets` module for tokens: `secrets.token_urlsafe(32)`.
- Use `hashlib.scrypt` or `bcrypt` for password hashing.
- Use `hmac.compare_digest()` for constant-time secret comparison.
- Load secrets from environment: `os.environ["SECRET_KEY"]`, never hardcode.

## Dependencies
- Run `pip-audit` or `safety check` in CI.
- Use `uv` or `pip-compile` for reproducible dependency resolution.
- Avoid installing packages with native extensions from untrusted sources.
- Pin all dependency versions. Review dependency updates carefully.

## Deserialization
- Never deserialize untrusted data with `pickle`, `yaml.load()`, or `marshal`.
- Use `yaml.safe_load()` instead of `yaml.load()`.
- Use `json.loads()` for untrusted data (safe by default).
- Validate deserialized data with Pydantic before use.

## Django-Specific
- Set `DEBUG = False` in production. Never expose debug pages.
- Use `django.utils.html.escape()` for manual HTML escaping.
- Use `CSRF_COOKIE_HTTPONLY = True` and `SESSION_COOKIE_SECURE = True`.
- Keep `SECRET_KEY` unique per environment and out of version control.

# Python Testing

## Framework
- Use pytest as the default test framework. No unittest for new code.
- Use pytest-asyncio for async test functions.
- Use pytest-cov for coverage measurement.
- Use hypothesis for property-based testing on parsing/validation logic.

## File Naming
- Test files: `test_*.py` in `tests/` directory.
- Conftest: `conftest.py` at each test directory level for shared fixtures.
- Mirror source: `src/auth/service.py` -> `tests/auth/test_service.py`.

## Fixtures
- Use `@pytest.fixture` for setup. Prefer fixtures over setup/teardown methods.
- Scope fixtures appropriately: `function` (default), `module`, `session`.
- Use `yield` fixtures for setup + teardown: `yield resource; cleanup()`.
- Use `tmp_path` fixture for temporary files, not manual `tempfile`.
- Use `monkeypatch` for patching env vars, attributes, and dict items.

## Parametrize
- Use `@pytest.mark.parametrize` for testing multiple inputs/outputs.
- Use `pytest.param(..., id="descriptive_name")` for readable test IDs.
- Combine parametrize decorators for cross-product testing.

## Mocking
- Use `unittest.mock.patch` or `monkeypatch` for dependency replacement.
- Mock at the import location: `patch("myapp.service.http_client")`.
- Use `MagicMock(spec=ClassName)` to get attribute checking.
- Use `AsyncMock` for async functions.
- Prefer dependency injection over patching when possible.

## Markers
- Use `@pytest.mark.slow` for tests >1s. Exclude from default runs.
- Use `@pytest.mark.integration` for tests requiring external services.
- Register all custom markers in `pyproject.toml` to avoid warnings.

## Async Testing
- Use `@pytest.mark.anyio` or `@pytest.mark.asyncio` for async tests.
- Use `httpx.AsyncClient` for testing FastAPI/Starlette apps.
- Use `aiosqlite` or test containers for async database tests.

## Configuration
- Configure pytest in `pyproject.toml` under `[tool.pytest.ini_options]`.
- Set `addopts = "--strict-markers -ra"` for strict mode.
- Set `testpaths = ["tests"]` to avoid scanning the entire repo.
