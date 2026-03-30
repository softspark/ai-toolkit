# Python Pytest Patterns

## Fixtures

### Basic Fixture

```python
import pytest

@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "path": "kb/test/doc.md",
        "title": "Test Document",
        "content": "Test content"
    }

def test_process_document(sample_document):
    result = process(sample_document)
    assert result.title == "Test Document"
```

### Async Fixture

```python
import pytest
import httpx

@pytest.fixture
async def async_client(app):
    """Create async HTTP client for testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_api_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### Scoped Fixtures

```python
@pytest.fixture(scope="module")
def database():
    """Database connection reused across module."""
    db = create_database()
    yield db
    db.close()

@pytest.fixture(scope="session")
def config():
    """Configuration reused across entire session."""
    return load_config()
```

## Mocking

### Basic Mock

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_client = Mock()
    mock_client.search.return_value = [{"id": 1}]

    result = function_using_client(mock_client)

    mock_client.search.assert_called_once_with("query")
    assert len(result) == 1
```

### Patch Decorator

```python
@patch("module.external_api")
def test_with_patch(mock_api):
    mock_api.return_value = {"data": "mocked"}

    result = function_calling_api()

    assert result == {"data": "mocked"}
```

### Async Mock

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_async_function():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"result": "data"}

    result = await async_function(mock_client)

    mock_client.fetch.assert_awaited_once()
```

### pytest-mock (Recommended)

```python
def test_with_mocker(mocker):
    mock_client = mocker.patch("module.Client")
    mock_client.return_value.search.return_value = []

    result = search_function()

    assert result == []
```

## Parametrization

```python
@pytest.mark.parametrize("input_val,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("test", "TEST"),
])
def test_uppercase(input_val, expected):
    assert input_val.upper() == expected

@pytest.mark.parametrize("query,limit,expected_count", [
    ("test", 5, 5),
    ("test", 10, 10),
    ("", 5, 0),
])
def test_search_with_params(query, limit, expected_count):
    results = search(query, limit)
    assert len(results) <= expected_count
```

## Exception Testing

```python
def test_raises_value_error():
    with pytest.raises(ValueError, match="Invalid input"):
        function_that_raises(None)

def test_raises_any_exception():
    with pytest.raises(Exception):
        risky_function()
```

## Markers

```python
@pytest.mark.slow
def test_slow_operation():
    """Marked as slow, can be skipped with -m 'not slow'."""
    pass

@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.version_info < (3, 10), reason="Requires Python 3.10+")
def test_new_feature():
    pass

@pytest.mark.xfail(reason="Known bug #123")
def test_known_bug():
    pass
```

## conftest.py

```python
# tests/conftest.py
import pytest

@pytest.fixture
def app():
    """Create test application."""
    from app import create_app
    return create_app(testing=True)

@pytest.fixture
def mock_llm(mocker):
    """Mock LLM client for all tests."""
    return mocker.patch("scripts.llm_client.LLMClient")
```

## Running Tests

**Direct execution:**
```bash
# All tests
pytest tests/

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific file
pytest tests/unit/test_search_core.py

# By marker
pytest -m "not slow"

# Verbose with print output
pytest -v -s

# Failed tests only
pytest --lf
```

**Docker execution (if containerized):**
```bash
# All tests
docker exec {app-container} pytest tests/

# With coverage
docker exec {app-container} pytest --cov=src --cov-report=term-missing

# Specific file
docker exec {app-container} pytest tests/unit/test_search_core.py

# By marker
docker exec {app-container} pytest -m "not slow"

# Verbose with print output
docker exec {app-container} pytest -v -s

# Failed tests only
docker exec {app-container} pytest --lf
```
