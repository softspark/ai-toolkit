---
title: "Spike: F2 MCP Context Trim — Hook Feasibility & Path Decision"
category: planning
service: ai-toolkit
tags:
  - mcp
  - hooks
  - claude-code
  - spike
  - feasibility
doc_type: spike
status: completed
created: "2026-05-04"
last_updated: "2026-05-04"
completed: "2026-05-04"
shipped_in: "v3.2.0 (decision only — implementation deferred to v4.0)"
description: "Spike conclusion for Feature 2 of the output-token-discipline plan. Determines whether Claude Code hooks can modify MCP tool descriptions before they reach the LLM. Result: hooks operate per-call, not on tool list metadata. Full feature requires an MCP proxy server (multi-day scope). Outcome: F2 deferred to v4.0 with own dedicated PRD."
---

# Spike: F2 MCP Context Trim — Hook Feasibility & Path Decision

## Question

Can Claude Code's hook system modify MCP **tool descriptions** that get included in the model's system prompt, or do hooks only intercept individual tool **calls**?

## Method

Reviewed local sources only (RAG MCP offline at spike time):

1. `app/skills/hook-creator/SKILL.md` — exhaustive list of supported hook events and their data shapes
2. `app/hooks/guard-destructive.sh`, `app/hooks/guard-path.sh` — actual examples reading `tool_input` from stdin
3. `app/skills/mcp-builder/SKILL.md` — MCP server-side conventions
4. `~/.claude/.mcp.json` — user's installed MCP servers (Context7, sequential-thinking, filesystem, rag-mcp, memory, jira-mcp)

## Findings

### Hook events that touch tool data

| Event | Modifies tool list? | Modifies tool input? | Notes |
|-------|--------------------|--------------------|-------|
| `PreToolUse` | no | no (only block via exit 2) | Reads `tool_input.*`, decides allow/deny |
| `PostToolUse` | no | no | Sees result for logging / feedback |
| `PermissionRequest` | no | yes (`updatedInput`) | Can rewrite a single call's args |
| `Elicitation` | no | n/a | Intercepts MCP UI prompts, not tool list |
| `SessionStart` | no | n/a | Context injection only |
| `InstructionsLoaded` | no | n/a | Verifies CLAUDE.md presence |

**No event exposes the MCP `tools/list` response or the system-prompt tool catalog**. The tool catalog is materialized once per MCP server connection from the server's own `tools/list` reply.

### Why this matters

The compression target was the bulk of MCP tool descriptions sitting in every model turn's system prompt. Examples from the user's installed servers:

- `dart-mcp-server` — ~30 tools with multi-paragraph descriptions
- `filesystem` — verbose paths and example sections
- `pencil` — "IMPORTANT" stanzas repeated across tools
- `jira-mcp` — long `Use this tool to...` boilerplate

At ~100 tools across 7 servers in this user's config, easily 8–15k tokens of pure description text. Real waste, but Claude Code does not let a hook touch it.

### What would actually work

To compress MCP tool descriptions before they reach the LLM, exactly two architectures are viable:

1. **Local MCP proxy server** between Claude Code and each target server. The proxy re-implements `tools/list` to rewrite descriptions on the fly while passing through `tools/call`. Requires JSON-RPC 2.0 over stdio + SSE per server, per-server config in `~/.claude/.mcp.json`, and a process supervisor for the proxies. Multi-day scope. Failure mode: a buggy proxy breaks all MCP-dependent skills.
2. **Source-side fork**: ship pre-trimmed copies of common MCP servers (`@softspark/jira-mcp-trim`, etc.) — high maintenance burden, doesn't help users with custom servers.

Neither is a "minimal change" by the standards of this plan.

## Decision (final, 2026-05-04)

**Drop F2 from v3.2.0 entirely. Defer the full MCP proxy approach to v4.0** with its own dedicated PRD and architecture spike.

The spike originally surfaced a smaller "F2-lite observability tool" alternative (read-only inventory + suggestions). After review, the user chose to drop both options from v3.2.0:

- v3.2.0 ships F1 + F3 + F3.5 only (output modes, token telemetry, default statusline)
- F2 work — including any observability-first prototype — moves wholesale to v4.0 milestone
- Reasoning: keep v3.2.0 release scope tight; v4.0 owns MCP-cost story end-to-end with proper proxy architecture

## Alternatives considered

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Build full MCP proxy in v3.2.0 | Achieves original compression goal | Multi-day work, single-bug-breaks-all-MCP failure mode, would block release | Rejected — too big for current release |
| Pre-install rewrite of `.mcp.json` | One-shot, no runtime cost | MCP spec sources descriptions from server, not config — wouldn't actually take effect | Rejected — does not work |
| F2-lite observability tool in v3.2.0 | Low risk, gives users data | Not the original target; partial value; mixes two milestones | Rejected by user — keep v3.2.0 focused |
| **Defer F2 entirely to v4.0** | Clean release boundaries; v4.0 owns MCP story end-to-end with full proxy scope | Token waste in MCP descriptions stays invisible to users until v4.0 | **Selected** |

## What was delivered in v3.2.0 (F1 + F3 + F3.5)

The output-discipline goal is partially addressed by what shipped:

- **Output modes** (F1) cut conversational response tokens 60–80% on the shipped fixture set
- **Real token telemetry** (F3) lets users see actual cost per session — including the MCP description overhead, even if they cannot yet trim it
- **Default statusline** (F3.5) surfaces that cost continuously

Users now have visibility into the MCP-description waste this spike identified, even though automated compression has to wait for v4.0.

## What goes into v4.0

Tracked separately. The v4.0 PRD will need to:

1. Reuse the compression heuristics from the original F2 design (preserved in `output-token-discipline-plan-20260504.md` under "Original design (historical)")
2. Build a local MCP proxy server architecture: JSON-RPC 2.0 over stdio + SSE per server, process supervisor, per-server config in `~/.claude/.mcp.json`
3. Define rollback / opt-out story (a buggy proxy must not break MCP-dependent skills)
4. Specify failure mode: proxy down → fall through to direct MCP server, with telemetry warning
5. Migration of existing user `.mcp.json` configs

## Status

| Date | Status | Author |
|------|--------|--------|
| 2026-05-04 | Spike completed | claude |
| 2026-05-04 | User decision: defer F2 to v4.0 entirely (no F2-lite in v3.2.0) | lukasz.krzemien |
| 2026-05-04 | Spike archived to `kb/history/completed/` alongside the parent plan | claude |
