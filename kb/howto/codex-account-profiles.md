---
title: "Codex Account Profiles by Project"
category: howto
service: ai-toolkit
tags: [codex, openai, accounts, profiles, cli, authentication]
created: "2026-10-04"
last_updated: "2026-10-04"
description: "Route Codex CLI accounts by project directory and read official account usage limits."
---

# Codex account profiles

`ai-toolkit codex-switch` routes the Codex CLI. It does not switch accounts in ChatGPT, the Codex
desktop app, an existing session, or an independently started IDE integration.

## Prerequisites

- Install the toolkit so `ai-toolkit` is on `PATH`, plus the native Codex CLI.
- Node.js 18+ and Python 3.11+ are required.
- Have access to each intended account and existing project directories.
- For a source checkout, use `node bin/ai-toolkit.js codex-switch` from the repository root.

## 1. Create profiles and log in

```bash
ai-toolkit codex-switch init
ai-toolkit codex-switch add infinity --share-config
ai-toolkit codex-switch add play-reserve --share-config
ai-toolkit codex-switch bind /absolute/path/to/infinity infinity
ai-toolkit codex-switch bind /absolute/path/to/play-reserve play-reserve
ai-toolkit codex-switch login infinity
ai-toolkit codex-switch login play-reserve
```

Use real existing project paths. `init` preserves an existing registry and
keeps the native default home (`~/.codex`, or the existing absolute
`CODEX_HOME` captured during initialization). Each named profile has a private
directory under `~/.softspark/ai-toolkit/codex-profiles/NAME` and logs in through
Codex's own browser flow. Tokens, history, databases and plugin state are never
copied between accounts. Codex owns credential storage, including its keyring.

`--share-config` explicitly links existing `config.toml`, `AGENTS.md`,
`AGENTS.override.md`, `agents`, `skills`, `rules`, `hooks.json`, and
`ai-toolkit-hooks` from the original default profile. These are live shared
settings, including any provider, workspace, permission or project-trust
configuration stored in `config.toml`. Changes through any linked profile
affect the others. Omit the flag for independent settings. Portable skills
under `~/.agents/skills` remain discoverable through native Codex behavior.

## 2. Launch through the toolkit

```bash
ai-toolkit codex-switch run                          # select by current directory
ai-toolkit codex-switch run --account infinity       # explicit override
ai-toolkit codex-switch run --account default        # original account
ai-toolkit codex-switch run -- -C /path/to/project    # select by native directory flag
```

Plain `codex` keeps its native behavior. Project bindings apply only to
`ai-toolkit codex-switch run`; no shell function or standalone account-switch
command is installed.

The longest complete directory match wins. Subdirectories inherit their
binding; an unbound Git worktree inherits the main checkout's binding.
`--account` is consumed only at the start of wrapper arguments. All subsequent
arguments remain native Codex arguments; `--` ends wrapper option parsing.
Native `--profile` selects a configuration layer, not an account login.

Named profiles use `--no-daemon` to avoid attaching to the shared background
server. They clear inherited `CODEX_SQLITE_HOME` and constrain `sqlite_home`
to the selected profile. Remote connections, shared-server management,
desktop launches and explicit SQLite home overrides are rejected for named
profiles because they could use state outside that profile. Use the native
`command codex` directly for those separate workflows.
This restriction also applies when native global options, such as
`--local-provider ollama`, precede a shared-server or desktop command.

Named launches refuse inherited `CODEX_API_KEY`, `CODEX_ACCESS_TOKEN`, or
`OPENAI_API_KEY` rather than silently use an unrelated credential. Error
messages name variables without printing values. The original default profile
retains native behavior. Account selection never changes in response to quotas.

## 3. Check status and limits

Use `ai-toolkit llm-status` for a combined dashboard of these profiles and all configured
Claude accounts. `ai-toolkit llm-status`, `ai-toolkit llm-status --refresh` and `ai-toolkit llm-status refresh`
all fetch current limits for both providers. See [combined status options](../reference/cli-reference.md#combined-llm-account-status).

```bash
ai-toolkit codex-switch status
ai-toolkit codex-switch status --refresh
ai-toolkit codex-switch status --verbose
ai-toolkit codex-switch status --refresh --json
```

The terminal dashboard matches `ai-toolkit claude-switch`: profile count, active/default
markers, colored progress bars, reset countdowns and fetch age. Details
use `--verbose`; `--color auto|always|never` and `NO_COLOR` control colors.
JSON includes selected routing and the complete profile list.

Every `status` invocation starts a short-lived native Codex app-server for each
profile and calls the documented `account/rateLimits/read` method. It does not
submit a model turn, start a conversation, or read tokens itself. Codex may
refresh its native authentication and write its normal local state.

The reader uses the `codex` quota bucket and identifies five-hour/seven-day
windows by their declared durations. It never assumes `primary` is five hours.
Missing windows remain unknown. Other model-specific buckets, API billing and
arbitrary window durations are not displayed as these two subscription limits.
Quota readings are not written to disk. Failed requests show a sanitized error
on the affected profile without falling back to historical observations.
An API-key-only or logged-out profile may not
provide subscription quotas. Use native Codex `/status` for its own view.

The request has a 10-second timeout per profile and its owned subprocess is
stopped afterwards. Credentials and full protocol messages are never cached
by the toolkit. `--refresh` remains an alias for the normal live behavior.

## Storage and configuration

- Registry: `~/.softspark/ai-toolkit/codex-switch.json`.
- Profiles: `~/.softspark/ai-toolkit/codex-profiles/NAME`.
- `CODEX_SWITCH_CONFIG` selects another registry; `AI_TOOLKIT_HOME` relocates
  toolkit data. Claude's registry remains separate.

Historical quota cache files from earlier versions are neither read nor updated.
The command leaves those files in place.

To change the fallback, use `ai-toolkit codex-switch default NAME`. To reassign a
directory, run `ai-toolkit codex-switch bind PATH NAME` again.

## 4. Migrate an older shell setup

Remove old account-switch `shell-init` evaluation lines from `~/.zshrc` or
`~/.bashrc`, including standalone and `ai-toolkit` spellings. Open a new
terminal. Sourcing the edited startup file does not remove functions already
loaded in the current shell. To clear an existing zsh/bash session:

```bash
unset -f codex
hash -r
```

Use `ai-toolkit codex-switch` instead of the removed `openai-switch` or
`codex-switch` standalone commands and the removed `ai-toolkit openai-switch`
alias. Account registries, bindings and credentials remain in place.

## Verification

1. Run `ai-toolkit codex-switch status --json` from a bound project and check
   the selected account and routing source.
2. Launch `ai-toolkit codex-switch run` and check native Codex `/status`.
3. Run `ai-toolkit llm-status` to fetch both providers' current limits.

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| Old command fails after upgrade | Remove its startup evaluation, open a new terminal or run `unset -f codex` and `hash -r`; use `ai-toolkit codex-switch` |
| Plain `codex` uses the original login | Use `ai-toolkit codex-switch run` for project-based selection |
| A profile is logged out | Run `ai-toolkit codex-switch login NAME` and retry status |
| Limits are unknown | Confirm the profile uses a subscription login; API-key-only profiles may not expose subscription quotas |
| A usage request fails | Read the profile's error; the dashboard does not substitute historical readings |

Sources: [Codex authentication](https://learn.chatgpt.com/docs/auth),
[configuration and state](https://learn.chatgpt.com/docs/config-file/config-advanced),
and [official app-server rate limits](https://learn.chatgpt.com/docs/app-server#6-rate-limits-chatgpt).
