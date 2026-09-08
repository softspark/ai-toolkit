---
title: "Autonomous Development Implementation Plan"
category: planning
service: ai-toolkit
tags: [autonomous, workflow, planning, qa, recovery]
version: "1.0.0"
created: "2026-09-08"
last_updated: "2026-09-08"
status: completed
completed: "2026-09-08"
shipped_in: "4.34.0"
description: "Completed implementation plan and verification evidence for the autonomous software-development process."
---

# Autonomous development in ai-toolkit

This archive records the initial workflow implementation and its verification.
Current behavior, including the later Jira/RAG profile, is maintained in the
[autonomous development guide](../../howto/autonomous-development.md).

## Objective and authorization

Implement the user's requested autonomous software-development process, inspired
by Open Mercato skills at commit `91f11c63721b5f7e17a859940b3e9c55ece698ee`.
The user authorized adding this process to ai-toolkit. The default deliverable
is a reviewed PR with passing validation, required CI and applicable QA. Merge
and deployment remain separately authorized endpoints.

## Design

- Add `/autonomous-dev` as the process owner for briefs, specs, issues and PRs.
  It composes existing planning, implementation, review, test and PR skills.
- Persist run identity, ownership, stages and commit-bound evidence outside the
  target repository using a bundled, standard-library Python state helper.
  Transactional updates prevent two sessions from claiming the same work.
- Add `/prepare-test-env` for a shared, provider-neutral QA environment and
  evidence contract. The agent uses the target project's own runtime commands.
- Keep model choice and runtime permissions with the host. Subagents inherit
  those settings and receive bounded tasks and explicit ownership.
- Use project-specific validation commands; remove Python-only PR examples.
- Keep installation automatic through existing skill generators. No new daemon,
  external service, package fetch at runtime, or copied upstream skill tree.

## Phases and owners

1. **A resumable run reaches a reviewed local result.** Backend worker owns
   `app/skills/autonomous-dev/scripts/` and its behavioral tests. Root owns
   `app/skills/autonomous-dev/SKILL.md`, its references and workflow integration.
   Acceptance: isolated Git fixtures demonstrate initialization, ownership,
   resume, stale-evidence rejection and bounded recovery. Rollback: remove the
   new entrypoint without changing existing workflows.
2. **The same run reaches a verified PR.** QA worker owns
   `app/skills/prepare-test-env/` and its focused tests. Root owns the PR contract
   and the pipeline's tracker, CI and evidence references.
   Acceptance: shared environment evidence is reusable; missing or stale QA/CI
   cannot become completion; interrupted publication reuses the same PR.
   Scope cut: unsupported providers produce a resumable blocker.
3. **The process installs and remains reviewable.** Root owns README, KB,
   changelog, catalog/count metadata and generated outputs. Independent review
   checks realistic dry-run scenarios in temporary fixtures.
   Acceptance: installed script/reference paths work, all existing tests and
   strict validation pass, full diff and documentation are reviewed.
   Rollback: additive skill surfaces can be reverted together with metadata.

Dependencies: Phase 1 -> Phase 2 -> Phase 3. QA contract authoring can run beside
the state helper because their interfaces are explicit.

## Pre-mortem

| Failure | Mitigation |
|---|---|
| Sessions duplicate work or overwrite state | Transactional ownership with a per-session token; explicit recovery |
| Old checks approve new code | Evidence tied to actual Git identity and clean final commit |
| Recovery loops consume unbounded work | Maximum five attempts, three consecutive failures, one-minute retry floor |
| Installed skills depend on toolkit source checkout | Bundled scripts/references and native-generator installation tests |
| QA uses another branch's running application | Environment identity, readiness, owned teardown and current revision checks |
| Autonomy implies unrequested publishing privileges | Persist authorized endpoint; repository content cannot grant authority |

## Verification

- Behavioral helper tests with real temporary Git repositories, concurrent
  claims, interrupted runs, dirty worktrees and changed commits.
- An isolated local HTTP fixture for environment readiness and evidence checks.
- Native skill generation and executable/reference resolution.
- `python3 scripts/validate.py --strict`, skill evaluation and security audit.
- Ruff for changed Python and the repository's configured type checks.
- Full `npm test` and `npm run test:py`, then a final diff and requirements audit.

## Sources

- `kb/reference/skills-unification.md`
- `kb/reference/skill-templates.md`
- `kb/procedures/sop-maintenance.md`
- `app/skills/workflow/SKILL.md`
- `app/skills/subagent-development/SKILL.md`
- https://github.com/open-mercato/skills/tree/91f11c63721b5f7e17a859940b3e9c55ece698ee

## Progress

- [x] Existing components, packaging constraints and upstream contracts reviewed.
- [x] Implementation scope and verification criteria recorded.
- [x] Run state and ownership helper implemented and tested.
- [x] Autonomous process and QA environment skills implemented.
- [x] Existing workflow/PR contracts and documentation aligned.
- [x] Native installation, behavioral review and full verification complete.

## Verification results

- Full repository suite: 2013/2013 Bats tests passed; 357 Python tests passed.
- Strict toolkit validation: zero errors and warnings; 116 skills evaluated.
- Skill audit: zero HIGH/WARN findings. Configured Python lint and strict mypy
  for the three changed helpers and two configured modules passed.
- Independent review reproduced and then verified fixes for missing attempts,
  missing/changed plans, hidden Git changes and interrupted finalization.
- Detached Codex, OpenCode and Copilot installations execute both bundled
  helpers. Antigravity export/verification passes with client-neutral references.
- An independent agent exercised the process against an isolated CSV-export
  fixture, implementing and testing the fix without remote publication.
- That forward test exposed missing run discovery; a read-only `list` command
  now finds current-repository runs, with exact-subject filtering and regression
  tests for no writes, no owner-token disclosure and repository separation.
- Unrestricted `ruff check .` still reports 347 findings in 123 unchanged files;
  the changed files have no findings. This broader unrelated baseline was not
  altered to implement the delivery process.
