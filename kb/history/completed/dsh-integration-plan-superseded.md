---
title: "Plan: DeepSeek Harness (dsh) Integration"
category: planning
service: ai-toolkit
tags:
  - dsh
  - deepseek-harness
  - cordis
  - integration
  - skills
  - subagents
  - multi-model
  - acp
  - emission-target
doc_type: plan
status: superseded
created: "2026-08-25"
last_updated: "2026-08-27"
closed: "2026-08-27"
completion: "Functional objective delivered through standalone 1.0.0 modules; native ai-toolkit install target moved to a replacement plan"
superseded_by: "kb/planning/dsh-native-install-target-plan.md"
description: "Superseded DSH integration plan retained as the historical record of the subscription-backed runtime validation and the architecture split into dsh-codex and dsh-orchestrator."
---

# Plan: DeepSeek Harness (dsh) Integration (Superseded)

**Status:** Superseded on 2026-08-27
**Completion:** Functional objective delivered; native ai-toolkit install target moved to a replacement plan
**Created:** 2026-08-25
**Origin:** Requirement for a single window driving three already-owned subscriptions (Claude Max, ChatGPT Plus, Gemini) without buying API credits
**Upstream reviewed:** `deepseek-ai/deepseek-harness` @ `b150a55` (2026-08-21), package version `0.1.1-rc.2`, MIT, developer preview
**Replacement:** [`kb/planning/dsh-native-install-target-plan.md`](../../planning/dsh-native-install-target-plan.md)

## Closure Record

This plan mixed two outcomes that now have different ownership:

1. The user-facing runtime objective is complete. `@softspark/dsh-codex@1.0.0` provides the ChatGPT-backed Codex parent, and `@softspark/dsh-orchestrator@1.0.0` delegates bounded tasks to Claude Code and GitHub Copilot Gemini. Both are public Apache-2.0 modules with CI, provenance, security gates, KB, release SOPs, and post-release verification.
2. Direct Gemini delegation through a personal Google AI Pro/Ultra login is not supported. The delivered route uses GitHub Copilot CLI ACP, GitHub authentication, and GitHub plan credits. No Google credential proxy or Antigravity workaround is part of the system.
3. The native ai-toolkit emission target was not implemented. `ai-toolkit install --local --editors dsh`, managed preset installation, DSH-specific uninstall, registry metadata, and focused bats coverage move to the replacement plan.

The historical phases below remain useful as the research and validation record. Their status table is updated to show what shipped, what was cut, and what moved.

## 1. Objective

Add dsh as the twelfth emission target so a single harness can delegate to Claude Code, Codex,
and Gemini CLI while each child authenticates natively against its own vendor subscription.

**Non-goal:** rewriting ai-toolkit on top of dsh. The toolkit stays the control plane and source
of truth. dsh is a runtime it emits to, exactly like Codex CLI and opencode.

**Hard constraint that shaped this plan:** Anthropic prohibits third-party tools from routing
Free/Pro/Max OAuth credentials, and enforces it server-side without notice. Any harness that
speaks the Anthropic API itself therefore requires a separate API key. dsh avoids this by
spawning the real Claude Code binary instead of routing credentials.

## 2. Why dsh satisfies the subscription constraint

`packages/subagent/subagent-claude-code/README.md` states the provider deliberately omits the SDK
`settingSources` option, so the official Agent SDK reads the host's normal user, project, and local
Claude settings relative to the parent session cwd, including native account state. It neither
copies nor filters those files and does not create or modify login state. Authentication and
account state remain native; the bundle supplies the CLI but does not create an account, log in,
or probe an account. Credential-shaped ambient variables are scrubbed before the explicit `env`
overlay, so `ANTHROPIC_API_KEY` reaches the child only when supplied deliberately. The runtime is
pinned to `@anthropic-ai/claude-agent-sdk@0.3.220` (Claude Code 2.1.220) and the executable comes
from the SDK platform package, not from `PATH`.

Consequence: the subscription is exercised by Claude Code authenticating itself, not by dsh
presenting the user's credentials to Anthropic.

### Subagent providers present in the tree

| Package | Spawns | Subscription exercised |
|---|---|---|
| `subagent-claude-code` | Agent SDK to native `claude` | Claude Max |
| `subagent-codex` | Codex | ChatGPT Plus |
| `subagent-acp` | any Agent Client Protocol agent (Gemini CLI ships native ACP) | Gemini |
| `subagent-dsh-sdk` | dsh SDK loop | model provider config |
| `subagent-fork-in-process` | forked in-process session | inherited |
| `subagent-spawn-in-process` | fresh in-process session | inherited |
| `subagent-in-process-driver` | shared driver for the in-process providers | inherited |

## 3. Verified compatibility surface

### 3.1 Skill discovery is already satisfied

`packages/skill/skill-filesystem` resolves roots in rank order:

| Rank | Source | Path |
|---|---|---|
| 100 | `project-dsh` | `<projectRoot>/.dsh/skills` |
| 200 | `project-agents` | `<projectRoot>/.agents/skills` |
| 300 | `custom` | `Config.customSkillDirs` |
| 400 | `user-dsh` | `<dshHome>/skills` (`$DSH_HOME`, default `~/.dsh`) |
| 500 | `user-agents` | `<agentsHome>/skills` (`$DSH_AGENTS_HOME`, default `~/.agents`) |

Skill format: single-level directory bundles `<name>/SKILL.md` or flat `<name>.md`. Frontmatter is
an open YAML object; the provider interprets required `name` and `description` plus optional
`whenToUse`, `metadata`, `disable-model-invocation`, and `user-invocable`. Names must be kebab-case.

This is the ai-toolkit skill convention field for field. `scripts/generate_codex_skills.py` already
mirrors every skill in `app/skills/` into `<target>/.agents/skills/<name>/`, native skills as
symlinks to canonical `app/skills` and delegation-heavy skills as adapted wrappers through
`codex_skill_adapter.sync_codex_skill`.

**No new skill generator is required.** Rank 200 is the same directory Codex CLI consumes.

A bare checkout shows only `ai-toolkit-skill-catalogue` under `.agents/skills/` because
`enable_codex_skills` defaults to `False` for the standalone generator; the installer sets it when
Codex is selected.

### 3.2 Presets are compositions, not personas

`packages/preset/agent-presets` treats a preset as a plugin composition: the composition file is a
top-level list of plugin rows, with an optional sibling `preset.yml` carrying display `name` and
`description` only. The `id` is the directory name and must match `[a-z0-9][a-z0-9-]*`; `trust`
derives from the discovery root. Authoring is copy-only: `copy()` rejects a non-conforming id, an
id already supplied by any root, and an unknown source, then re-tightens the copied tree to
owner-only permissions and dereferences symlinks. A copied `preset.yml` keeps the description but
drops `name` and roster `order`.

Package-name rows resolve against the host composition rather than the preset directory, because a
user-home preset cannot reach the harness through Node's upward `node_modules` walk. Relative
paths resolve from the preset's own directory, so a preset's own plugin files and skill directories
travel with it.

**Implication:** mapping 44 agents onto 44 presets is architecturally wrong. Presets are session
compositions (expect 2-3 of them). The 44 agents belong on the subagent surface.

## 4. Gotchas that must become gates

1. **Invocation frontmatter fails closed.** A camel-case spelling (`userInvocable`,
   `disableModelInvocation`) or a non-boolean invocation value **drops the entire skill from
   discovery** with a warning rather than falling back to a permissive default. Accepted boolean
   spellings are YAML booleans plus case-insensitive `true`/`false`, `yes`/`no`, `on`/`off`,
   `1`/`0`. Current emitters are clean; this must be enforced by `validate.py`, not left to chance.
2. **Discovery is one level deep.** Only `<root>/<name>/SKILL.md` and `<root>/<name>.md` are
   recognized. Nested skill trees and package manifests are ignored. Resources under `references`,
   `scripts`, and `assets` inside a bundle are fine and do not invalidate the catalog.
3. **Project root is the nearest `.git` ancestor.** Without that marker the provider falls back to
   the supplied cwd. No alternate project-root marker, no monorepo subproject selection.
4. **Symlinked skills.** `generate_codex_skills.py` emits symlinks into `app/skills`.
   `watchFollowSymlinks` defaults to `true`, so this should hold, but it needs empirical
   confirmation before being relied on.
5. **Malformed entries disappear silently.** The model catalog receives no per-skill diagnostic and
   cannot distinguish an absent skill from an invalid one.

## 5. Open questions

| # | Question | How to close |
|---|---|---|
| Q1 | Subagent definition format: how a delegatable agent such as `security-auditor` is declared | Moved to the replacement plan; the released orchestrator deliberately exposes two bounded static tools instead of mapping 44 toolkit agents |
| Q2 | Whether `packages/hooks` ("Claude Code/Codex hook bridges + wire-protocol library") accepts the toolkit's `app/hooks/*.sh` directly | Moved to the replacement plan as an optional compatibility slice, not a prerequisite for the install target |
| Q3 | Whether `subagent-acp` can drive Gemini CLI end to end on a Google login | Closed negative: individual Gemini CLI access ended; Antigravity has no ACP and prohibits third-party login use |
| Q4 | Plugin row schema for a composition file | Closed by the released `softspark-orchestrator` preset and `cordis.patch.yml` |
| Q5 | Whether Claude Max actually authenticates through the spawned CLI in practice | Closed positive by isolated Codex-to-Claude Max verification without an Anthropic API key |

## 6. Progress Tracking

| Phase | Deliverable | Depends on | Status |
|---|---|---|---|
| 0 | Empirical validation: dsh sees all 109 skills; subscription-backed providers run | none | completed through standalone modules; direct Google route replaced by Copilot Gemini |
| 1 | `validate.py` gates for kebab-case invocation fields and one-level `.agents/skills` depth | 0 | moved to replacement Phase 1 |
| 2 | `scripts/generate_dsh_preset.py` emitting 1-2 compositions | 0, Q4 | replaced by the released `softspark-orchestrator` preset; managed installation moved to the replacement plan |
| 3 | 44 agents mapped onto the subagent surface | Q1 | cut; the released boundary exposes only Claude Code and Copilot Gemini delegation tools |
| 4 | MCP servers and hook bridge | Q2 | cut from the runtime deliverable; optional compatibility work moved to the replacement plan |
| 5 | `ecosystem_tools.json` entry, docs across the nine mandated files, bats coverage | 1-4 | native ai-toolkit registry, docs, tests, and uninstall moved to the replacement plan |

### Phase 0 checkpoint: Codex primary provider verified (2026-08-26)

- The checkpoint began at `@softspark/dsh-codex@0.1.0`; the public `1.0.0` release now bridges DSH to the official local `codex app-server`
  over JSONL stdio. Codex retains sole ownership of ChatGPT authentication and tokens.
- The isolated DSH profile loaded provider `codex`, exposed seven models, booted the Web UI
  on `127.0.0.1:3080`, and completed end-to-end session prompts on Codex models.
- The live app-server reported authentication kind `chatgpt`; no OpenAI API key was configured.
- The final local tarball passed 92 tests, typecheck, lint, build, coverage, dependency,
  signature, SARIF, package, and composition gates. Its SHA-256 is
  `87db7be9f959de507d708bfa74feb4b5890b9b8a7a33d3520e31d91fcbe673c0`.
- A persistent DSH session resumed the identical Codex thread after a host restart, and a live
  cancellation ended with reason `aborted`.
- The public `1.0.0` release keeps stable mode unchanged and exposes a bounded, opt-in
  `experimentalDynamicTools` bridge. Dynamic-tool threads remain non-replayable after restart.

Evidence and release gates live in the standalone repository:
`/Users/lukaszkrzemien/External/WorkspaceSoftSpark/dsh-codex`.

### Phase 0 checkpoint: SoftSpark orchestrator composition (2026-08-26)

- `@softspark/dsh-codex@1.0.0` exposes an explicit bounded dynamic-tool bridge while stable mode remains unchanged.
- `@softspark/dsh-orchestrator@1.0.0` is a separate Apache-2.0 public module with exact DSH dependencies, multi-OS CI, provenance, security gates, tests, KB, and release SOPs.
- The isolated DSH profile loads `softspark-orchestrator` as its default preset and registers one-shot `subagent_claude_code` plus `subagent_gemini_copilot` tools.
- A real Codex-to-DSH `todo_write` tool roundtrip completed on the final composition with no provider API keys.
- Claude Max native login is verified. Google AI Pro/Ultra cannot be delegated through DSH: Gemini CLI ended individual access, Antigravity has no ACP, and its terms prohibit third-party use of account login. No proxy or token workaround will be implemented.
- The final isolated profile completed both a neutral Codex-to-DSH tool call and a Codex-to-Claude Max delegation with exact markers and no provider API keys.

## 7. Detailed Implementation

### Phase 0 - Empirical validation (no code)

```bash
ai-toolkit install --local --editors codex     # populates .agents/skills/ with all 109
npx @deepseek-ai/dsh web                        # UI on 127.0.0.1:3080
```

Verify, in order:

1. The skill catalog lists 109 entries, not the single `ai-toolkit-skill-catalogue` pointer.
2. Symlinked skill bodies load (gotcha 4).
3. A `subagent-claude-code` delegation runs without an `ANTHROPIC_API_KEY` present (Q5).
4. A `subagent-codex` delegation runs on the ChatGPT login.
5. A `subagent-acp` delegation reaches Gemini CLI on the Google login (Q3).

If step 3 fails, the entire premise collapses and the plan reverts to the ACP-in-JetBrains
alternative recorded in section 10.

### Phase 1 - Gates

Extend `scripts/validate.py`:

- Reject any emitted `SKILL.md` whose frontmatter carries `userInvocable` or
  `disableModelInvocation`, or a non-boolean value for the kebab-case forms.
- Reject any `SKILL.md` deeper than `<root>/<name>/SKILL.md` under `.agents/skills/`.
- Reject skill directory names failing `[a-z0-9]+(-[a-z0-9]+)*`.

These protect Codex CLI and opencode as well; the fail-closed behavior is what makes them
non-optional rather than cosmetic.

### Phase 2 - Presets

`scripts/generate_dsh_preset.py` emits composition directories plus `preset.yml` display metadata.
Start with `ai-toolkit-standard`; add `ai-toolkit-strict` only if the profile split earns it. Ids
must satisfy `[a-z0-9][a-z0-9-]*`. Do not attempt to author presets by writing into a shipped
preset directory. Upstream authoring is copy-only and `remove()` refuses shipped presets.

### Phase 3 - Agents

Blocked on Q1. Expected shape: one subagent declaration per `app/agents/*.md`, carrying
`description`, tool allowances, and delegation targets, with the model left unset so host settings
stay authoritative. The `model` alias problem is the same one documented for opencode in
`kb/reference/opencode-compatibility.md`: the toolkit stores `opus`/`sonnet`/`haiku`, which cannot
be mapped without assuming a provider.

### Phase 4 - MCP and hooks

`packages/mcp` for server config, `packages/hooks` for the bridge. If the hook bridge speaks the
Claude Code hook wire protocol, `app/hooks/*.sh` may attach with a thin adapter rather than a
rewrite. Preserve `exit 2` blocking semantics for `guard-destructive.sh`. This matters most under
unattended delegation, where nobody is watching the permission prompt.

### Phase 5 - Registry, docs, tests

Follow the opencode precedent exactly:

- `scripts/ecosystem_tools.json` entry with docs and release-notes URLs for drift detection.
- `kb/reference/dsh-compatibility.md` mirroring the section layout of
  `kb/reference/opencode-compatibility.md` (Summary, Local/Global Install Outputs, Editor Surface
  Comparison, translation models, Behavioral Limits, Verification, CLI Commands).
- Entry in `kb/reference/supported-tools-registry.md`.
- The nine files mandated by `CLAUDE.md`: README.md, CLAUDE.md, ARCHITECTURE.md, package.json,
  plugin.json, skills-catalog.md, architecture-overview.md, llms.txt, AGENTS.md.
- bats generator contract tests, auto-detection tests, idempotency tests.
- `python3 scripts/validate.py --strict`, `python3 scripts/audit_skills.py --ci`, and
  `shellcheck --severity=warning app/hooks/*.sh` if any hook is touched.

## 8. Original Success Criteria and Outcome

| Criterion | Outcome |
|---|---|
| `ai-toolkit install --local --editors dsh` creates the workspace without manual editing | Not delivered; moved to the replacement plan |
| One session runs Claude Max, ChatGPT-backed Codex, and Gemini without provider API keys | Delivered with Gemini hosted through GitHub Copilot rather than a Google login |
| `validate.py --strict` and `audit_skills.py --ci` pass | Delivered for the standalone repositories; native target coverage remains in the replacement plan |
| Uninstall preserves user-authored files | Not applicable until ai-toolkit owns DSH artifacts; moved to the replacement plan |
| DSH remains opt-in | Delivered by separate packages and retained as a requirement of the replacement plan |

## 9. Risks and Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Upstream breaking changes (declared developer preview) | Generators break for users mid-release | Keep dsh strictly opt-in; never in `--editors all` defaults until it leaves preview |
| Anthropic changes its stance on spawned-CLI orchestration | Phase 0 premise invalidated | Fall back to ACP in JetBrains/Zed, where each agent owns its own auth by design |
| Preset schema churn | Phase 2 rework | Emit the minimum viable composition; keep display metadata in `preset.yml` where the contract is narrow and stable |
| Documentation drift across the nine mandated files | Broken user trust, per CLAUDE.md | Phase 5 is one atomic change with `validate.py --strict` as the gate |
| Silent skill loss from fail-closed frontmatter | Skills vanish with only a warning | Phase 1 gates land before phase 2 |

## 10. Pre-Mortem

*It is six months out and this failed. What happened?*

1. **We shipped dsh in the default editor set.** An upstream breaking change broke `install` for
   every toolkit user, not just dsh users. Prevented by success criterion 5.
2. **Phase 0 was skipped.** Phases 1-5 were built on the assumption that Max authenticates through
   the spawned CLI, and it turned out to require an API key in practice. Prevented by making Q5 a
   hard gate.
3. **We mapped 44 agents onto 44 presets.** The preset surface is a session composition, not a
   persona, so the emission produced 44 near-identical compositions nobody could maintain.
   Prevented by section 3.2.
4. **We became Cordis contributors.** Time went into upstream plugin work instead of the toolkit.
   Prevented by treating dsh as an emission target with a fixed contract surface, never a fork.
5. **A frontmatter regression silently dropped skills.** Nobody noticed because discovery only
   warns. Prevented by phase 1.

## 11. Archived Next Actions

No work should continue from this archived document. Implement only the scoped native install target in [`kb/planning/dsh-native-install-target-plan.md`](../../planning/dsh-native-install-target-plan.md). Reopen this record only if evidence about the 2026-08-26 validation needs correction.

## Sources

- `deepseek-ai/deepseek-harness` @ `b150a55`, `0.1.1-rc.2`, MIT: `packages/skill/skill-filesystem`,
  `packages/preset/agent-presets`, `packages/subagent/*`, `docs/`
- https://github.com/deepseek-ai/deepseek-harness
- https://deepseek.com/harness/en/
- `kb/reference/opencode-compatibility.md`: precedent for the emission-target contract
- `kb/reference/codex-cli-compatibility.md`: `.agents/skills` precedent
- `kb/reference/supported-tools-registry.md`

## Related

- `kb/reference/opencode-compatibility.md`
- `kb/reference/codex-cli-compatibility.md`
- `kb/reference/architecture-overview.md`
- `kb/reference/supported-tools-registry.md`
