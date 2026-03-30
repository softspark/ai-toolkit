---
name: search
description: "Search the knowledge base with semantic and hybrid modes"
user-invocable: true
effort: medium
argument-hint: "[query]"
allowed-tools: Read, Grep, Glob
---

# Knowledge Base Search

$ARGUMENTS

## Search Methods

### Method 1: MCP Tools (requires rag-mcp MCP server)

If the `rag-mcp` MCP server is configured, use these tools:

| Tool | Best For | Speed |
|------|----------|-------|
| `smart_query` | Default (90% of queries), auto-routing | 2-4s |
| `hybrid_search_kb` | Raw vector + text search | <1s |
| `get_document` | Full document content | <1s |
| `crag_search` | Vague queries (Corrective RAG) | 1-3s |
| `multi_hop_search` | Complex multi-step reasoning | 20-30s |

```python
# Primary search
smart_query("your search query", limit=10)

# Full document retrieval
get_document(path="kb/reference/architecture.md")
```

### Method 2: Local File Search (fallback, always available)

If MCP tools are unavailable, use built-in tools:

```
# Search file contents
Grep: pattern="your query" path="kb/"

# Search file names
Glob: pattern="kb/**/*.md"

# Read specific document
Read: "kb/reference/architecture.md"
```

## Search Tips

1. **Be specific** - "nginx rate limiting" > "rate limiting"
2. **Try MCP first**, fall back to Grep/Glob if unavailable
3. **Use multi-hop** for "compare X with Y" questions (MCP only)
4. **Always cite sources**: `[PATH: kb/reference/doc.md]`

## Examples

```
/search rate limiting configuration
/search how to deploy to production
/search database migration patterns
```
