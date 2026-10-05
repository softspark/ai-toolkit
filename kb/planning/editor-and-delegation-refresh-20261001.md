---
title: "Editor support and Claude-to-Codex delegation refresh"
category: planning
service: ai-toolkit
tags: [editors, claude, codex, antigravity, orchestration, models]
version: "1.0.0"
created: "2026-10-01"
last_updated: "2026-10-01"
description: "Approved editor priorities, conditional Codex plugin delegation and supervised model tiers, with implementation evidence."
---

# Editor support and delegation refresh

## Status and objective

Approved by the user on October 1; repository implementation, validation and
global toolkit activation are complete.
The user additionally requires plugin detection: delegate from Claude to Codex
only when its plugin is installed, enabled and available in the active session.
Otherwise use the installed native agents and their configured models.
Prioritize Claude Code, Codex and Antigravity, integrate the installed Codex
plugin into Claude task delegation, and move bounded implementation work to
less expensive model tiers while retaining stronger supervision.

The selected scope keeps three primary clients and the remaining adapters
optional. No editor removal or subscription change is part of this implementation.
Runtime installation and verification evidence is recorded below.

## Implementation evidence

- Eleven bounded implementation roles now default to Sonnet `high`; the Claude
  orchestrator uses Opus `high`, and the debugger uses Opus `xhigh`.
- Normal Claude sessions receive a read-only installed/enabled plugin hint and
  the shared routing skill. Project disablement, missing/malformed metadata and
  unavailable runtime agents retain native configured execution.
- The forwarding wrapper has a narrow SubagentStart exception, including quiet
  behavior. The detector ships alongside deployed hooks and in the Claude app
  package, so it remains available with an older npm-global installation.
- Other clients filter Claude-only guidance, preserve their model selection and
  keep literal examples, metadata and resources. Malformed blocks fail before
  agent/command writes. No editor or vendor plugin was removed or installed.
- Independent routing/spec and export/quality reviews approved the final fixes.
- Full Bats suite: **1946 passed**, exit 0, log
  `/private/tmp/ai-toolkit-delegation-bats-final-20261001.log`.
- Full Python suite: **677 passed**, log
  `/private/tmp/ai-toolkit-delegation-pytest-final-20261001.log`.
- Targeted detector/export suite: **80 passed**; hook integration: **10 passed**,
  rerun after the final quiet-mode correction. Export reviewer independently
  confirmed 37 prompt-surface tests.
- Ruff, ShellCheck, strict mypy (12 modules), strict toolkit validation and
  `git diff --check` passed. Native artifacts were regenerated.
- The first sandboxed full run exposed a local HTTP socket restriction, plus a
  test fixture using the real home for a registry lock. The fixture now isolates
  its home, and the final full run used the required local-socket permission.
- The local metadata detector recognizes the user's enabled Codex plugin.
  No paid delegated-model task or security scan was run; model access and actual
  security-package execution are not certified by these contract tests.
- Activated with the existing `standard` profile, saved module set and 11 selected
  editors using `scripts/install.py --modules agents,core,rules-common,skills
  --profile standard --only agents,skills,hooks`. Claude agent/skill links now
  reference this checkout. No vendor application binaries were upgraded.
- Post-install checks confirmed the selected Claude model/effort pairs, identical
  deployed detector and forwarding-hook bytes, the Codex plugin still enabled,
  no Claude plugin routing in native Codex exports, and unchanged saved module
  and editor selections. Skill audit: zero high-severity or warning findings.
- Start a new Claude session to load the updated definitions. Native Codex
  reported changed global hooks and requires its normal `/hooks` trust review;
  no trust/approval state was bypassed or automatically granted.
- The installer encountered HTTP 404 for the existing external `jira-mcp-hooks`
  refresh URL and retained its cached version. This unrelated upstream source
  did not prevent toolkit installation.

## Verified local baseline

- Claude Code: `2.1.287`; Codex CLI: `0.159.3`.
- Claude plugin `codex@openai-codex`: installed and enabled, version `1.0.6`,
  originating from `openai/codex-plugin-cc`.
- Its installation is under `~/.claude/plugins/cache/openai-codex/codex/1.0.6`.
  `agents/codex-rescue.md` describes proactive implementation delegation and
  defaults to write access; its Sonnet wrapper forwards to a separate Codex run.
- `app/agents/` declares 44 agent models: 29 Opus, 14 Sonnet and one Haiku.
  `app/skills/orchestrate/SKILL.md`, `swarm/SKILL.md` and `workflow/SKILL.md`
  select Opus and maximum effort.
- `scripts/generate_antigravity_agents.py` emits `model: inherit`.

Existing project references: [PATH: kb/reference/model-compatibility.md],
[PATH: kb/reference/codex-cli-compatibility.md],
[PATH: kb/reference/mcp-editor-compatibility.md].

## Editor support proposal

This is a support-priority recommendation based on product status and the
user's stated workflow, not a market-share ranking or evidence of local usage.

| Surface | Proposed treatment | Evidence / reason |
|---------|--------------------|-------------------|
| Claude Code, Codex, Antigravity | Primary maintained and tested targets | User's stated priorities |
| Cursor, Copilot, Cline, OpenCode | Optional integrations | Distinct workflows; no justification for removing working adapters merely because they are not primary |
| Windsurf / Devin Desktop | Optional; update naming and migration guidance | [Vendor rebranding](https://devin.ai/blog/windsurf-is-now-devin-desktop) and [compatibility FAQ](https://docs.devin.ai/desktop/devin-desktop-faq) |
| Gemini CLI | Exclude from recommended individual-user stack; preserve explicit enterprise/API cases | [Google's transition to Antigravity CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) |
| Roo Code / Zoo Code | Retire old product branding; keep successor compatibility optional | [Roo archive](https://github.com/RooCodeInc/Roo-Code), [Zoo releases](https://github.com/Zoo-Code-Org/Zoo-Code/releases); same adapter also serves Zoo |
| Aider, Augment | Optional, candidates to remove from the user's own setup if unused | No verified basis for claiming both products are discontinued |

Antigravity 2.19.1, released September 30, fixes custom agents ignoring project
and global rules. Check the installed application version before updating it;
this audit did not establish the local Antigravity version.
[Antigravity changelog](https://antigravity.google/docs/changelog).

Do not reinterpret `--editors all` as three editors. A recommended subset must
remain distinct from the full supported-adapter set, preserving existing
installation choices and cleanup paths.

## Claude-to-Codex integration

Reuse the installed `codex:codex-rescue` agent. Do not copy or modify its cache.
Treat Codex as a task executor with ownership and acceptance criteria, without
claiming it has native Claude Team membership or shared team messaging.

1. Add a shared routing rule for orchestration, workflow and agent creation.
   When the plugin agent is available and the user permits Codex execution,
   proactively delegate suitable independent coding tasks to it.
2. Use an availability reminder at session start only if necessary. Enabled
   plugin metadata is a hint; the current tool/agent catalog is authoritative.
   Hooks must not install plugins, authenticate, launch paid work or grant access.
3. Dispatch via `Agent(subagent_type="codex:codex-rescue", prompt="--fresh ...")`.
   Include the original objective, work directory, owned files, relevant evidence,
   constraints, acceptance criteria and verification commands. Use explicit
   task/thread identity for continuation rather than an ambiguous last thread.
4. Correct `app/hooks/subagent-start.sh`: the forwarding wrapper must not receive
   the generic instruction to inspect files before forwarding. The actual Codex
   worker still researches, implements and verifies its assigned task.
5. The supervisor collects the result, inspects the diff, runs required checks,
   handles blockers and closes completed work. Do not duplicate the plugin's
   session hooks or automatically enable its optional review gate.
6. Apply the user-selected task routes below while preserving explicit task-level
   model choices and permissions. Outside those routes, retain the client's
   selected Codex model. The plugin uses
   `workspace-write` for writes and `approvalPolicy: never`; permission failures
   return to the supervisor instead of triggering a bypass.
7. Do not recommend the plugin's stale Spark alias. The official
   [Codex changelog](https://learn.chatgpt.com/docs/changelog) records Spark's
   September 14 retirement. Model IDs must be available in the actual client.

Claude 2.1.287 supports nested agents subject to the current Agent tool and depth
limit. Do not generalize the plugin's older warning into a ban on all delegation
from forked agents. [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents).

## Proposed model policy

User-selected routes, recorded October 1: implementation, tests and routine
fixes use Sonnet 5.5 at `high` or Codex; security uses Codex Astra at `xhigh`;
hard debugging uses Codex or Opus at `xhigh`. Normalize the user's spellings
`height` and `xheight` to the configuration values `high` and `xhigh`.
Security-package entitlement and accreditation are account-specific; this
implementation does not certify either.
For security work, prefer the requested Astra route and existing account setup
when available. If the plugin is absent or disabled, use the installed native
security agent and its configured model, noting that the Codex route is unavailable.

Sonnet 5.5 was released September 28. Current standard API input/output prices
are $2/$10 per million tokens, versus Opus 5.5 at $4/$20. Those rates are not
subscription usage prices or guaranteed per-task savings.
[Model comparison](https://platform.claude.com/docs/en/models/overview),
[Sonnet announcement](https://www.anthropic.com/claude-sonnet-5-5).

| Work | Proposed route |
|------|----------------|
| Decomposition, architecture, ambiguous decisions, final acceptance | Opus, high effort as a starting policy to evaluate |
| Bounded backend/frontend implementation, tests, routine fixes, QA automation, approved DevOps changes | Sonnet 5.5, `high`; Codex for suitable independent work |
| Documentation and routine maintenance | Sonnet; retain existing explicit user choices |
| Small read-only discovery tasks | Existing Haiku explorer; evaluate Sonnet for difficult repository navigation |
| Security work and security decisions | Codex Astra, `xhigh`, using the user's existing security setup |
| Hard debugging | Codex or Opus, `xhigh` |
| Migrations | Supervisor assessment based on risk and failed checks |

Use supported Claude aliases with provider-aware resolution, not global search
and replace. On direct Anthropic API, current Claude Code resolves `sonnet` to
Sonnet 5.5; other providers differ. Installed Claude Code meets the required
minimum version 2.1.284. [Model configuration](https://code.claude.com/docs/en/model-config).

Skills mostly supply procedures and effort; agents and forked skill definitions
select execution models. Inspect both before changing routing. Keep exceptions
for difficult tasks; changing every worker to the cheapest tier is not the goal.
Lower routine orchestration from unconditional `max` only as part of the
approved policy. Compare total supervisor, worker, retry and review usage.

Antigravity supports `inherit`, `flash` and `pro` in custom-agent definitions.
It needs its own explicit mapping if the user wants differentiated tiers;
do not translate Claude model identifiers into its schema.
[Antigravity subagents](https://antigravity.google/docs/subagents/).

API examples need a separate compatibility review: Sonnet 5.5 rejects forced
`tool_choice` values `any` and `tool` and changes thinking-block handling.
Do not upgrade executable examples by replacing only the model ID.
[Migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide).

## Delivery plan and acceptance criteria

### Internet verification of the selected routes (October 1)

The selected division is consistent with documented capabilities and is a
reasonable quality-oriented starting policy. It is not a measured optimum for
this repository or proof of a working end-to-end plugin setup.

- **Sonnet 5.5 `high`:** Anthropic suggests `medium` for well-defined agentic
  work and `high` for harder or longer tasks. It explicitly notes that `low`
  and `medium` can stop early to check in with the user. Keeping `high` fits
  the requested autonomous implementation workflow.
  [Sonnet prompting guidance](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5).
- **Opus supervision:** Anthropic documents a Sonnet executor with an Opus
  advisor. This supports the broader division of work, but its API advisor
  mechanism is not the same implementation as Claude-to-Codex delegation.
  Opus 5.5 supports `high` and `xhigh`; its default is `medium`, so the proposed
  levels are explicit choices, not universal vendor defaults.
  [Advisor tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool),
  [effort reference](https://platform.claude.com/docs/en/build-with-claude/effort).
- **Astra `xhigh`:** GPT-6 Astra supports `xhigh`; Codex documents High and
  Extra High for difficult multistep work. The installed Claude plugin accepts
  `--model gpt-6-astra --effort xhigh` and forwards model and effort to
  `turn/start` in `scripts/lib/codex.mjs`. The wrapper's Claude model and effort
  do not automatically set those controls for the Codex worker.
  [Astra reference](https://developers.openai.com/api/docs/models/gpt-6-astra),
  [Codex models](https://learn.chatgpt.com/docs/models).
- **Security package and access:** selecting Astra does not itself invoke
  Codex Security or establish Trusted Access. The exact security package has
  not been identified in this review. If the user means OpenAI's offering,
  verify its loaded plugin/CLI route and the account used by the delegated
  runtime. Current cyber guidance recommends GPT-Daybreak-Blue for most
  authorized defensive work; access is scoped to the approved identity,
  workspace or API project, model and product surface. Preserve the user's
  Astra choice until that intended package and access route are established.
  [Codex Security plugin](https://learn.chatgpt.com/docs/security/plugin),
  [models and Trusted Access](https://learn.chatgpt.com/docs/cyber-safety).

Runtime acceptance must include observing the selected model and effort in an
actual delegated task and confirming that the intended security workflow ran.
No paid task, security scan or access-status check was performed in this review.

### Implementation sequence

1. Implement the approved recommended editor support profile and the worker
   routes above; preserve explicit task-level model choices and native fallback
   when the Codex plugin is absent, disabled or unavailable.
2. Implement routing guidance in `app/agents/orchestrator.md` and orchestration,
   workflow, subagent-development, agent-creator and model-routing skills.
   Add the narrow hook exception and any required availability helper.
3. Update selected worker definitions, dated compatibility references and
   ecosystem registry. Correct the maintenance SOP's Project IDX link and
   outdated MCP-adapter count. Preserve historical release records.
4. Regenerate supported client artifacts and verify that Claude-specific routing
   does not cause Codex to invoke the Claude plugin recursively.
5. Test enabled, disabled, missing and malformed plugin metadata; ordinary-agent
   hook behavior; forwarding behavior; runtime capability absence; explicit
   model preservation; the requested `high`/`xhigh` worker routes; and
   translated/exported guidance.
6. Run affected Bats/Python suites, static checks, strict validation and the full
   repository suites before claiming the implementation complete. A live plugin
   smoke test additionally requires a working authenticated account and agreed
   execution scope; static checks do not establish runtime quality or savings.

## Alternatives and pre-mortem

- **Recommended:** three primary clients, optional remaining adapters, supervised
  Sonnet/Codex workers. Reduces operational focus without breaking installations.
- **Conservative:** refresh compatibility and Codex routing but retain all model
  tiers. Lower migration risk, less opportunity to reduce execution cost.
- **Minimal:** retain only the three primary clients. Requires explicit agreement
  to remove public support plus migration and cleanup compatibility for users.

Risks: an installed plugin may be disabled or unavailable at the current nesting
depth; workers may touch overlapping files; permission failures may look like
model failures; wrappers and redundant reviews may erase savings; a model
supervisor can still approve incorrect work. Use capability checks, explicit
ownership, surfaced blockers and independent executable acceptance checks.
