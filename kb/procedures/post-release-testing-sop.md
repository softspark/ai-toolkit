---
title: "SOP: Post-Release Testing"
category: procedures
service: ai-toolkit
tags: [sop, post-release, smoke-test, npm, sandbox, plugin-pack, provenance, isolation]
version: "1.0.0"
created: "2026-07-26"
last_updated: "2026-07-26"
description: "Smoke-test a published @softspark/ai-toolkit release from npm in an isolated HOME and npm prefix, without touching the maintainer's real install. Covers provenance, CLI, doctor, and the full plugin-pack lifecycle including the degraded-install path. Written after v4.18.0, the first release shipping a pack that downloads a binary."
---

# SOP: Post-Release Testing

Runs **after** `publish.yml` succeeds on a tag. Verifies the artifact users will
actually install, from npm, rather than the working tree.

Sibling procedures exist for `jira-mcp` and `legal-pl-pack`; this is the
ai-toolkit equivalent. It complements
[Release Verification](release-verification-sop.md), which checks the toolkit
from the maintainer's own installed copy. The difference that matters: this one
never writes to the maintainer's `~/.claude` or `~/.softspark`.

**Time:** 10 minutes.

## Why isolation is the first step, not a detail

The toolkit installs into `$HOME`. Testing a release against your own HOME
means the test either pollutes your working setup or, worse, passes because of
state your setup already had. Both make the result meaningless.

Every command below runs against a throwaway HOME and a throwaway npm prefix.
Nothing is global.

## Phase 1: Sandbox

```bash
SB=$(mktemp -d)
mkdir -p "$SB/home" "$SB/npm"
export HOME="$SB/home"
AT="$SB/npm/bin/ai-toolkit"
echo "sandbox: $SB"
```

Record the real state now, so Phase 7 can prove it is unchanged:

```bash
python3 -c "
import json, pathlib
p = pathlib.Path('$SB/../real-before.json')
import os
home = pathlib.Path(os.path.expanduser('~'))
" 2>/dev/null
# Simpler: note what exists today.
cat ~/.softspark/ai-toolkit/plugins.json 2>/dev/null
```

## Phase 2: Provenance

Do this before installing anything: an unsigned publish is a release-blocking
regression, and there is no point smoke-testing a build you would have to redo.

```bash
VERSION="X.Y.Z"
npm view "@softspark/ai-toolkit@${VERSION}" --json \
  | python3 -c "
import json, sys
d = json.load(sys.stdin); att = d['dist'].get('attestations', {})
pt = att.get('provenance', {}).get('predicateType')
assert pt == 'https://slsa.dev/provenance/v1', f'NO PROVENANCE: {pt}'
print('PROVENANCE OK:', att['url'])
"
```

## Phase 3: Install from npm

```bash
npm install -g --prefix "$SB/npm" "@softspark/ai-toolkit@${VERSION}"
"$AT" --version    # must equal VERSION
"$AT" --help >/dev/null && echo "help OK"
```

## Phase 4: Core surfaces

```bash
"$AT" install            # full global install into the sandbox HOME
"$AT" doctor             # must end: Errors: 0 | Warnings: 0
"$AT" status
"$AT" plugin list        # pack count must match app/plugins/
```

**A doctor run before `install` reports `agents directory missing` and
`skills directory missing`.** That is the sandbox being empty, not a defect.
Install first, then judge doctor.

## Phase 5: Plugin-pack lifecycle

Run this for any pack the release touched. For a pack that downloads a binary,
every step below has caught a real defect at least once.

```bash
"$AT" plugin install <pack>
"$AT" plugin status                       # does it report itself working?
find "$HOME/.softspark/ai-toolkit" -path '*<pack>*'   # what actually landed
```

**Verify:**
- [ ] `plugin status` distinguishes *installed* from *working*, not just present
- [ ] For a binary pack: the binary runs and reports the pinned upstream version
- [ ] The hook is registered in `~/.claude/settings.json` with the pack's `_source`

**Does it do its job?** Presence is not function. Drive the hook directly:

```bash
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"git status"}}' \
  | bash "$HOME/.softspark/ai-toolkit/hooks/plugin-<pack>-<hook>.sh"
```

**Update path:**

```bash
"$AT" plugin update --editor claude --all            # current version: silent
"$AT" plugin update --editor claude --all --dry-run  # says "up to date"
# force a stale marker, then confirm it updates and re-records:
python3 -c "
import json, pathlib, os
p = pathlib.Path(os.environ['HOME'] + '/.softspark/ai-toolkit/plugins.json')
d = json.loads(p.read_text()); d['targets']['claude']['versions']['<pack>'] = '0.0.9'
p.write_text(json.dumps(d, indent=2))
"
"$AT" plugin update --editor claude --all            # reports 0.0.9 -> <version>
"$AT" update                                          # core update leaves a current pack alone
```

**Removal must be complete:**

```bash
"$AT" plugin remove <pack>
find "$HOME/.softspark" -path '*<pack>*' | wc -l      # must be 0
python3 -c "
import json, pathlib, os
d = json.loads(pathlib.Path(os.environ['HOME'] + '/.claude/settings.json').read_text())
print('hook still present:', '<pack>' in json.dumps(d.get('hooks', {})))
"
"$AT" plugin install <pack>                           # re-install must work
```

## Phase 6: The degraded path

**This is the step most worth keeping.** A pack that fetches anything can fail
to fetch, and the failure mode must be inert rather than broken or silent.

```bash
"$AT" plugin remove <pack>
RTK_PACK_RELEASE_BASE_URL="file:///nonexistent" "$AT" plugin install <pack>
```

**Verify:**
- [ ] Install reports the failure in words a user can act on, and does not claim success
- [ ] No partial artifact is left behind
- [ ] The hook is still wired, and passes commands through untouched
- [ ] `plugin status` says the pack is inert and names the fix
- [ ] Re-installing without the broken source recovers

## Phase 7: Prove the real environment is untouched

```bash
python3 -c "
import json, pathlib
d = json.loads(pathlib.Path.home().joinpath('.softspark/ai-toolkit/plugins.json').read_text())
print('plugins.json:', d['targets']['claude'])
p = pathlib.Path.home() / '.claude/settings.json'
print('pack hook leaked into real settings:', '<pack>' in json.dumps(json.loads(p.read_text()).get('hooks', {})) if p.exists() else False)
print('pack paths in real ~/.softspark:', len(list(pathlib.Path.home().joinpath('.softspark').rglob('*<pack>*'))))
"
```

All three must show the pre-test state.

## Phase 8: Clean up

`guard-destructive.sh` blocks `rm -rf` on a `PreToolUse` hook, so removal goes
through an enumerated delete that reports what it removed:

```bash
python3 -c "
import pathlib, shutil
sb = pathlib.Path('$SB')
assert sb.is_dir() and str(sb).startswith(('/tmp', '/var/folders')), sb
n = sum(1 for _ in sb.rglob('*') if _.is_file())
shutil.rmtree(sb)
print(f'removed {sb} ({n} files)')
"
```

## Success criteria

| Area | Criterion |
|---|---|
| Supply chain | `predicateType == https://slsa.dev/provenance/v1` |
| CLI | `--version` equals the tag, `--help` renders |
| Health | `doctor` after `install`: 0 errors, 0 warnings |
| Catalog | `plugin list` count matches `app/plugins/` |
| Pack install | Binary present, runs, digest verified, hook registered |
| Pack function | Driving the hook produces the expected effect, not just exit 0 |
| Pack update | Current version silent; stale version updates and re-records |
| Pack removal | Zero residue in `~/.softspark` and `settings.json`; re-install works |
| Degraded path | Fetch failure is inert, loud in status, and recoverable |
| Isolation | Real `~/.claude` and `~/.softspark` byte-identical to pre-test |

## Related

- [Release Preparation](release-preparation-sop.md) — run before tagging
- [Release Verification](release-verification-sop.md) — the maintainer-install checks
- [rtk Upstream Sync](rtk-upstream-sync-sop.md) — for the pack whose binary this SOP exercises
