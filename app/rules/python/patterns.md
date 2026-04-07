---
language: python
category: patterns
version: "1.0.0"
---

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
