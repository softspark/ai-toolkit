---
title: "Plan: Native DSH Install Target"
category: planning
service: ai-toolkit
tags:
  - dsh
  - deepseek-harness
  - installer
  - editor-target
  - subscriptions
  - lifecycle
  - security
doc_type: plan
status: in-progress
created: "2026-08-27"
last_updated: "2026-08-31"
approved: "2026-08-28"
started: "2026-08-28"
completion: "Phase 2 of 3 complete"
predecessor: "kb/history/completed/dsh-integration-plan-superseded.md"
description: "Implementation plan for an explicit ai-toolkit DSH target that emits project skills and safely manages the published dsh-codex and dsh-orchestrator packages without handling vendor credentials."
---

# Plan: Native DSH Install Target

## Status

Approved and started on 2026-08-28.

Estimated size: **L (3 to 5 days)**. The runtime integrations already exist. The remaining work is installer ownership, lifecycle safety, validation, tests, and documentation.

Predecessor: [`kb/history/completed/dsh-integration-plan-superseded.md`](../history/completed/dsh-integration-plan-superseded.md).

## Context

The subscription-backed runtime is already delivered in two standalone Apache-2.0 packages:

- `@softspark/dsh-codex@1.0.0` registers the DSH `codex` provider and delegates authentication, tools, thread state, and model execution to the locally installed Codex app server. [PATH: ../dsh-codex/package.json:3]
- `@softspark/dsh-orchestrator@1.0.0` registers bounded Claude Code and GitHub Copilot Gemini delegation through native vendor logins. It accepts no provider API keys. [PATH: ../dsh-orchestrator/README.md:7]

ai-toolkit does not expose `dsh` in its editor list, does not track DSH profile artifacts, and has no DSH-specific install, doctor, update, or uninstall contract. [PATH: bin/ai-toolkit.js:309]

The published packages currently require two explicit operations: install exact plugins into a named DSH profile, then copy `softspark-orchestrator` from the installed package into `$DSH_HOME/.agent-presets`. [PATH: ../dsh-orchestrator/README.md:75]

## Decision

The native target has two separate ownership surfaces:

1. `ai-toolkit install --local --editors dsh` emits project-owned `.agents/skills` and validates DSH compatibility. It must not mutate `$DSH_HOME`, install npm packages, or inspect vendor credentials.
2. `ai-toolkit dsh install --profile web` is the explicit profile mutation command. It installs exact reviewed package versions, copies the released preset, and records ownership in the existing ai-toolkit state model.

This split preserves the meaning of `--local`. It also makes global DSH changes impossible without a command that names DSH and the target profile.

`dsh` stays out of `--editors all`, auto-detection, default profiles, and global editor defaults while DSH remains a developer preview. Selecting `dsh` must be explicit.

## Scope

### Included

- Explicit project target under `--editors dsh`.
- Reuse of the existing `.agents/skills/<name>/SKILL.md` emission path.
- DSH-specific validation for fail-closed skill metadata and one-level discovery depth.
- Explicit `ai-toolkit dsh install`, `update`, `doctor`, and `uninstall` lifecycle commands.
- Exact installation of `@softspark/dsh-codex@1.0.0` and `@softspark/dsh-orchestrator@1.0.0` into a named DSH profile.
- Ownership-safe copy and update of `$DSH_HOME/.agent-presets/softspark-orchestrator`.
- State tracking through `~/.softspark/ai-toolkit/state.json`.
- Dry-run output, collision refusal, rollback, tests, registry metadata, and public documentation.

### Excluded

- Direct Google AI Pro/Ultra, Gemini CLI OAuth, Antigravity, or Gemini API integration.
- Provider API keys, custom OAuth, token copying, credential-file reads, or login automation.
- Mapping all 44 ai-toolkit agents into DSH subagents.
- A new DSH skill generator. DSH already consumes `.agents/skills`.
- Automatic DSH installation from `--editors all`, auto-detection, or default install profiles.
- Rewriting the released dsh-codex or dsh-orchestrator packages inside ai-toolkit.
- MCP and hook bridging in the first native-target release.
- Support for arbitrary DSH prereleases or unpinned community package versions.

## Global Success Criteria

- [x] `ai-toolkit install --local --editors dsh` emits the complete managed skill catalog and makes no write under `$DSH_HOME`.
- [x] `ai-toolkit dsh install --profile web` installs both exact 1.0.0 packages and the released preset without manual file editing.
- [x] Install, update, doctor, and uninstall preserve user-authored presets and unrelated DSH plugins.
- [x] No command accepts, reads, copies, logs, or forwards provider credentials.
- [x] `dsh` remains excluded from `--editors all`, auto-detection, default profiles, and default global editors.
- [x] Offline, missing-runtime, collision, partial-install, and interrupted-update paths fail without leaving untracked artifacts.
- [ ] The full repository test, validation, skill-audit, and documentation gates pass.

## Phase 1: Project Target and Fail-Closed Gates

Dependency: none.

Size: **M (1 to 2 days)**.

### Phase 1 Success Criteria

- [x] CLI help and validation accept `dsh` only when named explicitly.
- [x] `--editors all` resolves to the existing stable editor set and excludes `dsh`.
- [x] Dry-run lists `.agents/skills` changes but writes nothing.
- [x] Project installation emits every managed skill at one discovery level.
- [x] Validation rejects camel-case invocation fields, non-boolean invocation values, invalid skill directory names, and nested `SKILL.md` locations.
- [x] A read-only doctor check reports DSH, Codex, Claude Code, and Copilot executable availability without opening credential stores.

### Phase 1 Completion Evidence

Completed on 2026-08-28 after sequential TDD, three spec review passes, and four quality-review repair cycles.

- Full repository suite: 1726/1726 tests.
- Final spec review: 10/10 requirements approved.
- Final quality review: 0 Critical, 0 Important.
- Strict validator: 0 errors, 0 warnings.
- Skill audit: 0 HIGH, 0 WARN.
- DSH remains explicit-only, project-local, credential-blind, transactionally owned, and outside Phase 2 profile lifecycle behavior.

### Phase 1 Tasks

| ID | Outcome | Affected files | Owner | Depends on |
|---|---|---|---|---|
| P1.1 | Add an explicit-only DSH editor capability separate from the stable `ALL_EDITORS` expansion | `bin/ai-toolkit.js`, `scripts/install.py`, `scripts/install_steps/ai_tools.py` | `backend-specialist` | none |
| P1.2 | Reuse the managed Codex skill emitter for the DSH project surface without emitting unrelated Codex configuration | `scripts/generate_codex_skills.py`, `scripts/install_steps/ai_tools.py` | `backend-specialist` | P1.1 |
| P1.3 | Enforce the DSH fail-closed metadata, name, and depth contract | `scripts/validate.py`, `tests/test_metadata_contracts.bats`, `tests/test_skills_native.bats` | `backend-specialist` | none |
| P1.4 | Add read-only runtime and version diagnostics with no login automation | `scripts/doctor.py`, `tests/test_doctor_fix.bats`, `tests/test_dsh.bats` | `infrastructure-validator` | P1.1 |
| P1.5 | Cover explicit selection, `all` exclusion, dry-run, idempotency, and project-only writes | `tests/test_dsh.bats`, `tests/test_install.bats`, `tests/test_install_profiles.bats` | `test-engineer` | P1.1, P1.2, P1.3, P1.4 |

### Phase 1 Rollback and Scope Cut

Remove the explicit `dsh` selector and its focused tests. Existing Codex skill emission and both standalone DSH packages remain unchanged. If the fail-closed metadata gates reveal unrelated invalid skills, fix those skills before shipping rather than weakening the gate.

## Phase 2: Explicit DSH Profile Lifecycle

Dependency: Phase 1 → Phase 2.

Size: **M (1 to 2 days)**.

### Phase 2 Success Criteria

- [x] `ai-toolkit dsh install --profile web` performs preflight before the first mutation.
- [x] The command installs exact reviewed package versions through the DSH plugin manager.
- [x] The preset is copied from the installed orchestrator package, not reconstructed by ai-toolkit.
- [x] Existing user-owned preset or plugin collisions stop the command with an actionable error.
- [x] State records the DSH home, profile, package versions, preset path, and managed content hash without recording credentials.
- [x] Update replaces only artifacts whose ownership and previous hash match state.
- [x] Uninstall removes only ai-toolkit-managed DSH artifacts and leaves unrelated profile content unchanged.
- [x] Interrupted or failed installation restores the pre-operation state or reports a deterministic recovery command.

### Phase 2 Completion Evidence

Completed on 2026-08-31 after adversarial transaction, concurrency, rollback, path-swap, state-CAS, and credential-boundary testing.

- Full repository suite on the final isolated DSH scope: 1846/1846 tests.
- Phase 2 spec review: approved with zero must-fix gaps.
- Defensive security review: approved with zero findings.
- Code quality review: 0 Critical, 0 Important, 0 Suggestions.
- Strict validator: 0 errors, 0 warnings on the verified DSH tree.
- Skill audit: 0 HIGH, 0 WARN.
- Exact reviewed pins remain DSH `0.1.1-rc.2`, dsh-codex `1.0.0`, and dsh-orchestrator `1.0.0`.
- Lifecycle state stores canonical package and preset ownership metadata without credentials or package contents.

### Phase 2 Tasks

| ID | Outcome | Affected files | Owner | Depends on |
|---|---|---|---|---|
| P2.1 | Freeze the pinned DSH plugin add, update, and removal contract against DSH `0.1.1-rc.2` in bounded fixtures | `scripts/install_steps/dsh.py`, `tests/fixtures/dsh/`, `tests/test_dsh.bats` | `backend-specialist` | Phase 1 |
| P2.2 | Implement explicit profile install, update, doctor, and uninstall dispatch with `web` as the documented default profile | `bin/ai-toolkit.js`, `scripts/install.py`, `scripts/install_steps/dsh.py`, `scripts/uninstall.py` | `command-expert` | P2.1 |
| P2.3 | Extend state tracking with DSH profile and managed-preset ownership | `scripts/install_steps/install_state.py`, `kb/reference/manifest-install.md`, `tests/test_install_state.bats` | `backend-specialist` | P2.1 |
| P2.4 | Add atomic preset copy, collision refusal, hash verification, and recovery behavior | `scripts/install_steps/dsh.py`, `tests/test_dsh.bats`, `tests/test_uninstall_recovery.bats` | `backend-specialist` | P2.2, P2.3 |
| P2.5 | Audit command construction, environment filtering, logs, and state for credential exposure | `scripts/install_steps/dsh.py`, `scripts/uninstall.py`, `tests/test_dsh.bats` | `security-auditor` | P2.2, P2.4 |
| P2.6 | Exercise clean install, repeat install, update, collision, offline, interruption, and uninstall with fake DSH binaries and isolated roots | `tests/test_dsh.bats`, `tests/test_uninstall_ai_tools.bats`, `tests/fixtures/dsh/` | `test-engineer` | P2.2, P2.3, P2.4, P2.5 |

### Phase 2 Rollback and Scope Cut

Disable the lifecycle subcommand while retaining the Phase 1 project target and read-only doctor output. Users can continue following the standalone package installation guides. Never recover from a lifecycle bug by deleting an unowned preset or profile.

## Phase 3: Registry, Documentation, and Release Qualification

Dependency: Phase 2 → Phase 3.

Size: **S to M (1 day)**.

### Phase 3 Success Criteria

- [ ] DSH has one opt-in registry entry with pinned docs and release-note sources.
- [ ] Compatibility documentation distinguishes project emission, explicit profile mutation, vendor authentication, and unsupported Google routes.
- [ ] README, CLI help, architecture, supported-tools registry, manifest install reference, and `llms.txt` describe the same commands and boundaries.
- [ ] An isolated real-profile qualification installs the two published packages, selects the released preset, and completes Codex-to-Claude plus Codex-to-Copilot-Gemini delegation.
- [ ] No release is tagged while focused tests, full tests, validation, skill audit, ShellCheck, or generated-document checks are red.

### Phase 3 Tasks

| ID | Outcome | Affected files | Owner | Depends on |
|---|---|---|---|---|
| P3.1 | Add the opt-in DSH registry and drift-monitoring contract | `scripts/ecosystem_tools.json`, `tests/test_ecosystem_doctor.bats` | `technical-researcher` | Phase 2 |
| P3.2 | Publish one compatibility contract and synchronize all user-facing command surfaces | `kb/reference/dsh-compatibility.md`, `kb/reference/supported-tools-registry.md`, `kb/reference/architecture-overview.md`, `kb/reference/manifest-install.md`, `README.md`, `CLAUDE.md`, `llms.txt`, `bin/ai-toolkit.js` | `documenter` | P3.1 |
| P3.3 | Run isolated end-to-end qualification with real DSH and published packages, then record evidence | `kb/reference/dsh-compatibility.md`, `kb/procedures/release-verification-sop.md` | `infrastructure-validator` | P3.2 |
| P3.4 | Run focused and full repository gates and assess regression blast radius | `tests/test_dsh.bats`, `tests/test_cli.bats`, `tests/test_install.bats`, `tests/test_uninstall_ai_tools.bats`, `scripts/validate.py`, `scripts/audit_skills.py` | `qa-automation-engineer` | P3.2, P3.3 |
| P3.5 | Review final security boundaries and veto release on credential or ownership regressions | `scripts/install_steps/dsh.py`, `scripts/install_steps/install_state.py`, `scripts/uninstall.py`, `kb/reference/dsh-compatibility.md`, `tests/test_dsh.bats` | `security-architect` | P3.3, P3.4 |

### Phase 3 Rollback and Scope Cut

Do not tag or publish the ai-toolkit release. Keep the already published standalone 1.0.0 packages as the supported installation route. If upstream DSH drifts during qualification, retain the registry entry as unsupported-preview metadata and remove the user-facing install command until compatibility is restored.

## Dependencies

```text
Phase 1 → Phase 2 → Phase 3
```

Within phases:

```text
P1.1 → P1.2 → P1.5
P1.3 ─────────→ P1.5
P1.4 ─────────→ P1.5

P2.1 → P2.2 → P2.4 → P2.5 → P2.6
             ↘ P2.3 ↗

P3.1 → P3.2 → P3.3 → P3.4 → P3.5
```

No phase begins until the previous phase meets its success criteria. Phase 1 can ship as project-only compatibility without Phase 2. Phase 2 can remain unreleased if real-profile qualification fails.

## Requirement Traceability

| Requirement | Tasks |
|---|---|
| Explicit DSH project target | P1.1, P1.2, P1.5 |
| DSH excluded from defaults and `all` | P1.1, P1.5 |
| Fail-closed skill discovery | P1.3, P1.5 |
| No credential handling | P1.4, P2.5, P3.5 |
| Exact package installation | P2.1, P2.2, P2.6 |
| Managed preset lifecycle | P2.3, P2.4, P2.6 |
| Ownership-safe uninstall | P2.3, P2.4, P2.6 |
| Registry and documentation parity | P3.1, P3.2 |
| Real subscription-backed smoke test | P3.3, P3.4 |
| Release blocked on red gates | P3.4, P3.5 |

## Verification

### Focused gates

```bash
bats tests/test_dsh.bats
bats tests/test_install.bats
bats tests/test_install_profiles.bats
bats tests/test_install_state.bats
bats tests/test_uninstall_ai_tools.bats
bats tests/test_uninstall_recovery.bats
```

### Repository gates

```bash
python3 scripts/validate.py --strict
python3 scripts/audit_skills.py --ci
python3 scripts/ecosystem_doctor.py
npm test
```

Run ShellCheck when a shell fixture, hook, or command wrapper changes. Run the existing generated-document drift checks before commit.

### Isolated runtime qualification

Use a new task-specific `DSH_HOME` and DSH profile. Do not replace `HOME` and do not reuse the maintainer's regular DSH profile.

Verify these observations:

1. Project installation emits the full managed skill catalog and no nested skill entry.
2. Profile installation records exact package versions and one managed preset.
3. Codex reports ChatGPT-owned authentication through its own status command.
4. Claude Code and Copilot own their login state; ai-toolkit state and logs contain no credential values.
5. A Codex parent delegates one bounded marker task to Claude Code and one to Copilot Gemini.
6. Uninstall returns the isolated profile to its pre-install inventory while preserving an injected user-owned preset fixture.

## Pre-Mortem

| Failure mode | Probability | Impact | Mitigation |
|---|---|---|---|
| Generic `install --local` mutates a global DSH profile | Medium | High | Separate project emission from the explicit `ai-toolkit dsh install` command and test zero `$DSH_HOME` writes in Phase 1 |
| `--editors all` silently gains a developer-preview runtime | Medium | High | Keep explicit-only editors in a separate registry and assert expansion output in tests |
| Preset update overwrites user edits or a same-name user preset | Medium | High | Require ownership state plus matching previous hash; refuse every ambiguous collision |
| Partial DSH plugin installation leaves one provider without the matching preset | Medium | High | Preflight all inputs, snapshot managed state, order mutations, and implement deterministic recovery |
| Installer logs or state capture vendor credentials | Low | Critical | Never invoke login flows, never read credential files, redact command output, and audit fixtures for secret-shaped data |
| DSH prerelease changes plugin or preset discovery semantics | High | High | Pin the reviewed DSH version, run ecosystem drift checks, and block release on real-profile qualification failure |
| Reusing Codex-adapted skills produces incorrect DSH delegation instructions | Medium | Medium | Validate representative delegation-heavy skills in the Codex parent and add a DSH-specific adapter only if evidence requires it |
| Copilot changes Gemini model availability or credit policy | Medium | Medium | Treat model and credit policy as doctor-visible compatibility data, not a promise hardcoded into ai-toolkit behavior |

## Agent Assignments

| Workstream | Primary agent | Review agent | Reason |
|---|---|---|---|
| CLI and installer plumbing | `backend-specialist` | `tech-lead` | Python and Node entry-point integration with existing installer layers |
| Command UX | `command-expert` | `product-manager` | Explicit mutation semantics, dry-run output, and actionable errors |
| Runtime preflight and qualification | `infrastructure-validator` | `technical-researcher` | DSH profile behavior, pinned compatibility, and observable smoke evidence |
| Security and ownership | `security-auditor` | `security-architect` | Credential boundary, collision refusal, state minimization, and release veto |
| Test automation | `test-engineer` | `qa-automation-engineer` | Fake-runtime fixtures, lifecycle integration tests, and full regression gates |
| Documentation | `documenter` | `fact-checker` | Cross-file parity and evidence-backed compatibility claims |

## Approval Checkpoint

Implementation starts only after the user approves:

1. The two-command split between project emission and explicit DSH profile mutation.
2. Excluding DSH from `--editors all` and auto-detection while upstream remains a developer preview.
3. Pinning the first native target to DSH `0.1.1-rc.2`, dsh-codex `1.0.0`, and dsh-orchestrator `1.0.0`.
4. Deferring 44-agent mapping, MCP bridging, and hook bridging outside this plan.

## Sources

- `kb/history/completed/dsh-integration-plan-superseded.md`
- `bin/ai-toolkit.js`
- `scripts/install.py`
- `scripts/install_steps/ai_tools.py`
- `scripts/install_steps/install_state.py`
- `scripts/ecosystem_tools.json`
- `/Users/lukaszkrzemien/External/WorkspaceSoftSpark/dsh-codex`
- `/Users/lukaszkrzemien/External/WorkspaceSoftSpark/dsh-orchestrator`
- <https://github.com/deepseek-ai/deepseek-harness>
