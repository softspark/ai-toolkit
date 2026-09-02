---
title: "Claude App Plugin Loads Twice in Claude Code"
category: troubleshooting
service: ai-toolkit
tags: [plugin, claude-app, hooks, duplication, doctor]
created: "2026-08-21"
last_updated: "2026-08-21"
description: "Every toolkit hook fires twice and skills and agents load twice after the Claude app plugin ZIP is uploaded on a machine that already has the global install. Cause: the app registers the plugin under ~/.claude/plugins, which Claude Code also reads."
---

# Claude App Plugin Loads Twice in Claude Code

## Symptom

After uploading `ai-toolkit-claude-app.zip` through `Customize > Plugins`, Claude
Code sessions get slower and every hook side effect appears twice: duplicate rows
in `governance.log`, duplicate session state writes, two Stop gates per turn.
`ai-toolkit doctor` reports a healthy install because it only inspected
`~/.claude` and `app/plugins`.

## Cause

The Claude app writes uploaded plugins into
`~/.claude/plugins/marketplaces/local-desktop-app-uploads/` and sets
`enabledPlugins` in `~/.claude/settings.json`. Both paths belong to Claude Code
as well, so Claude Code loads the plugin on top of the global install. The
bundle carries the same catalog as `~/.claude`, and plugin hooks merge with user
hooks without deduplication.

Confirmed in a Claude Code debug log (`claude --debug -p ...`, then read
`~/.claude/debug/latest`):

```
Loaded 111 unique skills (... user: 111 ...)
Total plugin skills loaded: 111 (0 duplicate/user-owned entries skipped)
Total plugin agents loaded: 44
Read manifest hooks for plugin ai-toolkit (enabled=true): ./claude-app/hooks/hooks.json
```

The `skills` manifest field adds to the default `skills/` directory instead of
replacing it, so the plugin contributes its 109 catalog skills plus the 2
app-only rule skills.

## Diagnosis

```bash
ai-toolkit doctor
```

Check 11 reports the collision:

```
## 11. Plugin Double-Load
  WARN: ai-toolkit@local-desktop-app-uploads is active next to the global install: 28 toolkit hooks fire twice per event and skills/agents load twice (run: ai-toolkit doctor --fix)
```

To see the duplication directly, count hook invocations per source in a fresh
session log:

```bash
grep -oE "[^\"' ]*hooks/[a-z0-9._-]+\.sh" ~/.claude/debug/latest | sort | uniq -c
```

## Fix

```bash
ai-toolkit doctor --fix
```

That sets the plugin to `false` in `enabledPlugins` and leaves the global
install authoritative. Claude Code then logs
`enabled=false; will NOT register, plugin is disabled`, and plugin skills and
agents drop to 0.

The global install is the richer surface for Claude Code: it delivers rules as
real files under `~/.claude/rules/`, which are always in context, while the
plugin exposes them as an `ai-toolkit-rules` skill the model has to load. The
plugin also has no `session-context.sh` hook.

Keep the plugin enabled only when Claude Code has no global install, for example
a machine that runs the Claude app alone. In that case the plugin is the single
source and check 11 stays quiet.

## Verification

```bash
claude --debug -p "ok"
grep -E "Total plugin (skills|agents) loaded|enabled=" ~/.claude/debug/latest
```

Expect `Total plugin skills loaded: 0`, `Total plugin agents loaded: 0`, and the
`plugin is disabled` line.

## Related

- `kb/reference/global-install-model.md`
- `kb/procedures/maintenance-sop.md`
