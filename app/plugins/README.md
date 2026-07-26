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

Current packs (12):
- `csharp-pack`
- `enterprise-pack`
- `frontend-pack`
- `java-pack`
- `kotlin-pack`
- `memory-pack`
- `research-pack`
- `rtk-pack`
- `ruby-pack`
- `rust-pack`
- `security-pack`
- `swift-pack`

`rtk-pack` is the only one that fetches a native binary at install time and the
only one that rewrites commands before they run. Read its README before
installing it.

See `kb/reference/plugin-pack-conventions.md` for pack rules, validation, and adoption guidance.
