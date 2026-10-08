---
title: "Claude Code Account Profiles by Project"
category: howto
service: ai-toolkit
tags: [claude, accounts, profiles, cli, authentication]
created: "2026-10-04"
last_updated: "2026-10-08"
description: "Keep a default Claude Code login and route selected project directories to separate account profiles."
---

# Claude Code Account Profiles by Project

`ai-toolkit claude-switch` assigns a Claude Code account profile to a project directory.
The mapping is stable, including subdirectories. Each process gets its own
configuration directory, so terminals in different projects can run concurrently.
`status` fetches live usage for each configured profile. Usage never
changes routing: there is no account rotation or automatic paid fallback.

## Prerequisites

- Install the toolkit so `ai-toolkit` is on `PATH`, plus the native Claude Code CLI.
- Node.js 18+ and Python 3.11+ are required.
- Have access to each intended Claude account and existing project directories.
- For a source checkout, use `node bin/ai-toolkit.js claude-switch` from the repository root.

## 1. Create profiles

```bash
ai-toolkit claude-switch init
ai-toolkit claude-switch add infinity --share-config
ai-toolkit claude-switch add play-reserve --share-config
ai-toolkit claude-switch bind /absolute/path/to/infinity infinity
ai-toolkit claude-switch bind /absolute/path/to/play-reserve play-reserve
```

Replace the project paths with existing directories. `init` preserves an
existing registry. The initial `default` profile uses your existing `~/.claude/`
and does not move or copy its authentication data. Named profiles are created
under `~/.softspark/ai-toolkit/claude-profiles/NAME`.

`--share-config` links existing `agents`, `skills`, `rules`, `commands`,
`output-styles`, `CLAUDE.md`, `ARCHITECTURE.md`, and `settings.json` from the
default Claude directory. It does not
link credentials, history, global Claude JSON state, or plugin directories.
Shared files are live: changes through any profile affect all profiles using
those links. Review `settings.json` for authentication environment variables,
credential helpers, and account-specific hooks before sharing it. Omit
`--share-config` to start with an independent configuration. Plugins need
separate setup.

MCP servers: a profile's sessions read user-scope servers from
`<profile>/.claude.json`, not from `~/.claude.json`. `--share-config` seeds that
file with a copy of the default account's `mcpServers` (only that key; the
file also holds account state, so it is never linked). After that the lists
are per profile. `ai-toolkit mcp install --editor claude --scope global` (and
`remove`) writes every registered profile, so use it to keep them aligned. To
add a server to one profile only, run the real binary with that profile's
directory, because the `claude` alias re-selects the account itself:

```bash
CLAUDE_CONFIG_DIR=~/.softspark/ai-toolkit/claude-profiles/<name> \
  ~/.local/bin/claude mcp add --scope user jira -- jira-mcp
```

Profiles created before this change start without servers; add them with
either command above. `~/.mcp.json` (project scope under `~`) is the one MCP
file every profile sees without copying.

The toolkit installer continues to manage `~/.claude/`. Existing symlinks in
profiles see changes to the shared configuration without another install.

## 2. Log in once per profile

```bash
ai-toolkit claude-switch login infinity
ai-toolkit claude-switch login play-reserve
```

Each command starts Claude's native `auth login` with the selected configuration
directory. Choose the intended account in the browser. Login remains native;
the status reader later reads that profile's OAuth credentials to query usage,
without printing or copying them to toolkit storage.

Launch each profile and use Claude's `/status` to verify the actual signed-in
account and subscription:

```bash
ai-toolkit claude-switch run --account infinity
ai-toolkit claude-switch run --account play-reserve
```

`ai-toolkit claude-switch status` reports configuration routing and live limits, not a
verified account identity. If inherited environment credentials or provider flags are present,
the launcher warns using variable names without printing their values. Resolve
these overrides before assuming a Max subscription is used. Shared settings can
also contain authentication overrides. The launcher does not silently remove
credentials from your environment.

Named profiles reject an inherited `CLAUDE_SECURESTORAGE_CONFIG_DIR`, including
an empty value, because it overrides their credential directory. Unset it before
running or logging in to a named profile. The original default profile keeps
native Claude behavior.

## 3. Launch through the toolkit

```bash
cd /absolute/path/to/infinity
ai-toolkit claude-switch run                      # infinity profile
ai-toolkit claude-switch status

cd /absolute/path/to/play-reserve
ai-toolkit claude-switch run                      # play-reserve profile

cd /absolute/path/to/another-project
ai-toolkit claude-switch run                      # default profile
ai-toolkit claude-switch run --account infinity   # explicit override
```

The launcher resolves the native Claude executable on `PATH`. Plain `claude`
uses its native account selection; the toolkit installs no shell function or
standalone account-switch command.

## 4. Migrate an older shell setup

Remove old account-switch `shell-init` evaluation lines from `~/.zshrc` or
`~/.bashrc`, including standalone and `ai-toolkit` spellings. Open a new
terminal afterwards. Sourcing the edited file does not clear an already loaded
function. In an existing zsh/bash session, clear the old function and command
lookup cache:

```bash
unset -f claude
hash -r
```

Use `ai-toolkit claude-switch` for future commands. Existing registry bindings,
profile directories and credentials remain valid.

## Selection and arguments

Selection checks an explicit account first, then project bindings, then the
configured default. The longest matching directory wins. A binding for
`/work/infinity` matches `/work/infinity/src`, but not `/work/infinity-old`.
A linked Git worktree without its own matching binding inherits the binding
of its main checkout through Git's common directory. Binding a worktree
explicitly takes precedence.

```bash
ai-toolkit claude-switch status --json
ai-toolkit claude-switch status --account infinity --json
ai-toolkit claude-switch default default
ai-toolkit claude-switch run --account infinity -- --resume
ai-toolkit claude-switch run -- --help
```

`--account NAME` is a launcher option only at the beginning of the `run`
arguments. Subsequent arguments are passed to Claude unchanged. `--` ends
launcher argument handling. `ai-toolkit claude-switch --help` displays launcher help;
`ai-toolkit claude-switch run -- --help` displays Claude help.

JSON status preserves `account`, `config_dir`, `project` (the matching binding
or `null`), and `source` (`override`, `project`, `worktree`, or `default`). It also
includes `account_count`, `default_account`, and an `accounts` list. Each entry
has `name`, `selected`, `is_default`, `config_dir`, `projects`, and `usage`.
`--account` selects a profile for the report while retaining the complete list.

The registry lives at `~/.softspark/ai-toolkit/claude-switch.json` by default.
`AI_TOOLKIT_HOME` changes the toolkit data root, and `CLAUDE_SWITCH_CONFIG`
selects another registry file. Registry data stores directory mappings, not
email addresses or tokens.

The initial `default` profile removes `CLAUDE_CONFIG_DIR` from the launched
process to retain Claude's original default authentication location. Named
profiles set it to their absolute directory. Setting another profile as the
default changes which profile is selected outside bound projects.

## Usage statistics

Use `ai-toolkit llm-status` to see these profiles together with all configured Codex
accounts. `ai-toolkit llm-status`, `ai-toolkit llm-status --refresh` and `ai-toolkit llm-status refresh` all fetch
current limits for both providers. See [combined status options](../reference/cli-reference.md#combined-llm-account-status).

```bash
ai-toolkit claude-switch status
ai-toolkit claude-switch status --refresh
ai-toolkit claude-switch status --verbose
ai-toolkit claude-switch status --json
```

The compact report shows profile count, selected/default markers, five-hour and
seven-day progress bars, time until reset, and fetch age. Terminals under
86 columns use stacked rows. `--verbose` (or `-v`) adds configuration paths,
project bindings and exact UTC timestamps; paths under
your home directory are shortened to `~`.
The count describes registered profiles, not independently verified accounts.
Colors are automatic in a terminal and disabled in pipes. Use
`--color always|never|auto` to select a mode; `NO_COLOR` disables colors in every
mode. `--json` remains complete, uses absolute paths and never includes colors.

Every invocation queries `https://api.anthropic.com/api/oauth/usage` using
that profile's OAuth credentials. This is Claude's internal usage endpoint,
not a documented stable public API; its availability and response may change.
No model turn is submitted and no conversation is created. There is no
background polling and no dependency on the toolkit status line or an active
Claude session.

The reader uses the profile's macOS Keychain entry or native `.credentials.json`
file. Requests time out after 10 seconds per profile. It does not renew OAuth
tokens or modify credential storage. `authentication_expired` requires a native
login through `ai-toolkit claude-switch login NAME`; `rate_limited` means the provider
refused the current request. `--refresh` is an alias for normal live status.

Missing windows display `not provided` and are omitted from JSON, never zero.
Authentication, network and
response errors appear on the affected profile. Failed reads never fall back
to an earlier percentage. Use Claude's `/status` to verify the signed-in
identity and `/usage` to compare the provider's native display.

Quota readings stay in memory for the command and are not saved to disk.
Historical files under `~/.softspark/ai-toolkit/claude-usage/` from earlier
versions are ignored and left in place. Existing custom status lines remain
unchanged; the toolkit status line no longer collects quota snapshots.

In JSON, `usage.state` is `live` after a successful fetch or `error` after a
failure. Successful reads include `observed_at`, `age_seconds`, `windows`
and `refreshed: true`. Failed reads contain empty `windows`, null timestamps,
`refreshed: false` and a sanitized `refresh_error` code.

## Verification

1. Run `ai-toolkit claude-switch status --json` inside a bound project and
   check `account`, `source` and the matching `project`.
2. Launch `ai-toolkit claude-switch run` and inspect Claude's `/status` to
   confirm the signed-in account.
3. Run `ai-toolkit llm-status` to fetch both providers' current limits.

## Troubleshooting

| Symptom | Resolution |
|---------|------------|
| Old shell command fails after upgrade | Remove the old startup evaluation, open a new terminal or run `unset -f claude` and `hash -r`; use `ai-toolkit claude-switch` |
| Plain `claude` uses the original login | Use `ai-toolkit claude-switch run` for project-based selection |
| `authentication_expired` | Run `ai-toolkit claude-switch login NAME` and retry status |
| A usage request fails | Read the profile's error; no previous quota value is used as a fallback |

## Scope and sources

This routing applies to Claude Code CLI processes started through the launcher.
It does not change Claude Desktop, the web app, or independently launched IDE
integrations. Separate configuration directories do not establish provider
permission for any particular multi-account arrangement or spending entitlement.

Claude documents `CLAUDE_CONFIG_DIR` in its
[environment variable reference](https://code.claude.com/docs/en/env-vars).
See [Claude Code authentication](https://code.claude.com/docs/en/authentication)
for supported login and credential options.
The internal OAuth usage endpoint is an implementation dependency, not a
public API guarantee from Anthropic.
