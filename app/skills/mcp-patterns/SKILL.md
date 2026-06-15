---
name: mcp-patterns
description: "MCP server design: tool schemas, resources, stdio/SSE, capability negotiation. Triggers: MCP, Model Context Protocol, JSON-RPC, stdio, SSE, Claude Desktop."
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

## How to Write a Tool Description

The `description` is the only signal the model uses to route a request. The schema constrains the *call*; the description decides *whether the call happens at all*. Treat it as a routing contract, not API prose. A good one has five parts, in this order:

1. **One-line purpose** — what the tool does, in plain terms. Lead with a verb. `Search indexed knowledge-base documents and return ranked passages.` Skip the HTTP verb and endpoint; `calls GET /v2/search` tells the model nothing about intent.
2. **WHEN TO USE** — concrete trigger phrasings the user might say, not abstract categories. List the actual shapes: *"find docs about X", "what does the KB say about Y", "look up the runbook for Z"*. Models match on surface form, so give them surface forms.
3. **WHEN NOT TO USE** — the section that does most of the disambiguation work. Name the near-miss tools and the boundary that separates them. This is where you prevent the model from firing the wrong tool on a request that *looks* similar. Empty WHEN NOT TO USE = the tool is under-specified.
4. **CRITICAL** — one line for the single non-obvious failure mode. The constraint a reader would not guess from the schema: a required ordering, an ID that must come from another call, a cost/irreversibility warning. One line, not a checklist.
5. **Self-test** — close with a question the model can apply to itself to decide fit. `Ask: is the user looking up existing content, or asking me to create new content? This tool is read-only — if they want to create, stop.`

### Why negative examples outweigh positive ones

Positive triggers tell the model when a tool *could* apply; negative ones are what stop it firing on overlapping requests. When two tools have similar purposes (`search_kb` vs `search_code`, `get_document` vs `list_documents`), the only thing keeping the model off the wrong one is each description naming the other and drawing the line. Budget more words for the boundary than the bullseye.

### Disambiguating near-miss tools

When tools overlap, make each WHEN NOT TO USE point at its neighbour and state the discriminator explicitly:

```text
search_kb
  WHEN NOT TO USE: do not use to fetch a document you already have the id for —
    that is get_document. Use search_kb only when you need to discover *which*
    document, by meaning or keyword.

get_document
  WHEN NOT TO USE: do not use to find a document by topic or keyword — you must
    already hold an exact id (from search_kb results). For discovery, use search_kb.
```

### Worked example

```text
name: cancel_workflow
description: |
  Stop a running agent workflow and discard its in-flight results.

  WHEN TO USE: the user says "cancel the workflow", "stop run abc123",
    "kill that job", or asks to halt a workflow that get_workflow_status
    reports as RUNNING.

  WHEN NOT TO USE:
    - To inspect progress without stopping — use get_workflow_status.
    - To start a fresh run — use start_workflow.
    - On a workflow already in a terminal state (COMPLETED/FAILED) — the call
      is a no-op and signals the model misread the status.

  CRITICAL: cancellation is irreversible and drops partial output. Confirm the
    workflowId came from list_workflows or get_workflow_status — never type one
    from memory.

  Self-test: am I stopping work that is genuinely still RUNNING, or did I confuse
  "check status" with "cancel"? If I have not seen a RUNNING status, do not call this.
```

A description that survives this rubric routes correctly without the model reading your source. One that skips WHEN NOT TO USE will misfire the moment a second, similar tool exists in the same server.

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
