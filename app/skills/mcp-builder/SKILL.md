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

## Rules

- **MUST** pick 5-15 workflow-oriented tools, not a 1:1 API mirror. The model routes by task, not by endpoint.
- **MUST** use strict input schemas (Zod for TS, Pydantic for Python). `additionalProperties: true` lets the model invent fields and drift.
- **MUST** set correct tool annotations: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` — the host uses these for safety UIs and auto-approval policies
- **NEVER** expose an MCP server on a public network without auth. MCP clients default to trusting the transport — attackers reach tools directly.
- **NEVER** log API keys, tokens, or env vars in error messages. A verbose error thrown at the model becomes a stored credential in the conversation.
- **CRITICAL**: with `stdio` transport, **all** logs go to stderr. Any stdout write that is not a JSON-RPC message breaks the client.
- **MANDATORY**: every server ships with a README documenting env vars, required scopes, rate limits, and a minimal invocation example.

## Gotchas

- `stdio` transport sends the server's stdout directly to the client as protocol frames. A stray `print()` or `console.log()` crashes the client with a parse error and no clear diagnostic. Route all logs through a logger that writes to stderr.
- MCP tool descriptions are the only thing the LLM sees when routing. `description: "calls POST /api/v2/tickets"` tells the model nothing about intent. Describe **when to use**, not what it does at the HTTP level.
- Annotations (`readOnlyHint`, etc.) are optional in the spec but some hosts (Claude Desktop, Cursor) gate auto-approval on them. Missing `destructiveHint: true` on a delete tool may cause the client to run it silently.
- `streamable-http` with SSE requires the server to handle client reconnects with a `Last-Event-ID` header. Many quick-start templates skip this and drop events on flaky networks.
- Pagination cursors must be opaque from the client's perspective but stable across retries. A timestamp cursor that advances on every poll fails if the client retries the same cursor after a transient error.
- Claude Desktop caches server capabilities on first connection. After changing tool schemas, users must explicitly reload the server (quit + reopen or remove/re-add the server) — simply restarting the server process is not enough.

## When NOT to Use

- For **in-toolkit skills** (slash commands, knowledge docs) — use `/skill-creator`
- For **agents** inside ai-toolkit — use `/agent-creator`
- For plugin packs bundling multiple agents/skills — use `/plugin-creator`
- For protocol-level MCP theory and transport trade-offs — use `/mcp-patterns` (knowledge skill)
- For conformance/integration testing of an MCP server — delegate to the `mcp-testing-engineer` agent

## Related

- `mcp-patterns` — protocol reference (auto-loaded knowledge skill)
- `mcp-specialist` agent — for deep MCP design questions
- `mcp-testing-engineer` agent — for protocol conformance testing
- https://modelcontextprotocol.io/
- https://github.com/anthropics/skills/tree/main/skills/mcp-builder
