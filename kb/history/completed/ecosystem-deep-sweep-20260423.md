---
title: "Plan: Ecosystem Deep Sweep — All 12 Supported Tools"
category: planning
service: ai-toolkit
doc_type: plan
status: completed
tags: [ecosystem, editors, generators, deep-sweep, orchestrate, drift, integration]
created: "2026-04-23"
last_updated: "2026-04-23"
completed: "2026-04-23"
completion: "100%"
description: "Orchestrate-ready plan for a deep per-tool documentation sweep across all 12 supported tools (Claude Code + 11 editors). Each agent owns 2-3 tools: fetches docs, diffs against our generators, proposes minimal patches. Consolidation step collects results into a single changeset."
---

# Plan: Ecosystem Deep Sweep — All 12 Supported Tools

**Status:** :yellow_circle: PROPOSED
**Invocation:** `/orchestrate deep ecosystem sweep per kb/planning/ecosystem-deep-sweep-2026-04-23.md`
**Estimated effort:** 4-6 hours orchestrated (1-1.5 h per agent in parallel)
**Deliverable:** Per-tool drift report + concrete generator/skill patches + updated registry

---

## 1. Objective

For every supported tool in `scripts/ecosystem_tools.json`:

1. Read the current official documentation end-to-end (not just landing page)
2. Identify every feature that ai-toolkit could integrate with but does not currently
3. Classify each gap using the ecosystem-sync SOP taxonomy (class A-F)
4. Produce minimal, reviewable patches for class B/D/E/F gaps
5. Update the registry (`ecosystem_tools.json`) with new capability markers and config paths
6. Refresh the snapshot (`benchmarks/ecosystem-doctor-snapshot.json`)

**Explicit non-goals:** complete feature parity, deep refactor of generators, adding new editors to the roster.

---

## 2. Parallelization Strategy

12 tools → **4 agents × 3 tools each** by affinity and complexity:

| Agent | Role | Tools | Rationale |
|-------|------|-------|-----------|
| `backend-specialist` | Deep CLI / config analysis | `claude-code`, `codex-cli`, `opencode` | CLI + config.toml + agents/commands/plugins — backend integration depth |
| `frontend-specialist` | Editor UI integrations | `cursor`, `windsurf`, `google-antigravity` | Editor-embedded AI, rule files, MCP-via-UI |
| `devops-implementer` | Pipeline + rules tools | `github-copilot`, `cline`, `roo-code` | Rules directories, MCP JSON variants, mode configs |
| `ai-engineer` | LLM-native tools | `gemini-cli`, `aider`, `augment` | Pure LLM workflows, minimal IDE coupling |

Each agent works **in parallel**, independent file scopes (different generators). Cross-file coordination only at the registry update (single JSON file).

---

## 3. Per-Tool Task Template

Every agent applies the **same 7-step protocol** per tool in their bucket:

### Step 1 — Baseline our current integration

Read these files (read-only):
- `scripts/generate_<tool>_*.py` — every generator targeting this tool
- `scripts/ecosystem_tools.json` — the tool's registry entry
- `kb/reference/supported-tools-registry.md` — human docs section
- `benchmarks/ecosystem-doctor-snapshot.json` — last-seen headings/markers/version

Produce a 3-line summary: "we currently generate X, Y, Z for this tool".

### Step 2 — Fetch official docs

Primary URL is in `ecosystem_tools.json::urls.docs`. Additionally fetch:
- `urls.release_notes` — recent changes (last 6 months)
- `urls.changelog` — if distinct from release notes
- Any deep-link from the docs landing page that corresponds to an integration surface (rules, hooks, MCP, agents, commands, plugins, config schema)

Use `WebFetch` (for general) or `gh api` (for GitHub-hosted docs like Codex CLI, opencode).

### Step 3 — Extract the feature surface

For the current version of the tool, enumerate:
- Config file paths (the tool's OWN paths, not ours)
- Rule / instruction / prompt formats
- Hook / lifecycle event names (if any)
- MCP config target path (if supported)
- Agent / custom-mode / preset concepts (if any)
- Slash command / CLI subcommand surface
- Supported model providers (note, do not integrate)
- Authentication / API-key mechanisms

Produce a structured markdown table: `Feature | Since version | Stable? | Our integration?`

### Step 4 — Diff against our output

For each feature in the table, compare against:
- What our `generate_<tool>_*.py` produces
- What fields are in our registry's `capability_markers`

Mark each row with one of:
- `✅ supported` — we already emit / track it
- `⚠️ partial` — we emit a subset; specific sub-feature missing
- `❌ missing` — we do not support at all
- `➖ out of scope` — tool has it, but not applicable to ai-toolkit's mission

### Step 5 — Classify each gap

For each `⚠️` / `❌` row, assign one of the SOP drift classes:

| Class | Name | Action |
|-------|------|--------|
| A | Cosmetic | No code change; update snapshot only |
| B | New feature — integrate | Patch generator(s), add tests |
| C | New feature — not adopted | Note in registry, no code |
| D | Deprecation | Migration warning in generator + CHANGELOG |
| E | Feature promoted to default | Simplify generator; keep fallback comment |
| F | Newly globally available | New generator / extended generator |

### Step 6 — Produce patches (class B/D/E/F only)

For every class B/D/E/F gap:
1. Edit the relevant generator in `scripts/generate_<tool>_*.py`
2. If a new capability marker emerges, add to `ecosystem_tools.json::capability_markers`
3. If a new config path emerges, add to `ecosystem_tools.json::config_paths`
4. If a hook event or skill frontmatter field emerges (for Claude Code), update:
   - `app/skills/hook-creator/SKILL.md` (hooks table)
   - `app/skills/skill-creator/SKILL.md` (frontmatter reference)
   - `scripts/validate.py` (allowlist)
5. Add a bats test under `tests/test_<tool>.bats` covering the new output
6. Update the tool's section in `kb/reference/supported-tools-registry.md`

**Constraints on patches:**
- One generator change per logical feature (no "big bang" commits)
- Preserve existing output format for backward compatibility
- New output opt-in via flag if it would change existing user-visible state
- Every new capability marker must pass the doctor's probe on the live docs page

### Step 7 — Report

Each agent emits a single markdown report with:
- Feature matrix table (step 3+4+5 combined)
- List of patches applied (files changed, bats tests added)
- List of class B/D/E/F gaps NOT patched (with reason: "out of scope", "requires user decision", "blocker")
- Registry diff (before/after for the tool's JSON entry)

---

## 4. Consolidation (after all agents finish)

Run in order:

1. Merge registry entries — single edit to `ecosystem_tools.json` combining all 12 per-tool updates
2. Regenerate human registry doc: manually update `kb/reference/supported-tools-registry.md` from JSON
3. `python3 scripts/ecosystem_doctor.py --update` — baseline new capability markers
4. `python3 scripts/validate.py --strict` — must pass
5. `npm test` — must pass (includes the newly added bats tests per tool)
6. `python3 scripts/ecosystem_doctor.py --check` — exit 0
7. Regenerate downstream artifacts:
   ```bash
   npm run generate:all
   ```
8. Collect all per-agent reports into `kb/learnings/ecosystem-sweep-2026-04-23.md`

---

## 5. Success Criteria

- [ ] All 12 tools covered (no "skipped for time" items)
- [ ] Every class B/D/E/F gap has either a patch OR a documented reason for deferral
- [ ] Registry `capability_markers` list grew for at least 6 of 12 tools (signals real gap coverage)
- [ ] `validate.py --strict`: 0 errors, 0 warnings
- [ ] `npm test`: all green (including new per-tool bats tests)
- [ ] `ecosystem_doctor.py --check`: exit 0 after snapshot refresh
- [ ] Single consolidated commit per agent-bucket, plus one final consolidation commit

---

## 6. Known Traps (from prior ecosystem work)

- **SPA docs** (Cursor, Antigravity, some Augment pages): `urllib` gets empty HTML skeleton. Agents should note this and do a **manual browser visit** or use a JS-aware fetcher. Do not treat "0 headings" as "nothing new".
- **GitHub docs** rate-limit aggressively on repeated reads. Space out fetches or use `gh api`.
- **Feature gates** vary by user plan. Copilot Business vs Individual vs Enterprise have different surface. Integrate with the OSS surface; document gated features as C (not adopted).
- **Version skew** on config schemas. A setting that existed in v1.x may be deprecated in v2.x. When docs reference "available since v1.5" and we don't know what version users run, default to generating the newer form with a comment.
- **Markdown vs MDX**: Cursor uses `.mdc`, Claude Code uses `.md`, Cline uses `.md` in `.clinerules/`, Roo uses `.md` in `.roo/rules/`. Don't assume one format fits all.

---

## 7. Orchestrate Invocation

In a fresh Claude Code session (to avoid context rot from this session):

```
/orchestrate deep ecosystem sweep for ai-toolkit per kb/planning/ecosystem-deep-sweep-2026-04-23.md

Spawn 4 agents in parallel:
- backend-specialist: claude-code, codex-cli, opencode
- frontend-specialist: cursor, windsurf, google-antigravity
- devops-implementer: github-copilot, cline, roo-code
- ai-engineer: gemini-cli, aider, augment

Each agent follows the 7-step per-tool protocol in section 3.
After all 4 report, run consolidation (section 4) and produce the sweep summary.
```

---

## 8. Deliverables (per agent)

Each agent's final output to orchestrator:
1. **Feature matrix** — one table per assigned tool (step 3+4+5)
2. **Patch log** — list of commits staged (not committed yet — orchestrator consolidates)
3. **Registry delta** — proposed JSON diff for `ecosystem_tools.json`
4. **Gaps not patched** — with rationale (out-of-scope, blocker, deferred)
5. **Test additions** — bats test file names + test count

Orchestrator's final output:
1. Consolidated commit with message `feat(ecosystem): deep sweep 2026-04-23 — N class B/F integrations`
2. Version bump decision (minor if any class B/F, patch if only class A updates)
3. `kb/learnings/ecosystem-sweep-2026-04-23.md` — retrospective noting which tools needed most work (informs priority for next sweep)

---

## 9. Safety Rails

- **Do not** silently upgrade default behavior — every user-visible change lands behind a flag OR goes through a minor version bump with CHANGELOG mention
- **Do not** rewrite generators wholesale — incremental additions only
- **Do not** commit during the sweep — orchestrator consolidates at the end
- **Do not** modify files outside the tool's scope (e.g., backend-specialist touching frontend-specialist's files requires a handoff)
- **Do** preserve existing symlinks and file-path expectations — the installer depends on them

---

## 10. Related

- [Ecosystem Sync SOP](../procedures/ecosystem-sync-sop.md) — the process this plan instantiates
- [Supported Tools Registry](../reference/supported-tools-registry.md) — source of truth for tool list
- `scripts/ecosystem_doctor.py` — drift detector consumed by orchestrator consolidation
- `scripts/ecosystem_tools.json` — registry file edited by every agent

---

## 11. Retrospective — 2026-04-23

### Execution summary

- 4 parallel agents, 3 tools each — full 12/12 coverage, one consolidation pass.
- 161 new bats tests (679 → 840); validate.py 0 errors / 0 warnings; `ecosystem_doctor --check` exit 0.
- 14 files modified, 12 new test files, 2 registry docs updated, 1 snapshot rebaselined.

### What worked

- **Bucket-level file ownership** eliminated merge conflicts entirely. Agents that flagged cross-bucket edits (`ecosystem_tools.json`, registry markdown) correctly left them for the orchestrator.
- **The 7-step protocol** caught high-impact bugs we would have shipped otherwise — Windsurf rules missing `trigger:` frontmatter (silent invisibility to Cascade), Aider's default `attribute-co-authored-by: true` violating our own git policy, Roo modes lacking `whenToUse` (invisible to Orchestrator).
- **SPA-wall compensation patterns** (Antigravity bundle strings, Cursor/Windsurf llms.txt mirrors, GitHub release notes as fallback) were reusable across buckets.

### What surprised us

- **Claude Code 2.1.x grew ~14 new hook events** and 3 new handler types since our last sync. Our validate.py allowlist was the bottleneck, not any generator.
- **Cross-editor compat reads**: Cursor, Windsurf, and opencode now natively read `.claude/skills/` and `.claude/agents/` — we get skill/agent discovery in those editors "for free" without emitting duplicates. Saved ~300 generated files.
- **Copilot tier-gating is heavy**: half of the upstream surface (custom agents, repo MCP, org instructions) is Business/Enterprise-only and was classified as C (documented non-integration).
- **Test #755 regression** from the Codex `PermissionRequest` addition: the test counted `guard-destructive.sh` occurrences with `== 1`. Fixed by updating the expected count to 2 with a comment explaining why base hooks legitimately register it twice now.

### Open items flagged for future passes

1. **Native `.agents/skills/*/SKILL.md` emission** (class B) — writes the Codex skill catalog to the upstream discovery path.
2. **`.opencode/skills/` duplication** — deferred indefinitely; `.claude/skills/` fallback already works.
3. **New generators needed**: `generate_gemini_hooks.py`, `generate_augment_agents.py`, `generate_augment_commands.py`, `generate_augment_hooks.py`.
4. **Cross-editor hooks unification**: Cursor and Windsurf both shipped `.cursor/hooks.json` and `.windsurf/hooks.json` — worth a dedicated shared-schema pass rather than per-editor copies.
5. **Roo `.roomodes` YAML variant** — upstream-preferred; deferred until a YAML multi-line helper is added.
6. **Copilot install wiring**: new `.github/instructions/` and `.github/prompts/` directories are emitted when `generate_copilot.py` is called with a target dir, but `install_steps/ai_tools.py` doesn't invoke that path yet. Wire behind minor bump.

### Process refinements for next sweep

- **Add a "class B/F deferred" register**: buckets produced these ad-hoc; a structured list in the plan would make prioritization for the next sweep trivial.
- **Cross-bucket test impact**: adding per-tool bats tests inflates the test count and trips the README badge validator. Next time, bump the badge at the start of consolidation, not at the end.
- **Search docs via llms.txt first** when the vendor publishes one — bypasses SPA walls with zero fallback logic.
