---
title: "Plan: Drop Cascade hooks after 2026-07-01 sunset"
category: planning
service: ai-toolkit
tags:
  - windsurf
  - devin
  - cascade
  - hooks
  - deprecation
  - cleanup
doc_type: plan
status: completed
created: "2026-06-10"
last_updated: "2026-07-10"
completion: "100%"
trigger_date: "2026-07-01"
description: "Completed cleanup of the deprecated Windsurf Cascade hooks generator after the 2026-07-01 sunset; Devin CLI .devin/hooks.v1.json is now the sole live hook surface."
---

# Plan: Drop Cascade hooks after 2026-07-01 sunset

**Completed in v4.13.0 (2026-07-10).** The deprecated generator and install/test wiring were removed; the Devin hook generator remains.

> **Filed to history 2026-07-27.** The plan was finished in v4.13.0 but sat in
> `kb/planning/` for another two and a half weeks, where it read as open work.
> Before moving it, every claim in the Verification section below was re-run
> against the codebase:
>
> | Check | Result |
> |---|---|
> | `scripts/generate_windsurf_hooks.py` deleted | gone |
> | `grep -rn generate_windsurf_hooks scripts/ tests/` | no source references (one stale `.pyc` under gitignored `__pycache__`) |
> | `_HOOK_STEM_ALIAS = {"devin": "windsurf"}` retained in `validate.py` | present, line 882 |
> | windsurf `our_generators` in `scripts/ecosystem_tools.json` | Cascade generator absent, `generate_devin_hooks.py` present |
> | `kb/reference/supported-tools-registry.md` hooks-migration row | reads "Complete" in past tense |
> | `validate.py --strict` | 0 errors, 0 warnings |
>
> The work was real and complete. Only the filing was wrong.
>
> **Process note.** This is the second document found misfiled in
> `kb/planning/` on the same day; the other,
> [`mcp-context-trim-v4-prd-obsoleted-20260727.md`](mcp-context-trim-v4-prd-obsoleted-20260727.md),
> had gone obsolete because the platform shipped the fix first. A plan with a
> `trigger_date` needs a matching move-to-history step in the release that acts
> on it — otherwise `kb/planning/` accumulates work that is already done or no
> longer worth doing, and the next reader cannot tell which is which.

## Why this exists

Windsurf rebranded to Devin Desktop on 2026-06-02. The Cascade agent — and its
`.windsurf/hooks.json` hook surface (`agent_action_name`/`tool_info` format) — is
available **only through 2026-07-01**. Devin Local / Devin CLI do **not** read
`.windsurf/hooks.json` as a fallback.

v4.8.0 already shipped the replacement: `generate_devin_hooks.py` emits
`.devin/hooks.v1.json` in the Claude-compatible format Devin CLI uses. During the
transition **both** generators run at `profile=full` so pre-sunset Cascade users
keep working. After 2026-07-01 the Cascade half is dead code and must be removed
(Constitution Art. VI.1 — no dead code).

## Trigger

First ai-toolkit release **on or after 2026-07-01**. Do NOT do this earlier —
removing it before the sunset breaks Cascade users who are still on the old agent.

## Scope — remove the Cascade hooks surface

1. **Delete the generator:** `scripts/generate_windsurf_hooks.py`.
2. **Unwire the install step:** in `scripts/install_steps/ai_tools.py`, remove the
   `_try_generator("generate_windsurf_hooks", cwd)` call (keep
   `generate_devin_hooks`). Update the `profile=full` dry-run message to drop
   `.windsurf/hooks.json (Cascade, deprecated)`.
3. **Tests:** remove the windsurf-`.windsurf/hooks.json` cases from
   `tests/test_hooks_per_editor.bats` (output path, valid JSON, source tag,
   `$HOME` prefix, idempotence, user-preservation, `pre_write_code` coverage) and
   the `profile=full` assertion in `tests/test_install_profiles.bats`
   (`windsurf + full emits .windsurf/hooks.json`). Keep all `.devin/hooks.v1.json`
   tests. Adjust the README test-count badge to the new total.
4. **Registry:** in `scripts/ecosystem_tools.json` (windsurf entry), remove
   `scripts/generate_windsurf_hooks.py` from `our_generators`; keep
   `.windsurf/hooks.json` out of `config_paths` (it was never listed). Trim the
   `status_note` hooks-migration paragraph to past tense ("Cascade hooks removed
   in vX.Y.Z").
5. **Docs:** in `kb/reference/supported-tools-registry.md` drop the
   `generate_windsurf_hooks.py` row and the "drop after 2026-07-01" note; in
   `kb/reference/hooks-catalog.md` remove the Cascade row from the
   Per-Editor Native Hooks table and the deprecation wording, leaving the Devin CLI
   section as the windsurf-family hook surface.
6. **validate.py:** the `_HOOK_STEM_ALIAS = {"devin": "windsurf"}` mapping STAYS —
   it is what keeps the `devin` hook generator counted as windsurf hooks in the
   README-honesty check after the Cascade generator is gone.
7. **CHANGELOG / version:** minor bump, `Removed` entry, regen artifacts, full
   release-preparation SOP gate.

## Verification

- `python3 scripts/validate.py --strict` — 0/0 (editor-hooks-honesty must still
  report windsurf as hook-enabled via the `devin` generator alias).
- `python3 scripts/ecosystem_doctor.py --offline --check` — exit 0.
- `npm test` — 0 `not ok`; no test recreates the deleted
  `generate_windsurf_hooks.py` generator.
- `grep -rn "generate_windsurf_hooks" scripts/ tests/` returns nothing
  (Art. VI.1 orphan check — the deleted generator is fully unwired).
  `.windsurf/hooks.json` intentionally remains referenced by the one-time
  migration/strip cleanup (`scripts/install_steps/ai_tools.py`) and its test,
  and in narrative docs (CHANGELOG, README, `kb/`, docstrings).

## Do NOT touch

- `generate_devin_hooks.py` and `.devin/hooks.v1.json` — the live replacement.
- The `.devin/`/`.windsurf/` rules + skills dual-emit (that fallback persists as
  long as Devin Desktop reads legacy `.windsurf/` paths; this plan is hooks-only).

## Related

- `kb/reference/hooks-catalog.md` — Per-Editor Native Hooks + Devin CLI section
- `kb/reference/supported-tools-registry.md` — windsurf entry, hooks-migration row
- `kb/procedures/ecosystem-sync-sop.md` — class-D deprecation workflow
- `scripts/ecosystem_tools.json` — windsurf `status_note`
