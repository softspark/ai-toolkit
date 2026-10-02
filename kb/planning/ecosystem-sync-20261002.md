---
title: "Ecosystem review for ai-toolkit 5.1.0"
category: planning
service: ai-toolkit
tags: [release, ecosystem, compatibility, editors]
version: "1.0.0"
created: "2026-10-02"
last_updated: "2026-10-02"
description: "Dated compatibility decisions for all thirteen integrations before the 5.1.0 release."
---

# Ecosystem review for 5.1.0

The online doctor checked all 13 integrations: 3 clean, 10 with content,
navigation or version drift, and zero fetch errors. The initial sandboxed run
failed DNS for every tool; it was rerun with network access and was not accepted
as evidence of compatibility. Feature references were reviewed separately from
landing-page hashes. Sources and dispositions are recorded on each tool in
`scripts/ecosystem_tools.json` with review date 2026-10-02.

| Integration | Classes | Disposition |
|-------------|---------|-------------|
| Claude Code | A, C | Existing command hooks, model/effort metadata and plugin surfaces remain valid; optional plugin mods/function hooks not adopted |
| Claude Chat/Cowork | A, C | Export remains valid; ordinary Chat still has no hooks or subagents; organization publishing controls not generated |
| Cursor | A | BDK navigation changed; current hook/agent/skill contracts remain compatible |
| Windsurf/Devin | A | Existing native Devin and legacy-compatible skill/hook paths retained |
| GitHub Copilot | A, C | Computer-use navigation and optional HTTP/exec hooks do not require changes to emitted command hooks |
| Gemini CLI | A | Eleven hook events remain supported; no native Stop event introduced |
| Cline | A, C | Desktop is an additional optional surface; SDK navigation changed; source repository remains the hook-contract reference |
| Roo/Zoo | A | Successor retains mode schema and compatible paths |
| Aider | A | Existing configuration and conventions remain supported |
| Augment | A, B, C | Repair native tool permissions and conflicting restriction fields; optional Notification handler not adopted |
| Antigravity | A, C, D | Migrate standard workflow commands to skills before retirement; retain compatible legacy output |
| Codex | A, C | Native agent/skill/plugin contracts remain compatible; prompt/agent hook handlers are parsed but skipped |
| OpenCode | A, D | Agent tools field is deprecated, but our generator already omits it; no speculative v2 migration |

## Adopted changes

Augment's `disabled_tools` overrides `tools`, even when empty. The previous
generator emitted both and used Claude tool aliases. It now emits one positive
native allowlist, rejects unknown or empty grants, explains unsupported
orchestration tools and preserves both user content and recognized legacy
ownership. The real explorer exports only view/retrieval permissions.
[Augment subagents](https://docs.augmentcode.com/cli/subagents),
[permission aliases](https://docs.augmentcode.com/cli/permissions#migrating-from-legacy-tool-names).

Antigravity workflows retire on 2026-11-01. Thirteen same-named skills preserve
the generated slash commands locally and in both global skill roots. Legacy
files remain with deprecation notices. Protected updates and ownership-aware
cleanup preserve user collisions/resources; doctor warns only where a workflow
lacks a replacement. Native Windows keeps legacy output and receives WSL or
manual migration guidance; no unsafe filesystem fallback was added.
[Migration guide](https://antigravity.google/docs/migration/workflows-to-skills/).
Legacy-output removal is tracked separately in
[issue #34](https://github.com/softspark/ai-toolkit/issues/34); 5.1.0 keeps it.

Codex registry markers no longer imply that `prompt` and `agent` hook handlers
execute. The generator already limited executable handlers to `command` and
`mcp_tool`, so this correction changes documentation rather than runtime output.
[Codex hooks](https://learn.chatgpt.com/docs/hooks).

## Verification and scope

Regression tests cover native allowlists, read-only tools, legacy ownership,
user-file preservation, all thirteen migrated command names, global roots,
idempotency, transactional rollback, symlink refusal, native Windows degradation
and shared-directory editor detection. Final cross-platform release gates are
run by `npm run release -- 5.1.0`; their logs are retained by the release script.

Cline's hosted hook page did not expose a complete reference; the official
repository was used instead. Detailed Cursor BDK and Copilot computer-use
features were not adopted. This review establishes documented contract
compatibility, not live account access, model quality or paid execution results.
