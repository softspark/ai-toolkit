---
title: "SOP: rtk Upstream Sync"
category: procedures
service: ai-toolkit
tags: [sop, rtk, rtk-pack, upstream, cross-build, telemetry, checksum, port-validation, advisory]
version: "1.0.0"
created: "2026-07-26"
last_updated: "2026-07-26"
description: "Procedure for moving rtk-pack to a newer upstream rtk release: detect the tag, review the files we depend on, re-validate the Python port that every coverage number rests on, rebuild five targets with telemetry undefined, verify silence, publish to our own release namespace, and bump the pack. Written after the v0.43.0 to v0.44.0 bump, which changed every file this SOP names."
---

# SOP: rtk Upstream Sync

Moves `rtk-pack` from one pinned upstream tag to the next.

Currently pinned: **v0.44.0**, shipped as
`softspark-rtk-v0.44.0-1`. The pin lives in
`app/plugins/rtk-pack/plugin.json` under `upstream.version`.

Upstream ships stable tags roughly every two to four weeks behind a long
release-candidate train (300+ RCs preceded v0.44.0). Do not track RCs.

Background and the measured numbers: `kb/planning/rtk-pack-integration-plan.md`.

## Why this SOP is not "just rebuild"

The v0.43.0 to v0.44.0 bump was 200 commits and touched **every file listed in
Phase 2 below**. It also inverted pipeline rewriting: v0.43.0 rewrote the first
stage of a pipeline, v0.44.0 rewrites the last. A rebuild without the review
step would have shipped that silently, and the coverage numbers quoted to users
would have described a version we no longer ship.

## Phase 1: Detect

```bash
gh api repos/rtk-ai/rtk/releases --paginate \
  --jq '.[] | select(.tag_name | test("^v[0-9]")) | "\(.tag_name)\t\(.published_at)"' | head -5
```

Compare against `upstream.version` in `app/plugins/rtk-pack/plugin.json`.

Cadence: on demand, plus a check folded into release preparation.

## Phase 2: Review before building

Fetch the diff for the areas the pack depends on:

```bash
gh api repos/rtk-ai/rtk/compare/<pinned>...<new> \
  --jq '{ahead: .ahead_by, files: [.files[] | {f: .filename, add: .additions, del: .deletions}]}'
```

Read the changelog, then diff these specifically:

| File | Why it matters |
|---|---|
| `src/discover/registry.rs` | rewrite eligibility, pipeline handling, the TOML call sites |
| `src/discover/rules.rs` | the rule table and `IGNORED_PREFIXES` |
| `src/discover/lexer.rs` | tokenisation and `contains_unattestable_construct` |
| `src/core/toml_filter.rs` | the filter DSL, which affects users who write their own filters |
| `src/hooks/trust.rs` | the trust gate and its paths |
| `src/hooks/hook_cmd.rs` | the Claude hook contract and permission handling |
| `src/core/telemetry.rs`, `src/core/telemetry_cmd.rs` | the compile-time endpoint gate |
| `Cargo.toml`, `Cargo.lock` | native deps, the MSRV, and new advisories |

**A change to the DSL, to trust handling, or to the permission flow is a
stop-and-think, not a rebuild.** In particular:

- The pack ships no filters of its own, so a DSL change cannot break us. It can
  still break a **user's** `filters.toml`, which upstream then skips silently
  (`toml_filter.rs:220-221`). Worth a release-note line, not a code change.
- If `hook_cmd.rs` changes when `permissionDecision` is emitted, the trust
  boundary documented in the pack README changes with it.
- If `IGNORED_PREFIXES` or the `pipeline_final_safe` rule set moves, every
  coverage number is stale.

## Phase 3: Re-validate the port

Every coverage and saving figure the pack quotes comes from `rtk_port.py`, a
Python model of rtk's rewrite pipeline. **Anything short of full agreement
invalidates those numbers until the port is fixed.** Tooling lives in
`~/rtk-measurement-archive/`.

```bash
git clone --depth 1 --branch <new-tag> https://github.com/rtk-ai/rtk.git /tmp/rtk-new
cd ~/rtk-measurement-archive

# Rewrite assertions from the tag's own test block.
python3 extract_cases.py /tmp/rtk-new/src/discover/registry.rs cases.json
python3 validate_port.py cases.json

# The entry gate both real hook paths apply before rewrite_command.
# Its assertions live in lexer.rs; re-extract if that block moved.
python3 -c "import entry_gate; print('gate import ok')"
```

Baseline at v0.44.0: **203/203** rewrite assertions, **35/35** gate assertions.

If the port diverges, fix the port first, then re-measure:

```bash
python3 measure_gated.py gated 0:1224
```

Measure over the whole transcript pool, never the default 134-file window: at
that size the projection swings 8.8x on an unchanged mechanism.

## Phase 4: Rebuild

```bash
gh workflow run rtk-build.yml --ref main \
  -f upstream_tag=<new-tag> -f build_revision=1 -f rust_version=<pinned> -f publish=false
```

Five targets: `x86_64-apple-darwin`, `aarch64-apple-darwin`,
`x86_64-unknown-linux-musl`, `aarch64-unknown-linux-gnu`,
`x86_64-pc-windows-msvc`. A target that will not build is dropped, not faked.

Pin `rust_version` explicitly. Upstream uses unpinned `stable` with
`warnings = "deny"`, so a new rustc lint can turn the build red with no change
on either side.

**Advisories.** The `audit` job blocks. Re-derive the disposition rather than
carrying the previous one forward:

```bash
# Cross-reference the new lockfile against OSV without waiting for CI.
python3 - <<'PY'
import json, re, urllib.request, pathlib
lock = pathlib.Path("/tmp/rtk-new/Cargo.lock").read_text()
pkgs = [(re.search(r'^name = "([^"]+)"', b, re.M).group(1),
         re.search(r'^version = "([^"]+)"', b, re.M).group(1))
        for b in lock.split("[[package]]")[1:]
        if re.search(r'^name = ', b, re.M) and re.search(r'^version = ', b, re.M)]
q = [{"package": {"name": n, "ecosystem": "crates.io"}, "version": v} for n, v in pkgs]
req = urllib.request.Request("https://api.osv.dev/v1/querybatch",
    data=json.dumps({"queries": q}).encode(), headers={"Content-Type": "application/json"})
res = json.load(urllib.request.urlopen(req, timeout=60))
for (n, v), r in zip(pkgs, res["results"]):
    if r.get("vulns"):
        print(n, v, [x["id"] for x in r["vulns"]])
PY
```

For each advisory decide, and record the reason in the workflow:

- **In-range fix** (`cargo update -p <crate>` works): add the crate to
  `RTK_CARGO_UPDATES` in `.github/workflows/rtk-build.yml`. Both the audit job
  and every build job apply it, so we audit what we ship.
- **Needs a `Cargo.toml` change**: that is a source modification and breaks the
  NOTICE claim. Ignore with a written reason, or escalate.
- **Carried-forward ignores**: re-check every `--ignore` still applies. The
  quick-xml pair exists only because upstream pins `"0.37"`; **delete both the
  moment upstream moves to 0.41 or later** rather than carrying them.

## Phase 5: Verify

CI asserts this per target and the run fails on any `fail` verdict:

1. `RTK_TELEMETRY_URL` and `RTK_TELEMETRY_TOKEN` unset at build time
2. the artifact starts and reports the expected version
3. no telemetry state written into a sandboxed home
4. on Linux, identical behaviour with no network route
5. every archive holds exactly one flat entry

Then check by hand:

```bash
gh run download <run-id> --dir /tmp/rtk-verify
cd /tmp/rtk-verify && shasum -a 256 -c checksums.txt
```

Three things CI cannot tell you:

- **`strings` markers.** Compare `tls_markers_present` per target against the
  previous build. Their absence is an LLVM outcome under LTO, not a guarantee,
  so a sudden appearance means the telemetry stack survived and is worth
  understanding before shipping.
- **Reproducibility.** Four of five targets are bit-reproducible; compare
  extracted binaries, never the tarballs, because gzip records a timestamp.
  `x86_64-pc-windows-msvc` differs by 24 bytes per link (MSVC timestamp plus a
  CodeView GUID), so a changed Windows digest proves nothing on its own.
- **Upstream has no test asserting network silence.** That property can regress
  on any bump without turning their CI red. We own it.

## Phase 6: Publish

```bash
gh workflow run rtk-build.yml --ref main \
  -f upstream_tag=<new-tag> -f build_revision=1 -f rust_version=<pinned> -f publish=true
```

Creates `softspark-rtk-<upstream>-<revision>`. Bump the revision, not the
upstream part, when rebuilding the same upstream tag.

## Phase 7: Bump the pack

In `app/plugins/rtk-pack/plugin.json`:

- `upstream.version` to the new tag
- `binary.release_tag` to the new release
- every `assets.*.sha256` from the published `checksums.txt`
- `version` (the pack's own) — bump it whether or not the upstream tag moved,
  because `plugin update` skips a pack whose recorded version still matches, so
  an unbumped pack never reaches installed users. The two fields are separate so
  a pack-only fix does not pretend to be an upstream bump

Then:

```bash
npm test          # tests/test_rtk_pack.bats asserts digest shape and layout
python3 scripts/validate.py --strict
python3 scripts/audit_skills.py --ci
shellcheck --severity=warning app/hooks/*.sh app/plugins/*/hooks/*.sh
```

Verify a real install end to end, against the published release rather than a
mirror:

```bash
H=$(mktemp -d)
AI_TOOLKIT_DATA_DIR="$H" python3 app/plugins/rtk-pack/scripts/init.py
AI_TOOLKIT_DATA_DIR="$H" python3 app/plugins/rtk-pack/scripts/status.py
```

## Phase 8: Ship

The pack version bump reaches installed users through `ai-toolkit update`,
which runs `plugin update --editor all --all`. A pack whose recorded version
matches its manifest is skipped silently, so the bump in Phase 7 is what makes
the update fire at all. Forgetting it means nobody gets the new binary.

## Phase 9: Record the licence position

If upstream relicenses, adds a `NOTICE`, or changes `DISCLAIMER.md`, update the
NOTICE generated in `.github/workflows/rtk-build.yml`. It currently records two
build-time differences: the undefined telemetry endpoint, and in-range lockfile
security updates. If Phase 4 changes that set, the NOTICE text changes with it.

`DISCLAIMER.md` is deliberately not redistributed because it states telemetry is
collected by default, which our builds contradict. Re-check that this is still
the reason before changing the decision.

## Related

- `kb/planning/rtk-pack-integration-plan.md` — decisions, measurements, pre-mortem
- `kb/history/completed/output-filter-retirement-20260726.md` — why premise validation comes first
- `app/plugins/rtk-pack/README.md` — the user-facing trust boundary
