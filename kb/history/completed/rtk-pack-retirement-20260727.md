---
title: "Retirement: rtk-pack — Broken On Install, Removed One Day After Shipping"
category: planning
service: ai-toolkit
tags:
  - rtk
  - plugin-pack
  - token-reduction
  - postmortem
  - measurement
  - release-process
doc_type: postmortem
status: completed
created: "2026-07-27"
last_updated: "2026-07-27"
shipped_in: "v4.19.0 (removal)"
description: "Why rtk-pack, shipped in v4.18.0, was removed in v4.19.0: the first real install proved every rewritten command failed with exit 127, the wrong architecture was fetched on Apple Silicon, and the pack's own status check reported both as green. Measured value was 0.0615% of input tokens, so neither defect was worth fixing."
---

# Retirement: rtk-pack

**Shipped:** v4.18.0 (2026-07-26). **Removed:** v4.19.0 (2026-07-27).

The pack was installed on a maintainer's machine for the first time one day
after release. It did not work, in the strongest sense available: it broke the
shell.

## Defect 1: every rewritten command failed with exit 127

rtk emits its rewrite as a bare `rtk git status`. The pack installs its binary
at `~/.softspark/ai-toolkit/plugin-scripts/rtk-pack/bin/rtk` and never puts that
directory on `PATH` — deliberately, so a checksum-pinned binary cannot shadow
anything system-wide. The two decisions are individually defensible and jointly
fatal: the shell could not find `rtk`, so every command the hook touched died
before running.

Observed on the first three commands issued after install:

| Command | Result |
|---|---|
| `cat ~/.softspark/ai-toolkit/plugins.json` | `command not found: rtk` |
| `git --no-pager diff` | `command not found: rtk` |
| `find ~/.softspark -path '*rtk*'` | `command not found: rtk` |

The blast radius is every family in `rtk --help`: `git`, `ls`, `read`, `find`,
`grep`, `rg`, `diff`, `docker`, `kubectl`, `npm`, `jest`, `tsc`. On the reference
workload that is 35% of Bash bytes, which is the same 35% the pack was built to
save. The mechanism that produced the benefit produced the outage.

## Defect 2: the Intel build on an Apple Silicon host

`detect_platform()` trusted `platform.machine()`. The maintainer's `python3` is
an Intel Homebrew build at `/usr/local/opt/python@3.14`, so it runs under
Rosetta 2, where every architecture API inside the process reports `x86_64` —
`platform.machine()`, `os.uname()` and `uname -m` alike. The pack fetched
`rtk-x86_64-apple-darwin.tar.gz` onto an `arm64` machine and ran it emulated.

`sysctl.proc_translated` answers the question that distinguishes the two cases
and was not consulted. Note that CI had already met Rosetta on this project:
commit `30614ca`, *"build x86_64-darwin on arm64 and verify it under Rosetta"*.
The build pipeline knew. The install path did not.

## Defect 3: the pack's own health check called both of them green

`plugin status` reported the binary present, the digest recorded, `runs: rtk
0.44.0`, the hook script present and the hook registered. All true, all useless.
The pack's `status.py` was written specifically to *"distinguish installed from
working"*, and it checked only the installed half.

`kb/procedures/post-release-testing-sop.md`, written the day before the release,
requires exactly the missing step:

> Presence is not function. Drive the hook directly.

The SOP was written and not run. Every defect above would have surfaced in its
first five minutes.

## The number that made fixing it not worth it

All three defects were fixed and tested before the removal decision: a `PATH`
prefix on the emitted command, `sysctl.proc_translated` in the detector, and a
status check that executes what the hook emits and looks for 127. Six tests,
all passing, all failing against the previous code. The work was not hard.

It was measured against this, from `rtk-pack-integration-20260726.md` §10.1:

| | |
|---|---:|
| Measured saving | 1.44 MB = 360,529 tokens |
| As a share of input tokens | **0.0615%** |
| Kill number, published before the measurement | 0.05% |
| Margin | ×1.23 |

The integration plan's own verdict on that margin was *"a pass, not a
vindication"*. A pack that survives its kill number by 23%, carries a
supply-chain surface, an upstream-sync SOP, a cross-build workflow for five
targets, and a hook that rewrites every command before it runs, is not worth
three defect classes discovered on first contact. The cost side moved; the
benefit side never did.

## Why the ceiling was always low, independent of any defect

`Read` results are 62.8% of tool-result bytes on this traffic, and `rtk read`
measures 0.0% — at its default `--level none` it returns files verbatim. Tool
results are 4.54% of input token volume, so that is the arithmetic ceiling for
any tool-output mechanism here, and rtk addresses 8.8% of it.

Replayed against upstream's own claims, the families that can be measured
deliver 25.5% in aggregate against a claimed 60–90%:

| Family | Measured | Claimed |
|---|---:|---:|
| `rtk find` | 35.6% | 70% |
| `rtk git` | 33.1% | 70% |
| `rtk grep` | 22.3% | 75% |
| `rtk rg` | 7.0% | 75% |
| `rtk read` | 0.0% | 60% |

Better engineering does not move any of this. The lever is in the wrong place.

## The process lesson

The previous retirement in this series
([output-filter-retirement-20260726.md](output-filter-retirement-20260726.md))
concluded that premise validation must come first, with a kill number published
before the measurement. rtk-pack did that, and did it well: Phase 0 ran on 1224
transcripts before any build work, the kill number was published in advance, and
Phase 3 was cut on a measured 0.008%.

It then shipped without anyone installing it.

Measurement discipline and release discipline are different disciplines, and
this project now has one clean failure of each. The first shipped a feature that
worked and saved nothing. The second shipped a feature that would have saved
something and did not work. The next plan of this shape needs both gates, and
the second one is the cheap one: install the artifact, run the thing, look at
what happens.

## What survives

- **Multi-runtime pack hook wiring.** Packs write user-scope entries to
  `~/.cursor/hooks.json` and `~/.gemini/settings.json`, tagged per pack, with
  `plugin remove` taking only its own back out. Generic; no rtk in it.
- **`supported_editors` in the manifest.** A pack declares the runtimes it works
  on instead of installing everywhere and silently doing nothing.
- **Generic `plugin status` dispatch.** Any pack can ship `scripts/status.py`.
  The lesson attached: a status check must prove the working half by exercising
  it.
- **Version-aware `plugin update`.** A pack whose manifest has not moved is a
  silent no-op.
- **`audit_skills.py --ci` and the ShellCheck gate now cover `app/plugins/`.**
- **[Post-Release Testing SOP](../../procedures/post-release-testing-sop.md).**
  Kept, and now carries the note that the one time it existed and was skipped,
  this happened.

## What was removed

`app/plugins/rtk-pack/`, `.github/workflows/rtk-build.yml`,
`scripts/verify_rtk_binary.py`, `tests/test_rtk_pack.bats`,
`tests/test_verify_rtk_binary.bats`, `kb/procedures/rtk-upstream-sync-sop.md`,
and the GitHub Release `softspark-rtk-v0.44.0-1` holding the five cross-built
binaries.

Anyone who installed the pack under v4.18.0 should run
`ai-toolkit plugin remove rtk-pack`. With the release deleted, a fresh
`plugin install rtk-pack` on v4.18.0 fails at the fetch and leaves the pack
inert rather than half-installed, which is the degraded path the pack was
designed for.
