---
title: "SOP: Release Preparation"
category: procedures
service: ai-toolkit
tags: [sop, release, version, publish, changelog, semver, provenance, sarif, ecosystem]
version: "1.10.0"
created: "2026-04-10"
last_updated: "2026-04-24"
description: "Step-by-step checklist for preparing a new ai-toolkit release — ecosystem-sync drift check, version sync, changelog, artifact regeneration, validation, and tagging. Run BEFORE every git tag. Includes mandatory Provenance, SARIF, and checksum-pin checks added in v2.8.0, the single-run npm test discipline added in v1.8.0, the ecosystem-sync gate added in v1.9.0, and the registry-vs-generators drift gate added in v1.10.0."
---

# SOP: Release Preparation

Complete checklist for preparing a new `@softspark/ai-toolkit` release.
Run this **before** tagging. After tagging and publishing, run the
[Release Verification SOP](release-verification-sop.md) to smoke-test.

**Pipeline:**
```
Ecosystem Sync SOP (drift check + generator updates)
      ↓
Release Preparation (this SOP)
      ↓
git tag → CI publish → Release Verification SOP
```

**Time:** 10-20 minutes (includes ecosystem sync review)

---

## Quick Checklist (TL;DR)

```bash
# 0. Ecosystem sync (mandatory for minor/major releases; optional for patch)
#    Full procedure: kb/procedures/ecosystem-sync-sop.md
python3 scripts/ecosystem_doctor.py --format text > /tmp/eco-report.txt
cat /tmp/eco-report.txt
# If drift detected: stop here, follow ecosystem-sync-sop.md Phase 2-4 to
# classify each drift (A-F), update generators as needed, refresh snapshot,
# THEN resume this SOP.
python3 scripts/ecosystem_doctor.py --update    # after all drift resolved

# 1. Decide version bump
#    patch (1.4.2 → 1.4.3): bugfix, typo, doc fix
#    minor (1.4.2 → 1.5.0): new feature, new skill, new flag, any ecosystem-class-B/F change
#    major (1.4.2 → 2.0.0): breaking change, any ecosystem-class-D removed path

# 2. Sync version across all files
python3 scripts/sync_version.py X.Y.Z          # if script exists, else manual

# 3. Write CHANGELOG.md entry
# 4. Regenerate artifacts
python3 scripts/generate_agents_md.py > AGENTS.md
python3 scripts/generate_codex_rules.py .
python3 scripts/generate_llms_txt.py > llms.txt
python3 scripts/generate_llms_txt.py --full > llms-full.txt

# 5. Validate + audit + SARIF + test + ecosystem check
python3 scripts/validate.py --strict && python3 scripts/audit_skills.py --ci && python3 scripts/audit_skills.py --sarif > /tmp/audit.sarif && npm test

# 5a. Supply-chain standard (v2.8.0+) — non-negotiable
grep -q -- '--provenance' .github/workflows/publish.yml || { echo "MISSING --provenance"; exit 1; }
grep -q 'id-token: write'   .github/workflows/publish.yml || { echo "MISSING id-token: write"; exit 1; }
python3 scripts/audit_skills.py --permissions   # review Bash/Write/Edit footprint

# 5b. Ecosystem gate — snapshot must be current before tag
python3 scripts/ecosystem_doctor.py --offline --check || { echo "STALE ecosystem snapshot — re-run doctor"; exit 1; }

# 6. Commit + tag + push
git add -A && git commit -m "chore: release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

---

## Phase 0: Ecosystem Sync (MANDATORY for minor/major)

Before touching version numbers, confirm the toolkit is aligned with the current state of every editor / platform it integrates with. Skipping this phase ships a release whose generators may lag a month-old CLI refactor, a rename of `.cursorrules` to `.cursor/rules/`, or a new hook event we do not yet emit.

**When this phase is mandatory:**
- Minor release (X.Y.0) — always
- Major release (X.0.0) — always
- Patch release (X.Y.Z) — only if the patch touches a generator or install flow

**When to skip:** pure doc-only patches, SOP edits, internal refactors that do not touch `scripts/generate_*` or `app/skills/*/SKILL.md`.

### 0.1 Run the doctor

```bash
python3 scripts/ecosystem_doctor.py --format text | tee /tmp/eco-report.txt
```

Output classifies every registered tool as **Clean**, **Drift**, or **Errored**.

### 0.2 Act on drift

For each drifting tool, follow [ecosystem-sync-sop.md](ecosystem-sync-sop.md) Phase 2-4:

| Drift class | Release impact |
|-------------|----------------|
| A (cosmetic reword) | No version impact — refresh snapshot, continue |
| B (new feature — integrate) | **Minor** version bump at minimum; new generator or extended generator |
| C (new feature — not adopted) | No impact — note in registry |
| D (deprecation) | **Minor** or **major** depending on user impact; add migration warning |
| E (feature promoted to default) | **Minor**; simplify generator, keep fallback comment |
| F (feature newly globally available) | **Minor**; may require new generator or new config path |

If any B/D/E/F changes land in this preparation pass, mention them explicitly in the CHANGELOG entry (Phase 3) under a `Ecosystem` subsection.

### 0.3 Refresh snapshot

Once every drift is resolved (either by code change or by re-classifying as acceptable):

```bash
python3 scripts/ecosystem_doctor.py --update
```

This writes the new baseline to `benchmarks/ecosystem-doctor-snapshot.json`. Commit it as part of the release commit.

### 0.4 Gate

```bash
python3 scripts/ecosystem_doctor.py --offline --check
```

Must exit `0`. If it exits `1`, the snapshot is stale — rerun Phase 0.3 or review the remaining drift.

---

## Phase 1: Determine Version Bump

Follow [Semantic Versioning](https://semver.org/):

| Change Type | Bump | Examples |
|-------------|------|---------|
| Bugfix, typo, doc-only | **patch** | Fix install flag, correct description |
| New feature, skill, agent, flag | **minor** | Add `/hipaa-validate`, add `--output json` |
| Breaking CLI change, removed skill, config format change | **major** | Rename `install` to `setup`, remove skill |

**Rule:** When in doubt, bump minor.

---

## Phase 2: Sync Version in All Files

The canonical version lives in `package.json`. These files **must** match:

### Mandatory sync (every release)

| File | Field | How to update |
|------|-------|---------------|
| `package.json` | `"version": "X.Y.Z"` | Edit directly |
| `manifest.json` | `"version": "X.Y.Z"` | Edit directly |
| `app/.claude-plugin/plugin.json` | `"version": "X.Y.Z"` | Edit directly |

### Auto-synced (no manual action)

| File | Mechanism |
|------|-----------|
| `package-lock.json` | Regenerated by `npm install --package-lock-only` |

### Conditional sync (only if the doc was modified in this release)

| File | Field | When to update |
|------|-------|---------------|
| `kb/procedures/maintenance-sop.md` | frontmatter `version:` | If SOP content changed |
| `kb/reference/skills-catalog.md` | frontmatter `version:` | If skills added/removed |
| `kb/reference/agents-catalog.md` | frontmatter `version:` | If agents added/removed |
| `kb/reference/hooks-catalog.md` | frontmatter `version:` | If hooks changed |
| `kb/reference/architecture-overview.md` | frontmatter `version:` | If architecture changed |
| `kb/reference/distribution-model.md` | frontmatter `version:` | If install model changed |
| `kb/reference/global-install-model.md` | frontmatter `version:` | If install model changed |

> **Note:** KB `version:` fields track the **document version**, not the toolkit version.
> Only bump them when the document content actually changes in this release.

### Count sync (if skills/agents/hooks changed)

| File | What to check |
|------|---------------|
| `package.json` | `"description"` — skill/agent count |
| `README.md` | Badge counts, "What You Get" table |
| `app/ARCHITECTURE.md` | Section headings with counts |

> **Tip:** `validate.py --strict` catches count drift AND version mismatches
> (package.json vs manifest.json vs plugin.json) automatically.
> If validation passes, counts and versions are correct.

### Verification command

After syncing, verify all mandatory files match:

```bash
VERSION=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")
echo "Target: $VERSION"
echo "manifest.json:     $(python3 -c "import json; print(json.load(open('manifest.json'))['version'])")"
echo "plugin.json:       $(python3 -c "import json; print(json.load(open('app/.claude-plugin/plugin.json'))['version'])")"
echo "package-lock.json: $(python3 -c "import json; print(json.load(open('package-lock.json'))['version'])")"
```

All four must print the same version. If not, fix before proceeding.

---

## Phase 3: Write CHANGELOG Entry

Add entry at the top of `CHANGELOG.md` (after the header, before previous release):

```markdown
## vX.Y.Z — Short Title (YYYY-MM-DD)

### Added
- **Feature name** — description

### Changed
- **What changed** — old behavior → new behavior

### Fixed
- **Bug description** — what was broken and how it's fixed

### Removed
- **What was removed** — migration path if any
```

**Rules:**
- Use **bold** for feature names
- Start descriptions with a verb (Added, Changed, Fixed, Removed)
- Reference skill names with backticks and slash: `/hipaa-validate`
- Include script names: `scripts/hipaa_scan.py`
- Include count changes: `Skill count: 91 → 92`
- Date format: `YYYY-MM-DD`
- Title: short, descriptive, no version number repetition

### Update README "What's New" section

**MANDATORY on every release.** Update the `## What's New in vX.Y.Z` section in `README.md`:

1. Change the heading version: `## What's New in vX.Y.Z`
2. Replace bullet points with 3-5 highlights from this release
3. **Keep only the latest version block.** Delete the previous `## What's New in vA.B.C` section(s). README is the shop window, not the archive — users see the current release, full history lives in `CHANGELOG.md`.
4. Keep the `See [CHANGELOG.md](CHANGELOG.md) for full history.` link directly below the bullet list.

> **Warning:** This section is the first thing users see after the badges.
> A stale version here (e.g., "What's New in v2.1.3" when shipping v2.3.0)
> signals an unmaintained project. Do NOT skip this step.

> **Single-version rule:** README.md must contain **exactly one** `## What's New in vX.Y.Z` heading at any time. If you find multiple stacked (e.g. v2.6.1 + v2.6.0 + v2.5.0), that is a SOP drift — collapse to the latest on the next release commit.

---

## Phase 4: Regenerate Artifacts

```bash
python3 scripts/generate_agents_md.py > AGENTS.md
python3 scripts/generate_codex_rules.py .
python3 scripts/generate_llms_txt.py > llms.txt
python3 scripts/generate_llms_txt.py --full > llms-full.txt
```

Check if anything actually changed:

```bash
git diff --stat AGENTS.md llms.txt llms-full.txt
```

If no diff, the artifacts are already current. If there is a diff, stage them.

---

## Phase 5: Validate, Audit, Test

Run the full quality gate:

```bash
python3 scripts/validate.py --strict
python3 scripts/audit_skills.py --ci
python3 scripts/audit_skills.py --sarif > audit.sarif       # MANDATORY — GHAS ingest
python3 scripts/audit_skills.py --permissions               # review Bash/Write/Edit footprint

# Registry / generator drift (added in 1.10.0). Meta-generators excluded.
META="generate_agents_md.py|generate_llms_txt.py"
diff \
  <(grep -oE 'scripts/generate_[a-z_]+\.py' kb/reference/supported-tools-registry.md | sort -u) \
  <(ls scripts/generate_*.py | grep -vE "$META" | sort -u) \
  && echo "OK: registry matches filesystem" \
  || { echo "DRIFT: update supported-tools-registry.md before tagging"; exit 1; }

# Run npm test ONCE, cache output, parse from file. The suite is 900+ bats
# cases — rerunning it per check wastes minutes. Do not pipe npm test into
# tail/grep multiple times in the same session.
npm test > /tmp/npm-test.log 2>&1
tail -3 /tmp/npm-test.log
echo "ok: $(grep -c '^ok ' /tmp/npm-test.log) | not ok: $(grep -c '^not ok' /tmp/npm-test.log)"
```

**Expected results:**
- `validate.py`: `Errors: 0 | Warnings: 0 | VALIDATION PASSED`
- `audit_skills.py --ci`: `HIGH: 0 | WARN: 0` (INFO is acceptable)
- `audit_skills.py --sarif`: valid JSON, non-empty `runs[0].tool.driver.rules`
- `audit_skills.py --permissions`: review `Skills with Bash + Write + Edit` list — any newly-added skill with broad access MUST be justified in the CHANGELOG entry
- Registry drift: `OK: registry matches filesystem`. If `DRIFT:` appears, add the missing `scripts/generate_*.py` rows to `kb/reference/supported-tools-registry.md` before tagging.
- `npm test`: `1..N` with zero `not ok` (read from the cached `/tmp/npm-test.log`, do not rerun)

**One-liner:**
```bash
python3 scripts/validate.py --strict && python3 scripts/audit_skills.py --ci && python3 scripts/audit_skills.py --sarif > audit.sarif && diff <(grep -oE 'scripts/generate_[a-z_]+\.py' kb/reference/supported-tools-registry.md | sort -u) <(ls scripts/generate_*.py | grep -vE 'generate_agents_md\.py|generate_llms_txt\.py' | sort -u) && npm test
```

**If tests fail:** Fix the issue, do NOT skip. Common failures:
- Stale counts → re-run `generate:all` or fix README/ARCHITECTURE
- Missing frontmatter → add to new KB docs
- Broken symlink → `ai-toolkit doctor --fix`

### Phase 5a: Supply-Chain Hardening Verification (v2.8.0+)

These checks enforce the security standard introduced in v2.8.0. Do NOT tag a release until all pass.

**1. Publish workflow emits provenance:**

```bash
grep -E '\-\-provenance|id-token: write' .github/workflows/publish.yml
```

- [ ] Both markers present (`--provenance` flag + `id-token: write` permission)
- [ ] Any PR that changes `publish.yml` REQUIRES an approved security review

**2. URL-sourced rules and hooks are checksum-pinned:**

```bash
# On a machine that has consumed URL rules/hooks at least once:
jq 'to_entries | map(select(.value.url != null and (.value.sha256 // "" | length) == 0))' ~/.softspark/ai-toolkit/rules/sources.json
jq 'to_entries | map(select(.value.url != null and (.value.sha256 // "" | length) == 0))' ~/.softspark/ai-toolkit/hooks/external/sources.json
```

- [ ] Both queries return empty arrays (every URL entry has a `sha256`)
- [ ] If not, run `ai-toolkit update` to backfill missing hashes before tagging

**3. Audit SARIF output is well-formed:**

```bash
python3 scripts/audit_skills.py --sarif | python3 -c "import json, sys; d=json.load(sys.stdin); assert d['version']=='2.1.0' and d['runs'][0]['tool']['driver']['name']; print('SARIF OK')"
```

- [ ] Prints `SARIF OK`
- [ ] If the script ever grows new rule classes, extend the SARIF `rules[]` coverage before releasing

**4. Strict-pin mode passes on CI** (optional, recommended for stable branches):

```bash
AI_TOOLKIT_STRICT_PIN=1 ai-toolkit update --dry-run
```

- [ ] Exit 0, no `CHECKSUM CHANGED` line
- [ ] Any unexpected upstream change blocks the release until explicitly approved

---

## Phase 6: Commit

Stage all release files:

```bash
git add package.json manifest.json app/.claude-plugin/plugin.json
git add package-lock.json
git add CHANGELOG.md
git add AGENTS.md llms.txt llms-full.txt
git add -p  # review and stage any other changes
```

Commit:

```bash
git commit -m "chore: release vX.Y.Z"
```

---

## Phase 7: Tag and Push

```bash
git tag vX.Y.Z
git push origin main --tags
```

This triggers `.github/workflows/publish.yml` which:
1. Runs `validate.py --strict`
2. Runs `npm test`
3. Publishes to npm as `@softspark/ai-toolkit@X.Y.Z` with `--provenance` (SLSA v1 build attestation)

**Provenance is non-negotiable.** If `id-token: write` permission or the `--provenance` flag is missing from `publish.yml`, fix it BEFORE tagging — an unsigned release is a regression against the v2.8.0 standard.

**After CI completes:** Run the [Release Verification SOP](release-verification-sop.md)
to smoke-test the published package AND verify the provenance attestation landed on npm.

---

## Rollback

If a bad release was published:

```bash
# Unpublish from npm (within 72h)
npm unpublish @softspark/ai-toolkit@X.Y.Z

# Or deprecate (preferred — doesn't break existing installs)
npm deprecate @softspark/ai-toolkit@X.Y.Z "Known issue: <description>. Use vA.B.C instead."

# Delete tag
git tag -d vX.Y.Z
git push origin --delete vX.Y.Z
```

---

## Checklist Summary

| # | Step | Command / Action | Pass Criteria |
|---|------|-----------------|---------------|
| 0a | Ecosystem drift check | `ecosystem_doctor.py --format text` | All tools Clean, or drift classified and resolved |
| 0b | Ecosystem snapshot refresh | `ecosystem_doctor.py --update` | `benchmarks/ecosystem-doctor-snapshot.json` updated |
| 0c | Ecosystem gate | `ecosystem_doctor.py --offline --check` | Exit 0 |
| 1 | Version bump type | Decide patch/minor/major | — |
| 2 | `package.json` version | Edit `"version"` | Matches target |
| 3 | `manifest.json` version | Edit `"version"` | Matches target |
| 4 | `plugin.json` version | Edit `"version"` | Matches target |
| 5 | `package-lock.json` | `npm install --package-lock-only` | Matches target |
| 6 | Count sync | Check `package.json` description, README | `validate.py` passes |
| 7 | CHANGELOG.md | Add release entry (incl. `Ecosystem` subsection if any B/D/E/F drift) | Entry exists for vX.Y.Z |
| 8 | Regenerate artifacts | `generate_agents_md.py`, `generate_codex_rules.py`, `generate_llms_txt.py` | No unexpected diff |
| 9 | Validate | `validate.py --strict` | 0 errors, 0 warnings |
| 10 | Security audit (CI mode) | `audit_skills.py --ci` | 0 HIGH |
| 11 | Security audit (SARIF) | `audit_skills.py --sarif` | Valid SARIF 2.1.0 JSON |
| 12 | Per-skill permissions | `audit_skills.py --permissions` | New broad-access skills justified in CHANGELOG |
| 13 | Provenance flag check | `grep -- '--provenance' .github/workflows/publish.yml` | Present |
| 14 | Checksum-pin backfill | `sources.json` entries all have `sha256` | No unpinned URL sources |
| 15 | Tests | `npm test` | All pass |
| 16 | Commit | `git commit` | Clean working tree |
| 17 | Tag | `git tag vX.Y.Z` | Tag exists |
| 18 | Push | `git push origin main --tags` | CI triggered with `id-token: write` |
