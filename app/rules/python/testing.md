---
language: python
category: testing
version: "1.0.0"
---

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
