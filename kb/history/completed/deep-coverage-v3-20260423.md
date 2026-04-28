---
title: "Plan: Deep Coverage v3.0 — 100% Native Surface Utilization Across 12 Tools"
category: planning
service: ai-toolkit
doc_type: plan
status: completed
tags: [v3, deep-coverage, ecosystem, generators, hooks, skills, subagents, commands, profile-full]
created: "2026-04-23"
last_updated: "2026-04-23"
completed: "2026-04-23"
completion: "100%"
description: "Ship v3.0.0 where every supported editor exposes the full ai-toolkit surface it is capable of hosting natively: hooks, subagents, custom commands, skill pointers. Introduce --profile full. Skip the 2.13.0 interim release and fold the completed deep sweep into 3.0.0."
---

# Plan: Deep Coverage v3.0 — 100% Native Surface Utilization

**Status:** :yellow_circle: IN PROGRESS
**Invocation:** continuation of `ecosystem-deep-sweep-2026-04-23` — same orchestration model
**Estimated effort:** 10-15h orchestrated (~3h wall-clock across 4 parallel buckets + consolidation)
**Deliverable:** v3.0.0 release where every editor's native surface is fully utilized; `--profile full` available

---

## 1. Objective

After the 2026-04-23 deep sweep closed the doc-drift gap, **v3.0.0 closes the capability-utilization gap**: each editor now exposes the full ai-toolkit surface it can host natively.

Definition of "100% coverage" chosen: **each editor works at 100% of its native capability** (compat-read counts). No cargo-cult duplication. No writing to `~/.cursor/`, `~/.augment/rules/` etc. globally.

---

## 2. Policy decisions (immutable constraints for all buckets)

| # | Decision | Rule |
|---|----------|------|
| 1 | Skill propagation | `.claude/skills/` canonical. Cursor/Windsurf/opencode → compat-read (nothing). Augment/Gemini/Antigravity → **pointer skill** (1 file per editor). Codex → native `.agents/skills/` mirror |
| 2 | Global writes | Only `~/.claude/`. Cursor/Windsurf/opencode get global coverage via compat-read. Augment/Gemini/Roo require `--local` |
| 3 | Surface activation | **`--profile full`** turns on every native surface. `standard` stays close to today's defaults but adds niepodważalne wypełnienia (Copilot wiring + Gemini hooks). `minimal` unchanged |
| 4 | Default behavior | `--editors <name>` alone uses `standard`. Users who want the full stack pass `--profile full` |
| 5 | Version | Skip 2.13. Ship everything (completed sweep + v3 work) as **3.0.0** with migration notes |

---

## 3. What's missing → what each bucket delivers

### Bucket 1 — Hooks generators (backend-specialist)

**Owned files**
- New: `scripts/generate_gemini_hooks.py` (writes `.gemini/settings.json` hooks merge)
- New: `scripts/generate_cursor_hooks.py` (writes `.cursor/hooks.json`)
- New: `scripts/generate_windsurf_hooks.py` (writes `.windsurf/hooks.json`)
- New: `scripts/generate_augment_hooks.py` (writes `~/.augment/settings.json` hooks merge)
- New: `tests/test_hooks_per_editor.bats` (≥20 tests covering all 4 generators)

**Must-haves**
- All generators reuse `~/.softspark/ai-toolkit/hooks/*.sh` scripts (no duplicate shell code).
- Preserve user-authored hook entries; mark our entries with `_source: ai-toolkit`.
- Idempotent on regeneration.
- Event mapping informed by each editor's docs (Claude Code events ↔ target editor events).

### Bucket 2 — Native agents + custom commands (ai-engineer)

**Owned files**
- New: `scripts/generate_augment_agents.py` (`.augment/agents/*.md` with YAML frontmatter: name, description, model, color, tools, disabled_tools)
- New: `scripts/generate_augment_commands.py` (`.augment/commands/*.md` from user-invocable skills)
- New: `scripts/generate_cursor_agents.py` (`.cursor/agents/*.md` mirroring Claude Code agents)
- New: `scripts/generate_gemini_commands.py` (`.gemini/commands/*.toml` custom slash commands)
- New: `tests/test_native_surfaces.bats` (≥25 tests)

**Must-haves**
- Filter: only `user-invocable: true` skills become custom commands.
- `ai-toolkit-*` prefix everywhere for install/uninstall sweep.
- Do not touch files without our prefix.

### Bucket 3 — Skill pointers + Codex mirror (ai-engineer)

**Owned files**
- New: `scripts/generate_gemini_skills.py` (`.gemini/skills/ai-toolkit-skill-catalogue/SKILL.md` — pointer)
- New: `scripts/generate_augment_skills.py` (`.augment/skills/ai-toolkit-skill-catalogue/SKILL.md` — pointer)
- New: `scripts/generate_codex_skills.py` (Codex-native mirror to `.agents/skills/<name>/SKILL.md`)
- New: `tests/test_skills_native.bats` (≥15 tests)

**Must-haves**
- Pointer pattern same as Antigravity: 1 file per editor referencing `~/.claude/skills/<name>` and listing the catalogue.
- Codex mirror respects `user-invocable: false` (knowledge skills stay, task skills stay — Codex reads them all).
- Codex skills use the upstream `.agents/skills` discovery path.

### Bucket 4 — Install wiring + profile full + docs (devops-implementer)

**Owned files**
- `scripts/install_steps/ai_tools.py` — wire in all new generators from buckets 1-3
- `scripts/install.py` — parse `--profile full`, propagate to `_create_local_ai_tool_configs`
- `scripts/config_validator.py` — ensure `full` profile is accepted (already present, verify)
- `README.md` — "What's New in v3.0.0" + migration notes
- `CHANGELOG.md` — v3.0.0 entry
- `kb/reference/global-install-model.md` — document profile semantics
- `kb/reference/supported-tools-registry.md` — per-tool "generators by profile" column
- `kb/procedures/maintenance-sop.md` — profile table update
- `package.json` version bump → `3.0.0`
- `package-lock.json` sync
- `tests/test_install_profiles.bats` (≥15 tests covering minimal/standard/strict/full × 3 editors)

**Must-haves**
- `standard` profile: Copilot directory mode ON, Gemini hooks ON (non-breaking additions).
- `full` profile: everything from `standard` + all native surfaces from buckets 1-3.
- Migration note: users on `standard` today get Copilot instructions/prompts and Gemini hooks automatically after upgrading (acceptable breaking for major bump, documented).

---

## 4. Success criteria

- [ ] 13 new Python generators (6+4+3, minus wiring)
- [ ] ≥75 new bats tests across buckets
- [ ] `npm test` green
- [ ] `python3 scripts/validate.py --strict` 0/0
- [ ] `python3 scripts/ecosystem_doctor.py --check` exit 0
- [ ] `ai-toolkit install --local --editors all --profile full` produces every native surface per editor
- [ ] `ai-toolkit install --local --editors all --profile standard` is still minimal-invasive (no subagents, no hooks for non-Claude editors) **except** Copilot + Gemini hooks (both documented migration notes)
- [ ] README test badge bumped
- [ ] CHANGELOG v3.0.0 entry
- [ ] All docs updated (registry, install model, maintenance SOP)
- [ ] Single atomic commit
- [ ] Tag `v3.0.0` ready (push held for user confirmation)

---

## 5. Safety rails

- **Do not commit during bucket work.** Orchestrator consolidates.
- **Do not touch files outside your bucket's ownership list.**
- **Preserve user files** via `ai-toolkit-*` prefix on generated artifacts.
- **Do not write to global editor paths** (`~/.cursor/`, `~/.augment/rules/`, etc.) — policy decision 2.
- **Do not change `standard` profile in ways that break existing users**, beyond the two documented additions (Copilot directory mode + Gemini hooks).
- **Test per bucket locally before reporting.** Bucket reports must include a "tests green" line.

---

## 6. Consolidation steps (orchestrator)

1. Merge all 4 bucket registry deltas into `scripts/ecosystem_tools.json`
2. Run `python3 scripts/ecosystem_doctor.py --update`
3. Run `npm run generate:all`
4. Bump `package.json` → `3.0.0`; sync `package-lock.json`
5. Update `README.md` badge + "What's New"
6. Update `CHANGELOG.md` with v3.0.0 entry (include migration notes)
7. Run `python3 scripts/validate.py --strict` (must pass 0/0)
8. Run `npm test` (all green)
9. Run `python3 scripts/ecosystem_doctor.py --check` (exit 0)
10. Move this plan doc to `kb/history/completed/deep-coverage-v3-20260423.md`
11. Single commit + tag `v3.0.0`
12. Hold push pending user confirmation

---

## 7. Related

- `kb/history/completed/ecosystem-deep-sweep-20260423.md` — predecessor plan (doc-drift closure)
- `kb/reference/global-install-model.md` — install scope semantics
- `kb/reference/supported-tools-registry.md` — tool registry
- `scripts/config_validator.py` — `VALID_PROFILES` already includes `full`
