# opencode Integration — Implementation Plan

> Add [opencode](https://opencode.ai) as the 11th supported editor in `@softspark/ai-toolkit`, alongside Claude, Cursor, Windsurf, Copilot, Gemini, Cline, Roo Code, Aider, Augment, Antigravity, and Codex CLI.

## Overview

- **Type**: Editor/IDE integration (additive)
- **Stack**: Python stdlib (scripts), Bash (hooks), Node.js (CLI)
- **Complexity**: **Medium** — opencode's config surface is larger than most editors (agents + commands + rules + MCP + plugins with lifecycle hooks), but several primitives are already covered by the Codex adapter and can be reused.
- **Risk**: Low-medium — opencode already reads `CLAUDE.md` as a fallback, so "day-0" compatibility exists; full native integration is additive.

## Why opencode Is Different From Every Other Editor We Support

| Feature            | Claude Code | Codex CLI       | opencode                                  |
|--------------------|-------------|-----------------|-------------------------------------------|
| Rules file         | `CLAUDE.md` | `AGENTS.md`     | `AGENTS.md` **+ `CLAUDE.md` fallback**    |
| Subagents          | Yes         | No              | Yes (`mode: subagent`)                    |
| Slash commands     | Skills      | Adapted skills  | Native commands w/ frontmatter            |
| MCP                | Yes         | Yes             | Yes (`opencode.json`)                     |
| Lifecycle hooks    | JSON config | `.codex/hooks`  | **JS/TS plugins** (~30+ events)           |
| Global config dir  | `~/.claude` | `~/.codex`      | `~/.config/opencode`                      |
| Project config dir | `.claude`   | `.agents`       | `.opencode`                               |

**Key insight**: opencode is the first editor we support that accepts `CLAUDE.md` as a drop-in fallback AND has a native lifecycle-hook plugin API. That means we can ship two maturity levels:

1. **MVP (fallback)** — opencode just reads existing `CLAUDE.md`; nothing changes in the toolkit except docs recognizing opencode.
2. **Native integration** — generate `AGENTS.md` (reuse Codex generator), project `.opencode/agents/*.md`, `.opencode/commands/*.md`, `opencode.json` with MCP, and a JS plugin wrapper that bridges our Bash hooks to opencode's event system.

## Requirements

1. `ai-toolkit install --editors opencode` installs opencode-native configs (project-local).
2. `ai-toolkit install --editors all` includes opencode.
3. Global install works: `~/.config/opencode/AGENTS.md`, `~/.config/opencode/agents/`, `~/.config/opencode/commands/`.
4. Auto-detection: if `opencode.json`, `.opencode/`, or `~/.config/opencode/` exists, `opencode` appears in detected editors.
5. All 44 agents surface as opencode subagents (`.opencode/agents/*.md` with `mode: subagent`).
6. User-invocable skills (slash commands) surface as opencode commands (`.opencode/commands/*.md`).
7. MCP servers from `.mcp.json` sync into `opencode.json` under the `mcp` key.
8. Lifecycle hooks: a JS plugin wrapper invokes our existing Bash hooks on matching opencode events (`session.created`, `tool.execute.before`, `tool.execute.after`, etc.).
9. Manifest bumped, `manifest.json` `editors` field updated, README/AGENTS.md/ARCHITECTURE.md/llms.txt regenerated with correct counts.
10. Doctor + eject + uninstall handle opencode artifacts cleanly.
11. bats tests cover generator output; Python unit tests cover detection + install flow.

## Non-Goals (Out of Scope)

- Publishing a standalone opencode plugin npm package. Ship the plugin file inline.
- Rewriting the Bash hook suite in TypeScript. The plugin wrapper `exec`s existing scripts.
- Opencode's TUI theming / modes / custom tools.

## Task Breakdown

### Phase 1 — Discovery & Scaffolding

- [ ] **1.1** Confirm opencode current version + schema URL (`https://opencode.ai/config.json`) — pin in a `SCHEMA_VERSIONS` constant (Agent: `technical-researcher`)
- [ ] **1.2** Document integration surface in [app/ARCHITECTURE.md](ai-toolkit/app/ARCHITECTURE.md) under a new "opencode" section — reuse the comparison table above (Agent: `documenter`)
- [ ] **1.3** Add `"opencode"` to `ALL_EDITORS` and `_EDITOR_MARKERS` in [scripts/install_steps/ai_tools.py:195](ai-toolkit/scripts/install_steps/ai_tools.py#L195) (markers: `opencode.json`, `.opencode/`) (Agent: `backend-specialist`)
- [ ] **1.4** Add `"opencode"` to `GLOBAL_CAPABLE_EDITORS` in [scripts/install_steps/install_state.py:92](ai-toolkit/scripts/install_steps/install_state.py#L92) (Agent: `backend-specialist`)

### Phase 2 — Generators (Python stdlib only)

- [ ] **2.1** Create [scripts/generate_opencode.py](ai-toolkit/scripts/generate_opencode.py) — emits `AGENTS.md` body. **Reuse `codex_skill_adapter.codex_skill_description` via composition** — opencode and Codex both lack Claude orchestration primitives, so the same adaptation layer applies. Model it on [scripts/generate_codex.py](ai-toolkit/scripts/generate_codex.py). (Agent: `backend-specialist`)
- [ ] **2.2** Create [scripts/generate_opencode_agents.py](ai-toolkit/scripts/generate_opencode_agents.py) — for each file in `app/agents/*.md`, emit a file in `.opencode/agents/<name>.md` with frontmatter: `description`, `mode: subagent`, `model` (optional), copying Claude frontmatter where compatible. (Agent: `backend-specialist`)
- [ ] **2.3** Create [scripts/generate_opencode_commands.py](ai-toolkit/scripts/generate_opencode_commands.py) — for each **user-invocable** skill (`user-invocable: true` or not `disable-model-invocation`), emit `.opencode/commands/<name>.md` with required `template` field built from SKILL.md body. Skip knowledge skills (`user-invocable: false`). (Agent: `backend-specialist`)
- [ ] **2.4** Create [scripts/generate_opencode_json.py](ai-toolkit/scripts/generate_opencode_json.py) — merge MCP servers from existing `.mcp.json` into `opencode.json` under the `mcp` key, preserving user's other keys. Use [scripts/mcp_editors.py](ai-toolkit/scripts/mcp_editors.py) as reference. (Agent: `backend-specialist`)
- [ ] **2.5** Create [scripts/generate_opencode_plugin.py](ai-toolkit/scripts/generate_opencode_plugin.py) — emits a single-file JS plugin `.opencode/plugins/ai-toolkit-hooks.js` that calls our existing Bash hooks. Map: `session.created` → SessionStart, `tool.execute.before` → PreToolUse, `tool.execute.after` → PostToolUse, `message.updated` → UserPromptSubmit. Use `Bun.$` from the plugin context. (Agent: `backend-specialist`)

### Phase 3 — Install Wiring

- [ ] **3.1** Add `if "opencode" in eds` branch in `install_ai_tools()` at [scripts/install_steps/ai_tools.py:56](ai-toolkit/scripts/install_steps/ai_tools.py#L56) — global: `~/.config/opencode/AGENTS.md`, `~/.config/opencode/agents/`, `~/.config/opencode/commands/` (Agent: `backend-specialist`)
- [ ] **3.2** Add `if "opencode" in eds` branch in `_create_local_ai_tool_configs()` at [scripts/install_steps/ai_tools.py:610](ai-toolkit/scripts/install_steps/ai_tools.py#L610) — project: `AGENTS.md` (reuse toolkit marker injection), `.opencode/agents/`, `.opencode/commands/`, `opencode.json` merge, `.opencode/plugins/ai-toolkit-hooks.js` (Agent: `backend-specialist`)
- [ ] **3.3** Add dry-run messages to `_EDITOR_DRY_RUN` at [scripts/install_steps/ai_tools.py:479](ai-toolkit/scripts/install_steps/ai_tools.py#L479) (Agent: `backend-specialist`)
- [ ] **3.4** Update [scripts/uninstall.py](ai-toolkit/scripts/uninstall.py) to remove opencode artifacts (`.opencode/`, opencode keys in `opencode.json`, global `~/.config/opencode/agents/ai-toolkit-*`). Do NOT delete user-authored opencode files — only ai-toolkit-marked sections. (Agent: `backend-specialist`)
- [ ] **3.5** Update [scripts/doctor.py](ai-toolkit/scripts/doctor.py) `--fix` to detect and repair opencode stale symlinks/markers. (Agent: `backend-specialist`)
- [ ] **3.6** Update [scripts/eject.py](ai-toolkit/scripts/eject.py) to bake opencode outputs into the ejected copy. (Agent: `backend-specialist`)

### Phase 4 — CLI & Manifest

- [ ] **4.1** Add `ai-toolkit opencode-md`, `opencode-agents`, `opencode-commands` commands in [bin/ai-toolkit.js](ai-toolkit/bin/ai-toolkit.js) mirroring `codex-md`/`codex-rules`/`codex-hooks` pattern (Agent: `backend-specialist`)
- [ ] **4.2** Update [manifest.json](ai-toolkit/manifest.json) — bump `version` to `2.5.0` (new editor = minor), no new top-level component (opencode is handled via generators). (Agent: `backend-specialist`)
- [ ] **4.3** Update [package.json](ai-toolkit/package.json) — description mentions opencode, bin commands exposed. (Agent: `backend-specialist`)

### Phase 5 — Tests

- [ ] **5.1** `tests/unit/test_generate_opencode.bats` — golden-file test: run generator, diff against `tests/fixtures/opencode/AGENTS.md.expected` (Agent: `test-engineer`)
- [ ] **5.2** `tests/unit/test_generate_opencode_agents.bats` — assert each generated `.opencode/agents/*.md` has required frontmatter (`description`, `mode: subagent`) (Agent: `test-engineer`)
- [ ] **5.3** `tests/unit/test_generate_opencode_commands.bats` — assert generated commands have `template` field; assert knowledge skills excluded (Agent: `test-engineer`)
- [ ] **5.4** `tests/unit/test_opencode_json_merge.bats` — test MCP merge preserves unrelated keys, idempotent re-run (Agent: `test-engineer`)
- [ ] **5.5** `tests/integration/test_install_opencode.bats` — `ai-toolkit install --local --editors opencode` in a tmp dir; verify file tree (Agent: `test-engineer`)
- [ ] **5.6** `tests/unit/test_opencode_detection.py` — auto-detection when `opencode.json` or `.opencode/` present (Agent: `test-engineer`)
- [ ] **5.7** `tests/integration/test_uninstall_opencode.bats` — reinstall cycle does not leave stale files (Agent: `test-engineer`)

### Phase 6 — Docs & Regeneration (CRITICAL per [CLAUDE.md](ai-toolkit/CLAUDE.md))

> Per CLAUDE.md: *"Every change to skills, agents, hooks, or editors MUST be reflected in ALL docs"* and the maintainer regenerates doc counts post-merge (per auto-memory). **Do not hand-edit counts in README/package.json/manifest.json/AGENTS.md/llms-full.txt.**

- [ ] **6.1** Add opencode section to [README.md](ai-toolkit/README.md) under supported editors. Leave count strings alone. (Agent: `documenter`)
- [ ] **6.2** Add opencode section to [app/ARCHITECTURE.md](ai-toolkit/app/ARCHITECTURE.md) — integration surface, file layout, hook-event mapping table (Agent: `documenter`)
- [ ] **6.3** Regenerate `AGENTS.md` via `python3 scripts/generate_agents_md.py > AGENTS.md` (Agent: `documenter`)
- [ ] **6.4** Regenerate `llms.txt` via `python3 scripts/generate_llms_txt.py > llms.txt` (Agent: `documenter`)
- [ ] **6.5** Run `python3 scripts/validate.py --strict` + `python3 scripts/audit_skills.py --ci` — both must exit 0 (Agent: `test-engineer`)
- [ ] **6.6** Add CHANGELOG.md entry under `## 2.5.0` describing opencode support (Agent: `documenter`)

### Phase 7 — Devil's Advocate Review (user preference)

- [ ] **7.1** Code review with `/review` focused on: duplication between `generate_codex.py` and `generate_opencode.py`, silent failure modes in the JS plugin wrapper, MCP merge idempotency edge cases (Agent: `code-reviewer`)
- [ ] **7.2** Security audit of the JS plugin: does it `exec` Bash hooks safely? Any command injection surface from opencode event payloads? (Agent: `security-auditor`)

## Agent Assignment

| Phase | Primary Agent            | Secondary / Review           |
|-------|--------------------------|------------------------------|
| 1     | technical-researcher     | documenter                   |
| 2     | backend-specialist       | code-reviewer                |
| 3     | backend-specialist       | infrastructure-validator     |
| 4     | backend-specialist       | tech-lead                    |
| 5     | test-engineer            | qa-automation-engineer       |
| 6     | documenter               | fact-checker                 |
| 7     | code-reviewer            | security-auditor             |

## File Structure (Post-Implementation)

```
ai-toolkit/
├── scripts/
│   ├── generate_opencode.py                # NEW — AGENTS.md generator
│   ├── generate_opencode_agents.py         # NEW — .opencode/agents/*.md
│   ├── generate_opencode_commands.py       # NEW — .opencode/commands/*.md
│   ├── generate_opencode_json.py           # NEW — opencode.json MCP merge
│   ├── generate_opencode_plugin.py         # NEW — plugin JS emitter
│   └── install_steps/
│       ├── ai_tools.py                     # MODIFIED — +opencode branches
│       └── install_state.py                # MODIFIED — +GLOBAL_CAPABLE_EDITORS
├── tests/
│   ├── unit/test_generate_opencode*.bats   # NEW
│   ├── unit/test_opencode_detection.py     # NEW
│   ├── integration/test_install_opencode*.bats # NEW
│   └── fixtures/opencode/                  # NEW — golden files
├── bin/ai-toolkit.js                       # MODIFIED — +opencode-* commands
├── manifest.json                           # MODIFIED — version 2.5.0
├── package.json                            # MODIFIED
├── README.md                               # MODIFIED
├── CHANGELOG.md                            # MODIFIED
├── AGENTS.md                               # REGENERATED
├── llms.txt                                # REGENERATED
└── app/ARCHITECTURE.md                     # MODIFIED

# After install, user gets:
~/.config/opencode/AGENTS.md                # global rules
~/.config/opencode/agents/ai-toolkit-*.md   # global subagents
~/.config/opencode/commands/ai-toolkit-*.md # global commands
# + project-local:
.opencode/agents/*.md
.opencode/commands/*.md
.opencode/plugins/ai-toolkit-hooks.js
opencode.json                                # merged
AGENTS.md                                    # marker-injected
```

## Success Criteria

- [ ] `ai-toolkit install --local --editors opencode` in a clean dir produces a working opencode setup verifiable by running `opencode --help` and confirming the ai-toolkit AGENTS.md is read (manual smoke test).
- [ ] All 44 agents appear as opencode subagents (auto-completable with `@`).
- [ ] User-invocable skills appear as opencode slash commands (auto-completable with `/`).
- [ ] MCP servers defined in `.mcp.json` are reachable from opencode after install.
- [ ] The JS plugin fires SessionStart-equivalent hook on `opencode` launch in a test project (verifiable via hook output in logs).
- [ ] `python3 scripts/validate.py --strict` passes.
- [ ] `python3 scripts/audit_skills.py --ci` passes (no HIGH findings).
- [ ] `npm test` passes (bats suite).
- [ ] Uninstall + reinstall cycle leaves no stale files (doctor reports clean).
- [ ] No user-authored `opencode.json` keys are clobbered by the MCP merge (regression test exists).

## Pre-Mortem — How This Could Go Wrong

| Risk                                                     | Mitigation                                                                                                             |
|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| opencode ships a schema change mid-flight                | Pin schema URL; keep generator output minimal and conformant; add a `--schema-version` arg to generator for pinning    |
| `AGENTS.md` conflicts with Codex's `AGENTS.md`           | Both editors read the same file — this is actually a feature (shared rules). Use the same marker blocks for both.      |
| Duplication between Codex and opencode generators        | Extract shared logic into `emission.py` / `codex_skill_adapter.py` helpers BEFORE writing opencode generator (Task 2.1) |
| JS plugin fails silently and users don't know hooks are down | Plugin logs to stderr on any exec failure; add `ai-toolkit doctor` check that runs opencode plugin in test-mode       |
| Command-injection surface from opencode event payloads   | Plugin never `eval`s; only spawns Bash with `Bun.$` using argv array (no shell string concatenation). Task 7.2 audits. |
| Stale counts in docs                                     | Per auto-memory, counts are maintainer-regenerated. Do NOT edit them in this branch.                                   |
| Breaking change for users with hand-written `opencode.json` | MCP merge reads, merges only the `mcp` key, preserves all others. Write idempotency test (5.4).                        |

## Three Alternatives Considered (per user preference)

1. **Rely solely on opencode's `CLAUDE.md` fallback** — zero code change, zero work. **Rejected**: no native subagents, no slash commands, no hook integration. Misses the product value.
2. **Full native integration with JS plugin** (this plan) — **Selected**. Maximum feature parity, justifies minor version bump.
3. **Publish `@softspark/opencode-plugin` as a separate npm package** — cleanest separation, but doubles release overhead and splits docs. **Rejected for v2.5**; reconsider in v3.0 if the plugin grows beyond ~200 LOC.

## Socratic Checks (before writing code)

1. *Are we duplicating the Codex adapter?* → Task 2.1 explicitly reuses `codex_skill_adapter.codex_skill_description`. If during implementation the generators share >30% of logic, extract to `emission.py`.
2. *Do we need a global install branch and a project-local branch?* → Yes, opencode supports both; they're symmetric, so factor into one helper parameterized by target root.
3. *What happens if a user already has `AGENTS.md` for Codex?* → Marker-based injection handles this. The same `<!-- TOOLKIT:* START/END -->` blocks work for both editors; the file is shared.
4. *Is this really a minor version bump?* → Yes. New editor = additive, no breaking change to existing editors. If hook signature changes, it'd be major.

## Next Steps

1. Human review this plan — confirm scope, especially Phase 7 gating.
2. Run `/orchestrate opencode-integration` (or spawn agents per-phase manually).
3. Follow-up: benchmark opencode install time via `python3 scripts/benchmark_ecosystem.py --offline` and add to perf regression suite.

---

Sources:
- [opencode docs — Config](https://opencode.ai/docs/config/)
- [opencode docs — Agents](https://opencode.ai/docs/agents/)
- [opencode docs — Commands](https://opencode.ai/docs/commands/)
- [opencode docs — Rules](https://opencode.ai/docs/rules/)
- [opencode docs — MCP Servers](https://opencode.ai/docs/mcp-servers/)
- [opencode docs — Plugins](https://opencode.ai/docs/plugins/)
