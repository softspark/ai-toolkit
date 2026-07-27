# Plugin Packs

Experimental opt-in plugin packs that group existing ai-toolkit assets by domain.

These packs are **not** installed automatically by `ai-toolkit install` and are **not** part of the default install.
They serve three purposes:

1. formalize a plugin-pack contract for runtime-aware plugin installation,
2. provide curated bundles by domain,
3. give `plugin-creator` a concrete scaffold to follow.

Plugin packs can target:
- Claude Code global runtime via `ai-toolkit plugin install --editor claude <name>`
- Codex global plugin layer via `ai-toolkit plugin install --editor codex <name>`
- both runtimes via `ai-toolkit plugin install --editor all <name>`

These packs are not directly uploadable Claude app plugins. For Claude Chat,
Desktop, and Cowork use `ai-toolkit claude-app export`.

Current packs (2):
- `memory-pack` — SQLite cross-session memory. Owns 2 hooks, 2 scripts and its own skill.
- `enterprise-pack` — owns the `status-line` and `output-style` hooks.

**A pack must install something the core install does not.** `ai-toolkit install`
links every core skill and agent, so a pack whose manifest names only core assets
puts zero files on disk. Nine packs did exactly that and were removed in v4.20.0
(`csharp`, `java`, `kotlin`, `ruby`, `rust`, `swift`, `frontend`, `research`,
`security`) — see
[`no-op-plugin-packs-removed-20260727.md`](../../kb/history/completed/no-op-plugin-packs-removed-20260727.md).
Nothing was lost with them: the language packs never held their own content.
`rust-patterns`, `java-patterns` and the rest are core skills and stayed where
they were.

Neither remaining pack fetches anything at install time. `rtk-pack` did, and was
retired in v4.19.0; see `kb/history/completed/rtk-pack-retirement-20260727.md`
before proposing another pack of that shape.

See `kb/reference/plugin-pack-conventions.md` for pack rules, validation, and adoption guidance.
