---
title: "SOP: Release Verification"
category: procedures
service: ai-toolkit
tags: [sop, verification, release, smoke-test, install, update, qa]
version: "1.1.0"
created: "2026-04-08"
last_updated: "2026-04-08"
description: "End-to-end smoke test after installing or updating @softspark/ai-toolkit — verifies CLI, install, doctor, validation, tests, and eject from user perspective."
---

# SOP: Release Verification

End-to-end smoke test after installing or updating `@softspark/ai-toolkit`.
Verifies all critical paths from the user's perspective.

**Use this SOP when:**
- After `npm install -g @softspark/ai-toolkit@latest`
- After `ai-toolkit update`
- Before tagging a new version (`git tag`)
- Before publishing to npm (`npm publish`)
- As a smoke test in CI/CD

**Prerequisites:**
- Node.js >= 18, Python 3, `bats`, git
- `@softspark/ai-toolkit` installed globally

**Time:** 10-15 minutes (full), 2 minutes (quick checklist)

---

## Quick Checklist (TL;DR)

9 commands — if all pass, the release is ready:

```bash
# Pre-commit (Phase 0)
python3 scripts/generate_agents_md.py > AGENTS.md   # 1. Regenerate artifacts
python3 scripts/generate_llms_txt.py > llms.txt      # 2. Regenerate llms.txt
python3 scripts/validate.py --strict                 # 3. Validation passed?
npm test                                             # 4. All tests passed?

# Post-install verification (Phases 1-7)
ai-toolkit --version                                 # 5. Version OK?
ai-toolkit status                                    # 6. Status OK?
ai-toolkit doctor                                    # 7. Health check passed?
ai-toolkit install --dry-run                         # 8. Global install OK?
python3 scripts/audit_skills.py --ci                 # 9. Security audit clean?
```

---

## Phase 0: Pre-Commit & Pre-Push (2 min)

Run these commands **before every commit and push to main**. CI validates
counts but does NOT auto-regenerate — you must do it locally.

```bash
# 1. Regenerate generated artifacts
python3 scripts/generate_agents_md.py > AGENTS.md
python3 scripts/generate_llms_txt.py > llms.txt
python3 scripts/generate_llms_txt.py --full > llms-full.txt

# 2. Validate everything (catches stale counts, missing assets)
python3 scripts/validate.py --strict

# 3. Security audit
python3 scripts/audit_skills.py --ci

# 4. Run tests
npm test

# 5. Stage and commit
git add AGENTS.md llms.txt llms-full.txt
git add -p  # stage your other changes
git commit -m "feat: your change description"
```

**Why local?** Branch protection on `main` requires PRs and status checks.
CI cannot push directly to `main`, so generated artifacts must be committed
by the developer as part of their PR.

**One-liner (copy-paste):**
```bash
python3 scripts/generate_agents_md.py > AGENTS.md && python3 scripts/generate_llms_txt.py > llms.txt && python3 scripts/generate_llms_txt.py --full > llms-full.txt && python3 scripts/validate.py --strict && python3 scripts/audit_skills.py --ci && npm test
```

---

## Phase 1: CLI & Version (1 min)

```bash
ai-toolkit --version
ai-toolkit --help
which ai-toolkit
```

**Verify:**
- [ ] `--version` returns correct semver (e.g., `1.3.15`)
- [ ] `--help` displays full command list without errors
- [ ] `which` points to global npm bin path

---

## Phase 2: Global Install & Status (2 min)

```bash
ai-toolkit install --dry-run
ai-toolkit status
```

**Verify `--dry-run`:**
- [ ] Agents >= 40
- [ ] Skills >= 80
- [ ] Hooks merged into settings.json
- [ ] "Other AI Tools" section lists cursor, windsurf, gemini, augment (antigravity via --local)

**Verify `status`:**
- [ ] Version matches expected
- [ ] Profile: minimal/standard/strict
- [ ] Modules: list of installed modules
- [ ] Latest: up to date / update available

---

## Phase 3: Doctor Health Check (1 min)

```bash
ai-toolkit doctor
```

**Expected sections (all OK):**
- Environment: node, bash, python3, bats
- Global Install: .claude exists, agents/skills symlinks (0 broken), settings.json hooks
- Hook Scripts: all present and executable
- Hook Configuration: 12 events registered
- Generated Artifacts: AGENTS.md, llms.txt, llms-full.txt
- Planned Assets: plugin.json, benchmarks, plugin packs
- Benchmark Freshness: < 30 days
- Stale Rules: all healthy

**Verify:**
- [ ] `Errors: 0 | Warnings: 0`
- [ ] `HEALTH CHECK PASSED`

If doctor detects problems: `ai-toolkit doctor --fix` auto-repairs
(broken symlinks, non-executable hooks, missing scripts, missing llms-full.txt).

---

## Phase 4: Local Install (2 min)

```bash
mkdir -p /tmp/ai-toolkit-verify && cd /tmp/ai-toolkit-verify
git init -q
ai-toolkit install --local --dry-run
cd - && rm -rf /tmp/ai-toolkit-verify
```

**Verify "Project-local" section:**
- [ ] Would create: CLAUDE.md
- [ ] Would create: .claude/settings.local.json
- [ ] Would inject: .claude/constitution.md
- [ ] Would inject: .github/copilot-instructions.md
- [ ] Would inject: .clinerules, .roomodes, .aider.conf.yml
- [ ] Would generate: .agent/rules/ and .agent/workflows/ (Antigravity)
- [ ] Would install: .git/hooks/pre-commit
- [ ] Would inject language rules (auto-detected)

---

## Phase 5: Validation & Security Audit (3 min)

```bash
python3 scripts/validate.py --strict
python3 scripts/audit_skills.py --ci
```

**Verify validate.py:**
- [ ] Agents >= 40, Skills >= 80, Tests >= 350
- [ ] Hook events: 12, Hook scripts: >= 20
- [ ] Plugin packs >= 10, KB documents >= 20
- [ ] `Errors: 0 | Warnings: 0` → `VALIDATION PASSED`

**Verify audit_skills.py:**
- [ ] `HIGH: 0` (MUST be zero — CI fails otherwise)
- [ ] `WARN: 0`
- [ ] `INFO: N` (acceptable — broad-access skills: orchestrate, swarm, teams)

---

## Phase 6: Tests (3-5 min)

```bash
npm test
```

**Verify:**
- [ ] Bats runs tests in parallel (4 jobs)
- [ ] All `ok` — zero `not ok`
- [ ] Groups: agents, autodetect, cli, generators, guards, hooks, inject,
      install, kb, mcp, readme, profiles, uninstall, validate

**Key test areas:**
- Guards: rm -rf, DROP TABLE, git push --force blocked
- Install: idempotent, profiles, --only/--skip, orphan cleanup
- Eject: real files (not symlinks), inlined rules
- Uninstall: removes toolkit, preserves user content

---

## Phase 7: Eject (1 min)

```bash
mkdir -p /tmp/ai-toolkit-eject-test
cd /tmp/ai-toolkit-eject-test
ai-toolkit eject
cd - && rm -rf /tmp/ai-toolkit-eject-test
```

**Verify:**
- [ ] Agents copied as real files (not symlinks)
- [ ] Skills copied as real directories
- [ ] Rules inlined into CLAUDE.md
- [ ] constitution.md and ARCHITECTURE.md copied

---

## Troubleshooting

### `ai-toolkit: command not found`

```bash
npm install -g @softspark/ai-toolkit
# or check PATH:
export PATH="$(npm config get prefix)/bin:$PATH"
```

### Doctor: broken symlinks

```bash
ai-toolkit doctor --fix    # auto-repair
ai-toolkit update          # or full re-install
```

### Tests fail: missing bats

```bash
brew install bats-core     # macOS
npm install -g bats        # cross-platform
```

### validate.py: stale counts

README badges don't match the current agents/skills/tests counts.
Update README.md and re-run.

### Eject: missing skills

```bash
ai-toolkit update          # re-link missing symlinks
ai-toolkit eject /tmp/test # retry
```

---

## Success Criteria

| Area | Criterion |
|------|-----------|
| CLI | `--version` correct, `--help` full list, `status` current |
| Health | `doctor`: 0 errors, 0 warnings, PASSED |
| Install | `--dry-run` correct counts, `--local` all configs |
| Quality | `validate.py --strict`: PASSED |
| Security | `audit_skills.py --ci`: 0 HIGH |
| Tests | `npm test`: N/N passed, 0 failures |
| Eject | Standalone .claude/ with real files |
| Guards | Destructive commands blocked |
