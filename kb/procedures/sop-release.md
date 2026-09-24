---
title: "SOP: Release Preparation"
category: procedures
service: ai-toolkit
tags: [sop, release, version, publish, changelog, semver, provenance, sarif, ecosystem, shellcheck, local-gates]
version: "2.0.0"
created: "2026-04-10"
last_updated: "2026-09-24"
description: "Release procedure for ai-toolkit under Local Release Gates, Publish-Only CI: ecosystem-sync drift check, version sync, changelog, artifact regeneration, then one command (npm run release -- X.Y.Z) that runs every gate on macOS and in Linux containers, tags, pushes and watches the publish-only workflow."
---

# SOP: Release Preparation

Complete procedure for a new `@softspark/ai-toolkit` release. Model: every
test runs on the maintainer's machine, GitHub Actions only turns the tag into
an npm package and a GitHub Release (the shared SoftSpark standard "Local
Release Gates, Publish-Only CI", 2026-09-24). No workflow runs on branch
pushes or pull requests, and no workflow re-runs the test suite.

After the publish, run the [Release Verification SOP](sop-release-verification.md)
and the [Post-Release Testing SOP](sop-post-release-testing.md).

**Pipeline:**
```
Ecosystem Sync SOP (drift check + generator updates)
      ↓
Prepare the release commit on main (this SOP, Phases 0-5)
      ↓
npm run release -- X.Y.Z   (gates → Linux → pack + smoke → tag → push → watch publish)
      ↓
Release Verification SOP
```

**Time:** 10-20 minutes of preparation, then about 20 minutes of unattended
gates (the Linux bats run alone takes about 10).

---

## Quick Checklist (TL;DR)

```bash
# 0. Ecosystem sync (mandatory for minor/major releases; optional for patch)
python3 scripts/ecosystem_doctor.py --format text | tee /tmp/eco-report.txt
python3 scripts/ecosystem_doctor.py --update    # after all drift resolved

# 1. Decide the bump, then on an up-to-date main:
git switch main && git pull --ff-only

# 2. Sync the version in package.json, manifest.json, app/.claude-plugin/plugin.json
npm install --package-lock-only

# 3. CHANGELOG.md "## vX.Y.Z - Title (YYYY-MM-DD)" + README "## What's New in vX.Y.Z"

# 4. Regenerate committed artefacts
npm run generate:all
git status --short          # stage llms.txt, llms-full.txt, README badges if changed

# 5. Commit the release on main
git add -A && git commit -m "chore: release vX.Y.Z"

# 6. Rehearse (optional, runs every gate, tags nothing)
npm run release -- X.Y.Z --dry-run

# 7. Release: gates, Linux run, pack + smoke, tag, push main, push the tag,
#    watch publish.yml, verify npm + provenance + GitHub Release, upload SARIF
npm run release -- X.Y.Z
```

`scripts/release.sh` is the only supported way to create a release tag. A tag
made by hand skipped the gates, and nothing on GitHub will catch that.

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

For each drifting tool, follow [sop-ecosystem-sync.md](sop-ecosystem-sync.md) Phase 2-4:

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

The release script runs `ecosystem_doctor.py --offline --check`. That offline
check verifies declared generator paths; it does not fetch documentation or
establish snapshot freshness, so Phases 0.1 to 0.3 stay a human step.

---

## Phase 1: Determine Version Bump

Follow [Semantic Versioning](https://semver.org/):

| Change Type | Bump | Examples |
|-------------|------|---------|
| Bugfix, typo, doc-only | **patch** | Fix install flag, correct description |
| New feature, skill, agent, flag | **minor** | Add `/hipaa-validate`, add `--output json` |
| Breaking CLI change, removed skill, config format change | **major** | Rename `install` to `setup`, remove skill |

**Rule:** When in doubt, bump minor.

Prepare the release on `main`, up to date with `origin/main`
(`git fetch` first: `origin/main` moves between sessions). There is no release
branch, no PR and no CI to wait for: the release script's gates are the check.

---

## Phase 2: Sync Version in All Files

The canonical version lives in `package.json`. These files **must** match, and
`scripts/release.sh` refuses to continue when one does not:

| File | Field | How to update |
|------|-------|---------------|
| `package.json` | `"version": "X.Y.Z"` | Edit directly |
| `manifest.json` | `"version": "X.Y.Z"` | Edit directly |
| `app/.claude-plugin/plugin.json` | `"version": "X.Y.Z"` | Edit directly |
| `package-lock.json` | `version` and `packages[""].version` | `npm install --package-lock-only` |

### Conditional sync (only if the doc was modified in this release)

| File | Field | When to update |
|------|-------|---------------|
| `kb/procedures/sop-maintenance.md` | frontmatter `version:` | If SOP content changed |
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

`validate.py --strict` catches count drift and version mismatches; the release
script runs it.

### Public surface review

```bash
python3 scripts/surface_manifest.py --update
git diff app/surface.json
```

**Every line the diff removes is a breaking change.** Restore it, or take the
deprecation path in `BACKWARD_COMPATIBILITY.md` and add a `DECISIONS.md` entry
before the tag. Lines added are new surface being adopted into protection — that
needs no ceremony.

Do not run `--update` to make a red build green. The check fails because something
users depend on disappeared; regenerating the manifest deletes the evidence, not
the problem.

### Skill body budget ratchet

`validate.py` prints the largest skill body on every run:

```
Body budget: largest is <skill> at <N> bytes (warn 18000, error 20000)
```

Once that number sits at least 2000 bytes under `SKILL_BODY_BUDGET_WARN`, lower
`SKILL_BODY_BUDGET_WARN` by 2000 in `scripts/validate.py` and ship the tightened
threshold with the release. Target floor is 12000.

Two rules, both learned the hard way:

- **Never lower a threshold in the same change that something violates it.** Split
  the offending skill into `SKILL.md` + `reference/` first, prove it with
  `python3 scripts/check_split.py <skill> --before <pre-split SKILL.md>`, then
  tighten in a follow-up.
- **Never raise a threshold to make a red build green.** A body over budget means
  detail that belongs in `reference/` is loading on every trigger match, including
  the accidental ones. Raising the number hides the cost, it does not remove it.

If the largest body has not moved since the previous release, leave the threshold
alone and say so in the release notes. A ratchet that never advances is honest;
one that advances past reality is not.

---

## Phase 3: Write CHANGELOG Entry

Add entry at the top of `CHANGELOG.md` (after the header, before previous release).
The release script requires a heading that starts with `## vX.Y.Z `:

```markdown
## vX.Y.Z - Short Title (YYYY-MM-DD)

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

**MANDATORY on every release**, and checked by the release script. Update the
`## What's New in vX.Y.Z` section in `README.md`:

1. Change the heading version: `## What's New in vX.Y.Z`
2. Replace bullet points with 3-5 highlights from this release
3. **Keep only the latest version block.** Delete the previous `## What's New in vA.B.C` section(s). README is the shop window, not the archive — users see the current release, full history lives in `CHANGELOG.md`.
4. Keep the `See [CHANGELOG.md](CHANGELOG.md) for full history.` link directly below the bullet list.

> **Single-version rule:** README.md must contain **exactly one** `## What's New in vX.Y.Z` heading at any time.

---

## Phase 4: Regenerate Artifacts

Use the npm scripts, not the generators directly:

```bash
npm run generate:all
git status --short
```

`generate:agents` sets `AI_TOOLKIT_NO_CUSTOM_RULES=1`. Running
`generate_agents_md.py` bare picks up whatever is registered in the maintainer's
own `~/.softspark/ai-toolkit/rules/`, which then ships inside `AGENTS.md`.

`AGENTS.md`, `GEMINI.md` and `.github/copilot-instructions.md` are generated
and gitignored; the publish workflow regenerates them for the tarball. Commit
the tracked outputs that changed (`llms.txt`, `llms-full.txt`, README badges).
The release script re-runs `generate:all` and fails if it changes any
committed file, so a stale artefact cannot reach a tag.

**Adding or deleting a `kb/` file?** Commit it: the test "npm package KB files
match the tracked release set" compares `git ls-files kb` with what `npm pack`
sees, and the release script only runs on a clean tree anyway.

---

## Phase 5: Commit

```bash
git add -A
git commit -m "chore: release vX.Y.Z"
```

The subject must be exactly `chore: release vX.Y.Z`: the script checks `HEAD`
and later asserts the tag sits on that commit.

---

## Phase 6: Run the Release

```bash
npm run release -- X.Y.Z --dry-run   # optional rehearsal, steps 1-5 only
npm run release -- X.Y.Z
```

Logs go to `${TMPDIR:-/tmp}/ai-toolkit-release-X.Y.Z/<gate>.log`. The script
stops at the first failure and prints the tail of that gate's log.

| Step | What `scripts/release.sh` does |
|---|---|
| 1. Preconditions | Branch is `main`; tree clean; `git fetch` done and `origin/main` is an ancestor of `HEAD` (not behind, not diverged); `X.Y.Z` is semver; `vX.Y.Z` exists neither locally nor on `origin`; the version is not on npm yet |
| 2. Version and notes | `package.json`, `manifest.json`, `app/.claude-plugin/plugin.json`, `package-lock.json` (both fields) say `X.Y.Z`; CHANGELOG `## vX.Y.Z`; README `What's New in vX.Y.Z`; `HEAD` subject `chore: release vX.Y.Z` |
| 3. Gates (macOS host) | Required files; `generate:all` changes no committed file; `ecosystem_doctor.py --offline --check`; `validate.py --strict`; `evaluate_skills.py`; `audit_skills.py --ci`; `audit_skills.py --sarif` (kept for step 7); `audit_skills.py --permissions` (logged for review); `shellcheck --severity=warning` on hooks, plugin hooks and the release script; registry-vs-generator drift; `publish.yml` still has `--provenance` and `id-token: write`; `npm test` with zero `not ok`; the gates left the tree unchanged |
| 4. Linux | The repository (tracked files plus `.git`, copied in, never mounted) into throwaway containers: `ubuntu:24.04` runs the full bats suite as a non-root user; `python:3.11-slim` (the declared floor) runs `py_compile`, an import of every `scripts/` module, `test:py`, `lint:py` and `typecheck:py`; `python:3.13-slim` runs `py_compile` and the import check |
| 5. Build and smoke | `npm pack` into the log directory; the tarball carries `AGENTS.md` and `NOTICE` and not `scripts/release.sh`; installed into a scratch prefix with a scratch `HOME`, `ai-toolkit --version` reports `X.Y.Z` and `ai-toolkit help` runs |
| 6. Tag and push | Lightweight tag `vX.Y.Z` on `HEAD` (the repository's existing format); asserts `vX.Y.Z^{commit}` is `HEAD` and its subject is `chore: release vX.Y.Z`; `git push origin main`; `git push origin refs/tags/vX.Y.Z` |
| 7. Watch publish | Finds the `publish.yml` run for the tagged commit, `gh run watch --exit-status`; `npm view` shows `X.Y.Z` with a SLSA v1 provenance attestation; the GitHub Release exists; uploads the step-3 SARIF to code scanning for `refs/tags/vX.Y.Z` |

`--gates-only` runs steps 3-5 on the current working tree without any git
precondition and tags nothing. Use it to check a branch before the release
commit exists. Its Linux step copies the working tree, uncommitted changes
included.

### Why step 4 applies here

macOS bash 3.2 does not fail a bare `[[ ]]` assertion inside a bats test while
Linux bash does, and parts of the suite are path-sensitive (`/var` against
`/private/var`) or misbehave as root. A green macOS run alone is not a green
suite. The Python containers keep the old CI coverage of the declared floor
(`PYTHON_MIN` 3.11): `py_compile` catches syntax, only an import catches
version-gated runtime features.

### What the publish workflow still does

`.github/workflows/publish.yml`, on a `v*` tag only: checkout, Node setup,
**tag equals `package.json` version**, `npm run generate:all` (build: the
gitignored generated files ship in the tarball), `npm publish --access public
--ignore-scripts --provenance`, GitHub Release. Actions are pinned by commit
SHA. It runs no test, lint, validate or audit step: the tag exists only because
the local gates passed.

**Provenance is non-negotiable.** `id-token: write` and `--provenance` stay in
`publish.yml`; the release script's `publish-workflow` gate fails without
them and step 7 fails when the published version has no attestation. Any change
to `publish.yml` needs a security review.

### Postmortems the script encodes

- **v4.19.0: tag on the wrong commit.** It was tagged on a commit that carried
  only a KB document and `package.json` version `4.18.0`; the release sat in the
  commit above under a recycled `fix:` message, and the publish failed on a
  version already on npm. Step 2 checks `HEAD`, step 6 asserts the tag before
  pushing it, and the workflow asserts tag equals version.
- **`--tags` push.** GitHub suppresses tag-triggered runs when many tags arrive
  in one push, so nothing publishes (rag-mcp's `1.0.3` image build was skipped
  this way with 37 tags). The script pushes exactly one ref,
  `refs/tags/vX.Y.Z`.
- **v4.5.1: red ShellCheck, published anyway.** ShellCheck is a step-3 gate.
- **v4.30.2: macOS-only failure.** The macOS host run and the Linux container
  run both have to be green before the tag exists.

### Licensing gate

The project is Apache-2.0. `tests/test_licensing.bats` runs inside `npm test`
(step 3 and step 4):

| Check | Fails when |
|---|---|
| Every shipped source file carries an SPDX header | A new `.py`/`.sh`/`.js`/`.bats` file was added without one |
| Headers name Apache-2.0 and nothing else | A file was copied in from an MIT/GPL source with its own header intact |
| **No** markdown file carries an SPDX header | Someone ran the header script over `app/skills/` |
| `LICENSE` is the complete Apache 2.0 text | The file was truncated or replaced with a summary |
| `NOTICE` carries attribution, the source URL, §4(d) and the MIT-era notice | The attribution mechanism was gutted |
| `LICENSE` **and** `NOTICE` ship in the npm package | `package.json` `files` lost an entry |
| Every manifest declaring a licence declares Apache-2.0 | `package.json`, `manifest.json`, `plugin.json` and `package-lock.json` drifted apart |

**Adding source files in this release?** The header goes *after* the shebang,
never before it:

```
# SPDX-License-Identifier: Apache-2.0
# Copyright 2024-2026 Lukasz Krzemien (biuro@softspark.eu)
# Source: https://github.com/softspark/ai-toolkit
```

`//` for JavaScript. Full convention: [Licensing](../reference/licensing.md).

### Checksum-pinned URL sources (manual, optional)

On a machine that has consumed URL rules/hooks at least once:

```bash
jq '.rules | to_entries | map(select(.value.url != null and (.value.sha256 // "" | length) == 0))' ~/.softspark/ai-toolkit/rules/sources.json
jq '.hooks | to_entries | map(select(.value.url != null and (.value.sha256 // "" | length) == 0))' ~/.softspark/ai-toolkit/hooks/external/sources.json
AI_TOOLKIT_STRICT_PIN=1 ai-toolkit update --dry-run
```

Both queries return empty arrays and the dry run prints no `CHECKSUM CHANGED`.

### If a gate fails

Fix the cause, amend or add to the release commit, run the script again. Do
not skip a gate and do not tag by hand. Common failures:
- Stale counts → `npm run generate:all`, commit
- `generate-all` gate → a committed artefact was stale, commit the regenerated file
- Broken symlink → `ai-toolkit doctor --fix`
- `bats-linux` only → a bare `[[ ]]`, a root-only assumption or a macOS path; reproduce with `npm run release -- X.Y.Z --gates-only`

If step 7 fails, the tag is already pushed: read the run log (`gh run view
<id> --log-failed`), and follow Rollback when a broken version reached npm.

---

## Repository settings

Branch protection and rulesets must not require status checks: the checks no
longer exist, and a required check that never reports blocks every merge.
Releases push `main` directly, which needs a rule set that lets the maintainer
push (today the `main protection` ruleset allows repository admins to bypass).

---

## Rollback

If a bad release was published:

```bash
# Deprecate (preferred — doesn't break existing installs)
npm deprecate @softspark/ai-toolkit@X.Y.Z "Known issue: <description>. Use vA.B.C instead."

# Unpublish from npm (within 72h, security issues only)
npm unpublish @softspark/ai-toolkit@X.Y.Z

# Delete tag (does not delete what was published)
git tag -d vX.Y.Z
git push origin --delete vX.Y.Z
```

Then fix on `main`, bump the patch version and release again.

---

## Checklist Summary

| # | Step | Command / Action | Pass Criteria |
|---|------|-----------------|---------------|
| 0a | Ecosystem drift check | `ecosystem_doctor.py --format text` | All tools Clean, or drift classified and resolved |
| 0b | Ecosystem snapshot refresh | `ecosystem_doctor.py --update` | `benchmarks/ecosystem-doctor-snapshot.json` updated |
| 1 | Version bump type | Decide patch/minor/major | — |
| 2 | Version files | `package.json`, `manifest.json`, `plugin.json`, `npm install --package-lock-only` | All say `X.Y.Z` |
| 3 | Count sync + surface review | README, ARCHITECTURE, `surface_manifest.py --update` | No removed surface line |
| 4 | CHANGELOG + README | `## vX.Y.Z - Title (date)`, `## What's New in vX.Y.Z` | Both present |
| 5 | Regenerate | `npm run generate:all` | Tracked outputs committed |
| 6 | Commit on `main` | `git commit -m "chore: release vX.Y.Z"` | Clean tree |
| 7 | Rehearse | `npm run release -- X.Y.Z --dry-run` | Steps 1-5 green |
| 8 | Release | `npm run release -- X.Y.Z` | Exit 0: gates green on macOS and Linux, tag pushed, publish run green, npm version with provenance, GitHub Release, SARIF uploaded |
| 9 | Review | `<log dir>/audit-permissions.log` | New broad-access skills justified in CHANGELOG |
| 10 | Verify | [Release Verification SOP](sop-release-verification.md) | Pass |
