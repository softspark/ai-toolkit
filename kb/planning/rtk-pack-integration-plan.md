---
title: "Plan: rtk Pack Integration"
category: planning
service: ai-toolkit
tags:
  - rtk
  - plugin-pack
  - token-reduction
  - vendored-binaries
  - cross-build
  - upstream-sync
doc_type: plan
status: proposed
created: "2026-07-26"
last_updated: "2026-07-26"
completion: "Phase 0 done"
pinned_upstream: "v0.44.0"
description: "Integrate rtk as an opt-in ai-toolkit plugin pack: binaries cross-built from source in our CI with telemetry disabled, hosted on our own GitHub Release, fetched and checksum-verified at pack install, with our own filter presets, auto-update on ai-toolkit update, and an SOP for tracking upstream releases. Phase 0 validated the premise against v0.44.0 on the full transcript corpus before any build work."
---

# rtk Pack Integration

## 1. Decision

Ship `rtk` to ai-toolkit users as an **opt-in plugin pack**, with the binary
supply chain owned end to end by us.

Five choices, made and locked:

| Question | Decision |
|---|---|
| Delivery | Plugin pack (`rtk-pack`), never a native feature |
| Binary hosting | Our own GitHub Release, fetched and SHA-256 verified at pack install |
| Binary provenance | Cross-built from upstream source in our CI, `RTK_TELEMETRY_URL` unset |
| Pinned upstream tag | **v0.44.0** (2026-07-26). v0.43.0 was ruled out on evidence, see section 2 |
| Upstream tracking | An SOP that rebuilds, verifies, and re-publishes when rtk ships a release |

Upstream: https://github.com/rtk-ai/rtk, Apache-2.0, Rust 1.91 plus a C
toolchain (rusqlite `bundled` compiles SQLite from source).

## 2. Phase 0: premise validated before building anything

The retired output filter validated its design across five phases and its
premise not at all until the fifth. This plan runs premise validation first.
Everything below is measured, not estimated.

### 2.1 Why v0.43.0 was ruled out

Two structural facts, read from the source of both tags:

- **Custom TOML filters are not wired into the rewrite path in v0.43.0.**
  `src/discover/registry.rs` at v0.43.0 contains zero references to
  `toml_filter`. In v0.44.0 they appear at `registry.rs:1047,1055,1058`. Our own
  presets, the pack's entire value-add over upstream, cannot fire on v0.43.0.
- **`pipeline_final_safe` does not exist in v0.43.0.** It arrives in v0.44.0
  (`rules.rs:7,115,124`, `registry.rs:605,659,864,1069`). v0.43.0 rewrote the
  first pipeline stage; v0.44.0 rewrites the last. On this traffic 56.5% of
  `rtk grep` hits arrive through the pipeline-final path, so they do not exist
  at all on v0.43.0.

### 2.2 The port models v0.44.0, not v0.43.0

`rtk_port.py` is re-validated by extracting the `assert_eq!` assertions from
each tag's `registry.rs` `#[cfg(test)]` block and replaying them:

| Port checked against | Assertions | Exact-string agreement |
|---|---:|---:|
| **v0.44.0** | 203 | **203/203** |
| v0.43.0 | 160 | 147/160 |

The 13 v0.43.0 failures are all the same pipeline inversion. The port also
passes the 15 assertions v0.44.0 added after the port was written. Pinning
v0.44.0 makes the existing measurement correct rather than requiring rework.

`registry.rs:590-592` returns `Some(unchanged)` for a simple already-`rtk`
command; the port's equivalent bail must be mapped to that, not to `None`.

### 2.3 The recorded numbers came from an 11% sample

`measure_rtk.py` sets `N_FILES = 134` and takes the most recently modified
transcripts. The available pool is **1224 transcripts**. At n=134 the projected
saving swings **8.8x** across windows (0.071% to 0.628%); at n>=408 it converges
to within **1.05x**. The spread recorded in earlier revisions of this plan was
sampling noise.

### 2.4 The port over-counted, and by how much

Both real entry points call `contains_unattestable_construct` **before**
`registry::rewrite_command`: `hook_cmd.rs:149-151` (Defer) and
`rewrite_cmd.rs:54-56` (Passthrough). Any command carrying a command
substitution, a process substitution, or a redirect with a file target is
rejected whole. Upstream's rewrite tests call `rewrite_command` directly, so a
port validated only against them passes while still over-counting.

The gate is ported from `lexer.rs:295-347` and validated **35/35** against
upstream's own assertions at `lexer.rs:1186-1276`. Applying it costs 3.1%
relative coverage.

### 2.5 Corrected numbers

Full corpus, 1224 transcripts, 552 MB, 106 MB of tool results, 26.6 MB of
successful Bash, entry gate applied:

| Metric | Earlier revision (n=134, ungated) | Phase 0 (n=1224, gated) |
|---|---:|---:|
| Coverage of successful Bash bytes | 31.5% | **35.17%** |
| Coverage of all tool-result bytes | 9.69% | **8.77%** |
| Ceiling: tool results as share of input volume | 5.52% | **4.54%** |
| Projection at rtk's 60-90% claim | 0.32-0.48% | **0.239-0.359%** |
| Projection, mechanism modelled | 0.15-0.21% | **0.117-0.164%** |
| Reach of our own TOML presets | 1.91% of Bash | **1.08% of Bash** |
| `Read` share of tool-result bytes | 53.8% | **62.8%** |

Modelled effectiveness per family against the claim: `rtk grep` 75% claimed and
**9.0%** modelled; `rtk read` 60% claimed and **0.0%** modelled; `rtk rg` 75%
and 30%; `rtk make` 65% and 16%; `rtk jq` 74%.

Largest unaddressed buckets, as a share of successful Bash bytes: pipeline not a
rewritable final stage **39.78%**, ignored by rtk **10.72%**, entry gate
**8.29%**, multiline script **4.71%**.

### 2.6 Open question 3 answered: no

Patching `pipeline_final_safe` for `head` and `tail` unlocks 10.56 MB, 39.96% of
Bash bytes. **88.3% of that (9.33 MB) routes to `rtk read`, measured at 0.00%
saving** on this traffic because it returns files verbatim at the default
`--level none`. The largest reachable gap is reachable and worthless. The
argument for maintaining a fork does not survive its own measurement.

## 3. Why a pack rather than a native feature

- **Opt-in is structural, not a policy.** Plugin packs must not be
  auto-installed [PATH: kb/reference/plugin-pack-conventions.md]. The retired
  output filter shipped `off` by default and still had to be wired into every
  install path, which is why v4.17.0 needed a bespoke migration cleanup.
- **Removal is already solved.** `plugin remove` strips hook entries from
  `settings.json`, deletes owned `plugin-<pack>-*` assets, and leaves core and
  user files alone.
- **The core package stays lean.** ai-toolkit is 4.4 MB unpacked; the platform
  artifacts are ~19.5 MB compressed. They never enter the base package.
- **There is a working precedent.** `memory-pack` ships hooks, a shared script
  directory, an install-time init script, its own data with retention, and a
  clean uninstall. `rtk-pack` is the same shape with a binary instead of a
  database.

## 4. Architecture

```text
app/plugins/rtk-pack/
├── plugin.json          # pinned rtk version + per-platform SHA-256
├── README.md
├── hooks/
│   └── rewrite.sh       # PreToolUse; delegates to the fetched binary
├── scripts/
│   ├── init.py          # platform detect → fetch → verify → install → trust
│   └── measure.py       # replay-based saving measurement
├── filters/
│   └── softspark.toml   # our own presets (section 7)
└── skills/
    └── rtk-report/      # optional: surface measured savings on demand
```

Runtime layout on a user machine:

```text
~/.softspark/ai-toolkit/
├── hooks/plugin-rtk-pack-rewrite.sh        # installed hook
└── plugin-scripts/rtk-pack/
    ├── bin/rtk                              # verified binary, 0755
    └── version.json                         # pinned version + recorded digest
<dirs::config_dir()>/rtk/filters.toml        # our presets, user scope
<dirs::data_local_dir()>/rtk/trusted_filters.json   # rtk's trust store
```

The global filter path is **not** `~/.config/rtk/filters.toml` on every
platform. `trust.rs:206-216` builds it from `dirs::config_dir()`, which on
macOS is `~/Library/Application Support`, so the file lands at
`~/Library/Application Support/rtk/filters.toml`. rtk's own error text hardcodes
the Linux path and is wrong on macOS. The installer must resolve this per OS and
must not copy the path from rtk's messages or README.

Binary supply chain:

```text
upstream tag  →  our CI cross-build (RTK_TELEMETRY_URL unset)
              →  our GitHub Release  softspark-rtk-<upstream>-<build>
              →  SHA-256 recorded in plugin.json
              →  plugin install: detect platform, fetch, verify, chmod, trust
```

## 5. Phase 1: build pipeline and binary release

**Outcome:** we can produce, from an upstream tag, a set of binaries that
provably make no network calls of their own.

**Targets: five, not six.** `x86_64-apple-darwin`, `aarch64-apple-darwin`,
`x86_64-unknown-linux-musl`, `aarch64-unknown-linux-gnu`,
`x86_64-pc-windows-msvc`. Earlier revisions added `x86_64-unknown-linux-gnu` on
the reasoning that upstream does not ship it. It is dropped: upstream's own
Homebrew formula routes Linux x86_64 to the **musl** tarball
(`release.yml:314-316`), a static musl binary runs on glibc, and upstream has
never validated a gnu x86_64 artifact, so we would be first to ship one and
would own all its breakage plus an uncontrolled glibc floor inherited from the
runner image.

Build constraints, all read from the pinned checkout:

- **Pin the toolchain.** Upstream uses `dtolnay/rust-toolchain@stable`
  (`release.yml:65,116`) with `warnings = "deny"` (`Cargo.toml:70-72`) and ships
  no `rust-toolchain` file. A future rustc lint turns our builds red with no
  change on either side. We pin an exact version at or above 1.91.
- **Windows must build natively.** `build.rs:6-13` emits
  `cargo:rustc-link-arg=/STACK:8388608` under `#[cfg(windows)]`, which in a
  build script is a **host** predicate. Cross-building Windows from Linux
  silently drops the 8 MiB stack reservation that upstream's own comment says is
  what makes `rtk.exe --version`, `--help`, and hook entry points start
  reliably. Build on `windows-latest`, or pass the link-arg explicitly.
- **Every target needs a target-capable C compiler.** rusqlite `bundled`
  (`Cargo.toml:26`) is not switchable off; there is no `[features]` table and no
  `cfg(feature` in `src/`. There is no pure-Rust escape route.
- **aarch64-linux is the hard case, but upstream already solves it** with
  `cross: true` on `ubuntu-latest` (`release.yml:51-54`). Copy that. Upstream
  sets only the linker env var and lets the `cc` crate guess the C compiler;
  export `CC_aarch64_unknown_linux_gnu` and `AR_aarch64_unknown_linux_gnu`
  explicitly so a runner image change surfaces as a clear error.
- **Run our own blocking `cargo audit`.** Upstream's is advisory: `ci.yml:88-96`
  swallows failures into a warning. Rebuilding from a tag inherits that
  lockfile, and on v0.44.0 it inherits four advisories across three of its 203
  crates. The audit and the build jobs apply the same remediation, so we audit
  the dependency set we ship rather than a different one:

  | Crate | Advisory | Disposition |
  |---|---|---|
  | `anyhow` 1.0.102 | RUSTSEC-2026-0190 | `cargo update` to 1.0.103, in range |
  | `crossbeam-epoch` 0.9.18 | RUSTSEC-2026-0204 | `cargo update` to 0.9.20, in range |
  | `quick-xml` 0.37.5 | RUSTSEC-2026-0194, RUSTSEC-2026-0195 | ignored with reasons |

  The quick-xml fix lands only in 0.41.0 while rtk pins `"0.37"` as a direct
  dependency (`Cargo.toml:34`), so taking it means editing `Cargo.toml` and the
  calling code in `src/cmds/dotnet/dotnet_trx.rs`. That would break the promise
  that the only difference from an upstream build is the undefined telemetry
  endpoint. The reachable surface is narrow: quick-xml parses .NET TRX test
  output only, the input is a report produced locally by the user's own test
  run, and both advisories are availability-only (CVSS `C:N/I:N/A:H`). The SOP
  re-checks this on every sync and deletes the ignores once upstream moves to
  quick-xml 0.41 or later.
- A target that will not build is dropped, not faked.

### 5.1 Proving the binary is silent

The endpoint is compile-time only: `option_env!("RTK_TELEMETRY_URL")` at
`telemetry.rs:16` and `telemetry_cmd.rs:176`, with the token at
`telemetry.rs:17` and `telemetry_cmd.rs:189`. Nothing supplies a default:
`build.rs` emits no `cargo:rustc-env`, `TelemetryConfig` has no URL field, and
no runtime `std::env::var` resolves the endpoint. Upstream injects it only in
`release.yml:85-86,124-125,151-152`. Building without it yields a binary whose
telemetry destination cannot be re-enabled by any env var or config at runtime.

**The acceptance criterion in earlier revisions was untestable and is replaced.**
"No telemetry symbols in the binary" cannot be checked: the guard is a runtime
`if TELEMETRY_URL.is_none()` on a const (`telemetry.rs:23-26`), not a `#[cfg]`,
so the code compiles in and is only eliminated by LLVM as an optimisation; and
`Cargo.toml:51` sets `strip = true`, which removes the symbols regardless of
whether the code is present. A symbol check would pass for the wrong reason.

What we assert instead:

1. **Build gate.** `RTK_TELEMETRY_URL` and `RTK_TELEMETRY_TOKEN` are unset in
   the build environment, asserted in CI before `cargo build`, with a clean
   target directory per build.
2. **Offline smoke run.** Each artifact runs its real command surface with no
   network route available and makes zero outbound connections. This is
   Linux-only: `unshare -rn` has no unprivileged equivalent on macOS or Windows
   runners, and Ubuntu 24.04's
   `kernel.apparmor_restrict_unprivileged_userns=1` means even there it needs
   `sudo`. On the first run this assertion silently degraded to a skip on every
   target while the verdict still read `pass`, so the manifest now records which
   isolator was used and a target that could not be started at all reports
   `inconclusive` rather than `pass`.
3. **Filesystem assertion.** No telemetry state is created under the resolved
   data directory.
4. **Drift detection.** Record artifact size and a string-allowlist hash per
   target and fail the build on unexplained drift, since whether `ureq`,
   `rustls`, `ring` and `webpki-roots` are actually eliminated is an LLVM
   outcome under `lto = true`, not a guarantee.

Three findings that must reach the pack README:

- **`rtk cc` shells out to `npx --yes ccusage`** when `ccusage` is not on PATH
  (`ccusage.rs:104-119`). That is a runtime npm fetch and third-party code
  execution. It is not telemetry and not automatic, but it is outbound network
  from a binary we tell users makes no network calls.
- **`RTK_TELEMETRY_DISABLED` only accepts the exact string `1`**
  (`telemetry_cmd.rs:31-33`, locked by the test at `:222-229`). `true` and `yes`
  are silent no-ops. Never write anything else anywhere in the pack.
- **`rtk telemetry forget` on an endpoint-free build prints a misleading
  failure** telling the user to email upstream to complete erasure
  (`telemetry_cmd.rs:158-169`), when nothing was ever sent.

Apache-2.0 obligations ship alongside: upstream `LICENSE`, a `NOTICE` file
(upstream has none), and a statement that the only build-time change is leaving
the telemetry endpoint undefined. **Do not redistribute upstream
`DISCLAIMER.md` verbatim**: `DISCLAIMER.md:25` states telemetry is collected by
default, which the code contradicts and which a compliance reviewer would read
as a reason to block the pack. `docs/TELEMETRY.md:180` calls the mechanism
"compile-time gating" where "all telemetry code is dead", which is imprecise for
the same reason our own criterion changed.

**Success criteria:** five artifacts build from the pinned tag; each runs
`rtk --version` on its target; the four silence assertions pass; checksums
published.

## 6. Phase 2: the pack

**Outcome:** `ai-toolkit plugin install rtk-pack` produces a working setup and
`plugin remove` leaves nothing behind.

- `scripts/init.py` detects platform and libc, fetches the matching artifact,
  verifies its SHA-256 against `plugin.json`, and installs to
  `plugin-scripts/rtk-pack/bin/rtk`. A mismatch aborts and removes the partial
  download. No network at runtime, only at install.
- Failure to fetch is not an install failure: the pack degrades to inert and
  says so, matching how the core behaves when `jq` is missing.
- The hook is wired at `PreToolUse` through the existing pack hook mechanism, so
  `plugin remove` strips it via the `_source` marker.
- `plugin status` reports rtk version, digest match, and hook wiring.
- `ai-toolkit doctor` gains an rtk-pack section.

### 6.1 The trust step is mandatory, and it is where this pack fails silently

An untrusted or content-changed preset produces **zero output on the command
path with no warning, no stderr line, and no non-zero exit**
(`toml_filter.rs:220-221`, `:450-458`). That is the same shape of failure as the
retired filter's 0%: installed, apparently fine, doing nothing. Install must end
with a verification step, not a write.

Rules the installer and doctor must follow, each read from the pinned source:

- **Re-trust after every write.** Trust is a byte-exact SHA-256 comparison
  (`trust.rs:142-163`). A pack upgrade, a repair, an added trailing newline, or
  git CRLF normalisation on Windows all invalidate it.
- **Run `rtk trust --yes` from a scratch directory.** It is indiscriminate and
  trusts every gated file that exists, including a `.rtk/filters.toml` an
  attacker committed into whatever repo happens to be the CWD
  (`trust.rs:262-305`, project path is CWD-relative at `:207`).
- **Branch on its exit code.** `rtk trust --yes` exits 1 both when there is
  nothing to trust and when the file is invalid TOML (`trust.rs:307-312`). Under
  `set -e` a naive installer aborts on the benign case. Treat "not valid TOML"
  as a hard failure, because the preset would be a permanent no-op.
- **Doctor must re-hash, not list.** There is no `rtk doctor`, and
  `rtk trust --list` always exits 0 and never re-hashes (`trust.rs:242-256`).
  Our doctor reads the trust store, canonicalises the preset path the way rtk
  does (`trust.rs:80-86`), and compares the stored digest to a freshly computed
  one.
- **Inject between markers, do not own the file.** The global `filters.toml` is
  a single file with no include mechanism, and the merge-friendly install model
  [PATH: kb/reference/merge-friendly-install-model.md] forbids full-file
  replacement. Presets go between TOML comment markers, the same way
  `constitution.md` and `CLAUDE.md` are handled, so a user's own filters
  survive install, update, and removal. See open question 5.
- **Prefer the global path over a project-scoped file.** The trust key is a
  canonicalised absolute path, so a moved checkout, a changed `$HOME` symlink, a
  container mount point, or macOS `/var` versus `/private/var` all silently
  invalidate a project entry. `.rtk/filters.toml` is also resolved against the
  process CWD with no repo-root walk (`toml_filter.rs:677`), so an agent that
  cd's into a subdirectory loses it mid-session.
- **Never set `RTK_TRUST_PROJECT_FILTERS=1` outside CI.** Without a recognised
  CI marker it is ignored and prints a warning per gated file
  (`trust.rs:104-118`).
- **Serialise the trust step.** The store is written non-atomically with no lock
  (`trust.rs:65-74`).

**Success criteria:** install, status, update, remove, and re-install are
idempotent; a machine without the pack behaves exactly as today; uninstalling
ai-toolkit removes every pack artifact; and a post-install assertion proves the
preset is trusted and its digest matches.

## 7. Phase 3: our own filter presets

**Outcome, revised down.** Phase 0 measured what this phase can reach:
**1.08% of Bash bytes**, which is 0.27% of tool-result bytes. At a generous 60%
reduction that is **0.008% of input tokens**. Phase 3 as originally scoped does
not earn its maintenance cost, and the decision on whether to keep it, cut it to
a single measured preset, or drop it belongs to the plan owner. The engineering
constraints below hold either way, because they also govern any preset we ship.

rtk's TOML DSL is a documented public interface, but the shipped documentation
is wrong in several places and the structs are the only reliable source.

- **One unknown key rejects the entire file.** `deny_unknown_fields` propagates
  a parse error out of `parse_and_compile` before any filter compiles
  (`toml_filter.rs:226-227`), whereas a bad regex only drops one filter
  (`:237-242`). A key added by a future rtk version silently disables everything.
- **Precedence inside a file is alphabetical by filter name**, not file order
  (`toml_filter.rs:76`, `:237`, first match wins at `:481-486`). A specific
  filter placed above a general one still loses if it sorts later.
- **`strip_lines_matching` and `keep_lines_matching` return `Lossiness::None`**
  (`toml_filter.rs:642,647`), so no tee file is written and no recovery hint is
  emitted. Content is dropped with no way back. This collides directly with the
  retention rules carried over from the retired effort: never elide a
  diagnostic, a file location, a severity, or a rule name, and never compress
  failure output. A preset that must stay recoverable needs `head_lines` or
  `max_lines` to reach `Lossiness::Tail`.
- **With tee disabled the savings are zero.** Every lossy result is discarded
  and the full raw output printed instead (`main.rs:1356`). Tee is a hard
  dependency of any saving claim.
- **Presets never fire in the final stage of a pipeline.** TOML-only commands
  return before the filter lookup in `RewriteContext::PipelineFinal`
  (`registry.rs:1043-1046`). Do not advertise pipeline coverage; smoke tests
  must invoke commands standalone or they produce a false negative.
- **`rtk verify` is not an acceptance gate.** It never loads the user-global
  file (`toml_filter.rs:661-699`), and it calls `apply_filter` directly,
  bypassing the never-worse guard, so a preset can pass verify and behave
  differently in production.
- **Reserved names are dead on arrival.** A preset whose `match_command` hits
  `RUST_HANDLED_COMMANDS` or `RTK_META_COMMANDS` never runs; rtk warns only at
  filter compile time (`toml_filter.rs:250-326`). Validate at pack build time.
- **Pin `schema_version = 1`.** `rtk trust`'s pre-flight listing does not check
  it while the loader does, so a wrong version lists fine and then filters
  nothing.

**Success criteria:** each preset measured on owned fixtures against real
captured output; presets install, trust cleanly, verify their trust digest, and
survive `plugin update`.

## 8. Phase 4: auto-update on `ai-toolkit update`

**Outcome:** a user who installed the pack gets the new binary and presets by
running the update they already run.

Verified gap: `handleUpdate` in `bin/ai-toolkit.js` reads installed modules from
`state.json` and does not touch `plugins.json`. Nothing propagates to packs
today, so this is new wiring, not a configuration change.

- After the core update completes, `ai-toolkit update` reads `plugins.json` and
  runs the equivalent of `plugin update` for every **currently installed** pack.
  Packs that are not installed stay untouched, which preserves adoption rule 1.
- The rtk-pack update path is: compare the manifest's pinned version against the
  recorded `version.json`; if they differ, fetch and verify the new binary, then
  re-install hooks and presets **and re-run the trust step**, because any write
  invalidates the digest.
- `--dry-run` reports what would change per pack.
- A pack update failure warns and continues; it never fails the core update.
- Bats coverage: stale binary replaced; current binary untouched; pack absent
  means no work; fetch failure warns without breaking the core update; and a
  preset rewrite leaves the filter trusted rather than silently inert.

**Success criteria:** the wiring is generic across packs, not rtk-specific;
`update` remains idempotent; a failed pack update never leaves a half-installed
binary.

## 9. Phase 5: upstream sync SOP

**Outcome:** a written procedure so tracking upstream is routine rather than a
research project each time. Lands as `kb/procedures/rtk-upstream-sync-sop.md`,
modelled on the existing ecosystem-sync SOP.

The 0.43.0 to 0.44.0 bump is a worked example of why the review step exists: 200
commits, and every file the SOP names changed, including a semantic inversion in
pipeline rewriting and the arrival of the trust gate.

Steps the SOP must cover:

1. **Detect.** Check the upstream releases feed for a tag newer than the pinned
   one. Their stable cadence is roughly two to four weeks, behind a long
   release-candidate train. Cadence: on demand, plus a check folded into release
   preparation.
2. **Review before building.** Read the changelog and diff `src/discover/rules.rs`,
   `src/discover/registry.rs`, `src/discover/lexer.rs`, `IGNORED_PREFIXES`, the
   TOML DSL structs in `src/core/toml_filter.rs`, `src/hooks/trust.rs`, and
   anything touching telemetry. A change to the DSL or to trust handling is a
   stop-and-think, not a rebuild.
3. **Re-validate the port.** Re-extract the `rewrite_command` assertions from the
   new tag's `registry.rs` test block and the gate assertions from `lexer.rs`,
   and replay both. Anything short of full agreement invalidates every coverage
   number until the port is fixed.
4. **Rebuild** all five targets from the new tag with telemetry unset.
5. **Verify.** Binary runs on each target; the four silence assertions pass; our
   presets still parse, still trust, and still fire; the pack's fixtures still
   produce the expected decisions.
6. **Publish** a new release in our namespace and record the new digests.
7. **Bump** `rtk-pack` version in `plugin.json` and note the upstream version it
   tracks. Pack version is ours; upstream version is a separate field, so a
   preset-only change does not pretend to be an upstream bump.
8. **Ship** in the next ai-toolkit release; installed packs pick it up through
   Phase 4.
9. **Record** the licence position if upstream relicenses or adds a NOTICE.

There is no upstream test asserting network silence, so that property can
regress on any bump without turning their CI red. We own that test and re-run it
every time.

**Success criteria:** a maintainer who has never done it can follow the SOP end
to end; the review step names specific files rather than saying "check for
breaking changes".

## 10. Verification

The pack must be able to answer "did this help?" with a number.

**The before-and-after design is replaced.** Phase 0 measured its noise floor:
on a 134-transcript window the projected saving varies by 8.8x while the
mechanism is unchanged. A before-and-after comparison cannot detect an effect of
0.117% to 0.164% against that. Two changes make the measurement possible:

- **Measure over the whole transcript pool, not a recency window.** At n>=408
  the same metric converges to within 1.05x.
- **Measure by replay, not by elapsed calendar time.** Run real captured tool
  output through the built binary and compare byte counts directly. That is the
  method that produced the honest 0% which retired the in-house filter, and it
  removes the confound of what work the user happened to do that week.

`scripts/measure.py` reports session input tokens from the session JSONL
[PATH: scripts/session_token_stats.py], summing all four usage fields, since in
a cached session most context tokens land in the cache fields rather than
`input_tokens`.

**Kill number, published before the measurement rather than argued after it:**
if replay on the full corpus shows the shipped binary saving less than 0.05% of
input tokens, the pack is not worth its maintenance and supply-chain surface,
and it is retired the way the output filter was.

The projection to beat: **0.117% to 0.164%**, or 0.239% to 0.359% if rtk's own
60-90% claim holds on this traffic, against an arithmetic ceiling of 4.54% for
any tool-output mechanism. If the live number lands near the vendor claim, the
projection was wrong about this workload and that belongs in the KB.

## 11. Licence and security obligations

- **Apache-2.0.** Ship upstream `LICENSE` with the binaries, add a `NOTICE`, and
  state the build-time change. Never relabel any upstream file MIT. Do not ship
  `DISCLAIMER.md` verbatim, see section 5.1.
- **Telemetry.** Proven absent per build by the four assertions in section 5.1,
  re-proven on every upstream sync.
- **Supply chain.** Digests pinned in `plugin.json`, verified on fetch,
  re-verified by `doctor`. This mirrors the existing checksum-pin discipline for
  URL-sourced rules and hooks. Run a blocking `cargo audit` on the pinned
  lockfile, because upstream's is advisory.
- **Trust boundary.** rtk rewrites commands before execution, which the retired
  in-house contract explicitly forbade for itself. Adopting it is a conscious
  reversal of that constraint and its own threat surface: what runs is not what
  the model asked for. The pack's README must say this plainly, and
  `plugin install` must not be silent about it. The README must also disclose
  the `rtk cc` npx path.

## 12. Pre-mortem

| Rank | Failure mode | Probability | Impact | Mitigation |
|---:|---|:---:|:---:|---|
| 1 | Presets install but are untrusted, so they silently do nothing | High | High | Install ends in a verification step; doctor re-hashes; `rtk trust` exit code branched on. Section 6.1 |
| 2 | Cross-building with bundled SQLite is fragile in CI | Medium | Medium | Copy upstream's `cross` setup for aarch64-linux; five targets not six; a target that will not build is dropped, not faked |
| 3 | Pre-execution rewriting changes command semantics | Medium | High | Opt-in pack, documented one-flag disable, upstream's own review process, our integration tests on real commands |
| 4 | Windows binary cross-built without the 8 MiB stack reservation | Medium | High | Build natively on `windows-latest`, or pass the link-arg explicitly. `build.rs:6-13` |
| 5 | Upstream velocity breaks our presets or the DSL | Medium | Medium | Pinned version, SOP review step naming exact files, port re-validation as a gate, fork option preserved by Apache-2.0 |
| 6 | Unpinned toolchain plus `warnings = "deny"` turns builds red with no change | Medium | Low | Pin an exact rustc version; treat bumps as deliberate |
| 7 | A fetch failure leaves a half-installed pack | Medium | Medium | Verify-then-install, abort and clean on digest mismatch, `doctor` detects drift |
| 8 | Live saving lands near the projection, not the claim | High | Medium | Section 10 measures it by replay either way, against a published kill number |
| 9 | The auto-update wiring makes `update` slower or flakier | Low | Medium | Skip when versions match, warn-and-continue on failure, `--dry-run` coverage |
| 10 | The pack drifts into being installed by default | Low | High | Adoption rule 1 plus a test asserting `install` never pulls it in |

## 13. Open questions

1. ~~Which upstream tag do we pin first?~~ **Answered: v0.44.0.** See section 2.1.
2. Do our presets install to user scope only, or also offer a project-scoped
   variant for registered projects? Section 6.1 argues for user scope only: the
   project path is CWD-relative with no repo-root walk, and its trust key breaks
   on any path change.
3. ~~Is patching `pipeline_final_safe` for `head`/`tail` in scope later?~~
   **Answered: no.** See section 2.6.
4. **New.** Does Phase 3 survive its own measurement at 0.008% of input tokens,
   and if it ships in reduced form, which single preset is worth the trust and
   maintenance surface?
5. **New, and mostly answered by existing convention.** rtk has exactly one
   global filter file with no include or merge mechanism (`trust.rs:206-216`).
   The merge-friendly install model
   [PATH: kb/reference/merge-friendly-install-model.md] rules out full-file
   replacement and prescribes **marker injection** for exactly this shape, the
   same strategy already used for `constitution.md`, `ARCHITECTURE.md` and
   `CLAUDE.md`: user content outside the markers is preserved and uninstall
   removes only the marked block. TOML comments carry the markers.

   Two things that model does not anticipate, and which the pack must handle:

   - **Any write invalidates trust.** Injection must be followed by
     `rtk trust --yes`, and so must a user's own edit outside the markers,
     which rtk accepts silently while filtering nothing. Only our doctor check
     surfaces that state.
   - **Marker position does not set precedence.** Ordering inside the file is
     alphabetical by filter name (`toml_filter.rs:76,237`), so the injected
     block cannot rely on being first. Preset names carry the namespace that
     makes ordering deterministic.

   What remains open is narrow: does the pack refuse to inject when the file
   already contains a `[filters.*]` table whose `match_command` overlaps a
   preset, or inject anyway and report the collision through doctor?
