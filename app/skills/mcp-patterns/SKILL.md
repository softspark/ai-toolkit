---
name: mcp-patterns
description: "MCP (Model Context Protocol) server design: tool schemas, resource patterns, transport selection (stdio/SSE), client configuration, error handling, capability negotiation. Triggers: MCP, Model Context Protocol, MCP server, MCP tool, MCP resource, JSON-RPC, stdio transport, SSE transport, Claude Desktop config, Cursor MCP. Load when building or integrating MCP servers."
effort: medium
user-invocable: false
allowed-tools: Read
---

# MCP Patterns Skill

## MCP Specification (2025-06-18)

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Server** | Exposes tools, resources, prompts to clients |
| **Client** | Connects to servers, invokes tools |
| **Transport** | Communication layer (stdio, HTTP, SSE) |
| **Tool** | Executable function with JSON Schema |
| **Resource** | Read-only data (files, URLs) |
| **Prompt** | Reusable prompt template |

---

## Tool Definition Pattern

```typescript
// TypeScript with @modelcontextprotocol/sdk
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: "search_kb",
    description: "Search the knowledge base",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query"
        },
        limit: {
          type: "number",
          description: "Max results",
          default: 10
        }
      },
      required: ["query"]
    },
    annotations: {
      readOnlyHint: true,      // Doesn't modify state
      idempotentHint: true,    // Same input = same output
      openWorldHint: false     // Bounded result set
    }
  }]
}));
```

### Tool Annotations

| Annotation | Meaning | Use When |
|------------|---------|----------|
| `readOnlyHint` | No side effects | Read operations |
| `destructiveHint` | Deletes/modifies data | Write operations |
| `idempotentHint` | Safe to retry | GET-like operations |
| `openWorldHint` | Results may change | External API calls |

---

## Transport Patterns

### 1. stdio (Default)

```typescript
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio";

const transport = new StdioServerTransport();
await server.connect(transport);
```

### 2. HTTP with SSE

```python
# FastAPI implementation
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse

app = FastAPI()

@app.get("/mcp/sse")
async def sse_endpoint():
    async def event_generator():
        while True:
            # Yield MCP events
            yield {"event": "message", "data": json.dumps(response)}
    return EventSourceResponse(event_generator())

@app.post("/mcp")
async def jsonrpc_endpoint(request: Request):
    body = await request.json()
    response = await handle_jsonrpc(body)
    return JSONResponse(response)
```

### 3. Streamable HTTP (Modern)

Single `/mcp` endpoint handling GET (SSE) and POST (JSON-RPC):

```python
@app.api_route("/mcp", methods=["GET", "POST"])
async def mcp_endpoint(request: Request):
    if request.method == "GET":
        # SSE streaming
        return EventSourceResponse(stream_generator())
    else:
        # JSON-RPC
        body = await request.json()
        return JSONResponse(await handle_jsonrpc(body))
```

---

## JSON-RPC 2.0 Pattern

### Request Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_kb",
    "arguments": {"query": "test", "limit": 5}
  }
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {"type": "text", "text": "Search results..."}
    ]
  }
}
```

### Error Format
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

### Standard Error Codes
| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

---

## Completion Support

Enable intelligent argument suggestions:

```typescript
server.setRequestHandler(CompletionCompleteRequestSchema, async (request) => {
  const { argument } = request.params;

  if (argument.name === "service") {
    return {
      completion: {
        values: ["nginx", "postgresql", "redis", "qdrant"],
        hasMore: false
      }
    };
  }

  return { completion: { values: [], hasMore: false } };
});
```

---

## Session Management

```typescript
// Generate secure session ID
const sessionId = crypto.randomUUID();

// Validate Origin header
const allowedOrigins = ["http://localhost:3000", "https://claude.ai"];
if (!allowedOrigins.includes(request.headers.origin)) {
  throw new Error("Invalid origin");
}

// Session storage (don't expose to client)
const sessions = new Map<string, SessionData>();
```

---

## Batching Support

Handle multiple requests in single HTTP call:

```python
async def handle_jsonrpc(body):
    if isinstance(body, list):
        # Batch request
        return [await process_single(req) for req in body]
    else:
        # Single request
        return await process_single(body)
```

---

## Best Practices

### Security
- [ ] Validate all inputs against JSON Schema
- [ ] Validate Origin header
- [ ] Implement rate limiting
- [ ] Use environment variables for secrets
- [ ] No secrets in logs or errors

### Performance
- [ ] Connection pooling
- [ ] Response caching where appropriate
- [ ] Streaming for large responses
- [ ] Batch support for efficiency

### Logging
- [ ] Log to stderr (never stdout)
- [ ] Structured JSON logs
- [ ] Request/response tracing
- [ ] Error logging with context

### Documentation
- [ ] Document all tools clearly
- [ ] Include example usage
- [ ] Version your API
- [ ] Maintain changelog

---

## RAG-MCP MCP Tools

| Tool | Description |
|------|-------------|
| `smart_query` | Primary search with auto-routing |
| `hybrid_search_kb` | Raw vector + text search |
| `get_document` | Full document content |
| `crag_search` | Self-correcting search |
| `multi_hop_search` | Complex reasoning |
| `start_workflow` | Start agent workflow |
| `get_workflow_status` | Check workflow progress |
| `list_workflows` | List all workflows |
| `cancel_workflow` | Cancel workflow |
