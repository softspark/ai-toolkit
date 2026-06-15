---
name: api-patterns
description: "REST/GraphQL API design: naming, versioning, pagination, idempotency, OpenAPI. Triggers: API design, REST, GraphQL, OpenAPI, Swagger, idempotency, rate limit."
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

## Parameter Documentation Conventions

The same rules apply to OpenAPI `description` fields, Pydantic `Field(description=...)`, and MCP tool parameters: the description should encode the *workflow*, not just restate the type. A consumer (human or LLM) reads it to know how to supply a valid value, not what language primitive it is.

### Prefer enums with per-value descriptions for closed sets

A free-form `string` for `status` forces the caller to guess valid values. Constrain it and document each one:

```python
class ListReposRequest(BaseModel):
    visibility: Literal["PUBLIC", "PRIVATE", "INTERNAL"] = Field(
        "PUBLIC",
        description=(
            "Repository visibility filter. "
            "PUBLIC = visible to anyone; "
            "PRIVATE = only members with explicit access; "
            "INTERNAL = visible to all org members (Enterprise only)."
        ),
    )
```

In OpenAPI, pair `enum` with the value meanings in the description (or `x-enum-descriptions` if your tooling renders it). Avoid documenting a closed set as plain `string` — the caller cannot tell `INTERNAL` is valid but `internal` is not.

### Encode cross-field dependencies in the description

If a field is only valid given another, say so where the dependent field is defined — schemas cannot express "required when":

```python
cursor: str | None = Field(
    None,
    description=(
        "Pagination cursor. Requires a `next_cursor` value obtained from a prior "
        "GET /api/v1/documents response. Omit on the first page; do not synthesize."
    ),
)
```

State the source call by name (`next_cursor` from the previous list response), not just "an opaque token".

### Add provenance and exactness constraints for opaque IDs

Opaque identifiers (resource IDs, idempotency keys, cursors) are the most common source of bad calls because they look like something the caller can invent. Pin them down:

```python
document_id: str = Field(
    ...,
    description=(
        "Exact document id, e.g. `doc_9f3a21`. Copy it verbatim from a search or "
        "list response — case-sensitive, do not type from memory or guess the format. "
        "Obtain it from GET /api/v1/documents or the search results."
    ),
)
```

The two load-bearing phrases: **where it comes from** (`from a search or list response`) and **how to handle it** (`copy verbatim, case-sensitive, do not type from memory`). Both belong in the description, not a separate doc.

### Descriptions encode workflow, not type

| Weak | Strong |
|------|--------|
| `id: The document id` | `id: Exact document id (e.g. doc_9f3a21), copied verbatim from a list/search response — case-sensitive` |
| `status: The status string` | `status: One of OPEN, MERGED, CLOSED (see per-value meanings); filters the result set` |
| `cursor: Pagination cursor` | `cursor: next_cursor from the previous page response; omit on first request` |
| `since: A timestamp` | `since: RFC 3339 UTC timestamp; returns records created strictly after it` |

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

## Hard Rules

- **MUST** version the API from day one (URL path or Accept header) — unversioned APIs break clients on every change
- **MUST** validate every input at the API boundary, not inside business logic
- **MUST** use PUT for full replacement and PATCH for partial update — confusing the two causes silent data loss
- **NEVER** return unbounded list responses — pagination (offset or cursor) is mandatory
- **NEVER** expose stack traces or internal error details in 5xx responses — clients get a `code`, `message`, and optional `details[]`
- **CRITICAL**: idempotency on POST/PUT/PATCH is non-negotiable when retries are possible — accept an `Idempotency-Key` header or design the endpoint to be naturally idempotent
- **CRITICAL**: rate limits exist from the first deploy, not "later" — unprotected endpoints get abused within hours

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

## Gotchas

- CDN and load-balancer caches key on the full URL by default. If you version via both URL path and `Accept` header (e.g., `/api/v1/...` + `Accept: application/vnd.myapi.v2+json`), the edge returns the wrong payload for non-path versioning. Pick one versioning axis and stick to it.
- OpenAPI `additionalProperties: false` is **not** enforced by most JSON Schema validators unless you explicitly enable strict mode (`ajv({strict: true})`, Pydantic `Config.extra = "forbid"`). An API marked "strict" in the spec silently accepts unknown fields.
- `Idempotency-Key` only works if the server persists the mapping from key to response — purely in-memory implementations forget it on restart. Back it with Redis or the primary DB.
- HTTP methods are **case-sensitive** per RFC 7230 (all uppercase); some clients and proxies normalize, some don't. A `post` method reaches the server as-is through some edge proxies and hits a 405 instead of the POST route.
- `429 Too Many Requests` without a `Retry-After` header leaves clients guessing — most libraries back off exponentially from zero and hammer the server. Always include `Retry-After` on 429 and 503.

## When NOT to Load

- For **MCP protocol** (JSON-RPC over stdio/SSE) specifics — use `/mcp-patterns`; this skill covers generic JSON-RPC only
- For **gRPC, GraphQL subscriptions, or message queues** — outside scope; this skill is REST-first with a JSON-RPC aside
- For **language-specific idioms** (Fastify middleware chains, ASP.NET minimal APIs, etc.) — pair this skill with `/typescript-patterns`, `/csharp-patterns`, etc.
- For **OpenAPI schema authoring** as the primary task — use `/docs` with OpenAPI output; this skill is design-only
- For **authentication deep-dives** beyond the starter API-key and JWT snippets — use `/security-patterns`

