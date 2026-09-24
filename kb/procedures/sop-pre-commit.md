---
title: "SOP: Pre-Commit Gate"
category: procedures
service: ai-toolkit
tags: [pre-commit, quality-gate, shellcheck, bats, validation, secrets]
version: "1.1.0"
created: "2026-09-02"
last_updated: "2026-09-24"
description: "The local gate to run before every commit to ai-toolkit: staged-file and secret scan, ShellCheck, Python syntax, toolkit validation, and the Bats suite. No GitHub workflow tests pushes, so this gate is what keeps main green between releases."
---

# SOP: Pre-Commit Gate

## Why this exists

No GitHub workflow tests a push or a pull request: CI only publishes a tag.
Nothing checks `main` between releases except this gate, and a red `main`
turns the next release into a debug session.

This gate is not a substitute for `sop-release.md`. That SOP gates
a *tag* (`npm run release -- X.Y.Z` runs every check below plus the Linux
container run); this one gates a *commit*. To run the full release gate on a
branch without tagging: `npm run release -- X.Y.Z --gates-only`.

## Prerequisites

`shellcheck`, `python3` and `bats` must be on `PATH`. The suite is the one
check that silently does nothing when its runner is absent, so install it
before relying on this gate:

```bash
brew install bats-core shellcheck    # macOS
sudo apt-get install -y bats shellcheck   # Debian / Ubuntu
```

## The gate

Run all five from the repository root. Each is also a release gate in
`scripts/release.sh`.

```bash
# 1. Staged files: secrets, large blobs, commit-type suggestion
python3 app/skills/commit/scripts/pre-commit-check.py

# 2. ShellCheck hooks -- the check that has published while red before
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

- **Cross-platform.** The suite here runs on your machine only. The release
  script also runs it in an `ubuntu:24.04` container as a non-root user, and
  both runs must be green before a tag (`sop-release.md`, Phase 6).
  `npm run release -- X.Y.Z --gates-only` runs that Linux step on a branch.
- **Required files and version sync.** Release gates in `scripts/release.sh`
  (steps 2 and 3): every file the module template mandates is present and the
  version agrees across all four manifests.
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

- `sop-release.md` -- the pre-tag gate (`npm run release`), macOS and Linux
- `sop-post-release-testing.md` -- what to verify after a release ships
- `sop-release-verification.md` -- end-to-end smoke test of an installed build
