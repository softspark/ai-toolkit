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
description: "Spike conclusion for Feature 2 of the output-token-discipline plan. Determines whether Claude Code hooks can modify MCP tool descriptions before they reach the LLM. Result: hooks operate per-call, not on tool list metadata. Full feature requires an MCP proxy server (multi-day scope). Recommends a smaller observability-first replacement."
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

## Decision

**Drop the in-flight MCP description rewrite from the v3.2 scope.** The original F2 plan assumed hooks could rewrite tool metadata — that assumption is wrong.

Replace with a **smaller observability-first feature** (call it F2-lite) that:

- Connects to each MCP server in `~/.claude/.mcp.json`, calls `tools/list`, measures total description tokens
- Reports per-server cost and identifies the 10 most expensive tool descriptions
- Suggests trim targets (e.g., "removing `Use this tool to` boilerplate from 17 tools in jira-mcp would save ~340 tokens")
- Stays inert: does NOT modify any MCP traffic

This shifts the value from automated compression to human-in-the-loop awareness — users see the cost, then choose to fix it upstream (open a PR to the MCP server, switch to a leaner alternative, or disable a server they don't need).

Full MCP proxy compression goes into a future v3.4 or v4.0 milestone with its own dedicated plan.

## Alternatives considered (and why rejected)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| Build full MCP proxy now | Achieves original compression goal | Multi-day work, single-bug-breaks-all-MCP failure mode, defers F1/F3 commits | Out of scope |
| Pre-install rewrite of `.mcp.json` | One-shot, no runtime cost | MCP spec says descriptions come from server, not config — wouldn't actually take effect | Doesn't work |
| Skip F2 entirely | Closes the plan at F1+F3 (75%) | Leaves measurable token waste invisible to users | Acceptable but worse than F2-lite |
| **F2-lite observability tool** | Low risk, gives users data, easy to ship | Not the original "automatic compression" target | **Selected** |

## Action items

1. Update `kb/planning/output-token-discipline-plan.md` — mark original F2 as **descoped**, add F2-lite as new section
2. Implement F2-lite as `scripts/mcp_inventory.py` + `/briefing --mcp` extension
3. Document the proxy-server path as a separate v4 candidate in `kb/planning/`

## Open questions for user

1. Accept the F2 → F2-lite swap, or push back and demand the full proxy?
2. If F2-lite: ship in 3.2.0 (delays release) or 3.3.0 (3.2.0 ships now with F1+F3 only)?

## Status

| Date | Status | Author |
|------|--------|--------|
| 2026-05-04 | Spike completed, F2-lite proposed | claude |
