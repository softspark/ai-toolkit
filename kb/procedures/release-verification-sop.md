---
title: "SOP: Release Verification"
category: procedures
service: ai-toolkit
tags: [sop, verification, release, smoke-test, install, update, qa, provenance, sarif]
version: "1.3.0"
created: "2026-04-08"
last_updated: "2026-04-21"
description: "End-to-end smoke test after installing or updating @softspark/ai-toolkit — verifies CLI, install, doctor, validation, tests, eject, npm provenance attestation, SARIF audit, and per-skill permissions. Reflects the v2.8.0 supply-chain standard. v1.3.0 adds the single-run npm test discipline (cache to file, parse ok/not-ok once)."
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

13 commands — if all pass, the release is ready:

```bash
# Pre-commit (Phase 0)
python3 scripts/generate_agents_md.py > AGENTS.md           # 1. Regenerate AGENTS.md
python3 scripts/generate_codex_rules.py .                   # 2. Refresh standard Codex rules
python3 scripts/generate_llms_txt.py > llms.txt             # 3. Regenerate llms.txt
python3 scripts/validate.py --strict                        # 4. Validation passed?
npm test > /tmp/npm-test.log 2>&1 && grep -c '^ok ' /tmp/npm-test.log && ! grep -q '^not ok' /tmp/npm-test.log  # 5. All tests passed? (single run, cached)

# Post-install verification (Phases 1-7)
ai-toolkit --version                                        # 6. Version OK?
ai-toolkit status                                           # 7. Status OK?
ai-toolkit doctor                                           # 8. Health check passed?
ai-toolkit install --dry-run                                # 9. Global install OK?
python3 scripts/audit_skills.py --ci                        # 10. Security audit clean?

# Supply-chain verification (Phase 8, v2.8.0+)
python3 scripts/audit_skills.py --sarif | python3 -c "import json,sys; assert json.load(sys.stdin)['version']=='2.1.0'; print('SARIF OK')"   # 11. SARIF 2.1.0 well-formed?
python3 scripts/audit_skills.py --permissions | head -30    # 12. Broad-access skills reviewed?
npm view @softspark/ai-toolkit@X.Y.Z --json | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['dist']['attestations']['provenance']['predicateType']=='https://slsa.dev/provenance/v1'; print('PROVENANCE OK')"   # 13. Provenance attested on npm?
```

---

## Phase 0: Pre-Commit & Pre-Push (2 min)

Run these commands **before every commit and push to main**. CI validates
counts but does NOT auto-regenerate — you must do it locally.

```bash
# 1. Regenerate generated artifacts
python3 scripts/generate_agents_md.py > AGENTS.md
python3 scripts/generate_codex_rules.py .
python3 scripts/generate_llms_txt.py > llms.txt
python3 scripts/generate_llms_txt.py --full > llms-full.txt

# 2. Validate everything (catches stale counts, missing assets)
python3 scripts/validate.py --strict

# 3. Security audit
python3 scripts/audit_skills.py --ci

# 4. Run tests
npm test

# 5. Stage and commit
git add AGENTS.md .agents/rules/ai-toolkit-*.md llms.txt llms-full.txt
git add -p  # stage your other changes
git commit -m "feat: your change description"
```

**Why local?** Branch protection on `main` requires PRs and status checks.
CI cannot push directly to `main`, so generated artifacts must be committed
by the developer as part of their PR.

**One-liner (copy-paste):**
```bash
python3 scripts/generate_agents_md.py > AGENTS.md && python3 scripts/generate_codex_rules.py . && python3 scripts/generate_llms_txt.py > llms.txt && python3 scripts/generate_llms_txt.py --full > llms-full.txt && python3 scripts/validate.py --strict && python3 scripts/audit_skills.py --ci && npm test
```

---

## Phase 1: CLI & Version (1 min)

```bash
ai-toolkit --version
ai-toolkit --help
which ai-toolkit
```

**Verify:**
- [ ] `--version` returns correct semver (e.g., `1.4.0`)
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
ai-toolkit install --local --editors all --dry-run
cd - && rm -rf /tmp/ai-toolkit-verify
```

**Verify "Project-local" section:**
- [ ] Would create: CLAUDE.md
- [ ] Would create: .claude/settings.local.json
- [ ] Would inject: .claude/constitution.md
- [ ] Editors: all 8 listed (copilot, cursor, windsurf, cline, roo, aider, augment, antigravity)
- [ ] Would generate configs for each editor (legacy + directory-based)
- [ ] Would install: .git/hooks/pre-commit
- [ ] Would inject language rules (auto-detected)

**Also test auto-detect (no --editors flag):**
```bash
ai-toolkit install --local --dry-run
# → Editors: none (empty project has no existing configs)
```

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
# Run ONCE, capture to file, then parse. Full suite is 669+ bats cases —
# re-running it per check (tail / grep ok / grep not ok piped separately)
# wastes minutes every release. Always cache the output.
npm test > /tmp/npm-test.log 2>&1
exit=$?
tail -3 /tmp/npm-test.log
echo "ok:     $(grep -c '^ok '    /tmp/npm-test.log)"
echo "not ok: $(grep -c '^not ok' /tmp/npm-test.log)"
echo "exit:   $exit"
```

**Verify:**
- [ ] `exit == 0`
- [ ] `ok == expected test count` (e.g., 669)
- [ ] `not ok == 0`
- [ ] Bats runs tests in parallel (4 jobs)
- [ ] Groups: agents, autodetect, cli, generators, guards, hooks, inject,
      install, kb, mcp, readme, profiles, uninstall, validate

**Anti-pattern — do NOT do this:**
```bash
# Runs the full suite THREE times. Adds 1-3 min and pressures CI capacity.
npm test 2>&1 | tail -3
npm test 2>&1 | grep -c '^ok '
npm test 2>&1 | grep -c '^not ok'
```

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
- [ ] `output-styles/` directory present (v2.7.1+)

---

## Phase 8: Supply-Chain Verification (2 min, v2.8.0+)

These checks enforce the v2.8.0 security standard on a freshly-published release. Run AFTER the `publish.yml` workflow completes on the tag.

### 8.1 Provenance attestation on npm

```bash
VERSION="X.Y.Z"                                           # the tag just published
npm view "@softspark/ai-toolkit@${VERSION}" --json \
  | python3 -c "import json, sys; d=json.load(sys.stdin); att=d['dist'].get('attestations', {}); assert att.get('provenance', {}).get('predicateType') == 'https://slsa.dev/provenance/v1', f'NO PROVENANCE for {d[\"version\"]}'; print(f'PROVENANCE OK: {att[\"url\"]}')"
```

**Verify:**
- [ ] Exit 0 and prints `PROVENANCE OK: https://registry.npmjs.org/...`
- [ ] `https://www.npmjs.com/package/@softspark/ai-toolkit/v/${VERSION}` shows the green "Provenance" badge

**If provenance is missing:** the `publish.yml` ran without `id-token: write` or `--provenance`. Restore them and cut a patch release — a silently unsigned publish is a regression against the v2.8.0 standard.

### 8.2 Audit SARIF output (for GHAS ingest)

```bash
python3 scripts/audit_skills.py --sarif > /tmp/audit.sarif
python3 -c "import json; d=json.load(open('/tmp/audit.sarif')); assert d['version']=='2.1.0' and d['runs'][0]['tool']['driver']['name']=='ai-toolkit-audit-skills'; print(f'SARIF OK: {len(d[\"runs\"][0][\"results\"])} results across {len(d[\"runs\"][0][\"tool\"][\"driver\"][\"rules\"])} rules')"
```

**Verify:**
- [ ] Valid SARIF 2.1.0
- [ ] In the publishing repo, the CI job uploads `audit.sarif` via `github/codeql-action/upload-sarif@v3` so findings appear in the Security tab

### 8.3 Per-skill permissions report

```bash
python3 scripts/audit_skills.py --permissions | head -40
```

**Verify:**
- [ ] Bash skill count has NOT jumped unexpectedly since the previous release
- [ ] Any newly added entry under `Skills with Bash + Write + Edit` matches a CHANGELOG bullet that justifies the broad scope
- [ ] JSON form (`--permissions --json`) is available for automated drift dashboards

### 8.4 URL-sourced rules/hooks are checksum-pinned

```bash
jq '.rules // .hooks // {}' ~/.softspark/ai-toolkit/rules/sources.json 2>/dev/null \
  | python3 -c "import json, sys; d=json.load(sys.stdin) or {}; bad=[n for n,v in d.items() if v.get('url') and not v.get('sha256')]; assert not bad, f'UNPINNED: {bad}'; print(f'RULE PIN OK: {len(d)} URL rules, all with sha256')"
jq '.hooks // {}' ~/.softspark/ai-toolkit/hooks/external/sources.json 2>/dev/null \
  | python3 -c "import json, sys; d=json.load(sys.stdin) or {}; bad=[n for n,v in d.items() if v.get('url') and not v.get('sha256')]; assert not bad, f'UNPINNED: {bad}'; print(f'HOOK PIN OK: {len(d)} URL hooks, all with sha256')"
```

**Verify:**
- [ ] Both commands print `... PIN OK`
- [ ] If any entry is unpinned, the `register_url_source()` call missed passing `content=` — fix the call-site and retag

### 8.5 Strict-pin smoke test (optional but recommended)

```bash
AI_TOOLKIT_STRICT_PIN=1 ai-toolkit update --dry-run
```

**Verify:**
- [ ] Exit 0, no `CHECKSUM CHANGED` line
- [ ] If a checksum change was intentional (e.g. upstream rule update), document it in the CHANGELOG entry before tagging

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
| Security (baseline) | `audit_skills.py --ci`: 0 HIGH |
| Security (SARIF) | `audit_skills.py --sarif`: valid SARIF 2.1.0 with non-empty rules array |
| Security (permissions) | `audit_skills.py --permissions`: broad-access skills unchanged or justified in CHANGELOG |
| Supply chain | `dist.attestations.provenance.predicateType == https://slsa.dev/provenance/v1` on npm |
| Supply chain | All `sources.json` URL entries carry a `sha256`; `AI_TOOLKIT_STRICT_PIN=1 ai-toolkit update --dry-run` passes |
| Tests | `npm test`: N/N passed, 0 failures |
| Eject | Standalone `.claude/` with real files AND `output-styles/` directory |
| Guards | Destructive commands blocked |
