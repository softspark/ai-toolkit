---
language: python
category: frameworks
version: "1.0.0"
---

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
