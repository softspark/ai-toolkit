# Python Clean Code Patterns

## Type Hints (Required for Public APIs)

```python
from typing import Any

def search(
    query: str,
    limit: int = 10,
    filters: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Search the knowledge base.

    Args:
        query: Search query string
        limit: Maximum results to return
        filters: Optional field filters

    Returns:
        List of matching documents

    Raises:
        ValueError: If query is empty
    """
    if not query:
        raise ValueError("Query cannot be empty")
    ...
```

## Docstrings (Google Style)

```python
def calculate_relevance(
    query: str,
    document: str,
    weights: dict[str, float]
) -> float:
    """Calculate relevance score between query and document.

    Uses hybrid scoring combining BM25 and semantic similarity.

    Args:
        query: Search query
        document: Document text
        weights: Score weights {"bm25": 0.4, "semantic": 0.6}

    Returns:
        Relevance score between 0 and 1

    Raises:
        ValueError: If weights don't sum to 1.0

    Example:
        >>> calculate_relevance("test", "test doc", {"bm25": 0.5, "semantic": 0.5})
        0.85
    """
```

## Error Handling

```python
# Bad - bare except
try:
    result = risky_operation()
except:
    pass

# Good - specific exceptions
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise
except ValueError as e:
    logger.warning(f"Invalid value: {e}")
    return default_value
```

## Context Managers

```python
# Bad
file = open("data.txt")
content = file.read()
file.close()

# Good
with open("data.txt") as file:
    content = file.read()

# Custom context manager
from contextlib import contextmanager

@contextmanager
def database_connection():
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
```

## Module Structure

```python
"""Module docstring explaining purpose.

This module provides functions for searching the knowledge base.
"""

# Standard library imports
import logging
from typing import Optional

# Third-party imports
import httpx
from qdrant_client import QdrantClient

# Local imports
from .config import Settings
from .models import Document

# Module-level constants
DEFAULT_LIMIT = 10
LOGGER = logging.getLogger(__name__)

# Public functions
def search(query: str) -> list[Document]:
    ...

# Private functions (underscore prefix)
def _normalize_query(query: str) -> str:
    ...
```

## Class Structure

```python
class SearchService:
    """Service for searching the knowledge base."""

    def __init__(self, client: QdrantClient, settings: Settings):
        """Initialize search service.

        Args:
            client: Qdrant client instance
            settings: Application settings
        """
        self._client = client
        self._settings = settings

    def search(self, query: str, limit: int = 10) -> list[Document]:
        """Search for documents."""
        ...

    def _validate_query(self, query: str) -> None:
        """Validate search query (private method)."""
        ...
```

## Linting Configuration

### pyproject.toml

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # line too long (handled by formatter)

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
```
