---
name: api-patterns
description: "Loaded when user asks about REST API design or GraphQL patterns"
effort: medium
user-invocable: false
allowed-tools: Read
---

# API Patterns Skill

## REST API Design

### Resource Naming

```
# Collection
GET    /api/v1/documents        # List documents
POST   /api/v1/documents        # Create document

# Single resource
GET    /api/v1/documents/{id}   # Get document
PUT    /api/v1/documents/{id}   # Replace document
PATCH  /api/v1/documents/{id}   # Update document
DELETE /api/v1/documents/{id}   # Delete document

# Nested resources
GET    /api/v1/users/{id}/documents  # User's documents
```

### HTTP Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | No permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 422 | Unprocessable | Validation error |
| 429 | Too Many Requests | Rate limited |
| 500 | Internal Error | Server error |

### Response Format

```json
{
  "data": {
    "id": "123",
    "type": "document",
    "attributes": {
      "title": "Example",
      "content": "..."
    }
  },
  "meta": {
    "total": 100,
    "page": 1,
    "per_page": 10
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {"field": "title", "message": "Title is required"},
      {"field": "limit", "message": "Must be between 1 and 100"}
    ]
  }
}
```

---

## FastAPI Implementation

```python
from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field

app = FastAPI(title="RAG-MCP API", version="1.0.0")

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Max results")

class SearchResult(BaseModel):
    id: str
    title: str
    score: float
    content: str

class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int

@app.post("/api/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """Search the knowledge base.

    Args:
        request: Search parameters

    Returns:
        Search results with scores
    """
    try:
        results = await perform_search(request.query, request.limit)
        return SearchResponse(results=results, total=len(results))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

---

## JSON-RPC 2.0 (MCP Pattern)

### Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search",
    "arguments": {"query": "test"}
  }
}
```

### Success Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {"type": "text", "text": "Results..."}
    ]
  }
}
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {"field": "query", "message": "Required"}
  }
}
```

---

## Pagination

### Offset-based

```
GET /api/v1/documents?page=2&per_page=20
```

```json
{
  "data": [...],
  "meta": {
    "total": 150,
    "page": 2,
    "per_page": 20,
    "total_pages": 8
  }
}
```

### Cursor-based (Recommended for Large Datasets)

```
GET /api/v1/documents?cursor=abc123&limit=20
```

```json
{
  "data": [...],
  "meta": {
    "next_cursor": "xyz789",
    "has_more": true
  }
}
```

---

## Rate Limiting

### Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1699999999
```

### Implementation

```python
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v1/search")
@limiter.limit("100/minute")
async def search(request: Request, query: str):
    ...
```

---

## Authentication

### API Key (Simple)

```python
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key

@app.get("/api/v1/protected")
async def protected_endpoint(api_key: str = Depends(verify_api_key)):
    ...
```

### JWT (Production)

```python
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"]
        )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## Versioning

### URL Path (Recommended)

```
/api/v1/documents
/api/v2/documents
```

### Header

```
Accept: application/vnd.myapi.v1+json
```

---

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "We'll version the API later" | Unversioned APIs break clients on every change — version from day one |
| "Retries are the client's problem" | Server-side idempotency prevents data corruption — design for at-least-once delivery |
| "We'll add rate limiting later" | Unprotected endpoints get abused within hours of deployment |
| "Error messages are just for debugging" | Error responses are your API's UX — clients depend on consistent, parseable errors |
| "PATCH and PUT are the same thing" | PUT replaces the resource, PATCH modifies it — wrong semantics cause data loss |

## Best Practices

- [ ] Use HTTPS only
- [ ] Version your API
- [ ] Validate all inputs
- [ ] Use proper HTTP methods and status codes
- [ ] Implement rate limiting
- [ ] Include pagination for lists
- [ ] Return consistent error format
- [ ] Document with OpenAPI/Swagger
- [ ] Log requests for debugging
- [ ] Set reasonable timeouts
