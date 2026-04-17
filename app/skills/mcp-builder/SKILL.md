---
name: mcp-builder
description: "Build production-grade MCP (Model Context Protocol) servers from scratch using the 4-phase methodology: research, implement, test, evaluate. Use when creating new MCP integrations for external APIs, databases, or internal services."
effort: high
disable-model-invocation: true
argument-hint: "[service name or API description]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# MCP Builder

$ARGUMENTS

Build a production-grade MCP server following Anthropic's 4-phase methodology.

## When to Use

- Wrapping a third-party REST API as MCP tools
- Exposing an internal database or service to Claude
- Creating reusable integrations for the team
- Migrating a custom tool into the MCP ecosystem

For MCP protocol theory, see `mcp-patterns` knowledge skill (auto-loaded).

## 4-Phase Workflow

### Phase 1 — Research & Planning

1. Read the target API's documentation (OpenAPI spec, README, changelog).
2. Identify the 5-15 most useful operations. Prefer workflow-oriented tools over 1:1 API mirror.
3. Decide transport: `stdio` for local dev tools, `streamable-http` for remote/shared.
4. Decide language: **TypeScript recommended** (best SDK), Python acceptable (`mcp` package).
5. List required secrets (API keys, tokens) and their env var names.

Output: `PLAN.md` with tool list, transport choice, auth model.

### Phase 2 — Implementation

Scaffold:
```
my-mcp/
├── package.json         # or pyproject.toml
├── src/
│   ├── server.ts        # entry point
│   ├── client.ts        # API client (axios/httpx)
│   ├── tools/           # one file per tool
│   ├── schemas.ts       # Zod/Pydantic schemas
│   └── errors.ts        # typed errors
├── .env.example
└── README.md
```

Per tool:
- Input/output schemas (Zod for TS, Pydantic for Python)
- Clear `name` with service prefix (e.g. `github_create_issue`)
- Description starts with a verb, mentions trigger keywords
- Annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`
- Pagination support via `cursor` or `page` parameters
- Focused responses — filter noise, don't dump raw API payloads

### Phase 3 — Review & Testing

- TypeScript: `npm run typecheck && npm run lint && npm test`
- Python: `ruff check . && mypy --strict src/ && pytest`
- MCP Inspector dry-run:
  ```bash
  npx @modelcontextprotocol/inspector node dist/server.js
  ```
- Verify each tool's schema validates a real request and rejects malformed input.

### Phase 4 — Evaluation

Write 10 realistic end-user questions that an LLM should be able to answer using your server. Run them through Claude with the server attached. Grade: did the model call the right tool? Did the response give enough to answer? Fix the description, schema, or response format of any tool that failed.

Example eval questions for a `github-mcp`:
1. "What issues are open on repo X with label `bug`?"
2. "Create an issue titled Y in repo Z"
3. "Who has the most commits this month in repo X?"

## Tool Design Checklist

- [ ] Name has service prefix and is verb-led
- [ ] Description mentions when to use it and includes trigger keywords
- [ ] Input schema is strict, no free-form `object` with `additionalProperties: true`
- [ ] Output is focused — essential fields only, with pagination cursor if applicable
- [ ] Error responses are actionable ("API returned 403 — check `GITHUB_TOKEN` env var")
- [ ] Annotations set correctly (readonly/destructive/idempotent)
- [ ] No secrets logged or echoed in errors
- [ ] Rate limiting respects the upstream API

## Transport Cheat Sheet

| Scenario | Transport |
|----------|-----------|
| Local dev tool, 1 user | `stdio` |
| Remote server, multiple users | `streamable-http` with SSE |
| Internal company tool, auth required | `streamable-http` + OAuth proxy |
| Embedded in IDE/editor | `stdio` spawned by editor |

## Registration Cheat Sheet

Local Claude Code (`.mcp.json`):
```json
{
  "mcpServers": {
    "my-mcp": {
      "command": "node",
      "args": ["dist/server.js"],
      "env": { "API_KEY": "$MY_API_KEY" }
    }
  }
}
```

Global Claude Code (user-scope):
```bash
claude mcp add my-mcp --scope user -- node /path/to/server.js
```

Claude Desktop: same JSON, placed in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS).

## Common Pitfalls

| Mistake | Fix |
|---------|-----|
| 1:1 API mirror with 80 tools | Pick 10 workflow-oriented tools |
| `description: "wrapper for /users endpoint"` | `description: "Find users by email, role, or team. Use when the user mentions employees, staff, or access"` |
| Dumping raw JSON responses | Filter to 3-5 fields the agent actually needs |
| Logging API keys on error | Redact all env vars in error formatters |
| `exit 1` on transient errors | Retry with exponential backoff, surface final error |
| Stdout pollution (MCP stdio) | All logs go to **stderr**, stdout is JSON-RPC only |

## Related

- `mcp-patterns` — protocol reference (auto-loaded knowledge skill)
- `mcp-specialist` agent — for deep MCP design questions
- `mcp-testing-engineer` agent — for protocol conformance testing
- https://modelcontextprotocol.io/
- https://github.com/anthropics/skills/tree/main/skills/mcp-builder
