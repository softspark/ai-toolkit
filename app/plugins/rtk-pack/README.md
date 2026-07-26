# rtk-pack

Opt-in command rewriting via [rtk](https://github.com/rtk-ai/rtk), Apache-2.0.

Install: `ai-toolkit plugin install rtk-pack`. Remove: `ai-toolkit plugin remove rtk-pack`.
Nothing installs it for you, and nothing in the core depends on it.

## Read this before installing

**This pack rewrites your commands before they run.** A `PreToolUse` hook hands
each command to `rtk`, which may replace it with an `rtk` equivalent that
produces shorter output. What executes is therefore not literally what the model
asked for.

That is a real trade-off and the reason this ships as an opt-in pack rather than
a core feature. ai-toolkit's own retired output filter explicitly refused to do
this. Adopting rtk is a deliberate reversal, made with the mechanism understood
rather than assumed.

**Your permission rules are evaluated against the original command, and the
verdict is applied to the rewritten one.** rtk checks what the model asked for
against your `settings.json`, and if a rule allows it, emits
`permissionDecision: allow` for the `rtk …` form it substituted. So an allowlist
entry for `git status` transitively authorises `rtk git status`, a command you
never wrote a rule for. With no matching allow rule, no decision is emitted and
your normal prompt appears. Verified against upstream's own test at
`src/hooks/hook_cmd.rs:1272-1283`.

If your allowlist is broad, review it before installing. If it is narrow, expect
prompts on commands that used to run without one.

Every failure path degrades to passthrough: no binary, a non-zero exit, a
timeout, or unparseable output all result in the original command running
unchanged. Removing the pack strips the hook from `settings.json`.

## What you get, measured

On the reference workload (1224 local transcripts, 26.6 MB of successful Bash
output) rtk addresses **35.2%** of Bash bytes, which is **8.8%** of all
tool-result bytes. The projected saving is **0.12% to 0.16%** of session input
tokens, or 0.24% to 0.36% if rtk's own 60-90% claim holds on your traffic.

That is small, and it is stated up front on purpose. The arithmetic ceiling for
any tool-output mechanism on that workload is 4.5%, because tool results are
that share of input token volume, and `Read` results are 63% of them. If your
work is dominated by `cargo test`, `mvn` or `jest` output rather than file
reading, rtk is calibrated for you and will do better. Measure before believing
either number.

Full method and caveats: `kb/history/completed/rtk-pack-integration-20260726.md`.

## The binary

Not bundled. `plugin install` fetches the artifact for your platform from an
ai-toolkit GitHub Release and verifies its SHA-256 against `plugin.json` before
installing anything. A digest mismatch aborts and leaves nothing behind. This is
the only moment the pack uses the network.

Binaries are cross-built from upstream source in ai-toolkit CI with
`RTK_TELEMETRY_URL` and `RTK_TELEMETRY_TOKEN` left undefined, so the
compile-time telemetry endpoint is absent and cannot be supplied at runtime.
Each build asserts that, runs the artifact, checks no telemetry state is
written, and on Linux confirms behaviour is unchanged with no network route.

| Platform | Artifact |
|---|---|
| macOS arm64 | `rtk-aarch64-apple-darwin.tar.gz` |
| macOS x86_64 | `rtk-x86_64-apple-darwin.tar.gz` |
| Linux x86_64 | `rtk-x86_64-unknown-linux-musl.tar.gz` (static, runs on glibc) |
| Linux aarch64 | `rtk-aarch64-unknown-linux-gnu.tar.gz` |
| Windows x86_64 | `rtk-x86_64-pc-windows-msvc.zip` |

## One thing the binary does reach the network for

`rtk cc` (Claude economics) shells out to `npx --yes ccusage` when `ccusage` is
not already on `PATH`, which fetches and executes a third-party npm package.
That is not telemetry and never happens automatically, but it is outbound
network from a binary otherwise described as silent. Do not run `rtk cc` in an
air-gapped or policy-restricted environment.

Related: `rtk telemetry forget` on these builds prints a failure telling you to
email upstream to complete erasure. Nothing was ever sent; the message is
upstream's and does not apply here.

## Layout

```
~/.softspark/ai-toolkit/
├── hooks/plugin-rtk-pack-rewrite.sh     # the PreToolUse hook
└── plugin-scripts/rtk-pack/
    ├── bin/rtk                          # verified binary
    └── version.json                     # pinned versions and recorded digest
```

## Installing from a mirror

Set `RTK_PACK_RELEASE_BASE_URL` to a base URL holding the release assets and the
install fetches from there instead of GitHub, for networks that cannot reach it
directly:

```bash
RTK_PACK_RELEASE_BASE_URL=https://mirror.internal/rtk/v0.44.0-1 \
  ai-toolkit plugin install rtk-pack
```

The digest check is unchanged. A mirror serving different bytes is rejected
exactly like a corrupt download, so this widens where the artifact comes from
without widening what is accepted.

## Disabling without removing

`rtk` honours `RTK_DISABLED=1` as a per-command prefix. To turn the pack off
entirely, remove it: `ai-toolkit plugin remove rtk-pack`.

## Licence

rtk is Apache-2.0. `LICENSE` and `NOTICE` ship with every release artifact. The
NOTICE records the two build-time differences from an upstream build: the
undefined telemetry endpoint, and in-range lockfile security updates for
`anyhow` and `crossbeam-epoch`. No upstream source is modified.

Upstream `DISCLAIMER.md` is deliberately not redistributed: it states that
telemetry is collected by default, which is not true of these builds.
