---
title: "SOP: Post-Release Testing"
category: procedures
service: ai-toolkit
tags: [sop, post-release, smoke-test, npm, sandbox, plugin-pack, provenance, isolation]
version: "1.2.2"
created: "2026-07-26"
last_updated: "2026-09-08"
description: "Smoke-test a published @softspark/ai-toolkit npm artifact in a disposable container or VM with its default HOME, no host settings or credential mounts, host-side configuration fingerprints, and retained evidence. Covers provenance, CLI, doctor, installed skill scripts, scanner wiring, and the plugin-pack lifecycle."
---

# SOP: Post-Release Testing

Runs **after** `publish.yml` succeeds on a tag. Verifies the artifact users will
actually install, from npm, rather than the working tree.

Sibling procedures exist for `jira-mcp` and `legal-pl-pack`; this is the
ai-toolkit equivalent. It complements
[Release Verification](sop-release-verification.md), whose cross-editor checks
must use the same isolated published artifact. Neither procedure installs or
updates the maintainer's working copy.

**Time:** 10 minutes.

## Why isolation is the first step, not a detail

The toolkit writes settings beneath the current user's home directory. Run the
published artifact in a disposable Docker container or VM with its normal HOME.
Do not override host HOME, CODEX_HOME, or another editor's configuration root as
a substitute for isolation. Do not expose the host home, credentials, SSH agent,
Docker socket, or existing toolkit installation to the test environment.

## Phase 1: Create and verify an isolated test environment

The recipe below uses Docker. A disposable VM is equivalent only when host shared
folders and authentication forwarding are absent. The host needs Docker and
Python 3; the container prerequisites are installed separately below.

**Host terminal:** keep this terminal open for Phases 7 and 8. The fingerprint
reads only these toolkit-managed settings files and records hashes and presence,
never their contents. Add a path only after verifying that the tested installer
actually manages it.

```bash
set -o pipefail
VERSION="X.Y.Z"
EVIDENCE=$(mktemp -d "${TMPDIR:-/tmp}/ai-toolkit-release-${VERSION}.XXXXXX")
SMOKE_CONTAINER=$(python3 -c 'import uuid; print("ai-toolkit-smoke-" + uuid.uuid4().hex)')

fingerprint_host() {
  python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

home = Path.home()
managed = [
    ".claude/settings.json",
    ".claude.json",
    ".softspark/ai-toolkit/plugins.json",
    ".codex/config.toml",
    ".cursor/mcp.json",
    ".gemini/settings.json",
    ".config/opencode/opencode.json",
]
rows = {}
for relative in managed:
    path = home / relative
    row = {"exists": path.exists() or path.is_symlink()}
    if path.is_symlink():
        row["link_sha256"] = hashlib.sha256(os.readlink(path).encode()).hexdigest()
    if path.is_file():
        row["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    rows[relative] = row
print(json.dumps({
    "host_home_sha256": hashlib.sha256(str(home).encode()).hexdigest(),
    "files": rows,
}, sort_keys=True, indent=2))
PY
}

fingerprint_host > "$EVIDENCE/host-before.json"
docker run -d --name "$SMOKE_CONTAINER" \
  --label "org.softspark.release-smoke=$SMOKE_CONTAINER" \
  --env "VERSION=$VERSION" \
  node:22-bookworm sleep infinity
docker inspect "$SMOKE_CONTAINER" > "$EVIDENCE/container-before.json"
python3 - "$EVIDENCE/container-before.json" <<'PY'
import json
import sys

container = json.load(open(sys.argv[1], encoding="utf-8"))[0]
assert container["Mounts"] == [], "Smoke container must have no mounts"
host = container["HostConfig"]
assert not host["Privileged"], "Privileged containers are forbidden"
assert host["NetworkMode"] != "host", "Do not share the host network namespace"
assert host["PidMode"] != "host", "Do not share host processes"
PY
docker exec "$SMOKE_CONTAINER" bash -lc \
  'test "$HOME" = "$(getent passwd "$(id -u)" | cut -d: -f6)"'
docker exec "$SMOKE_CONTAINER" bash -lc \
  'apt-get update && apt-get install -y --no-install-recommends python3 python3-yaml git coreutils jq bats shellcheck ca-certificates curl util-linux' \
  2>&1 | tee "$EVIDENCE/bootstrap.log"
```

Install any additional prerequisite declared by the pack under test only inside
the container. GNU coreutils supplies timeout; util-linux supplies the session
recorder. Use docker cp for evidence transfer, not host temporary-directory bind
mounts: a remote Docker daemon may not see the host's /private/tmp.

**Enter the container, then run Phases 2 through 6 there:**

```bash
docker exec -it "$SMOKE_CONTAINER" bash
```

Inside that container shell:

```bash
SB=/tmp/ai-toolkit-smoke
AT="$SB/npm/bin/ai-toolkit"
mkdir -p "$SB/npm" "$SB/evidence"
export SB AT
exec script -q -e -a "$SB/evidence/session.log" -c 'bash --noprofile --norc'
```

Keep HOME at the container user's default. VERSION was passed when the container
was created; SB and the npm prefix are disposable container paths. No command in
Phases 2 through 6 runs in the host shell.

## Phase 2: Provenance

Do this before installing anything: an unsigned publish is a release-blocking
regression, and there is no point smoke-testing a build you would have to redo.

```bash
npm view "@softspark/ai-toolkit@${VERSION}" --json > "$SB/evidence/npm-view.json"
python3 -c "
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8')); att = d['dist'].get('attestations', {})
pt = att.get('provenance', {}).get('predicateType')
assert pt == 'https://slsa.dev/provenance/v1', f'NO PROVENANCE: {pt}'
print('PROVENANCE OK:', att['url'])
" "$SB/evidence/npm-view.json"
```

## Phase 3: Install from npm

```bash
npm install -g --prefix "$SB/npm" "@softspark/ai-toolkit@${VERSION}"
"$AT" --version | tee "$SB/evidence/version.txt"    # must equal VERSION
"$AT" --help >/dev/null && echo "help OK"
```

## Phase 4: Core surfaces

```bash
"$AT" install            # global install inside the container's default HOME
"$AT" doctor             # must end: Errors: 0 | Warnings: 0
"$AT" status
"$AT" plugin list        # pack count must match app/plugins/
```

**A doctor run before `install` reports `agents directory missing` and
`skills directory missing`.** That is the sandbox being empty, not a defect.
Install first, then judge doctor.

## Phase 4b: Skill scripts resolve and run from the installed copy

Discover skills shipping executable scripts from the installed artifact rather
than requiring a historical fixed count. A skill body invokes its helper
through `${CLAUDE_SKILL_DIR}`, which only resolves once the skill is installed —
so presence in the working tree is insufficient. `validate.py` now checks
documented script paths; this phase proves the installed command actually runs.

This is exactly how four skills shipped with `$(dirname "$0")`, which expands to
the shell's directory rather than the skill's. Every one of them had been broken
for as long as the line existed.

Iterate over every skill that ships a script. Do not hand-pick the ones the
release touched — the point of this phase is to catch the ones nobody remembered.

```bash
for D in "$HOME"/.claude/skills/*/; do
  s=$(basename "$D")
  [ -d "$D/scripts" ] || continue
  # Match ANY interpreter and ANY extension. Narrowing this to `python3` and
  # `.py` is how the first version of this phase reported "no invocation" for a
  # skill that used `python`, and missed one that ran a .py file through bash.
  ref=$(grep -ohE '(python3?|bash|sh|node) +\$\{CLAUDE_SKILL_DIR\}/scripts/[A-Za-z0-9_.-]+' "$D/SKILL.md" | head -1)
  [ -n "$ref" ] || { printf '%-22s NO ${CLAUDE_SKILL_DIR} INVOCATION\n' "$s"; continue; }
  interp=${ref%% *}
  rel=${ref##*\$\{CLAUDE_SKILL_DIR\}/}
  printf '%-22s %-10s %-26s ' "$s" "$interp" "$rel"
  [ -f "$D/$rel" ] || { echo 'PATH DOES NOT RESOLVE'; continue; }
  if out=$(CLAUDE_SKILL_DIR="$D" timeout 20 "$interp" "$D/$rel" --help </dev/null 2>&1); then
    rc=0
  else
    rc=$?
  fi
  printf '%s\n' "$out" > "$SB/evidence/skill-$s.log"
  printf 'rc=%s %s\n' "$rc" "$(printf '%s\n' "$out" | head -1 | cut -c1-40)"
done
```

**Verify:**
- [ ] Every skill with a `scripts/` directory has a documented invocation
- [ ] Every documented path resolves to a file that exists
- [ ] Every script exits without a traceback and without hanging
- [ ] The interpreter matches the file: no `.py` through `bash`, no bare `python`

A skill reported as `NO ${CLAUDE_SKILL_DIR} INVOCATION` is not automatically a
defect — some ship assets rather than executables (`write-a-prd` ships `.html`,
`.js` and `.cjs`). Read the skill before filing it. What *is* always a defect is
an invocation that names a skill-owned script through any other path.

`validate.py` now fails the build on that class (`_validate_skill_script_invocations`),
so this phase is the second line rather than the first. Keep it: the validator
reasons about the source, this runs the real thing.

**`</dev/null` and `timeout` are not defensive padding.** Several of these
scripts are stdin filters (`error-parser.py`, `error-classifier.py`) documented
as `command 2>&1 | python3 …`. Probing one with `--help` and an open stdin
blocks forever, and the run looks like a slow test rather than a hung one. A
correct stdin filter answers an empty stdin with a JSON error and `rc=0`; a
traceback there is a real finding.

## Phase 4c: Skills that wrap a scanner actually scan

For any skill whose body tells the model to run a scanner, presence of the script
is not evidence the wiring works. Build a fixture with known defects and confirm
the scanner reports them.

```bash
FX="$SB/fixture"; mkdir -p "$FX"
cat > "$FX/index.html" <<'EOF'
<!DOCTYPE html><html><head><title>t</title></head>
<body><h1>A</h1><h3>skipped h2</h3><img src="x.png"><input type="text"><div onclick="go()">click</div></body></html>
EOF
cat > "$FX/patient.py" <<'EOF'
patient = {"ssn": "123-45-6789", "diagnosis": "fixture"}
endpoint = "http://example.com/patient"
encrypt = False
EOF
printf '{"name":"fx","dependencies":{"lodash":"4.17.20","react":"18"}}\n' > "$FX/package.json"
npm install --package-lock-only --ignore-scripts --prefix "$FX"

D="$HOME/.claude/skills/a11y-validate"
CLAUDE_SKILL_DIR="$D" timeout 60 python3 "$D/scripts/a11y-scanner.py" "$FX" --output json </dev/null
D="$HOME/.claude/skills/seo-validate"
CLAUDE_SKILL_DIR="$D" timeout 60 python3 "$D/scripts/seo-scanner.py" "$FX" --output json </dev/null
D="$HOME/.claude/skills/hipaa-validate"
CLAUDE_SKILL_DIR="$D" timeout 60 python3 "$D/scripts/hipaa_scan.py" "$FX" --output json </dev/null
D="$HOME/.claude/skills/cve-scan"
CLAUDE_SKILL_DIR="$D" timeout 60 python3 "$D/scripts/cve_scan.py" "$FX" --json </dev/null
```

**Verify:**
- [ ] The scanner returns findings, not an empty set — the fixture has real defects
- [ ] Findings span more than one category, proving the whole check set ran
- [ ] A scanner that exits non-zero on findings is doing its job, not failing
- [ ] CVE output has `total_findings > 0`; raw npm advisories with an empty
      normalized `findings` array are a parser failure, not a clean scan

`a11y-validate` and `seo-validate` shipped working scanners that **no step in
either skill invoked** for their entire life before v4.22.0. The model was told to
grep the pattern tables by hand instead. Nothing in the test suite noticed,
because a script nobody calls still passes every check that asks whether it
exists.

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

No pack in the toolkit fetches anything today. Run this phase if one ever does
again, pointing its source-override variable at a dead URL:

```bash
"$AT" plugin remove <pack>
<PACK>_RELEASE_BASE_URL="file:///nonexistent" "$AT" plugin install <pack>
```

**Verify:**
- [ ] Install reports the failure in words a user can act on, and does not claim success
- [ ] No partial artifact is left behind
- [ ] The hook is still wired, and passes commands through untouched
- [ ] `plugin status` says the pack is inert and names the fix
- [ ] Re-installing without the broken source recovers

## Phase 7: Verify the host configuration

Exit the recorded container shell. This returns to the unchanged host terminal
from Phase 1. Run fingerprint_host there, not through docker exec and not in a
shell that changed HOME:

```bash
fingerprint_host > "$EVIDENCE/host-after.json"
cmp -s "$EVIDENCE/host-before.json" "$EVIDENCE/host-after.json" || {
  diff -u "$EVIDENCE/host-before.json" "$EVIDENCE/host-after.json"
  echo "Host configuration changed: investigate before accepting the release."
  exit 1
}
docker inspect "$SMOKE_CONTAINER" > "$EVIDENCE/container-after.json"
```

The fingerprints must match. This proves the enumerated managed settings stayed
unchanged; the recorded container configuration separately proves there were no
host mounts or shared host namespaces. Do not claim to have hashed the whole
home directory, or print settings contents to demonstrate isolation.

## Phase 8: Preserve evidence and remove only the owned container

Run on the host, after leaving the container shell. Confirm ownership before any
cleanup, then copy the recorded session, npm provenance metadata, and CLI version.
Keep the host evidence directory for the release record.

```bash
test "$(docker inspect --format '{{index .Config.Labels "org.softspark.release-smoke"}}' "$SMOKE_CONTAINER")" = "$SMOKE_CONTAINER" || {
  echo "Container ownership does not match; refusing cleanup."
  exit 1
}
docker logs "$SMOKE_CONTAINER" > "$EVIDENCE/container.log" 2>&1
mkdir -p "$EVIDENCE/container"
docker cp "$SMOKE_CONTAINER:/tmp/ai-toolkit-smoke/evidence/." "$EVIDENCE/container/" || {
  echo "Evidence transfer failed; keep the container and investigate."
  exit 1
}
test -f "$EVIDENCE/container/session.log" || {
  echo "Session evidence is missing; refusing cleanup."
  exit 1
}
docker stop "$SMOKE_CONTAINER"
docker rm "$SMOKE_CONTAINER"
printf 'Evidence retained: %s\n' "$EVIDENCE"
```

There are no host bind mounts or named volumes to delete. Never bypass a
destructive-command guard with Python, shutil.rmtree, another interpreter, or a
different deletion tool. If a guard rejects cleanup, leave the owned container
and evidence in place and report the rejection through the normal approval
mechanism. Do not prune Docker resources or delete unrelated temporary files.

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
| Isolation | Host-side managed-settings fingerprints match; container has no host mounts or shared host namespaces |

## Related

- [Release Preparation](sop-release.md) — run before tagging
- [Release Verification](sop-release-verification.md) — cross-editor checks of the isolated npm artifact
- [rtk-pack Retirement](../history/completed/rtk-pack-retirement-20260727.md) — what happened the one time this SOP was written and not run
