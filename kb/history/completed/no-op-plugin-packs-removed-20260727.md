---
title: "Removed: Nine Plugin Packs That Installed Nothing"
category: planning
service: ai-toolkit
tags:
  - plugins
  - plugin-pack
  - measurement
  - postmortem
  - dead-code
doc_type: postmortem
status: completed
created: "2026-07-27"
last_updated: "2026-07-27"
shipped_in: "v4.20.0 (removal)"
description: "Nine of eleven plugin packs installed zero files, because every asset they declared already ships in the core install. Measured across both runtimes and all three profiles. Records what was removed, what survived, why the authoring guidance produced the problem, and the check that now prevents a repeat."
---

# Removed: Nine Plugin Packs That Installed Nothing

`csharp-pack`, `java-pack`, `kotlin-pack`, `ruby-pack`, `rust-pack`,
`swift-pack`, `frontend-pack`, `research-pack`, `security-pack` — removed in
v4.20.0. `memory-pack` and `enterprise-pack` stay.

## The measurement

`ai-toolkit install` into a throwaway `HOME`, then `plugin install <pack>`, on
each runtime. The number is what `plugin install` itself reports:

| Pack | claude | codex |
|---|---:|---:|
| `csharp-pack` | 0 | 0 |
| `java-pack` | 0 | 0 |
| `kotlin-pack` | 0 | 0 |
| `ruby-pack` | 0 | 0 |
| `rust-pack` | 0 | 0 |
| `swift-pack` | 0 | 0 |
| `research-pack` | 0 | 0 |
| `security-pack` | 0 | 0 |
| `frontend-pack` | 0 | **1** |
| **`memory-pack`** | **4** | **4** |
| **`enterprise-pack`** | **2** | **2** |

Cross-checked against the filesystem, not just the reported count: after core
install (108 skills, 44 agents, 4742 characters of hook config), installing
`rust-pack`, `security-pack`, `research-pack` or any language pack produced
`+0` skills, `+0` agents, `+0` bytes of `settings.json` and `+0` files under
`~/.softspark`.

Profiles make no difference. `minimal`, `standard` and `strict` all install the
same 108 skills and 44 agents, and packs add `+0` to each.

## Why

Every one of the nine declared only assets that already ship in core:

| Pack | Declared | All present in core? |
|---|---|---|
| `rust-pack` | `rust-patterns` | yes |
| `security-pack` | `review`, `security-patterns`, `panic`, `security-auditor`, `security-architect`, `code-reviewer` | yes |
| `research-pack` | `docs`, `research-mastery`, `plan`, `technical-researcher`, `fact-checker`, `search-specialist` | yes |

Since `ai-toolkit install` links every core skill and agent, a manifest that
names only core assets resolves to a set of things already installed. There is
nothing left to do, so nothing is done.

Eight of the nine owned no file but `README.md`. `security-pack`'s two hooks
were core's `guard-destructive.sh` and `quality-gate.sh`; `research-pack`'s was
core's `user-prompt-submit.sh`.

## The one that was not quite zero

`frontend-pack` installed exactly one file, on codex only:
`plugin-frontend-pack-post-tool-use.sh`. The pack owned no such file — it
declared core's `post-tool-use.sh`, which core's codex surface does not install,
so the pack copied it in under a pack-prefixed name.

That is a generic hook wearing a domain label, not frontend functionality. It
was removed with the pack. **If `post-tool-use` should run on codex, it belongs
in the core codex hook set**, and adding it there is a separate, honest change —
not a side effect of installing a pack named after a UI framework.

## The authoring rule that caused this

`app/skills/plugin-creator/SKILL.md` told pack authors:

> **MUST** reference existing toolkit assets before duplicating — packs extend,
> they do not fork

Read literally against a core install that ships everything, that instruction
produces a no-op every time. It was correct about avoiding forks and silent
about the pack needing to add anything. Nine packs followed it exactly.

The rule now reads that a pack **must install something the core install does
not**, with the verification spelled out, and the validation checklist carries a
line item requiring a non-zero file count on every runtime the pack claims.

## What survived, and what users lose

**Nothing.** Every skill and agent the nine packs named is a core asset, still
present, still installed, still triggering on the same conditions. A Rust
developer who had `rust-pack` installed keeps `rust-patterns`, because it was
never in the pack.

The two remaining packs are the two that own files:

- `memory-pack` — two hooks, `init_db.py`, `strip_private.py`, and its own
  `mem-search` skill. Verified working the same day: driving
  `observation-capture.sh` with a real payload wrote a row to the SQLite store.
- `enterprise-pack` — `status-line.sh` and `output-style.sh`, both its own.

## Process note

The removal was nearly made on a wrong measurement. The first pass concluded
"nine no-ops on every editor" after testing only four packs on the claude
surface. `tests/test_plugin.bats` contradicted it by asserting that
`frontend-pack` creates a file on codex — the test was right and the
measurement was incomplete. The full 11 × 2 matrix was only then run.

The existing test suite caught an error in a fresh measurement. That is worth
remembering next time a test looks like it is merely in the way of a cleanup.

## Related

- [Plugin Pack Conventions](../../reference/plugin-pack-conventions.md) — the rule this postmortem installed
- [Language Packs (removed)](language-packs-removed-20260727.md) — the reference doc for six of the nine
- [rtk-pack Retirement](rtk-pack-retirement-20260727.md) — the pack removed the day before, for a different reason
