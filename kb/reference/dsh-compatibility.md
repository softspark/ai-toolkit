---
title: "AI Toolkit - DSH Compatibility"
category: reference
service: ai-toolkit
tags: [dsh, deepseek-harness, subscriptions, lifecycle, compatibility]
version: "1.7.0"
created: "2026-08-31"
last_updated: "2026-09-01"
description: "Compatibility contract for project skills and the explicit SoftSpark package lifecycle in DeepSeek Harness."
---

# DSH Compatibility

## Summary

ai-toolkit supports DeepSeek Harness as an explicit developer-preview target. The integration is maintained by SoftSpark as a community compatibility layer. DeepSeek AI has not endorsed it.

The reviewed runtime is DSH `0.1.1-rc.2`. Newer upstream prereleases are not covered until they pass the Phase 3 qualification. The isolated real-profile qualification is still pending and this document does not claim it has completed.

## Project vs Profile Outputs

| Surface | Command | Managed output | Explicit non-output |
|---|---|---|---|
| Project install | `ai-toolkit install --local --editors dsh` | `CLAUDE.md`, `.claude/settings.local.json`, `.claude/constitution.md`, detected language rules, other generic local outputs, and the DSH-specific one-level `.agents/skills/<name>/SKILL.md` catalog with bundled resources | No `$DSH_HOME` writes, npm package changes, profile changes, preset changes, or credential reads |
| DSH profile | `ai-toolkit dsh install --profile web` | Two exact npm dependencies in the named profile, the released `softspark-orchestrator` preset, and ai-toolkit ownership state | No project files, provider login, API keys, unrelated plugins, or user presets |

DSH is excluded from `--editors all`, auto-detection, default profiles, and default editor selection. Naming `dsh` without `--local` is not a supported project install route.

Project `--dry-run` resolves and validates `extends`, then plans the generic local outputs and `.agents/skills` catalog without creating, changing, or deleting a project entry. It does not create or update `.softspark-toolkit.lock.json`, and it does not mutate `DSH_HOME`, packages, profiles, state, or authentication.

## Local and Global Commands

```bash
# Generic local outputs plus DSH-specific project skills
ai-toolkit install --local --editors dsh

# Read-only project preview
ai-toolkit install --local --editors dsh --dry-run

# Explicit machine profile lifecycle
ai-toolkit dsh install --profile web
ai-toolkit dsh update --profile web
ai-toolkit dsh doctor --profile web
ai-toolkit dsh uninstall --profile web --yes
```

The DSH profile defaults to `web` when `--profile` is omitted. `DSH_HOME` selects the DSH root and defaults to `~/.dsh`. Profile mutation is never an implicit side effect of local installation, global installation, update, or generic uninstall.

## Exact Pins

| Component | Reviewed version | Role |
|---|---:|---|
| DeepSeek Harness | `0.1.1-rc.2` | Profile host and plugin manager |
| pnpm | `>=11.7.0,<12.0.0` | Package manager used by the DSH plugin command |
| `@softspark/dsh-codex` | `1.0.0` | Codex parent provider through local `codex app-server` |
| `@softspark/dsh-orchestrator` | `1.0.1` | Claude Code and GitHub Copilot Gemini delegation bundle plus released preset |

Install and update use exact package arguments with `--save-exact`. Arbitrary DSH prereleases and unpinned SoftSpark packages are outside this contract.

The reviewed DSH tag declares `pnpm@11.7.0`. The isolated cold-install environment used Corepack pnpm `11.24.0`, so the lifecycle accepts stable pnpm releases from `11.7.0` through the end of major 11. Before it creates the lifecycle lock or changes a profile, it resolves exact DSH and pnpm command paths from the minimal child `PATH`, records their command and resolved-file identities, and runs their version probes with a five-second bound. Missing, nonzero, timed-out, malformed, or unsupported pnpm probes fail with no package, preset, state, or lifecycle artifact.

## Subscription and Authentication Boundaries

ai-toolkit does not log in to a model provider, accept a provider API key, read a vendor credential store, copy tokens, or add credentials to state. Each vendor CLI owns authentication:

| Route | Login owner | Subscription or billing boundary |
|---|---|---|
| Codex parent | `codex login` and `codex login status` | ChatGPT subscription managed by Codex |
| Claude delegate | `claude auth login` | Claude Max or Pro managed by Claude Code |
| Gemini delegate | `copilot login` | Active GitHub Copilot plan and GitHub AI credits |

Lifecycle subprocesses receive only `HOME`, the validated `DSH_HOME`, `PATH`, and locale or temporary-directory settings when present. Provider and registry secret environment variables are not forwarded. Vendor CLI output is not copied into lifecycle error messages.

## DSH, Codex, Claude, and Copilot Topology

```text
DSH session using SoftSpark Orchestrator
  |
  +-> @softspark/dsh-codex
  |     -> local codex app-server
  |     -> Codex-owned ChatGPT authentication and parent thread
  |
  +-> subagent_claude_code
  |     -> DSH Claude Code provider
  |     -> Claude Code native login
  |
  +-> subagent_gemini_copilot
        -> GitHub Copilot CLI ACP server
        -> Gemini 3.6 Flash under GitHub policy and AI credits
```

Codex is the parent provider. The preset keeps the optional Codex subagent row disabled. Claude Code and Copilot Gemini receive bounded standalone delegation tasks.

## Invocation Metadata and Shared Skill Ownership

DSH and Codex share the project `.agents/skills` output. `app/skills/<name>/` remains canonical. `scripts/generate_codex_skills.py` emits native links or adapted wrappers, so ai-toolkit does not maintain a second DSH-specific skill catalog.

DSH discovers one-level `<name>/SKILL.md` bundles and flat `<name>.md` entries. Names must use lowercase kebab-case. The required fields are `name` and `description`. Optional invocation fields use `user-invocable` and `disable-model-invocation` with boolean values. Camel-case spellings or invalid boolean values fail closed and remove the skill from discovery. Nested `SKILL.md` entries are not supported, but resources inside a valid bundle remain available.

The preset owns the session composition and external delegation tools. It does not copy the 44 ai-toolkit agent definitions into 44 DSH presets or subagents.

## Lifecycle State and Recovery

State resolves in this order:

1. `$AI_TOOLKIT_HOME/state.json` when `AI_TOOLKIT_HOME` is set.
2. `$SOFTSPARK_HOME/ai-toolkit/state.json` when `SOFTSPARK_HOME` is set.
3. `~/.softspark/ai-toolkit/state.json` by default.

The DSH record stores the canonical DSH home, profile, exact package versions, package-tree identity, preset path, preset hash, ownership flags, and timestamps. It stores no package contents, prompts, credentials, authentication paths, or child-process environment.

The published npm packages own their installed code. The canonical preset source is `@softspark/dsh-orchestrator/agent-presets/softspark-orchestrator` inside the exact installed package. ai-toolkit copies and verifies that tree. It does not reconstruct the preset.

Mutations first take a nonblocking exclusive POSIX `flock` on the already pinned `DSH_HOME` directory descriptor, then claim the bounded canonical lifecycle lock and use the shared state lock with compare-and-swap publication. Directory locking is independent of the replaceable lock filename. It remains held across sentinel scans, package and preset mutation, normal canonical-lock release, or recovery-sentinel creation plus file and directory `fsync`. A competing lifecycle must acquire the same directory lock before it can scan recovery state or claim the canonical name. The immutable prerequisite record is revalidated after lock acquisition and before every package mutation or package rollback. A replaced or removed executable, or a new earlier `pnpm` PATH shadow, blocks the command. The verified pnpm command directory is placed first in the child PATH so DSH's literal `pnpm` lookup resolves to the probed command. Install, update, and uninstall verify the profile manifest, package trees, preset identity, and unrelated dependencies before and after each external package-manager command. Rollback restores the immutable pre-operation target. It does not reinterpret concurrent bytes as owned data.

Each DSH plugin add, update, remove, or rollback command has a 300-second process bound, separate from the short prerequisite probe. This bound accommodates cold package resolution without promising registry or network latency. Every mutation starts DSH in a dedicated POSIX session and process group. A timeout or interruption signals the complete group, escalates from `SIGTERM` to `SIGKILL` when needed, and waits for confirmed group exit before rollback. If exit cannot be confirmed, package rollback is blocked and deterministic inspection steps are reported. Child stdout and stderr remain suppressed from user-facing errors.

Process-group signals are allowed only while the unreaped DSH supervisor still binds its PID to that group. If the supervisor identity is lost before escalation, the lifecycle fails closed instead of signaling a group identifier that the operating system could reuse. Before `Popen`, the calling thread blocks `SIGINT` with `pthread_sigmask`. It restores the previous mask only inside a catchable region that covers `communicate`, final PGID inspection, and command postconditions, then restores the mask again in `finally`. Any `BaseException` after spawn runs full process-tree teardown before propagation. Repeated `SIGINT` cannot escape the bounded TERM, KILL, and wait sequence.

An unconfirmed process-tree exit first verifies that `$DSH_HOME/.ai-toolkit-lifecycle.lock` still names the held inode, then creates and syncs a transaction-unique process-tree recovery sentinel. It rewrites the canonical lock as a recovery gate only while that identity remains exact. A removed or renamed lock leaves the sentinel as the gate; a foreign replacement is neither overwritten nor deleted. Install, update, and uninstall scan these sentinels before and after claiming the canonical lock, so recovery blocks DSH invocation even when the original lock name was displaced. `doctor` reports every gate's process-group identifier, original profile path, and exact artifact path. ai-toolkit never clears these gates automatically: the operator must verify that the recorded process group has exited, inspect the profile, and only then remove every named recovery artifact.

An identity conflict preserves the conflicting path and creates a doctor-visible recovery marker instead of deleting or replacing it. User plugins, dependencies, presets, profile patches, and unrelated state keys remain outside ai-toolkit ownership. Secure mutation and process-tree termination require POSIX primitives available on Linux, WSL, and macOS. Native Windows mutation is unsupported and fails before the lifecycle lock.

Profile lifecycle `--dry-run` is read-only. It runs the bounded DSH and pnpm prerequisite probes, but it does not create state, acquire a lock, invoke the plugin manager, or create profile paths. It can therefore report a missing or unsupported prerequisite without leaving lifecycle output.

## Unsupported Google, Antigravity, and API-Key Routes

This integration does not provide direct Google AI Pro or Ultra login, Gemini CLI OAuth, Antigravity login, Gemini API keys, DeepSeek API keys, Anthropic API keys, or OpenAI API keys. Gemini is available only through the GitHub Copilot CLI ACP route described above.

The first native target also excludes DSH hook bridging, MCP bridging, arbitrary preset import, automatic profile selection, and full ai-toolkit agent mapping. Generic `ai-toolkit uninstall` does not mutate DSH profiles.

## Behavioral Limits

- Claude Code and Copilot delegation are one-shot child tasks. Each child receives the task and workspace directory, not the parent conversation history.
- Copilot runs with no available tools, rejects permission requests, disables built-in MCP servers, remote control, custom instructions, and auto-update, and uses a 30-credit session cap.
- Child effects completed before cancellation are not rolled back.
- Workspace content selected by a vendor CLI may leave the machine under that vendor's product terms and account policy.
- Codex owns its built-in tools, sandbox, approval policy, thread state, and model execution. ai-toolkit does not reproduce those controls inside DSH.
- Existing DSH sessions keep the preset generation with which they started. Restart DSH and open a new session after install or update.

## Uninstall, Update, and Doctor

`ai-toolkit dsh update` changes only a recorded profile whose managed package and preset identities match state. It installs the current reviewed pins, then publishes the new state after all postconditions pass.

`ai-toolkit dsh doctor` is read-only. It reports the DSH runtime version, pnpm availability and version, package pins, package-tree and preset ownership, state consistency, lifecycle lock recovery artifacts, staging paths, and recovery markers. A recovery marker keeps `Recovery needed: yes` visible until the operator resolves the named paths.

`ai-toolkit dsh uninstall --yes` removes only the recorded SoftSpark packages, preset, and profile state. Drift or ownership ambiguity stops removal. Unrelated profile dependencies, patch files, presets, and state keys remain unchanged.

## Verification

Run the static and isolated checks without modifying a regular DSH profile:

```bash
bats tests/test_ecosystem_doctor.bats
bats tests/test_dsh.bats
python3 scripts/ecosystem_doctor.py --tool dsh --offline --format text
python3 scripts/validate.py --strict

ai-toolkit install --local --editors dsh --dry-run
ai-toolkit dsh install --profile web --dry-run
ai-toolkit dsh update --profile web --dry-run
ai-toolkit dsh doctor --profile web
ai-toolkit dsh uninstall --profile web --dry-run --yes
```

Phase 3 real-profile qualification remains pending. It must use a task-specific `DSH_HOME`, the published package artifacts, native vendor logins, one Codex-to-Claude marker task, one Codex-to-Copilot-Gemini marker task, and a final ownership-safe uninstall. Do not use a regular profile for that qualification.

## Preview and Upstream Drift

DeepSeek Harness describes itself as a developer preview with compatibility-breaking changes. The upstream release feed published `0.1.2-alpha.2` after the reviewed `0.1.1-rc.2` line. ai-toolkit does not adopt that prerelease by inference.

Use the registry doctor to detect documentation, capability-marker, and local version changes. A new upstream version requires source review, focused fixture updates, isolated real-profile qualification, and explicit pin changes before support moves.

## Sources

- [DeepSeek Harness documentation](https://deepseek-harness.github.io/deepseek-harness/)
- [DeepSeek Harness releases](https://github.com/deepseek-ai/deepseek-harness/releases)
- [Reviewed DSH 0.1.1-rc.2 release](https://github.com/deepseek-ai/deepseek-harness/releases/tag/dsh-v0.1.1-rc.2)
- [Reviewed DSH package-manager declaration](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.1-rc.2/package.json)
- [Reviewed DSH CLI profile and plugin contract](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.1-rc.2/apps/cli/reference/README.md)
- [Reviewed DSH skill discovery contract](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.1-rc.2/docs/subsystems/skills.md)
- [PATH: kb/reference/manifest-install.md]
- [PATH: kb/planning/dsh-native-install-target-plan.md]
