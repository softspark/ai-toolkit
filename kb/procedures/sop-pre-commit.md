---
title: "SOP: Pre-Commit Gate"
category: procedures
service: ai-toolkit
tags: [pre-commit, quality-gate, shellcheck, bats, validation, secrets]
version: "1.0.0"
created: "2026-09-02"
last_updated: "2026-09-02"
description: "The local gate to run before every commit to ai-toolkit: staged-file and secret scan, ShellCheck, Python syntax, toolkit validation, and the Bats suite. Runs the same checks CI runs, so main does not go red after a push."
---

# SOP: Pre-Commit Gate

## Why this exists

CI runs on `main` and on pull requests, but it runs *after* the push. Every
check below already exists in `.github/workflows/ci.yml`; running them locally
first is what keeps `main` green and keeps a release from becoming a debug
session. The v4.5.1 postmortem in `sop-release.md` is the case
where a hook lint failure published while reddening `main` CI.

This gate is not a substitute for `sop-release.md`. That SOP gates
a *tag*; this one gates a *commit*.

## Prerequisites

`shellcheck`, `python3` and `bats` must be on `PATH`. The suite is the one
check that silently does nothing when its runner is absent, so install it
before relying on this gate:

```bash
brew install bats-core shellcheck    # macOS
sudo apt-get install -y bats shellcheck   # Debian / Ubuntu
```

## The gate

Run all five from the repository root. Each mirrors a CI job.

```bash
# 1. Staged files: secrets, large blobs, commit-type suggestion
python3 app/skills/commit/scripts/pre-commit-check.py

# 2. ShellCheck hooks -- the CI job that has published while red before
shellcheck --severity=warning app/hooks/*.sh app/plugins/*/hooks/*.sh

# 3. Python syntax across every script the toolkit ships
python3 -m py_compile scripts/*.py app/skills/*/scripts/*.py

# 4. Toolkit integrity: agents, skills, registry drift, content quality
npm run validate

# 5. The suite. Run it ONCE -- see the single-run discipline below
npm test
```

A non-zero exit from any of them is a stop, not a warning to note and push past.

## Single-run discipline

`npm test` runs the Bats suite with `--jobs 4`. Running it repeatedly to see
whether a failure is "flaky" hides real ordering bugs and wastes minutes. Run
it once. If it fails, read the failure and fix the cause; if the same test
passes on a re-run without a code change, that instability is itself the bug
and belongs in an issue, not in a retry.

## What this gate does not cover

- **Cross-platform.** The suite here runs on your machine only. Both
  `ubuntu-latest` and `macos-latest` must be green before a tag; that gate
  lives in `sop-release.md`, Phase 7, and is bound to the exact
  release commit.
- **Required files.** The `required-files` CI job checks that every file the
  module template mandates is present and that the version is in sync across
  all four manifests. It is cheap and runs on every push.
- **Provenance and SARIF.** Release-time concerns; see
  `sop-release.md`.

## Commit message

Conventional Commits, and no AI co-authorship trailer:

```
feat(scope): summary in the imperative
fix(scope): summary in the imperative
docs|refactor|test|chore(scope): ...
```

`pre-commit-check.py` suggests a type from the staged paths. It is a
suggestion; the scope and the summary are yours.

## Related

- `sop-release.md` -- the pre-tag gate, including cross-platform CI
- `sop-post-release-testing.md` -- what to verify after a release ships
- `sop-release-verification.md` -- end-to-end smoke test of an installed build
