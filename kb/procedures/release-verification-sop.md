---
title: "SOP: Release Verification"
category: procedures
service: ai-toolkit
tags: [sop, verification, release, smoke-test, install, update, qa, provenance, sarif]
version: "1.4.2"
created: "2026-04-08"
last_updated: "2026-04-29"
description: "End-to-end smoke test after installing or updating @softspark/ai-toolkit — verifies CLI, install, doctor, validation, tests, eject, npm provenance attestation, SARIF audit, and per-skill permissions. Reflects the v2.8.0 supply-chain standard. v1.3.0 added the single-run npm test discipline; v1.4.0 adds v3.0.0 deep-coverage checks (--profile full, --codex-skills, breaking-change surfaces, idempotence, registry drift, live-JSON parse) and refreshes stale thresholds. v1.4.2 makes the Phase 9.4 idempotence check deterministic by sorting file paths before hashing."
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

# Deep-coverage verification (Phase 9, v3.0.0+)
META="generate_agents_md.py|generate_llms_txt.py|generate_language_rules_skills.py"
diff <(grep -oE 'scripts/generate_[a-z_]+\.py' kb/reference/supported-tools-registry.md | sort -u) <(ls scripts/generate_*.py | grep -vE "$META" | sort -u) && echo "OK: registry matches"   # 14. Registry <-> generators drift?
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
- [ ] Agents >= 44
- [ ] Skills >= 99
- [ ] Hooks merged into settings.json
- [ ] "Other AI Tools" section lists documented global targets only: aider, augment, cline, codex, gemini, opencode, roo, windsurf (Cursor, Copilot, Antigravity via --local for rules)

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
- [ ] Editors: all 11 listed (copilot, cursor, windsurf, cline, roo, aider, augment, antigravity, codex, gemini, opencode)
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
- [ ] Agents >= 44, Skills >= 99, Tests >= 900
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
- [ ] `ok == expected test count` (e.g., 945 on v3.0.0)
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

## Phase 9: Deep-Coverage Checks (v3.0.0+)

These verify the native-surface generators shipped in v3.0.0 actually emit the right files for the right profiles, and that the tool registry stays in sync with shipped generators.

> **Safety warning — HOME-scoped writes:** Running `--profile full` with `augment` in the editor list writes to `$HOME/.augment/settings.json` (Augment stores hooks under HOME, not per-project). Use `--dry-run` for verification unless you intend to carry ai-toolkit hook entries on this machine. The generator is marker-safe (only rewrites its own `_source: ai-toolkit` entries) but is still a side-effect.

### 9.1 `--profile full` emits every native surface

```bash
D=/tmp/aitk-profile-full-${RANDOM} && mkdir -p "$D" && cd "$D" && git init -q
ai-toolkit install --local --editors cursor,windsurf,gemini,augment,codex \
  --profile full --codex-skills --dry-run 2>&1 \
  | grep -E "\\.cursor/(hooks\\.json|agents)|\\.windsurf/hooks\\.json|\\.gemini/(settings\\.json|commands)|\\.augment/(agents|commands)|\\.agents/skills"
```

**Verify** — at least the following lines appear:
- [ ] `.cursor/hooks.json` and `.cursor/agents/`
- [ ] `.windsurf/hooks.json`
- [ ] `.gemini/settings.json` hooks AND `.gemini/commands/`
- [ ] `.augment/agents/` + `.augment/commands/` + `$HOME/.augment/settings.json`
- [ ] `.agents/skills/` (Codex native discovery path; refreshed by `--codex-skills`)

### 9.2 `--codex-skills` is orthogonal to `--profile`

```bash
D=/tmp/aitk-codex-skills-${RANDOM} && mkdir -p "$D" && cd "$D" && git init -q
ai-toolkit install --local --editors codex --profile standard --codex-skills --dry-run 2>&1 \
  | grep -q "Would refresh: .agents/skills" && echo "OK: --codex-skills refreshes .agents/skills without --profile full"
ai-toolkit install --local --editors codex --profile full --dry-run 2>&1 \
  | grep -q "Would generate: .agents/skills" && echo "OK: Codex skills use .agents/skills at profile full"
```

**Verify:**
- [ ] `--codex-skills` refreshes `.agents/skills/` at any profile
- [ ] `--profile full` never emits `.codex/skills/`; Codex skills use `.agents/skills/`

### 9.3 Breaking-change surfaces land on `--profile standard`

v3.0.0 moved two surfaces from opt-in to default:
- Copilot directory layout (`.github/instructions/`, `.github/prompts/`)
- Gemini hooks (`.gemini/settings.json`)

```bash
D=/tmp/aitk-breaking-${RANDOM} && mkdir -p "$D" && cd "$D" && git init -q
ai-toolkit install --local --editors copilot,gemini --profile standard --dry-run 2>&1 \
  | tee /tmp/aitk-breaking.log
grep -q "\\.github/instructions/" /tmp/aitk-breaking.log && echo "OK: Copilot dir layout at standard"
grep -q "\\.gemini/settings\\.json hooks" /tmp/aitk-breaking.log && echo "OK: Gemini hooks at standard"
```

**Verify both lines print `OK:`**. If either is missing, a regression has unwound the v3.0.0 breaking change.

### 9.4 Install is idempotent

```bash
D=/tmp/aitk-idem-${RANDOM} && mkdir -p "$D" && cd "$D" && git init -q
# Sort file paths before hashing — find traversal order follows inode order,
# which can shift between runs even when content is byte-identical, producing
# false FAIL signals.
ai-toolkit install --local --editors cursor,gemini --profile full >/dev/null 2>&1
SHA1=$(find .cursor .gemini -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum | shasum | awk '{print $1}')
ai-toolkit install --local --editors cursor,gemini --profile full >/dev/null 2>&1
SHA2=$(find .cursor .gemini -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum | shasum | awk '{print $1}')
[ "$SHA1" = "$SHA2" ] && echo "OK: idempotent" || echo "FAIL: install is not idempotent"
```

**Verify:** prints `OK: idempotent`. A second run must produce byte-identical files in every managed path.

### 9.5 Live-install JSON outputs parse

The bats suite validates JSON shape at generation time. This re-checks that what actually landed on disk after a live install parses without errors.

```bash
D=/tmp/aitk-json-${RANDOM} && mkdir -p "$D" && cd "$D" && git init -q
ai-toolkit install --local --editors cursor,windsurf,gemini,augment --profile full >/dev/null 2>&1
for f in .cursor/hooks.json .windsurf/hooks.json .gemini/settings.json $HOME/.augment/settings.json; do
  [ -f "$f" ] && python3 -c "import json; json.load(open('$f'))" && echo "OK: $f"
done
```

**Verify:** each emitted file prints `OK: <path>`. Any `json.decoder.JSONDecodeError` means the merge logic corrupted the output.

### 9.6 Registry / generator drift check

`kb/reference/supported-tools-registry.md` should enumerate every per-editor `scripts/generate_*.py` we ship. Meta-generators (`generate_agents_md.py`, `generate_llms_txt.py`) are excluded — they produce docs/artifacts, not editor configs.

```bash
META="generate_agents_md.py|generate_llms_txt.py|generate_language_rules_skills.py"
REG=$(grep -oE 'scripts/generate_[a-z_]+\.py' kb/reference/supported-tools-registry.md | sort -u)
FS=$(ls scripts/generate_*.py | grep -vE "$META" | sort -u)
diff <(echo "$REG") <(echo "$FS") && echo "OK: registry matches filesystem" || echo "DRIFT: update supported-tools-registry.md"
```

**Verify:** prints `OK: registry matches filesystem`. If not, add the missing rows to the registry before tagging the next release.

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
| Deep coverage | `--profile full` emits all 9 v3.0.0 native surfaces; `--codex-skills` works orthogonally |
| Breaking changes | Copilot directory layout + Gemini hooks emit at `--profile standard` (v3.0.0 contract) |
| Idempotence | Second `install` run produces byte-identical output in every managed path |
| Live JSON | Every generated `.json` file on disk parses as valid JSON |
| Registry | `supported-tools-registry.md` enumerates every `scripts/generate_*.py` we ship |
