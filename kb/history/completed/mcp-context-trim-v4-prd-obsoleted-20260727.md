---
title: "PRD: MCP Context Trim v4.0 — Local Proxy with Description Compression"
category: planning
service: ai-toolkit
tags:
  - mcp
  - proxy
  - tool-descriptions
  - jsonrpc
  - tokens
  - v4
doc_type: plan
status: obsoleted
created: "2026-05-04"
last_updated: "2026-07-27"
completion: "0% — never started, and no longer worth starting"
target_milestone: "v4.0 (abandoned)"
predecessor:
  - "kb/history/completed/output-token-discipline-plan-20260504.md"
  - "kb/history/completed/f2-mcp-trim-spike-20260504.md"
description: "ABANDONED 2026-07-27. Local MCP proxy that would compress tool descriptions before they reach the model. Never built. Claude Code now defers MCP tool schemas by default — the catalog costs ~120 tokens of tool names, with schemas fetched on demand — so the 8-15k per-turn overhead this PRD was written to remove no longer exists. Kept as the record of a plan the platform solved first."
---

# PRD: MCP Context Trim v4.0 — ABANDONED

> **Abandoned 2026-07-27, never implemented.**
>
> **Why:** the premise expired. This PRD is built on one measured claim — that
> MCP tool descriptions sit in every turn's system prompt, costing 8–15k tokens
> per turn. Claude Code now **defers MCP tool schemas by default**: the model
> receives roughly 120 tokens of tool *names*, and full schemas are fetched on
> demand through tool search when a task actually needs one.
> ([Claude Code docs — context window](https://code.claude.com/docs/en/context-window),
> `ENABLE_TOOL_SEARCH=auto|false` controls the older eager behaviour.)
>
> The overhead this proxy was designed to remove is already gone. Building it
> now would add a supervised local daemon, an `.mcp.json` rewrite, a rollback
> path and five pre-mortem failure modes in order to compress a 120-token
> catalog.
>
> **How it was caught:** during the 2026-07-27 token-reduction review, a
> measurement of 1189 real sessions put the median startup context at 22,175
> tokens against ~7,850 in the documented reference shape. Attributing that gap
> showed the excess was skill and agent descriptions and rule files — not MCP.
> The MCP catalog was already deferred, exactly as the docs describe. Full
> context: [`tool-output-token-reduction-closed-20260727.md`](tool-output-token-reduction-closed-20260727.md).
>
> **What survives:** nothing in the architecture below is reusable, because it
> exists to solve a problem the host now solves. What survives is the process
> note — this PRD sat in `kb/planning/` for nearly three months while the
> platform shipped the fix, and nobody re-checked the premise. A plan blocked on
> a host limitation should carry a re-validation date, not wait indefinitely.
>
> Everything below is the document as written on 2026-05-04. It is preserved
> unedited so the reasoning stays auditable.

---

**Status:** Proposed *(as of 2026-05-04; see abandonment note above)*
**Target milestone:** v4.0
**Carved out of:** [`output-token-discipline-plan-20260504.md`](output-token-discipline-plan-20260504.md) (was Feature 2)
**Spike basis:** [`f2-mcp-trim-spike-20260504.md`](f2-mcp-trim-spike-20260504.md)

## Problem

MCP server tool descriptions are injected into every model turn's system prompt. With ~100 tools across 7 typical servers, descriptions consume 8–15k tokens per turn — pure overhead, paid every message. Examples observed in users' configs:

- `dart-mcp-server` — ~30 tools with multi-paragraph descriptions
- `filesystem` — verbose paths and example sections
- `pencil` — "IMPORTANT" stanzas repeated across tools
- `jira-mcp` — long `Use this tool to…` boilerplate

The v3.2.0 output-discipline plan attempted to solve this with a hook-based trimmer. The spike conducted 2026-05-04 proved Claude Code hooks do not expose `tools/list` metadata or the system-prompt tool catalog. The only viable architecture is a local MCP proxy.

## Goal

Reduce MCP-description overhead by ≥40% per server, with **zero** loss of parameter schemas, required fields, or discrimination signals (`not`, `never`, `only`, `except`, `unless`).

## Non-goals

- Modifying tool **call** behavior (only descriptions)
- Compressing user-facing prompts or completions
- Replacing or rewriting upstream MCP servers
- Touching MCP servers we do not control

## Architecture

### Proxy topology

```
Claude Code  ──stdio──▶  ai-toolkit MCP proxy  ──stdio/SSE──▶  upstream MCP server
                                │
                                └─ rewrites tools/list response
                                   passes through tools/call unchanged
```

One proxy process per upstream server, supervised by `ai-toolkit mcp-trim daemon` (or equivalent). User's `~/.claude/.mcp.json` is rewritten by `ai-toolkit install` (opt-in) to point Claude Code at the proxy instead of upstream — proxy reads the original target from a sidecar config.

### Required components

| Component | Purpose |
|-----------|---------|
| `scripts/mcp_proxy_server.py` | JSON-RPC 2.0 proxy. Reads stdin, forwards to upstream over stdio or SSE, intercepts `tools/list` response, rewrites descriptions. Stdlib-only. |
| `scripts/mcp_description_trimmer.py` | Pure function library: `trim(description: str) → str`. Reused from heuristics below. Stdlib-only. |
| `scripts/mcp_proxy_config.py` | Reads `~/.softspark/ai-toolkit/mcp-proxy/servers.json`, validates upstream targets, generates supervisord/launchd config. |
| `app/hooks/mcp-proxy-health.sh` | SessionStart hook — verifies all configured proxies responsive; fall through (warn, do not block) if any down. |
| `app/skills/mcp-trim/SKILL.md` | Knowledge skill: how to enable, opt out, audit savings. |
| `bin/ai-toolkit-mcp-trim` | CLI: `enable`, `disable`, `status`, `audit` (per-server token savings report). |
| `tests/test_mcp_proxy.bats` | Integration tests with mock upstream MCP servers. |
| `tests/test_mcp_trimmer.bats` | Unit tests for description trim heuristics on captured fixtures. |

### Compression heuristics (from spike)

Applied to each tool description in `tools/list` response:

- Drop example sections >40 chars
- Collapse `Use this server to…` / `Use this tool to…` boilerplate to minimum form preserving intent
- Drop duplicate occurrences of tool name in its own description
- **Preserve bytewise:** `inputSchema.properties[*].description`, `required`, `enum` values, URL/path identifiers
- **Never strip:** the words `not`, `never`, `only`, `except`, `unless` — these carry "when NOT to use" signals
- Target: ≥40% length reduction, 0% schema loss

### Failure modes & rollback

| Scenario | Behavior |
|----------|----------|
| Proxy crashes mid-session | `mcp-proxy-health.sh` detects on next SessionStart, prints warning, suggests `ai-toolkit mcp-trim disable <server>` |
| Upstream MCP server changes its tool catalog | Proxy passes through unchanged tools (no cached schema), warns once if a tool's description was previously trimmed |
| Trimmer produces malformed JSON | Proxy falls through to upstream response unchanged, logs to `~/.softspark/ai-toolkit/mcp-proxy/error.log` |
| User wants to bypass | `AI_TOOLKIT_MCP_TRIM_DISABLE=1` env var → proxies pass everything through unchanged |
| User wants to fully uninstall | `ai-toolkit mcp-trim disable` reverts `~/.claude/.mcp.json` to original upstream targets |

### Migration of existing user `.mcp.json`

`ai-toolkit mcp-trim enable` does:

1. Backup `~/.claude/.mcp.json` → `~/.softspark/ai-toolkit/mcp-proxy/.mcp.json.bak.<timestamp>`
2. Read each server entry, store in `~/.softspark/ai-toolkit/mcp-proxy/servers.json`
3. Rewrite each entry to point at the local proxy (with sidecar `target` field)
4. Spawn supervisor (per-OS: launchd on macOS, systemd on Linux, scheduled task on Windows)
5. Verify each upstream reachable via proxy, abort + restore backup on any failure

## Out-of-scope decisions (rejected mid-spike)

| Option | Why rejected |
|--------|--------------|
| Pre-install rewrite of `.mcp.json` only | MCP spec sources descriptions from server runtime, not config — wouldn't take effect |
| Source-side forks of MCP servers | Doesn't help users with custom servers; high maintenance |
| F2-lite observability tool | User decision 2026-05-04: tracking token waste without trimming is half-value; do the full thing in v4.0 |
| Hook-based interception | Spike proved hooks cannot reach `tools/list` |

## Success criteria

- ≥40% description-length reduction per server on the captured fixture set (jira, filesystem, dart, pencil)
- Deep-equal `inputSchema` between trimmed and upstream — zero schema regression
- Proxy adds <50ms per `tools/list` call (one-time per session)
- Proxy adds <5ms per `tools/call` (passthrough overhead)
- Round-trip correctness: every tool callable via proxy returns byte-identical result vs direct call
- Zero MCP-skill regressions in `npm test` after enabling proxy in CI
- Rollback (`ai-toolkit mcp-trim disable`) restores byte-identical original `.mcp.json`

## Open questions

1. Process supervision per-OS — launchd / systemd / scheduled-task wrappers, or a built-in `ai-toolkit-mcp-trimd` daemon binary?
2. SSE-mode upstreams (e.g., rag-mcp at `http://localhost:8081/mcp/sse`) — proxy listens on SSE locally too, or stdio-only with internal SSE client?
3. Description rewrites — static dictionary of "boilerplate phrases to drop" (faster, deterministic) vs LLM-based summarizer (more aggressive, less predictable)? Recommend static for v4.0, LLM as v4.1 stretch.
4. Config path — `~/.softspark/ai-toolkit/mcp-proxy/` (matches existing convention) or `~/.claude/mcp-proxy/` (closer to MCP config)? Recommend the former.
5. Telemetry — does this become an opt-in metric in `/briefing --tokens` ("MCP descriptions: 12.3k → 7.2k, saved 5.1k per turn")? Recommend yes.

## Pre-mortem (failure scenarios to design against)

1. **Proxy gets out of sync with upstream** — upstream adds a new tool, proxy doesn't know how to compress it → passthrough that tool's description unchanged, log warning
2. **Compression breaks tool discriminability** — model picks wrong tool because trimmed description lost the "use only when X" qualifier → the `not/never/only/except/unless` blacklist must be exhaustive; add per-server allowlists for false positives
3. **Multi-process race on `.mcp.json` rewrite** — two `ai-toolkit install` invocations clobber each other → file lock during enable/disable
4. **Proxy supervisor fails to start on user's machine** — different distro / no systemd → ai-toolkit doctor must detect and report; degrade to "MCP proxy unavailable, falling through" with no functionality loss
5. **User has custom MCP server we don't recognize** — must work without per-server schema; default heuristics must be safe enough for arbitrary servers

## Estimate

- Architecture spike + working proxy prototype: 2 days
- Production proxy + supervisor + config + CLI: 3 days
- Test suite + fixtures + CI integration: 2 days
- Documentation + migration guide + release notes: 1 day

**Total: ~8 working days** (1.5–2 weeks calendar time at typical pace)

## Status

| Date | Status | Author |
|------|--------|--------|
| 2026-05-04 | PRD drafted from spike conclusions, carved out of v3.2.0 plan | claude |
| 2026-07-27 | Abandoned without implementation. Claude Code began deferring MCP tool schemas by default, removing the per-turn overhead this proxy targeted. Moved from `kb/planning/` to `kb/history/completed/`. | claude |
