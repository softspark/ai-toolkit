---
title: "AI Toolkit - DSH Compatibility (Retired)"
category: reference
service: ai-toolkit
tags: [dsh, deepseek-harness, retired, migration]
version: "2.0.0"
created: "2026-08-31"
last_updated: "2026-09-24"
status: retired
description: "Retired: ai-toolkit no longer supports DeepSeek Harness. Migration behaviour for old DSH project skills and manual removal of DSH profiles."
---

# DSH Compatibility (Retired)

## Summary

DeepSeek Harness (DSH) support was removed in 5.0.0 on 2026-09-24 by decision of the repository owner (see `DECISIONS.md`, "DSH integration retired"). Both entry points no longer do anything. Following the deprecation path in `BACKWARD_COMPATIBILITY.md`, they stay for that one release as warnings, so scripts that call them keep working:

- `ai-toolkit install --local --editors dsh`: prints a warning, ignores `dsh`, installs the other editors.
- `ai-toolkit dsh install|update|doctor|uninstall --profile <name>`: prints the manual cleanup steps below and exits 0.

Both stubs are removed in the next minor release.

## What the toolkit still does

The toolkit keeps just enough knowledge of DSH to clean up after itself:

| Existing state | Command | Result |
|---|---|---|
| `.agents/skills` surface with owners `codex` + `dsh` | `ai-toolkit update --local` or `ai-toolkit install --local` | Re-rendered as a Codex-only surface |
| `.agents/skills` surface with owner `dsh` only | `ai-toolkit update --local` or `ai-toolkit install --local` | Removed |
| Either of the above | `ai-toolkit uninstall` | Removed |
| Registered project listing `dsh` in its editors | any command reading the project registry | Not an error; the `dsh` entry is dropped |

Codex keeps using `.agents/skills`; nothing changes for Codex-only projects.

## Removing an old DSH profile

Profiles set up by `ai-toolkit dsh install` live under `$DSH_HOME` (default `~/.dsh`). The toolkit no longer reads, updates or removes them. If you no longer want the SoftSpark packages there, remove them with DSH itself. For the default `web` profile:

```bash
dsh plugin --profile web remove @softspark/dsh-codex
dsh plugin --profile web remove @softspark/dsh-orchestrator
rm -rf "${DSH_HOME:-$HOME/.dsh}/.agent-presets/softspark-orchestrator"
```

Repeat the two `plugin remove` lines for any other profile name you installed. Stop running DSH sessions first.

Notes:

- The preset directory `softspark-orchestrator` was a copy of `@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator`. Delete it only if you did not edit it and want it gone.
- `ai-toolkit dsh install` also set a pnpm override for `@anthropic-ai/claude-agent-sdk` (version `0.3.263`) under the `@deepseek-ai/dsh-subagent-claude-code` selector in the profile's `pnpm-workspace.yaml`. It is harmless to keep. Remove it by hand if you want the profile back to its DSH default.
- Old `dsh` ownership records in `~/.softspark/ai-toolkit/state.json` are no longer used.

## History

The design, qualification evidence and pins of the removed integration are kept for reference:

- [PATH: kb/history/completed/dsh-native-install-target-plan.md]
- [PATH: kb/history/completed/dsh-integration-plan-superseded.md]
- The last version of this document before retirement is in git history (v1.8.1, toolkit v4.39.0).
